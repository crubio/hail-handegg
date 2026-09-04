import pandas as pd

GAMES_IN_SEASON = 17


def extract_floor_ceiling(projections: pd.DataFrame) -> pd.DataFrame:
    """Extract floor and ceiling from a consensus projections DataFrame.
    player_id is optional — build_player_pool falls back to name matching when absent.
    Falls back to ±15% of consensus if explicit floor/ceiling are absent."""
    df = projections.copy()

    if "proj_pts" not in df.columns:
        df["proj_pts"] = 0.0
    if "proj_pts_floor" not in df.columns:
        df["proj_pts_floor"] = df["proj_pts"] * 0.85
    if "proj_pts_ceiling" not in df.columns:
        df["proj_pts_ceiling"] = df["proj_pts"] * 1.15

    cols = ["player_name", "position", "proj_pts", "proj_pts_floor", "proj_pts_ceiling"]
    if "player_id" in df.columns:
        cols = ["player_id"] + cols

    return df[[c for c in cols if c in df.columns]]


def compute_injury_risk(stats_df: pd.DataFrame) -> pd.Series:
    """Games-played multiplier (0.0–1.0) derived from the aggregated stats DataFrame.
    A player who played 17/17 games → 1.0; 8/17 → ~0.47.
    Index aligns with stats_df."""
    return (stats_df["games_played"] / GAMES_IN_SEASON).clip(upper=1.0)
