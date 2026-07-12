---
id: epic-stable-era-windows-mixed-horizon-consumers
kind: story
stage: implementing
tags: [analytics, advisory, viz]
parent: epic-stable-era-windows
depends_on: [epic-stable-era-windows-consumption]
release_binding: null
gate_origin: null
created: 2026-07-12
updated: 2026-07-12
---

# Align the two un-audited build_adaptive_matrix consumers with era windows

## Brief
The consumption review (Medium finding) identified two consumers the era-aware
`build_adaptive_matrix` default now reaches WITHOUT their sibling windows following: (1)
`viz/deck_dashboard.py:326` — the dashboard's matchup matrix is era-aware while its field/meta/
trends tiles resolve via `resolve_regime(regime)`; (2) `advisory/sideboard.py:4072` — the
slot-ROI base-equity matrix is era-aware while the per-opponent equity windows
(sideboard.py:3642/3819) stay ban-only `valid_since`. Both honest-degrade to identical output
without era data, so nothing is wrong TODAY — but once `eras run` populates the real DB, one
surface mixes two windowing regimes with no test coverage.

Deliver: make the sideboard per-opponent equity windows resolve through the same era-horizon
adapter as the matrix (one horizon source per recommendation); give the dashboard a seeded-eras
test pinning that its tiles either share the era window or label the difference in the tile
audit; one doc line in each surface naming the horizon source. No behavior change without era
data (byte-identical fallback preserved).

## Implementation
Small, review-scoped: `era_horizons` is the shared adapter (analytics/eras/consume.py). Seeded-
eras tests per the consumption feature's test patterns (tmp DB + eras store write).
