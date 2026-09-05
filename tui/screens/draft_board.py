import difflib
from pathlib import Path

import pandas as pd
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.suggester import SuggestFromList
from textual.widgets import DataTable, Footer, Header, Input, Label

from src.config import load_config
from src.draft.advisor import get_recommendations
from src.draft.session import DraftSession

_HEURISTIC_COLS = ("Rank", "Player", "Pos", "Score", "ADP")
_ML_COLS        = ("Rank", "Player", "Pos", "ML Score", "ADP")
_SLOT_ORDER     = ("QB", "RB", "WR", "TE", "FLEX", "K", "DST", "BN", "IR")

_PLACEHOLDER_MINE  = "My pick (player name)…"
_PLACEHOLDER_OTHER = "Off board — other team's pick…"

_HAS_ML_COL = "ml_score"

# Map column label → (df column, default ascending)
# "Rank" is intentionally absent — clicking it resets to default sort.
_H_COL_MAP: dict[str, tuple[str, bool]] = {
    "Player": ("player_display_name", True),
    "Pos":    ("position",            True),
    "Score":  ("score",               False),
    "ADP":    ("adp",                 True),
}
_ML_COL_MAP: dict[str, tuple[str, bool]] = {
    "Player":   ("player_display_name", True),
    "Pos":      ("position",            True),
    "ML Score": ("ml_score",            False),
    "ADP":      ("adp",                 True),
}


def _fuzzy_match(name: str, candidates: list[str]) -> str | None:
    matches = difflib.get_close_matches(name.lower(), [c.lower() for c in candidates], n=1, cutoff=0.6)
    if not matches:
        return None
    idx = [c.lower() for c in candidates].index(matches[0])
    return candidates[idx]


def _render_needs(session: DraftSession) -> str:
    needs = session.roster_needs()
    rnd = session.current_round()
    next_pick = session.next_pick_number()

    parts = [f"[bold]Rd {rnd}  Pick {next_pick}[/bold]  │"]
    for slot in _SLOT_ORDER:
        if slot not in needs:
            continue
        count = needs[slot] or 0
        if count == 0:
            parts.append(f"[dim]{slot} ✓[/dim]")
        else:
            parts.append(f"[bold yellow]{slot} {count}[/bold yellow]")

    return "  ".join(parts)


def _sort_arrow(ascending: bool) -> str:
    return "▲" if ascending else "▼"


