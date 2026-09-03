import pandas as pd
import requests

from src.ingestion.cache import load_df, save_df

# ffverse/ffanalytics-data stores season projections as parquet in releases.
# Tag format is typically "YYYY" matching the upcoming season.
BASE_RELEASE_URL = "https://github.com/ffverse/ffanalytics-data/releases/download"


def fetch_consensus_projections(season: int, ttl_hours: float = 12) -> pd.DataFrame:
    cached = load_df(f"ffanalytics_{season}", ttl_hours)
    if cached is not None:
        return cached

    url = f"{BASE_RELEASE_URL}/{season}/projections.parquet"
    resp = requests.get(url, timeout=30, allow_redirects=True)
    resp.raise_for_status()

    import io
    df = pd.read_parquet(io.BytesIO(resp.content))
    save_df(f"ffanalytics_{season}", df)
    return df
