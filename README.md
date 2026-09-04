# Project hail-handegg

Terminal-based fantasy football draft assistant. Ranks players in real time using a heuristic scorer and a LightGBM LambdaRank model, side by side.

---

## Setup

**With uv (recommended):**
```bash
uv sync
uv pip install -e .
```

**With pip:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Running

```bash
# uv
uv run hail-handegg

# Make
make run

# Direct entry point (after install)
hail-handegg
```

**First run:** fetch and cache all data sources before launching:

```bash
make prefetch
```

**Train the ML model** (required once before the ML ranking column populates):

```bash
make train
```

---

## Features

- **Dual ranking**: heuristic scorer (ADP, projections, WOPR, xFP, HVT, ADP trend) and LightGBM LambdaRank side by side
- **Live board**: window of 50 available players, tables are refreshed on every pick
- **Tab completion**  player name type-ahead assist; ghost-text suggestion accepts on Tab or →
- **Row selection**  navigate with arrow keys, press Enter to pick from either table
- **My pick / Off board**  `ctrl+d` toggles mode; off-board picks remove the player from both tables without affecting your roster to track other team picks.
- **Undo**  `ctrl+z` undo functionality (for roster & off-board picks)
- **Roster needs panel**  tracks remaining open slots with FLEX/BN logic; snake draft only
- **Column sorting**  click any column header to sort; click again to toggle direction; click Rank to reset
- **CSV export**  `ctrl+e` writes your current roster and a top-300 reference sheet (with both rankings) to `data/raw/`

---

## Config

Edit `config/league.yaml` before your draft:

```yaml
league:
  num_teams: 10          # number of teams in your league
  draft_position: 2      # your pick position (1-indexed)
  draft_style: snake

roster_slots:
  QB: 1
  RB: 2
  WR: 2
  TE: 1
  FLEX: 1
  K: 1
  DST: 1
  BN: 6
  IR:

weights:                 # heuristic scorer weights (must sum to 1.0)
  adp: 0.30
  projection: 0.30
  wopr: 0.15
  xfp: 0.10
  hvt: 0.10
  adp_trend: 0.05
```

---

## Key bindings

| Key | Action |
|---|---|
| `ctrl+d` | Toggle My Pick / Off Board mode |
| `ctrl+z` | Undo last action |
| `ctrl+e` | Export CSV (roster + top 300) |
| `ctrl+q` | Quit |
| `↑ / ↓` | Navigate table rows |
| `Enter` | Select highlighted row |
| `Tab / →` | Accept tab-completion suggestion |
