import pandas as pd

from src.ingestion.cache import load_df, save_df

BASE_URL = "https://raw.githubusercontent.com/fantasydatapros/data/master/yearly"

# Map of possible fdp column names → our standard schema
_COL_MAP = {
    "Player":         "player_name",
    "Pos":            "position",
    "FantasyPoints":  "proj_pts",
    "PPR":            "proj_pts",
    "FantPt":         "proj_pts",
    "FPTS":           "proj_pts",
}


def fetch_yearly_stats(year: int, ttl_hours: float = 168) -> pd.DataFrame:
    cached = load_df(f"fdp_{year}", ttl_hours)
    if cached is not None:
        return cached
    import requests
    resp = requests.get(f"{BASE_URL}/{year}.csv", timeout=15)
    resp.raise_for_status()
    import io
    df = pd.read_csv(io.StringIO(resp.text))
    df["season"] = year
    save_df(f"fdp_{year}", df)
    return df


def fetch_latest_yearly_stats(from_year: int, ttl_hours: float = 168) -> pd.DataFrame:
    """Try years in descending order from from_year until one is available."""
    for year in range(from_year, from_year - 5, -1):
        try:
            return fetch_yearly_stats(year, ttl_hours)
        except Exception:
            continue
    raise RuntimeError(f"No fdp yearly stats found for {from_year} through {from_year - 4}")


def fetch_multi_year(years: list[int], ttl_hours: float = 168) -> pd.DataFrame:
    frames = [fetch_yearly_stats(y, ttl_hours) for y in years]
    return pd.concat(frames, ignore_index=True)


def normalize_projections(df: pd.DataFrame) -> pd.DataFrame:
    """Rename fdp columns to the standard projections schema.
    Returns a DataFrame with at minimum player_name, position, proj_pts.
    player_id is left absent — build_player_pool will fall back to name matching."""
    df = df.rename(columns={k: v for k, v in _COL_MAP.items() if k in df.columns})
    # If multiple source cols mapped to proj_pts, keep first non-null
    if "proj_pts" not in df.columns:
        df["proj_pts"] = 0.0
    return df
