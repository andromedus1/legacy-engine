---
id: feature-multi-split-matrix
kind: feature
stage: drafting
tags: [advisory]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-13
updated: 2026-07-31
---

# Multi-split advisory matrix — one pass across all camp splits


**Camp-level ranking needs a multi-split matrix.** Ranking all camps (2026-07-13 meta-view
session) required 29 separate `build_advisory_inputs(split_variant=parent)` calls — one split
matrix per parent. Consequences: P(best) is incomparable across per-parent matrices (had to
omit it in the camp view of `decks/best-deck-best-call-ranking.html`), and the sweep costs ~29
matrix builds (~4-5 min). Support `split_variant` accepting multiple/all parents in one matrix
so every camp shares one shared-field MC ranking with a valid cross-camp P(best).
