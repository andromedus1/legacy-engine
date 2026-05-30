---
id: epic-foundations-card-data-package-skeleton
kind: feature
stage: drafting
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
