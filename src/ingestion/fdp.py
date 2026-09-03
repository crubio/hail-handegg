import pandas as pd

from src.ingestion.cache import load_df, save_df

BASE_URL = "https://raw.githubusercontent.com/fantasydatapros/data/master/yearly"


def fetch_yearly_stats(year: int, ttl_hours: float = 168) -> pd.DataFrame:
    cached = load_df(f"fdp_{year}", ttl_hours)
    if cached is not None:
        return cached
    df = pd.read_csv(f"{BASE_URL}/{year}.csv")
    df["season"] = year
    save_df(f"fdp_{year}", df)
    return df


def fetch_multi_year(years: list[int], ttl_hours: float = 168) -> pd.DataFrame:
    frames = [fetch_yearly_stats(y, ttl_hours) for y in years]
    return pd.concat(frames, ignore_index=True)
