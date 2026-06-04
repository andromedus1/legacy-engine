---
id: idea-bestcall-threshold-gradient
created: 2026-06-04
tags: [advisory]
---

best_deck_vs_best_call uses hard cutoffs (spread_hi=0.02, mean_hi=0.52) that create cliff effects: Death & Taxes had the highest field-weighted mean in the format (0.548 — clearly the best *call*) yet was labeled "neither" because its spread variance (0.0103) sat just under threshold. A user trusting the label would dismiss the best-positioned deck. Replace the binary label with a gradient/score, surface near-miss reasons, and always print the underlying means next to the label.
