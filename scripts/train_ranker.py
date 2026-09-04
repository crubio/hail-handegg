"""Train LightGBM LambdaRank model on historical nflverse data.

Training pairs: season Y-1 features → season Y PPR fantasy points.
Query groups: one group per season (ranks all players within a draft class).

Usage:
    .venv/bin/python scripts/train_ranker.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.nflverse import fetch_player_stats
from src.features.metrics import aggregate_season, add_metrics
from src.scoring.ranker import FEATURE_COLS, MODEL_PATH

POSITIONS  = {"QB", "RB", "WR", "TE"}
TRAIN_SEASONS = list(range(2018, 2025))  # features from Y-1, labels from Y


def _season_features(stats_raw: pd.DataFrame, season: int) -> pd.DataFrame:
    """Aggregate and compute metrics for one season."""
    try:
        agg = aggregate_season(stats_raw, season)
    except ValueError:
        return pd.DataFrame()
    return add_metrics(agg)


def build_training_data(stats_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[int]]:
    rows = []
    groups = []

    for season in TRAIN_SEASONS:
        feat_df = _season_features(stats_raw, season - 1)
        label_df = _season_features(stats_raw, season)

        if feat_df.empty or label_df.empty:
            print(f"  skipping {season} (no data for {season-1} or {season})")
            continue

        feat_df = feat_df[feat_df["position"].isin(POSITIONS)]
        label_df = label_df[label_df["position"].isin(POSITIONS)]

        merged = feat_df.merge(
            label_df[["player_id", "fantasy_points_ppr"]].rename(
                columns={"fantasy_points_ppr": "label_pts"}
            ),
            on="player_id",
            how="inner",
        )

        if merged.empty:
            continue

        # Relevance label: quartile bin within season (0–3)
        merged["label"] = pd.qcut(
            merged["label_pts"], q=4, labels=[0, 1, 2, 3], duplicates="drop"
        ).astype(int)

        rows.append(merged)
        groups.append(len(merged))
        print(f"  season {season}: {len(merged)} players")

    if not rows:
        raise RuntimeError("No training data could be built.")

    full = pd.concat(rows, ignore_index=True)

    for col in FEATURE_COLS:
        if col not in full.columns:
            full[col] = 0.0

    full["position_enc"] = full["position"].astype("category").cat.codes

    X = full[FEATURE_COLS + ["position_enc"]].fillna(0)
    y = full["label"]

    return X, y, groups


def train(X: pd.DataFrame, y: pd.Series, groups: list[int]) -> lgb.Booster:
    train_data = lgb.Dataset(
        X, label=y, group=groups,
        feature_name=list(X.columns),
    )

    params = {
        "objective":        "lambdarank",
        "metric":           "ndcg",
        "ndcg_eval_at":     [5, 10],
        "learning_rate":    0.05,
        "num_leaves":       31,
        "min_data_in_leaf": 5,
        "verbose":          -1,
    }

    print("\nTraining LightGBM LambdaRank…")
    model = lgb.train(
        params,
        train_data,
        num_boost_round=200,
        valid_sets=[train_data],
        callbacks=[lgb.log_evaluation(50)],
    )
    return model


def main() -> None:
    print("Loading nflverse player stats…")
    stats_raw = fetch_player_stats()

    print("\nBuilding training data…")
    X, y, groups = build_training_data(stats_raw)
    print(f"\nTotal training rows: {len(X)}")

    model = train(X, y, groups)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_PATH))
    print(f"\nModel saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
