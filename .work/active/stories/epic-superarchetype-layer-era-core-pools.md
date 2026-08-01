---
id: epic-superarchetype-layer-era-core-pools
kind: story
stage: drafting
tags: [analytics, archetype]
parent: epic-superarchetype-layer
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-01
updated: 2026-08-01
---

# Per-entity era core pools for superarchetype clustering

## Brief

`superarchetype run` computes every archetype's core set from ONE global `--since` window. The
principled endpoint per the era discipline (epic addendum #2) is per-entity pools: each
archetype's core computed from its OWN stable era (`entity_eras.stable_since`, ban-only fallback),
so a rebuilt archetype is represented by its current generation and an undisturbed archetype keeps
its full history. Keeps the one-window CLI as the explicit-override path. Note the known limit
this does NOT solve: behaviorally-kin families whose current compositions diverged (D&T+Energy)
stay separate — that is the curated layer's job. Design should reuse consume.py's horizon
resolution; the churn diagnostic must compare like-for-like across runs.
