import pandas as pd

from src.draft.session import DraftSession


def get_recommendations(session: DraftSession, scored_df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Return top_n players ranked by score, excluding players already on the user's roster."""
    available = scored_df[~scored_df["player_id"].isin(session.my_roster)].copy()
    return available.sort_values("score", ascending=False).head(top_n).reset_index(drop=True)
