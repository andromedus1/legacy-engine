---
id: epic-archetype-classifier-matcher
kind: feature
stage: drafting
tags: [archetype]
parent: epic-archetype-classifier
depends_on: [epic-archetype-classifier-rules-loader]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
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
