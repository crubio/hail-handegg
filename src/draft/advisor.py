import pandas as pd

from src.draft.session import DraftSession


def get_recommendations(session: DraftSession, scored_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    # Returns top_n available players ranked by score, weighted toward roster needs
    # TODO: implement
    raise NotImplementedError
