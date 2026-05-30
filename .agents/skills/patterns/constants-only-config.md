---
description: How config works in legacy-engine — a constants-only module with zero import side effects. Read before adding a path, URL, or tunable.
type: pattern
kind: planning
updated: 2026-05-29
summary: |
  src/legacy_engine/config.py holds paths, URLs, and constants only. Importing it must never touch the
  filesystem or network; directories are created by the code that writes into them. Paths root at
  PROJECT_ROOT.
decisions:
  - "config.py is module-level constants only — no functions with side effects, no mkdir, no I/O on import."
  - "All paths derive from PROJECT_ROOT = Path(__file__).parent.parent.parent."
  - "New external sources/tunables go here as named constants, not scattered literals."
---

# Pattern: Constants-Only Config

`src/legacy_engine/config.py` is the single home for paths, external URLs, and tunables — and importing
it has **zero side effects**.

## Rationale
Importing config happens everywhere; it must be free and safe (no filesystem writes, no network). The
module writing data owns directory creation (`SCRYFALL_DIR.mkdir(...)` at write time), not config. A
single source of truth for paths/URLs keeps reproducibility honest and makes the data layout obvious.

## Example (canonical)
**File**: `src/legacy_engine/config.py`
```python
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCRYFALL_DIR = DATA_DIR / "scryfall"
DUCKDB_PATH = DATA_DIR / "legacy.duckdb"
SCRYFALL_API_BASE = "https://api.scryfall.com"
SCRYFALL_API_DELAY = 0.1
USER_AGENT = "LegacyEngine/0.1.0"
RULES_PINNED_SHA = ""  # set by `legacy refresh rules`
```
Enforced by test (`tests/test_config.py`): paths are absolute and repo-rooted; import creates nothing.

## When to use
- Any new path, external URL, rate-limit delay, pinned SHA, or pipeline default.

## When NOT to use
- Per-run/user values (CLI options or env vars belong at the call site, not as module constants —
  except secrets-free env reads like an optional API key, mirroring edh-engine's `os.environ.get`).

## Common violations
- Calling `.mkdir()`, opening files, or fetching URLs at module top level.
- Hard-coding a path/URL inline in a module instead of importing the constant from config.
