import requests
import pandas as pd

from src.ingestion.cache import load_df, load_json, save_df, save_json

BASE_URL = "https://api.sleeper.app/v1"

RELEVANT_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF"}


def fetch_player_map(ttl_hours: float = 6) -> dict:
    cached = load_json("sleeper_player_map", ttl_hours)
    if cached is not None:
        return cached
    resp = requests.get(f"{BASE_URL}/players/nfl", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    save_json("sleeper_player_map", data)
    return data


def fetch_trending_adds(lookback_hours: int = 24, limit: int = 25) -> pd.DataFrame:
    url = f"{BASE_URL}/players/nfl/trending/add?lookback_hours={lookback_hours}&limit={limit}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return pd.DataFrame(resp.json())


def fetch_adp(ttl_hours: float = 6) -> pd.DataFrame:
    # Sleeper has no public ADP REST endpoint; search_rank from the player map
    # is their internal draft-order proxy and correlates well with ADP.
    cached = load_df("sleeper_adp", ttl_hours)
    if cached is not None:
        return cached

    player_map = fetch_player_map(ttl_hours)
    rows = [
        {
            "sleeper_id": pid,
            "player_name": p.get("full_name", ""),
            "position": p.get("position", ""),
            "team": p.get("team", ""),
            "adp": p.get("search_rank", 9999),
        }
        for pid, p in player_map.items()
        if p.get("active") and p.get("position") in RELEVANT_POSITIONS
    ]
    df = pd.DataFrame(rows).sort_values("adp").reset_index(drop=True)
    save_df("sleeper_adp", df)
    return df
