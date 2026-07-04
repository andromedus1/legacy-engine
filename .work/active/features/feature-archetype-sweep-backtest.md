---
id: feature-archetype-sweep-backtest
kind: feature
stage: drafting
tags: [advisory, analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-04
---


# Archetype-sweep backtest loop — batch divergence mining for the sideboard advisor

the maintainer's idea (2026-07-03): the loop that found this week's scorer gaps — generate a board for ONE
archetype (Dimir Tempo), compare against winners' boards via `advise backtest`, investigate each
divergence — should run as a **systematic sweep across every archetype**: generate a decklist +
recommended sideboard per archetype, validate each against that archetype's top-finisher boards,
and emit a ranked divergence report. Every divergence is a lead: a missing mechanic (like the
Consign colorless-tag gap), a structural scoring defect (like the Defense Grid `_hate`
recommendation), or a genuine engine edge worth documenting. One archetype's dogfooding found
FoN/Consign/Defense Grid in a day — N archetypes would mine the whole failure surface.

**Composes pieces that already exist:** `generate consensus` (per-archetype decklist),
`advise sideboard` (the board), `advise backtest --field-scope` (the comparison + honest-degrade
tiers). Missing: the batch driver (iterate archetypes with enough corpus), a cross-archetype
divergence report (rank scorer-only false positives + winners-only blind spots by adoption% ×
archetype count — a card that's winners-only across MANY archetypes is a systematic gap, not
per-deck noise), and dedupe/clustering so one root cause (e.g. creature-removal under-crediting)
shows once, not 20 times.

**Ethos guards:** divergence stays a DIAGNOSTIC (flag to investigate, never auto-calibration into
scores — the pure-mechanics guardrail); confidence-tier gating per archetype (thin winner samples
→ labeled, not mined); output as substrate-ready findings (each cluster → a backlog candidate).

Related: [[idea-winners-only-triage-creature-interaction]] (this generalizes it),
[[idea-hate-coverability-overvalues-defense-grid]], [[idea-card-semantics-rules-layer]] (the sweep
would feed its incident inventory), [[idea-ilp-tiebreak-nondeterminism]] (determinism matters for
reproducible sweeps).

## Scope notes (promotion, 2026-07-04)

Promoted per the maintainer's directive: run this arc BEFORE the rules-engine arc
([[idea-card-semantics-rules-layer]] stays in backlog until this completes) so the sweep's
divergence clusters give the rules arc a complete, prioritized error map ("types of errors that are
common and need to be addressed" — his words). Sized as a single feature: composes shipped tools
(`generate consensus` → `advise sideboard` → `advise backtest --field-scope`); the new work is the
batch driver, the cross-archetype divergence report (rank by adoption% × archetype-count;
winners-only across many archetypes = systematic), root-cause clustering, and substrate-ready
finding output. Follows the now-codified `divergence-as-diagnostic-surface` pattern; determinism
prerequisite is tracked (`idea-ilp-tiebreak-nondeterminism` — the sweep should either drain it
first or pin the greedy solver for reproducibility, a feature-design decision).

Known session-1 seeds the sweep should rediscover (validation that the harness works): FoN/Consign
(fixed), Defense Grid + Damping Sphere (tracked), the creature-interaction winners-only cluster,
Surgical-in-graveyardless-fields.

## Additional design input (2026-07-04)

The sweep's divergence report should collect **copy-count histograms** (0x/1x/2x/3x/4x per card
among top-finisher boards), not just presence% — required to test
[[idea-copy-count-tipping-point]] (winners run fixers at 0 or 2+; our solver produces 1-ofs — a
possible S-curve/minimum-viable-count gap in the per-copy value model). The backtest's
`observed_frequency` is presence-only today; the sweep should surface the copy dimension.
