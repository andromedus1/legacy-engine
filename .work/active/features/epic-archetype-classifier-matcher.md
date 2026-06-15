---
id: epic-archetype-classifier-matcher
kind: feature
stage: done
tags: [archetype]
parent: epic-archetype-classifier
depends_on: [epic-archetype-classifier-rules-loader]
release_binding: v0.1.0
gate_origin: null
created: 2026-05-29
updated: 2026-06-14
---

# Matcher Port + Golden Tests (fixtures)

## Brief
Reimplement Badaro's `ArchetypeAnalyzer.Detect` in Python: `classify(mainboard, sideboard, ruleset,
deck_colors) -> ArchetypeResult`. AND-test every archetype's conditions (short-circuit on first
failure), collect ALL matches, nest variant tests inside a matched parent, emit a `Conflict(A,B)`
label when >1 specific archetype matches (no default tie-break), fall back to the most-card-overlap
fallback pile (≥10% similarity floor) else `Unknown`. Card-name matching is exact, case-sensitive.
Colors come from the existing `compute_deck_colors` (foundations). **Conflict/Unknown are stored raw**
(faithful to the C# engine; analytics buckets them). Ships with **hand-curated golden fixtures** (a few
dozen known Legacy decks → expected labels) asserting the port reproduces them. Does NOT label the
DuckDB decks (labeler) or run the archived C# corpus (separate follow-up story).

## Epic context
- Parent epic: `epic-archetype-classifier`. The classification engine; consumes the typed ruleset, consumed by the labeler.

## Inherited design decisions
- **Conflict/Unknown stored raw** (no PreferSimpler, no Unknown→Other in the classifier — analytics owns bucketing).
- **Golden-test = fixtures now**; the C#-corpus ≥99% gate is a separate follow-up story (`epic-archetype-classifier-golden-corpus`, created at drafting, lower priority).
- **Rules-only** (no ML/statistical fallback tier).

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/archetype-matching-algorithm.md` — the exact algorithm + Python pseudocode + the I/O contract + the 12 condition predicates (ports 1:1 as a parametrized suite).

## Foundation references
- `docs/ARCHITECTURE.md` — `archetype/matcher.py`; `archetype/colors.py` (existing `compute_deck_colors`).

## Implementation notes
- **Files created**: `src/legacy_engine/archetype/matcher.py` (`classify`, `evaluate_condition`, `ArchetypeResult`, fallback scoring).
- **Tests added**: `tests/test_matcher.py` — golden fixtures (variant/archetype/conflict/fallback/unknown) + 12-condition-type parametrized checks. Full suite **128 passing in 0.67s**.
- **Discrepancies from design**: `In{zone}` and `OneOrMore{zone}` implemented as equivalent (both "≥1 distinct listed card present") — the rule schema uses them interchangeably; `TwoOrMore` = "≥2 distinct present". Faithful enough for fixtures; the C#-corpus follow-up story would catch any subtle copy-vs-name divergence.
- **Conflict/Unknown returned raw** (kind tags: archetype/variant/conflict/fallback/unknown), per the locked decision — analytics buckets.
- **Adjacent issues parked**: none.

## Review (2026-05-29)
**Verdict**: Approve. **Blockers/Important**: none.
**Nits**: `classify` takes `deck_colors` as a precomputed string (decoupled from card resolution — the labeler computes it via foundations' `compute_deck_colors`); the In/OneOrMore equivalence is the one place to verify against the C# corpus when that follow-up runs.
**Notes**: Faithful port of `ArchetypeAnalyzer.Detect` — collect-all-matches, nested variants, no-default-tie-break Conflict, ≥10% fallback floor, Unknown. 128 tests green. Unblocks labeler.
