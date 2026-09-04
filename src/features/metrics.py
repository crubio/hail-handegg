import pandas as pd

REGULAR_SEASON = "REG"
GAMES_IN_SEASON = 17


def aggregate_season(df: pd.DataFrame, season: int) -> pd.DataFrame:
    """Collapse weekly nflverse player_stats to one row per player for a given season.

    If the requested season has no REG data, falls back to the most recent season
    that does. Handles optional columns (e.g. expected_fantasy_points) gracefully.
    """
    reg = df[df["season_type"] == REGULAR_SEASON]

    filtered = reg[reg["season"] == season]
    if filtered.empty:
        available = sorted(reg["season"].dropna().unique(), reverse=True)
        if not available:
            raise ValueError("nflverse player_stats contains no regular-season data")
        season = int(available[0])
        filtered = reg[reg["season"] == season]

    filtered = filtered.copy()

    agg_spec: dict = {
        "games_played": ("week", "count"),
        "carries": ("carries", "sum"),
        "rushing_yards": ("rushing_yards", "sum"),
        "rushing_tds": ("rushing_tds", "sum"),
        "receptions": ("receptions", "sum"),
        "targets": ("targets", "sum"),
        "receiving_yards": ("receiving_yards", "sum"),
        "receiving_tds": ("receiving_tds", "sum"),
        "fantasy_points_ppr": ("fantasy_points_ppr", "sum"),
        "target_share": ("target_share", "mean"),
        "air_yards_share": ("air_yards_share", "mean"),
        "wopr": ("wopr", "mean"),
    }

    if "expected_fantasy_points" in filtered.columns:
        agg_spec["expected_fantasy_points"] = ("expected_fantasy_points", "sum")

    agg = filtered.groupby(
        ["player_id", "player_display_name", "position", "recent_team"]
    ).agg(**agg_spec).reset_index()

    if "expected_fantasy_points" not in agg.columns:
        agg["expected_fantasy_points"] = 0.0

    agg["season"] = season
    return agg


def compute_wopr(df: pd.DataFrame) -> pd.Series:
    """Weighted Opportunity Rating. Uses nflverse pre-computed value if present."""
    if "wopr" in df.columns and df["wopr"].notna().any():
        return df["wopr"].fillna(0)
    return (1.5 * df["target_share"].fillna(0)) + (0.7 * df["air_yards_share"].fillna(0))


def compute_xfp(df: pd.DataFrame) -> pd.Series:
    """Seasonal expected fantasy points from nflverse. Falls back to 0 if absent."""
    if "expected_fantasy_points" in df.columns:
        return df["expected_fantasy_points"].fillna(0)
    return pd.Series(0.0, index=df.index)


def compute_hvt(df: pd.DataFrame) -> pd.Series:
    """High-Value Touches: rushing TDs + targets (proxy for red zone involvement).
    True inside-10 carries require play-by-play; this is the best weekly-stats approximation."""
    return df["rushing_tds"].fillna(0) + df["targets"].fillna(0)


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add all computed metric columns to an aggregated seasonal DataFrame."""
    df = df.copy()
    df["wopr_calc"] = compute_wopr(df)
    df["xfp"] = compute_xfp(df)
    df["hvt"] = compute_hvt(df)
    return df
