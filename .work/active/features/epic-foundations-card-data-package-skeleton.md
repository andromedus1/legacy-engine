---
id: epic-foundations-card-data-package-skeleton
kind: feature
stage: review
tags: [ingestion]
parent: epic-foundations-card-data
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Package Skeleton, Config & Shared Model Base

## Brief

Stand up the `src/legacy_engine/` package and the project-wide patterns every other feature inherits:
the hatchling `pyproject.toml` (mirroring edh-engine: `src/` layout, `[project.scripts]
legacy-engine = "legacy_engine.cli:main"`, deps), `config.py` (paths, Scryfall URLs/delays, the
DuckDB path, pinned-SHA constants), the Click CLI skeleton (nested command groups +
`_setup_logging(verbose)`), and the shared model foundation — the Pydantic base conventions plus
`ConfidenceMetadata` (`established | evolving | speculative`) ported from edh-engine.

This is the pattern-setting feature: the model idiom, CLI idiom, config idiom, and logging idiom
decided here propagate to ingestion/, archetype/, analytics/, and advisory/. It does NOT implement
Scryfall ingestion, the Card model, the store, or the ban-list — those are sibling features that build
on this skeleton.

## Epic context
- Parent epic: `epic-foundations-card-data`
- Position in epic: **foundation feature** — every other feature in this epic (and project) depends on its package layout, config, CLI shell, and ConfidenceMetadata.

## Inherited design decisions
- **Card model:** typed Pydantic (see sibling `card-model-scryfall`) — so this feature establishes the Pydantic base conventions those models follow.
- **Stack:** mirror edh-engine exactly (hatchling, Click, Pydantic, httpx) + add duckdb/numpy/scipy/statsmodels/pulp in `pyproject.toml` (the advisory deps are declared now even though used later).

## Research briefs
- `docs/ARCHITECTURE.md` — conventions (code org, naming, CLI nested groups, error handling), dependency table.
- `docs/PRINCIPLES.md` — sibling-consistent, divergence-justified; confidence everywhere.

## Foundation references
- `docs/ARCHITECTURE.md` — `cli.py`, `config.py`, `confidence.py`, `models/` conventions.
- edh-engine reference: `/Users/andrewclark/dev/edh-engine/pyproject.toml`, `src/edh_engine/config.py` (32 lines), `src/edh_engine/cli.py`, `src/edh_engine/models/goldfish.py` (ConfidenceMetadata).

## Architectural choice

Mirror edh-engine's `src/`-layout hatchling package, with **one deliberate divergence: standardize all
shared models on Pydantic v2.** edh-engine mixes dataclasses (goldfish) and Pydantic (registry); since
the epic locked a typed Pydantic `Card`, the project uses Pydantic uniformly — `ConfidenceMetadata` is
ported as a Pydantic model, and a `LegacyEngineModel` base sets the shared config (strict validation at
boundaries). Considered alternatives: (a) copy edh-engine's dataclass+Pydantic mix — rejected, two
idioms invites drift; (b) attrs — rejected, no sibling precedent. The CLI is a thin Click skeleton of
nested groups whose leaf commands are stubs that fail loudly (`raise click.ClickException("not
implemented: <cmd>")`) so the command surface is real and discoverable from day one while the
implementations land feature by feature.

## Implementation Units

### Unit 1: Package + build config
**Files**: `pyproject.toml`, `src/legacy_engine/__init__.py`, and `__init__.py` in `models/ ingestion/ archetype/ analytics/ advisory/`
```toml
[project]
name = "legacy-engine"
version = "0.1.0"
description = "Analytics platform for the Magic: The Gathering Legacy format"
requires-python = ">=3.11"
dependencies = [
  "httpx>=0.27", "pydantic>=2.0", "click>=8.0", "matplotlib>=3.8", "pyyaml>=6.0",
  "duckdb>=1.0", "numpy>=1.26", "scipy>=1.11", "statsmodels>=0.14", "pulp>=2.8",
]
[project.scripts]
legacy-engine = "legacy_engine.cli:main"
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[tool.hatch.build.targets.wheel]
packages = ["src/legacy_engine"]
[tool.pytest.ini_options]
testpaths = ["tests"]
```
**Acceptance**: `pip install -e .` succeeds; `import legacy_engine` works; `legacy-engine --help` runs via the entry point.

