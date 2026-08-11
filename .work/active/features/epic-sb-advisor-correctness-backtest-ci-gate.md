---
id: epic-sb-advisor-correctness-backtest-ci-gate
kind: feature
stage: drafting
tags: [advisory, infra, deferred]
parent: epic-sb-advisor-correctness
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-11
---

# Backtest CI divergence gate — hermetic fixture + pinned budget

The four-of guard and acquire color filter prerequisites shipped in v0.4.0; no active dependency
edge remains.

## Brief

Stand up the CI-enforced divergence gate the epic's locked decision commits to: a hermetic
backtest fixture (file-backed tmp DuckDB per the `file-backed-cli-test-db-builder` pattern —
never the default DB) that runs `backtest_board` (`src/legacy_engine/advisory/backtest.py:363`)
against a fixed corpus, plus a **pinned divergence budget** that fails CI when an advisory
change WIDENS scorer-vs-observed divergence. The pin is a ratchet: each downstream
mechanism-fix feature re-pins tighter as it lands, and widening requires epic-level
justification. This feature is the measuring stick the epic's mechanism fixes prove
themselves against — it ships FIRST so `hate-self-cost` and `per-deck-castability` validate
hermetically instead of via live-DB runs (the green-local/red-CI trap).

The budget metric definition (e.g. pinned `scorer_only` / `winners_only` counts or named-card
sets per fixture archetype) and the fixture's corpus composition are feature-design's calls.
One hard requirement from the pre-mortem: the fixture must actually EXERCISE the mechanisms
under repair — it needs at least one reproducible scorer-only false positive driven by the
`_hate:`/impact machinery and one winners-only blind spot, or the ratchet measures nothing.
The gate never emits a pass/fail *verdict on the model* (divergence-as-diagnostic: the
partition stays an investigation surface); CI enforces only "did this change widen the pinned
gap" — a regression guard, not an auto-calibration.

Does NOT cover: fixing any divergence (that's the sibling features); blending observed
adoption into scores (locked out); slot-level empirical lift measurement (sibling epic
`epic-sb-config-evaluation`'s territory). Depends on the two in-flight legality stories
(4-of guard, acquire color filter) because both change recommender output — pinning before
they merge guarantees immediate pin churn.

## Epic context

- Parent epic: `epic-sb-advisor-correctness`
- Position in epic: foundation feature — `hate-self-cost` and `per-deck-castability` depend
  on it for hermetic before/after validation and the ratchet pin.

## Inherited design decisions

- **Backtest CI gate**: Yes — hermetic fixture + pinned divergence budget in CI; advisory
  changes that widen divergence vs the observed-boards reference fail. (This feature IS that
  decision.)
- **Calibration philosophy**: mechanism fixes only; adoption stays diagnostic — the gate pins
  a regression budget, it never feeds adoption back into scoring.
- **Decomposition call (epic-design)**: gate lands first and pins AFTER the in-flight
  fourof-guard / acquire-color-filter stories merge, so the baseline reflects corrected
  candidate legality.

## Research briefs

- `docs/briefs/scorer-flexibility-valuation.md` — the field-scoped backtest as acceptance
  harness precedent (§ backtest-scoped validation).
- `docs/briefs/advisory-methods.md` — advisory surface conventions.

## Foundation references

- `docs/ARCHITECTURE.md` — advisory table rows for `sideboard.py` / `backtest` (the
  "empirical (non-causal) anchor" framing).
- `docs/SPEC.md` — Pillar 4 "Archetype-sweep backtest" + HONEST-DEGRADE NFR.
- Patterns: `.agents/skills/patterns/file-backed-cli-test-db-builder.md`,
  `.agents/skills/patterns/divergence-as-diagnostic-surface.md`,
  `.agents/skills/patterns/freshness-stripped-cli-body-golden.md` (the enforcement shape).

<!-- The /feature-design pass will fill in interfaces, signatures, and implementation units. -->