class DraftBoardScreen(Screen):
    BINDINGS = [
        ("ctrl+d", "toggle_mode", "Off Board"),
        ("ctrl+z", "undo",        "Undo"),
        ("ctrl+e", "export",      "Export CSV"),
        ("ctrl+q",      "quit",        "Quit"),
    ]

    DEFAULT_CSS = """
    Horizontal {
        height: 1fr;
    }
    #heuristic-table {
        width: 1fr;
        border-right: solid $primary-darken-2;
    }
    #ml-table {
        width: 1fr;
    }
    """

    def __init__(self, session: DraftSession, scored_df: pd.DataFrame) -> None:
        super().__init__()
        self._session = session
        self._scored_df = scored_df
        self._all_names: list[str] = scored_df["player_display_name"].dropna().tolist()
        self._has_ml = _HAS_ML_COL in scored_df.columns
        self._mode: str = "mine"
        self._history: list[dict] = []
        # (df_column, ascending) — None means default sort
        self._h_sort:  tuple[str, bool] | None = None
        self._ml_sort: tuple[str, bool] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield DataTable(id="heuristic-table", cursor_type="row")
            yield DataTable(id="ml-table",        cursor_type="row")
        yield Label("", id="needs-label")
        yield Label("", id="mode-label")
        yield Label("", id="status-label")
        yield Input(
            placeholder=_PLACEHOLDER_MINE,
            id="pick-input",
            suggester=SuggestFromList(self._all_names, case_sensitive=False),
        )
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_tables()
        self._refresh_mode_label()

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def action_toggle_mode(self) -> None:
        self._mode = "other" if self._mode == "mine" else "mine"
        self._refresh_mode_label()

    def action_undo(self) -> None:
        if not self._history:
            self.query_one("#status-label", Label).update("[dim]Nothing to undo.[/dim]")
            return

        last = self._history.pop()
        if last["type"] == "mine":
            self._session.undo_last_pick(last["player_id"])
            self.query_one("#status-label", Label).update(
                f"[yellow]Undid pick: {last['name']}[/yellow]"
            )
        else:
            self._session.undo_mark_drafted(last["player_id"])
            self.query_one("#status-label", Label).update(
                f"[yellow]Undid off board: {last['name']}[/yellow]"
            )

        self._refresh_tables()

    def action_export(self) -> None:
        out_dir = Path(load_config()["data"]["cache_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)

        roster_path = out_dir / "hail-handegg-roster.csv"
        roster_rows = []
        for i, pick in enumerate(self._session.my_roster, start=1):
            rnd = ((i - 1) // self._session.num_teams) + 1
            roster_rows.append({
                "Round":  rnd,
                "Pick":   i,
                "Player": pick["name"],
                "Pos":    pick["position"],
                "Team":   pick.get("team", ""),
                "Score":  pick.get("score", ""),
            })
        pd.DataFrame(roster_rows).to_csv(roster_path, index=False)

        ref_path = out_dir / "hail-handegg-rankings.csv"
        drafted = self._session.all_drafted_ids()
        pool = self._scored_df[~self._scored_df["player_id"].isin(drafted)].copy()

        h_ranked = (
            pool.sort_values("score", ascending=False)
            .reset_index(drop=True)
        )
        h_ranked["Heuristic Rank"] = h_ranked.index + 1

        ref_cols = {
            "Heuristic Rank":      "Heuristic Rank",
            "player_display_name": "Player",
            "position":            "Pos",
            "recent_team":         "Team",
            "adp":                 "ADP",
            "proj_pts":            "Proj Pts",
            "score":               "Heuristic Score",
        }

        if self._has_ml:
            ml_rank_map = dict(zip(
                pool.sort_values("ml_score", ascending=False)["player_id"],
                range(1, len(pool) + 1),
            ))
            h_ranked["ML Rank"] = h_ranked["player_id"].map(ml_rank_map)
            ref_cols["ML Rank"]  = "ML Rank"
            ref_cols["ml_score"] = "ML Score"

        ref_df = h_ranked.rename(columns=ref_cols)[list(ref_cols.values())]
        ref_df.to_csv(ref_path, index=False)

        self.query_one("#status-label", Label).update(
            f"[green]Exported → {roster_path.name}  |  {ref_path.name}[/green]"
        )

    # ------------------------------------------------------------------ #
    # Sorting
    # ------------------------------------------------------------------ #

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        table_id = event.data_table.id
        label    = str(event.label)

        if table_id == "heuristic-table":
            col_map = _H_COL_MAP
            current = self._h_sort
        else:
            col_map = _ML_COL_MAP
            current = self._ml_sort

        if label not in col_map:
            # "Rank" or unknown — reset to default
            new_sort = None
        else:
            df_col, default_asc = col_map[label]
            if current and current[0] == df_col:
                new_sort = (df_col, not current[1])   # toggle direction
            else:
                new_sort = (df_col, default_asc)      # first click: default dir

        if table_id == "heuristic-table":
            self._h_sort = new_sort
        else:
            self._ml_sort = new_sort

        self._refresh_tables()

    # ------------------------------------------------------------------ #
    # Pick handling
    # ------------------------------------------------------------------ #

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "ml-table" and not self._has_ml:
            return
        row = event.data_table.get_row(event.row_key)
        self._process_pick(str(row[1]))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        if not raw:
            return
        matched = _fuzzy_match(raw, self._all_names)
        if matched is None:
            self.query_one("#status-label", Label).update(
                f"[red]No match found for '{raw}'[/red]"
            )
            return
        event.input.clear()
        self._process_pick(matched)

    def _process_pick(self, name: str) -> None:
        status = self.query_one("#status-label", Label)

        matches = self._scored_df[
            self._scored_df["player_display_name"].str.lower() == name.lower()
        ]
        if matches.empty:
            status.update(f"[red]Player not found: '{name}'[/red]")
            return
        if len(matches) > 1:
            status.update(f"[yellow]Multiple players named '{name}' — picking first match[/yellow]")

        player = matches.iloc[0]

        if self._mode == "other":
            self._session.mark_drafted(player["player_id"])
            self._history.append({"type": "other", "player_id": player["player_id"], "name": name})
            status.update(f"[dim]Off board: {name}[/dim]")
        else:
            self._session.add_pick({
                "player_id": player["player_id"],
                "name":      name,
                "position":  player["position"],
                "team":      player.get("recent_team", ""),
                "score":     player["score"],
            })
            self._history.append({"type": "mine", "player_id": player["player_id"], "name": name})
            status.update(f"[green]Picked: {name}[/green]")

        self._mode = "mine"
        self._refresh_mode_label()
        self._refresh_tables()

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #

    def _refresh_mode_label(self) -> None:
        label = self.query_one("#mode-label", Label)
        inp   = self.query_one("#pick-input", Input)
        if self._mode == "other":
            label.update("[bold red]● OFF BOARD MODE[/bold red]  (ctrl+d to switch back)")
            inp.placeholder = _PLACEHOLDER_OTHER
        else:
            label.update("[bold green]● MY PICK MODE[/bold green]  (ctrl+d to mark off board)")
            inp.placeholder = _PLACEHOLDER_MINE

    def _apply_sort(
        self,
        df: pd.DataFrame,
        sort: tuple[str, bool] | None,
        default_col: str,
    ) -> pd.DataFrame:
        if sort is None:
            return df.sort_values(default_col, ascending=False).reset_index(drop=True)
        col, asc = sort
        if col not in df.columns:
            return df.sort_values(default_col, ascending=False).reset_index(drop=True)
        return df.sort_values(col, ascending=asc).reset_index(drop=True)

    def _col_labels(self, default_cols: tuple, col_map: dict, sort: tuple[str, bool] | None) -> list[str]:
        active_df_col, active_asc = sort if sort else (None, None)
        labels = []
        for label in default_cols:
            df_col = col_map.get(label, (None,))[0]
            if df_col and df_col == active_df_col:
                labels.append(f"{label} {_sort_arrow(active_asc)}")
            else:
                labels.append(label)
        return labels

    def _refresh_tables(self) -> None:
        recs = get_recommendations(self._session, self._scored_df)

        # --- heuristic table ---
        h_table = self.query_one("#heuristic-table", DataTable)
        h_table.clear(columns=True)
        h_table.add_columns(*self._col_labels(_HEURISTIC_COLS, _H_COL_MAP, self._h_sort))
        h_sorted = self._apply_sort(recs, self._h_sort, "score")
        for _, row in h_sorted.iterrows():
            h_table.add_row(
                str(int(row["h_rank"])),
                row.get("player_display_name", ""),
                row.get("position", ""),
                f"{row['score']:.4f}",
                f"{row.get('adp', 0):.1f}",
            )

        # --- ML table ---
        ml_table = self.query_one("#ml-table", DataTable)
        ml_table.clear(columns=True)
        if self._has_ml:
            ml_table.add_columns(*self._col_labels(_ML_COLS, _ML_COL_MAP, self._ml_sort))
            ml_sorted = self._apply_sort(recs, self._ml_sort, "ml_score")
            for _, row in ml_sorted.iterrows():
                ml_table.add_row(
                    str(int(row["ml_rank"])),
                    row.get("player_display_name", ""),
                    row.get("position", ""),
                    f"{row['ml_score']:.4f}",
                    f"{row.get('adp', 0):.1f}",
                )
        else:
            ml_table.add_columns("ML Ranking")
            ml_table.add_row("Run scripts/train_ranker.py to enable ML ranking")

        self.query_one("#needs-label", Label).update(_render_needs(self._session))

        needs = self._session.roster_needs()
        if all(v == 0 for k, v in needs.items() if k != "IR"):
            self.query_one("#status-label", Label).update(
                "[bold green]Draft complete![/bold green]  "
                "Press [bold]ctrl+e[/bold] to export your roster.  "
                "(You can still pick to explore.)"
            )
