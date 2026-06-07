---
id: epic-advisory-output-honesty-transparency
kind: feature
stage: drafting
tags: [analytics, advisory, generation]
parent: epic-advisory-output-honesty
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Output Transparency Labeling

## Brief

Three surfaces print numbers without the context needed to trust them — three applications of the one
"Source transparency / no unlabeled headline numbers" NFR. (1) No report surfaces data currency, so a
stale DB yields confident-looking outdated output. (2) Card-inclusion percentages are reported without
foregrounding sample size — a 7-week-old current-regime Dimir Tempo (n=11) read "100%". (3)
`generate tune` reports Value/Coverage numbers with no sense of scale and no per-swap rationale, so the
user can't tell whether 0.0633 is large or whether a swap is justified.

Covers: a "data current as of <max event date>" + corpus-size header on reports (warn when newest
event is older than N days); foregrounding sample size on card-inclusion reads (gate/annotate small-n
inclusion %); adding scale-anchoring + per-swap rationale to `generate tune` output.

Does NOT cover: positioning coverage (separate feature); the underlying tune swap logic (this is about
making its output legible, not changing what it swaps).

## Epic context
- Parent epic: `epic-advisory-output-honesty`
- Position in epic: independent capability — parallelizable. Spans report/metashare/generation
  surfaces but is one coherent "label the output with its own confidence" capability.

## Inherited design decisions
- These three are unified by the source-transparency NFR; design them as one labeling pass applied to
  three output surfaces, not three unrelated changes.

## Foundation references
- `docs/SPEC.md` — NFR "Source transparency — every figure labeled with source, window, basis"
- `src/legacy_engine/analytics/metashare.py` (inclusion), `analytics/match_results.py`, `generation/tuning.py` (tune), report headers in `cli.py`/`advisory/report.py`
