from pathlib import Path

import pandas as pd

try:
    import lightgbm as lgb
    _HAS_LGB = True
except ImportError:
    _HAS_LGB = False

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "ranker.lgb"

# Features available at draft time, derived from the previous season
FEATURE_COLS = [
    "wopr_calc",
    "xfp",
    "hvt",
    "games_played",
    "injury_risk",
    "target_share",
    "air_yards_share",
    "carries",
    "receptions",
    "proj_pts",
]


def load_model():
    """Return a loaded LightGBM Booster or None if unavailable."""
    if not _HAS_LGB or not MODEL_PATH.exists():
        return None
    return lgb.Booster(model_file=str(MODEL_PATH))


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    feat = df.copy()
    for col in FEATURE_COLS:
        if col not in feat.columns:
            feat[col] = 0.0
    feat["position_enc"] = feat["position"].astype("category").cat.codes
    return feat[FEATURE_COLS + ["position_enc"]].fillna(0)


def rank_players(df: pd.DataFrame, model) -> pd.DataFrame:
    """Add ml_score column and return df sorted by it descending."""
    X = build_feature_matrix(df)
    scores = model.predict(X)
    result = df.copy()
    result["ml_score"] = scores
    return result.sort_values("ml_score", ascending=False).reset_index(drop=True)
