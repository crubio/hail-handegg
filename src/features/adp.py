import pandas as pd


def normalize_adp(adp: pd.Series, total_picks: int) -> pd.Series:
    """Invert and min-max normalize ADP so pick 1 → 1.0, last pick → 0.0.
    Players with no ADP (undrafted) get 0.0."""
    adp = adp.clip(upper=total_picks).fillna(total_picks)
    denom = max(total_picks - 1, 1)
    return 1.0 - ((adp - 1) / denom)


def score_adp_trend(adp_df: pd.DataFrame, trending_df: pd.DataFrame) -> pd.Series:
    """Assign a trend bonus (0.0–1.0) based on Sleeper trending adds.
    Players in the trending list get a scaled score by their rank in it;
    everyone else gets 0.0."""
    if trending_df.empty or "player_id" not in trending_df.columns:
        return pd.Series(0.0, index=adp_df.index)

    n = len(trending_df)
    trend_score = {
        row["player_id"]: 1.0 - (i / n)
        for i, row in trending_df.reset_index(drop=True).iterrows()
    }
    return adp_df["sleeper_id"].map(trend_score).fillna(0.0)
