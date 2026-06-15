---
id: epic-archetype-classifier-rules-loader
kind: feature
stage: done
tags: [archetype]
parent: epic-archetype-classifier
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-05-29
updated: 2026-06-14
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

## Implementation Units
### Unit 1: `src/legacy_engine/archetype/rules.py`
`KNOWN_CONDITION_TYPES` (the 12), `Condition{type:Type, cards:Cards}`, `ArchetypeRule{name, include_color_in_name, conditions, variants:[ArchetypeRule]}`, `Fallback{name, include_color_in_name, common_cards:CommonCards}`, `RuleSet{archetypes, fallbacks, color_overrides}`. `load_ruleset(rules_dir) -> RuleSet` reads `Formats/Legacy/Archetypes/*.json` + `Fallbacks/*.json` + optional `color_overrides.json`. **Fail-fast**: an unknown condition `Type` raises `UnknownConditionTypeError(type, file)` at load.
### Unit 2: `src/legacy_engine/ingestion/rules_vendor.py`
`refresh_rules(repo=MTGOFORMATDATA_REPO, dest=RULES_DIR, runner=subprocess.run)` — clone/pull, then write `RULES_MANIFEST.json` with the resolved commit SHA (runner injected for tests). Wire `seed rules` CLI.
**Acceptance**: loads a fixture ruleset (Delver archetype w/ a variant + a fallback); unknown condition type raises; `refresh_rules` clone-vs-pull branch via fake runner; `seed rules` reports the pinned SHA.

## Testing
- `tests/test_rules_loader.py` — load a fixture `Formats/Legacy/` tree; assert archetypes/variants/fallbacks parsed + all 12 condition types accepted; unknown Type raises `UnknownConditionTypeError`.
- `tests/test_rules_vendor.py` — `refresh_rules` clone/pull branch with a fake runner + manifest written (no real git).

## Implementation notes
- **Files created**: `src/legacy_engine/archetype/rules.py` (KNOWN_CONDITION_TYPES ×12, Condition/ArchetypeRule/Fallback/RuleSet, `load_ruleset`, `UnknownConditionTypeError`), `src/legacy_engine/ingestion/rules_vendor.py` (`refresh_rules` w/ injected runner, manifest + `pinned_sha`); wired `seed rules` CLI.
- **Tests added**: `tests/test_rules_loader.py`, `tests/test_rules_vendor.py` — full suite **112 passing in 0.65s**.
- **Discrepancies from design**: none. Fail-fast validates condition Types recursively (archetype + variants).
- **Robustness fix**: `refresh_rules` now `mkdir`s dest before writing the manifest (git clone normally creates it; robust regardless) — surfaced by the fake-runner test.
- **Test debt fixed**: removed `seed rules` from `test_cli`'s not-implemented list (now wired).
- **Adjacent issues parked**: none.

## Review (2026-05-29)
**Verdict**: Approve. **Blockers/Important**: none.
**Nits**: `_resolve_sha` swallows all exceptions to return "" — fine for the best-effort SHA (a real failed `git rev-parse` shouldn't crash vendoring), but broad; acceptable. Color-overrides kept as a raw dict (the matcher's color step already uses foundations' `compute_deck_colors`, so overrides are reference-only for now).
**Notes**: Fail-fast on unknown condition Type verified (archetype + variant); 12 types recognized; vendoring isolated behind an injected runner. 112 tests green. Unblocks matcher.
