import datetime
import traceback

import pandas as pd
from textual import work
from textual.app import App
from textual.widgets import Label

from src.config import load_config
from src.draft.session import DraftSession
from src.ingestion import nflverse, sleeper, fdp
from src.features.metrics import aggregate_season, add_metrics
from src.scoring.heuristic import build_player_pool, score_players
from src.scoring.ranker import load_model, rank_players
from tui.screens.draft_board import DraftBoardScreen

_CURRENT_SEASON = datetime.date.today().year


def _build_scored_df(cfg: dict) -> pd.DataFrame:
    total_picks = cfg["league"]["num_teams"] * sum(
        v or 0 for v in cfg["roster_slots"].values()
    )

    stats_raw = nflverse.fetch_player_stats()
    id_bridge = sleeper.fetch_id_bridge()
    adp_df = sleeper.fetch_adp()
    trending_df = sleeper.fetch_trending_adds()

    try:
        projections_df = fdp.normalize_projections(fdp.fetch_latest_yearly_stats(_CURRENT_SEASON - 1))
    except Exception:
        projections_df = pd.DataFrame(columns=["player_name", "position", "proj_pts"])

    stats_df = add_metrics(aggregate_season(stats_raw, _CURRENT_SEASON - 1))

    pool = build_player_pool(stats_df, id_bridge, adp_df, trending_df, projections_df, total_picks)
    return score_players(pool, cfg["weights"])


class HailHandeggApp(App):
    TITLE = "hail-handegg"

    def __init__(self) -> None:
        super().__init__()
        self._cfg: dict = {}

    def on_mount(self) -> None:
        self._cfg = load_config()
        self.mount(Label("Loading player data…", id="loading-label"))
        self._load_data()

    @work(thread=True)
    def _load_data(self) -> None:
        try:
            scored_df = _build_scored_df(self._cfg)
        except Exception as exc:
            tb = traceback.format_exc()
            self.call_from_thread(self._show_error, str(exc), tb)
            return

        model = load_model()
        if model is not None:
            scored_df = rank_players(scored_df, model)

        session = DraftSession(
            draft_position=self._cfg["league"]["draft_position"],
            num_teams=self._cfg["league"]["num_teams"],
            roster_slots=self._cfg["roster_slots"],
            draft_style=self._cfg["league"]["draft_style"],
        )

        self.call_from_thread(self._show_board, session, scored_df)

    def _show_board(self, session: DraftSession, scored_df: pd.DataFrame) -> None:
        self.query_one("#loading-label", Label).remove()
        self.push_screen(DraftBoardScreen(session=session, scored_df=scored_df))

    def _show_error(self, message: str, tb: str = "") -> None:
        from pathlib import Path
        log_path = Path("hail-handegg-error.log")
        log_path.write_text(f"--- hail-handegg pipeline error ---\n{tb}\n")
        self.query_one("#loading-label", Label).update(
            f"[red]Error loading data:[/red] {message}\n\n(full traceback in {log_path.resolve()})"
        )


def run() -> None:
    HailHandeggApp().run()
