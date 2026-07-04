---
id: idea-archetype-sweep-backtest-loop
created: 2026-07-03
tags: [advisory, sideboard, analytics]
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
