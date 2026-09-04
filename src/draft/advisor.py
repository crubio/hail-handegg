import pandas as pd

from src.draft.session import DraftSession


def get_recommendations(session: DraftSession, scored_df: pd.DataFrame) -> pd.DataFrame:
    """Return all available players sorted by score descending, with stable rank columns.

    h_rank and ml_rank reflect default-sort position and don't change when the
    caller re-sorts the returned DataFrame for display.
    """
    available = scored_df[~scored_df["player_id"].isin(session.all_drafted_ids())].copy()
    available = available.sort_values("score", ascending=False).reset_index(drop=True)
    available["h_rank"] = available.index + 1
    if "ml_score" in available.columns:
        available["ml_rank"] = (
            available["ml_score"]
            .rank(ascending=False, method="min")
            .astype(int)
        )
    return available
