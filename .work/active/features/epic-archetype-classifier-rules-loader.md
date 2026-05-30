---
id: epic-archetype-classifier-rules-loader
kind: feature
stage: drafting
tags: [archetype]
parent: epic-archetype-classifier
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Rules Vendoring + Typed Rule Loader

## Brief
Vendor Badaro's MTGOFormatData `Formats/Legacy/` rules as a pinned, versioned data dependency and load
them into typed Pydantic rule objects. Covers the `legacy refresh rules` CLI (git-fetch the repo into
`data/rules/`, record the commit SHA in `RULES_MANIFEST.json` / `config.RULES_PINNED_SHA`, behind an
injected runner so tests don't clone), and the rule loader: `ArchetypeRule`, `Condition` (12 `Type`
values), `Variant`, `Fallback`, plus the `color_overrides`. **Fail-fast on an unknown condition `Type`**
at load time (mirrors the foundation's fail-fast-on-unknown-role). Does NOT implement the matching
algorithm (matcher) or labeling (labeler).

## Epic context
- Parent epic: `epic-archetype-classifier`. Foundation feature — produces the typed ruleset the matcher consumes.

## Inherited design decisions
- **Rules vendoring**: pin a commit SHA in a manifest; `legacy refresh rules` pulls + diffs; unknown condition Type fails fast at load.
- Pydantic-everywhere via `LegacyEngineModel`; constants-only config (rules paths already in config).

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/mtgoformatdata-rule-schema.md` — the rule-as-data schema (Name, IncludeColorInName, Conditions, Variants, Fallbacks, color_overrides; 12 condition types; ~174 Legacy archetypes + 8 fallbacks).
- `docs/briefs/ingestion-archetype-contracts/csharp-python-port-strategy.md` — vendoring mechanism (subtree @ SHA, manifest, refresh CLI, fail-fast drift).

## Foundation references
- `docs/ARCHITECTURE.md` — `archetype/rules.py`, `ingestion/rules_vendor.py`; `config.RULES_DIR`, `MTGOFORMATDATA_REPO`, `RULES_PINNED_SHA`.
