---
id: idea-docstring-historical-prose-nit
created: 2026-07-04
tags: [cleanup]
---

# Docstring "removed by feature-X" historical prose (rolling-foundation nit)

gate-cruft v0.2.0, Low confidence. `src/legacy_engine/advisory/sideboard.py:1646`: the
element-weights docstring says "draw-prob deflation removed by feature-sfv-weights" — historical
prose + internal feature slug in code. Reword to present behavior only (draw_prob intentionally
excluded via `score_without_draw_prob()`); git is the audit trail. Optional/low priority.
