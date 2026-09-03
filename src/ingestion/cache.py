import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.config import load_config


def _cache_dir() -> Path:
    return Path(load_config()["data"]["cache_dir"])


def _path(name: str, ext: str) -> Path:
    return _cache_dir() / f"{name}.{ext}"


def _is_fresh(path: Path, ttl_hours: float) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(hours=ttl_hours)


def load_df(name: str, ttl_hours: float) -> pd.DataFrame | None:
    path = _path(name, "parquet")
    if _is_fresh(path, ttl_hours):
        return pd.read_parquet(path)
    return None


def save_df(name: str, df: pd.DataFrame) -> None:
    path = _path(name, "parquet")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def load_json(name: str, ttl_hours: float) -> dict | None:
    path = _path(name, "json")
    if _is_fresh(path, ttl_hours):
        with open(path) as f:
            return json.load(f)
    return None


def save_json(name: str, data: dict) -> None:
    path = _path(name, "json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)