### Unit 2: `src/legacy_engine/config.py`
**File**: `src/legacy_engine/config.py` (mirror edh-engine's shape)
```python
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCRYFALL_DIR = DATA_DIR / "scryfall"
CACHE_DIR = DATA_DIR / "cache"        # mirrored fbettega tournament JSON
RULES_DIR = DATA_DIR / "rules"        # vendored MTGOFormatData
BANLIST_DIR = DATA_DIR / "banlist"    # dated B&R snapshots
DUCKDB_PATH = DATA_DIR / "legacy.duckdb"
SCRYFALL_API_BASE = "https://api.scryfall.com"
SCRYFALL_BULK_TYPE = "oracle_cards"
SCRYFALL_API_DELAY = 0.1
USER_AGENT = "LegacyEngine/0.1.0"
FBETTEGA_CACHE_REPO = "https://github.com/fbettega/MTG_decklistcache"
MTGOFORMATDATA_REPO = "https://github.com/Badaro/MTGOFormatData"
RULES_PINNED_SHA = ""  # set by `legacy refresh rules`; "" = unpinned (fail-fast in archetype epic)
```
**Acceptance**: all paths are absolute and rooted at the repo; importing config triggers no filesystem writes.

### Unit 3: `src/legacy_engine/confidence.py`
**File**: `src/legacy_engine/confidence.py`
```python
ConfidenceLevel = Literal["established", "evolving", "speculative"]
Production = Literal["hand-written", "template-generated", "template+llm-enriched"]
Source = Literal["user", "llm-synthesis", "heuristic"]

class ConfidenceMetadata(BaseModel):
    level: ConfidenceLevel = "speculative"
    production: Production = "heuristic"  # maps from Source default? keep explicit
    source: Source = "heuristic"
    updated: date | None = None

def tier_for_sample(n: int, *, evolving_min: int = 30, established_min: int = 100) -> ConfidenceLevel:
    """Map a sample size to a confidence tier (advisory-methods §1 thresholds)."""
    if n >= established_min: return "established"
    if n >= evolving_min:    return "evolving"
    return "speculative"
```
**Acceptance**: `tier_for_sample(29)=="speculative"`, `(30)=="evolving"`, `(99)=="evolving"`, `(100)=="established"`; `ConfidenceMetadata()` validates with defaults.

### Unit 4: `src/legacy_engine/models/base.py`
**File**: `src/legacy_engine/models/base.py`
```python
class LegacyEngineModel(BaseModel):
    """Shared base for all project models. Strict at boundaries."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
```
**Implementation note**: `extra="ignore"` (not `forbid`) because Scryfall card JSON carries many fields we don't model; `models/__init__.py` re-exports `LegacyEngineModel`, `ConfidenceMetadata`, `tier_for_sample`.
**Acceptance**: a subclass with declared fields ignores unknown input keys; base importable from `legacy_engine.models`.

### Unit 5: `src/legacy_engine/cli.py`
**File**: `src/legacy_engine/cli.py`
```python
def _setup_logging(verbose: bool) -> None: ...   # mirror edh-engine exactly

@click.group()
def main() -> None:
    """legacy-engine — Magic: The Gathering Legacy analytics."""

@main.group()
def seed() -> None: """Fetch + cache external data."""
@seed.command("cards")
@click.option("-v", "--verbose", is_flag=True)
def seed_cards(verbose): _setup_logging(verbose); _not_implemented("seed cards")
# ... seed cache|rules|banlist; refresh; label;
# report group: meta|matchups|tiers; advise group: positioning|sideboard|whattoplay

def _not_implemented(cmd: str) -> NoReturn:
    raise click.ClickException(f"not implemented: {cmd}")
```
**Acceptance**: `legacy-engine --help` lists `seed`, `refresh`, `label`, `report`, `advise`; `legacy-engine seed --help` lists `cards/cache/rules/banlist`; every leaf stub exits non-zero with "not implemented: <cmd>"; `-v` enables DEBUG logging.

## Implementation Order
1. Unit 1 (package/pyproject) — nothing imports without it.
2. Unit 2 (config) — imported by everything.
3. Unit 3 (confidence) + Unit 4 (models/base) — independent, either order.
4. Unit 5 (cli) — imports config; the entry point that ties it together.

## Testing
pytest, `tests/` mirroring `src/legacy_engine/` layout; deterministic; shared fixtures in `tests/conftest.py` with `_make_X(**kwargs)` factory helpers per `.claude/rules/patterns.md` test-factory-patterns (establishes the project test idiom).
- `tests/test_config.py` — paths absolute + repo-rooted; no import side effects.
- `tests/test_confidence.py` — `tier_for_sample` boundaries (29/30/99/100); `ConfidenceMetadata` default + explicit construction validates; bad `level` rejected.
- `tests/test_models_base.py` — `LegacyEngineModel` subclass ignores extra keys; required fields enforced.
- `tests/test_cli.py` — Click `CliRunner`: `main --help` exit 0 and lists all groups; `seed --help`, `report --help`, `advise --help` list subcommands; a representative leaf stub exits non-zero with the not-implemented message.

## Risks
- **Pydantic-everywhere divergence from edh-engine** — low risk; isolated to model definitions, and consistency outweighs strict parity. **Fallback**: none needed; the base model is trivial to adjust.
- **Declaring advisory deps (scipy/statsmodels/pulp) now** — they go unused until later epics, slightly heavier install. Accepted: avoids churning `pyproject.toml` per epic; **fallback**: move to optional-dependency groups if install weight becomes an issue.

## Implementation notes
- **Files created**: `pyproject.toml`, `.gitignore`, `src/legacy_engine/__init__.py`, `config.py`, `confidence.py`, `cli.py`, `models/{__init__,base}.py`, and `__init__.py` for `ingestion/ archetype/ analytics/ advisory/`.
- **Tests added**: `tests/conftest.py` (factory-fixture idiom), `tests/test_config.py`, `tests/test_confidence.py`, `tests/test_models_base.py`, `tests/test_cli.py` — **35 tests, all passing** (`pytest -q` → 35 passed in 0.03s).
- **Verified**: editable install resolves the full dependency set (incl. duckdb/numpy/scipy/statsmodels/pulp); `legacy-engine --help` lists all 5 command groups via the entry point; every leaf stub exits non-zero with `not implemented: <cmd>`.
- **Discrepancies from design**:
  - Design sketch had `ConfidenceMetadata.production` default `"heuristic"` — invalid (that's a `source` value). Corrected to `production="template-generated"`, `source="heuristic"`.
  - Test factory delivered as a pytest **fixture returning a builder** (`make_confidence`) rather than a bare importable `_make_X` — more robust than cross-importing `conftest`; this is the established test idiom for the project.
  - Added a `[project.optional-dependencies] dev = ["pytest"]` group and a `.gitignore` (venv/pycache/`/data/`) — not in the design, standard hygiene for the pattern-setter.
  - Python 3.13.11 used for the venv (design said `>=3.11`; 3.13 satisfies it).
- **Patterns established for downstream features**: Pydantic-everywhere via `LegacyEngineModel` (`extra="ignore"`); `config.py` constants-only, no side effects; Click nested-group CLI with `_setup_logging` + `_not_implemented` stubs; pytest with factory-fixture builders in `conftest.py`.
- **Adjacent issues parked**: none.
