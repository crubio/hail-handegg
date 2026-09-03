import pandas as pd


BASE_URL = "https://api.sleeper.app/v1"


def fetch_player_map() -> dict:
    # TODO: implement — cache result locally, this payload is large
    raise NotImplementedError


def fetch_trending_adds(lookback_hours: int = 24, limit: int = 25) -> pd.DataFrame:
    # TODO: implement
    raise NotImplementedError


def fetch_adp() -> pd.DataFrame:
    # TODO: implement
    raise NotImplementedError
