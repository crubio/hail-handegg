import pandas as pd

from src.ingestion.cache import load_df, save_df

PLAYER_STATS_URL = "https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats.csv"
SNAP_COUNTS_URL = "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts.csv"
FF_ROSTERS_URL = "https://github.com/nflverse/nflverse-data/releases/download/ff_rosters/ff_rosters.csv"


def fetch_player_stats(ttl_hours: float = 24) -> pd.DataFrame:
    cached = load_df("nflverse_player_stats", ttl_hours)
    if cached is not None:
        return cached
    df = pd.read_csv(PLAYER_STATS_URL, low_memory=False)
    save_df("nflverse_player_stats", df)
    return df


def fetch_snap_counts(ttl_hours: float = 24) -> pd.DataFrame:
    cached = load_df("nflverse_snap_counts", ttl_hours)
    if cached is not None:
        return cached
    df = pd.read_csv(SNAP_COUNTS_URL, low_memory=False)
    save_df("nflverse_snap_counts", df)
    return df


def fetch_rosters(ttl_hours: float = 24) -> pd.DataFrame:
    cached = load_df("nflverse_rosters", ttl_hours)
    if cached is not None:
        return cached
    df = pd.read_csv(FF_ROSTERS_URL, low_memory=False)
    save_df("nflverse_rosters", df)
    return df
