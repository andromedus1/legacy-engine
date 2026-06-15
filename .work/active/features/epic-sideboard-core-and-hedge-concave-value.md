---
id: epic-sideboard-core-and-hedge-concave-value
kind: feature
stage: drafting
tags: [advisory, sideboard]
parent: epic-sideboard-core-and-hedge
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-15
updated: 2026-06-15
---

# Concave per-copy value model

## Brief

Replace the sideboard solver's linear-in-copies element value with a concave per-copy
marginal-value function, so the k-th copy of a hoser is correctly worth less than the first. This
is the foundation feature — every other feature in the epic builds on the value it produces. Per
the brief's **key correction**, the model is `Δvalue(C, k) = share(e) · swing(C,e) · ΔP_access(k) ·
U_redundancy(k)`: `ΔP_access` is the (mildly concave) hypergeometric access increment, and
`U_redundancy(k)` — the sharply-decaying redundant-DRAWN-copy utility — is the term that actually
produces saturation (the access curve alone is too gently concave to stop padding).

Lands in `advisory/sideboard.py::_build_coverage_model`, changing how element weights scale with
copies. Recommend the brief's defaults (hypergeometric `1 − C(60−k, seen)/C(60, seen)` at a
turn-N "cards seen" default; `U_redundancy` ≈ 1.0 / 0.5–0.6 / ≤0.25 at copies 1/2/3, tunable). The
product of concave terms must stay **submodular** so the greedy solver keeps 1−1/e and the ILP
stays valid via piecewise-linear concave segments.

Does NOT cover the natural-budget stop (that's the dedicated-core feature), the output contract, or
the hedge — only the per-(card,copy) marginal-value primitive they all consume.

## Epic context
- Parent epic: `epic-sideboard-core-and-hedge`
- Position in epic: foundation feature — the dedicated-core, output-contract, and hedge features all
  consume this value model. First in the v1 wave.

## Inherited design decisions
- Recommend the brief's defaults for the access curve + redundancy decay (strong evidence); keep the
  curve parameters tunable, no hardcoded per-card cap.
- Preserve submodularity (greedy 1−1/e; ILP piecewise-linear concavity) — not a solver-class change.

## Research briefs
- `docs/briefs/sideboard-core-and-hedge.md` §2 (the access-probability curve + the U_redundancy
  correction; the computed hypergeometric table; calibration inputs).
- `docs/briefs/advisory-methods.md` §3 (inherited max-coverage / submodular-greedy / ILP — do not
  re-derive).

## Foundation references
- `docs/ARCHITECTURE.md` — `sideboard.py` row (weighted submodular max-coverage).
- Patterns: [[objective-search-split]] (heavy DB compute → dict → pure scored loop — the seam to
  keep the value model unit-testable with hand-built inputs), [[confidence-metadata]].
