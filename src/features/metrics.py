import pandas as pd


def compute_wopr(df: pd.DataFrame) -> pd.Series:
    # Weighted Opportunity Rating: 1.5 * target_share + 0.7 * air_yards_share
    # TODO: implement
    raise NotImplementedError


def compute_xfp(df: pd.DataFrame) -> pd.Series:
    # Expected Fantasy Points based on opportunity quality
    # TODO: implement
    raise NotImplementedError


def compute_hvt(df: pd.DataFrame) -> pd.Series:
    # High-Value Touches: RB targets + carries inside the 10-yard line
    # TODO: implement
    raise NotImplementedError
