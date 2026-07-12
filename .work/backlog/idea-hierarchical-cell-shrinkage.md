---
id: idea-hierarchical-cell-shrinkage
created: 2026-07-11
tags: [analytics, methodology]
---

# Shrink camp matchup cells toward the PARENT cell, not flat 0.5

Matchup cells shrink toward flat 0.5 (α=β=7.5). The repo's own two-level-empirical-bayes pattern
(used in card_value) says: shrink toward the SHRUNK parent estimate, not the raw/flat prior. For
camp cells the natural hierarchy is camp → parent-archetype cell → 0.5: a Lands[Sphere/Tomb] vs
S&T cell (raw 31.2, n=16) currently displays 40.3 (pulled toward 50); shrunk toward the PARENT's
S&T cell (45.3) it would read ~38 — a materially more honest small-sample estimate. Parents in
turn could shrink toward their marginal WR. Design questions: does the hierarchy double-count
(parent includes camp's own matches — use leave-camp-out parent estimate); consumer impact (every
cell shifts — gated-additive rollout with a flag + goldens); interaction with idea-stable-era-windows
(hierarchical prior ACROSS a disturbance boundary is exactly the right prior for thin new-era
cells: new-era camp cell shrinks toward its own pre-disturbance value, labeled).
