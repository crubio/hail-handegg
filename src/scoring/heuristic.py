import pandas as pd

from src.features.adp import normalize_adp, score_adp_trend
from src.features.projections import compute_injury_risk, extract_floor_ceiling

# Features that are only meaningful for specific positions.
# Values are multipliers applied to that feature's weight before scoring.
_POSITION_WEIGHT_MASK: dict[str, dict[str, float]] = {
    "QB":  {"wopr": 0.0, "hvt": 0.0, "xfp": 1.5},
    "RB":  {"wopr": 0.2, "hvt": 1.5, "xfp": 1.0},
    "WR":  {"wopr": 1.5, "hvt": 0.1, "xfp": 1.0},
    "TE":  {"wopr": 1.3, "hvt": 0.2, "xfp": 1.0},
    "K":   {"wopr": 0.0, "hvt": 0.0, "xfp": 0.0},
    "DST": {"wopr": 0.0, "hvt": 0.0, "xfp": 0.0},
}


def _normalize(s: pd.Series) -> pd.Series:
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series(0.5, index=s.index)
    return (s - mn) / (mx - mn)


def _clean_name(s: pd.Series) -> pd.Series:
    return s.str.lower().str.replace(r"[^a-z ]", "", regex=True).str.strip()


def build_player_pool(
    stats_df: pd.DataFrame,
    rosters_df: pd.DataFrame,
    adp_df: pd.DataFrame,
    trending_df: pd.DataFrame,
    projections_df: pd.DataFrame,
    total_picks: int,
) -> pd.DataFrame:
    """Merge all data sources into a single player pool DataFrame.

    ID bridging:
      nflverse stats  (player_id = GSIS)
        -> ff_rosters (player_id = GSIS, sleeper_id)
        -> Sleeper ADP (sleeper_id)
        -> ffanalytics (player_id = GSIS preferred, name fallback)
    """
    # --- 1. stats + rosters → add sleeper_id ---
    roster_bridge = rosters_df[["player_id", "sleeper_id"]].drop_duplicates("player_id")
    df = stats_df.merge(roster_bridge, on="player_id", how="left")

    # --- 2. merge ADP ---
    adp_slim = adp_df[["sleeper_id", "adp"]].drop_duplicates("sleeper_id")
    df = df.merge(adp_slim, on="sleeper_id", how="left")

    # name-based ADP fallback for players without a sleeper_id bridge
    missing_adp = df["adp"].isna()
    if missing_adp.any() and "player_name" in adp_df.columns:
        adp_by_name = adp_df.copy()
        adp_by_name["_name"] = _clean_name(adp_by_name["player_name"])
        df["_name"] = _clean_name(df["player_display_name"])
        name_adp = adp_by_name.drop_duplicates("_name").set_index("_name")["adp"]
        df.loc[missing_adp, "adp"] = df.loc[missing_adp, "_name"].map(name_adp)
        df.drop(columns="_name", inplace=True)

    # players with no ADP at all — treat as undrafted (last pick)
    df["adp"] = df["adp"].fillna(total_picks)

    # --- 3. merge projections ---
    proj = extract_floor_ceiling(projections_df)

    if "player_id" in proj.columns:
        proj_slim = proj[["player_id", "proj_pts", "proj_pts_floor", "proj_pts_ceiling"]]
        df = df.merge(proj_slim, on="player_id", how="left")
    else:
        df["proj_pts"] = float("nan")
        df["proj_pts_floor"] = float("nan")
        df["proj_pts_ceiling"] = float("nan")

    # name-based projection fallback
    missing_proj = df["proj_pts"].isna()
    if missing_proj.any() and "player_name" in proj.columns:
        proj_by_name = proj.copy()
        proj_by_name["_name"] = _clean_name(proj_by_name["player_name"])
        df["_name"] = _clean_name(df["player_display_name"])
        for col in ("proj_pts", "proj_pts_floor", "proj_pts_ceiling"):
            name_map = proj_by_name.drop_duplicates("_name").set_index("_name")[col]
            df.loc[missing_proj, col] = df.loc[missing_proj, "_name"].map(name_map)
        df.drop(columns="_name", inplace=True)

    df[["proj_pts", "proj_pts_floor", "proj_pts_ceiling"]] = (
        df[["proj_pts", "proj_pts_floor", "proj_pts_ceiling"]].fillna(0)
    )

    # --- 4. ADP trend score ---
    df["adp_trend"] = score_adp_trend(df, trending_df)

    # --- 5. injury risk multiplier ---
    df["injury_risk"] = compute_injury_risk(df)

    return df


def score_players(df: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Apply weighted heuristic scoring. Returns df sorted by score descending."""
    df = df.copy()
    total_picks = int(df["adp"].max() or 1)

    # Normalize all input features to [0, 1]
    df["_adp_norm"]    = normalize_adp(df["adp"], total_picks)
    df["_proj_norm"]   = _normalize(df["proj_pts"])
    df["_wopr_norm"]   = _normalize(df["wopr_calc"].fillna(0))
    df["_xfp_norm"]    = _normalize(df["xfp"].fillna(0))
    df["_hvt_norm"]    = _normalize(df["hvt"].fillna(0))
    df["_trend_norm"]  = df["adp_trend"]  # already [0, 1]

    feature_map = {
        "adp":       "_adp_norm",
        "projection": "_proj_norm",
        "wopr":      "_wopr_norm",
        "xfp":       "_xfp_norm",
        "hvt":       "_hvt_norm",
        "adp_trend": "_trend_norm",
    }

    scores = pd.Series(0.0, index=df.index)

    for pos, group in df.groupby("position"):
        mask = _POSITION_WEIGHT_MASK.get(pos, {})
        row_idx = group.index
        pos_score = pd.Series(0.0, index=row_idx)

        # Compute adjusted weight total for this position (for re-normalization)
        adjusted = {
            feat: weights.get(feat, 0) * mask.get(feat, 1.0)
            for feat in feature_map
        }
        weight_sum = sum(adjusted.values()) or 1.0

        for feat, col in feature_map.items():
            w = adjusted[feat] / weight_sum
            pos_score += w * df.loc[row_idx, col]

        scores.loc[row_idx] = pos_score

    # Apply injury risk as a final multiplier
    df["score"] = (scores * df["injury_risk"]).round(4)

    # Drop internal columns
    df.drop(columns=[c for c in df.columns if c.startswith("_")], inplace=True)

    return df.sort_values("score", ascending=False).reset_index(drop=True)
