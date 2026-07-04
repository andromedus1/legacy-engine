---
id: idea-damping-sphere-base-model-near-miss
created: 2026-07-03
tags: [advisory, sideboard]
---

# Damping Sphere scorer-only divergence — base-model near-miss (verified)

Field-scoped backtest (Dimir Tempo + the local meta): Damping Sphere recommended but only **2.7%** of 258
top-finisher boards run it. Verified mechanism (option-value deep review, 2026-07-03): it is a
PRE-EXISTING near-miss in the base mean-field model — greedy at `alpha=1.0` (option-value term
fully disabled) already recommends it; the default ILP sits right at the margin (absent at α=1.0,
present at α=0.7). Not manufactured by the option-value term.

Likely axis: its `attacks: ["ramp", "storm-reliant"]` + symmetric flag — the base model prices its
ramp/storm coverage as competitive for this field while real pilots don't play it in Dimir Tempo
(its "spells cost {1} more per prior spell" tax also hits the caster's own cantrip turns — the same
symmetric-self-cost representability gap as [[idea-hate-coverability-overvalues-defense-grid]]).
Investigate with the divergence-as-diagnostic discipline; candidate systematic fix shared with the
Defense Grid item (graded self-cost for symmetric cards). Never auto-calibrate it away.
