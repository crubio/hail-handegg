"""Pre-fetch and validate all data sources. Run before launching the TUI."""
import datetime
import sys
import traceback

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from src.ingestion import nflverse, sleeper, fdp

_CURRENT_SEASON = datetime.date.today().year
_PREV_SEASON = _CURRENT_SEASON - 1

# (label, fetch_fn, required)
SOURCES = [
    ("nflverse player_stats",           lambda: nflverse.fetch_player_stats(ttl_hours=0),                    True),
    ("sleeper player map",              lambda: sleeper.fetch_player_map(ttl_hours=0),                       True),
    ("sleeper id bridge",               lambda: sleeper.fetch_id_bridge(ttl_hours=0),                        True),
    ("sleeper ADP",                     lambda: sleeper.fetch_adp(ttl_hours=0),                              True),
    ("sleeper trending adds",           lambda: sleeper.fetch_trending_adds(),                                True),
    (f"fdp yearly stats (≤{_PREV_SEASON})", lambda: fdp.fetch_latest_yearly_stats(_PREV_SEASON, ttl_hours=0), False),
]


def main() -> None:
    print(f"hail-handegg prefetch — season {_CURRENT_SEASON}\n")
    all_required_ok = True

    for name, fetch, required in SOURCES:
        tag = "     " if required else "[opt]"
        print(f"  {tag} {name}... ", end="", flush=True)
        try:
            result = fetch()
            rows = len(result) if hasattr(result, "__len__") else "?"
            print(f"OK ({rows} rows)")
        except Exception as exc:
            label = "FAILED" if required else "WARN (skipped)"
            print(label)
            traceback.print_exc()
            if required:
                all_required_ok = False

    print()
    if all_required_ok:
        print("Required sources OK. Run: .venv/bin/python main.py")
    else:
        print("One or more required sources failed. Fix above errors before launching.")
        sys.exit(1)


if __name__ == "__main__":
    main()
