import pandas as pd


def compute_adp_trend(adp_history: pd.DataFrame, window_days: int = 7) -> pd.Series:
    # ADP delta over rolling window — positive means rising stock
    # TODO: implement
    raise NotImplementedError


def normalize_adp(adp: pd.Series, max_pick: int) -> pd.Series:
    # Invert and normalize so pick 1 → 1.0, last pick → 0.0
    # TODO: implement
    raise NotImplementedError
