---
id: epic-stable-era-windows-mixed-horizon-consumers
kind: story
stage: done
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

## Implementation notes

**Sideboard** (`src/legacy_engine/advisory/sideboard.py`, `recommend_sideboard`'s adaptive-window
block, ~line 3819): swapped `analytics.affectedness.archetype_valid_since` for
`analytics.eras.consume.era_horizons` — the SAME adapter `build_adaptive_matrix`'s slot-ROI base
matrix (line ~4072, unchanged — it already called `build_adaptive_matrix` directly) already uses.
One horizon source per recommendation now, closing the gap the consumption review flagged.
`era_horizons`'s ban-only fallback branch calls the identical `archetype_valid_since` with the
identical arguments when `entity_eras` has no data at all, so this is byte-identical to the
pre-epic behavior until `eras run` actually populates era data (proven by
`test_adaptive_windows_byte_identical_without_era_data`, which compares against a direct
`archetype_valid_since` call rather than re-checking a constant). `plan_window_label`'s "ban-aware"
wording (and its one authoritative field docstring) updated to "era-aware" to match; no test pinned
the old literal string against a live `recommend_sideboard` call (checked — only substring/"contains
adaptive" assertions and one unrelated hand-built-fixture literal in `test_refresh_workflow.py`),
so this is a safe, honest rename, not a breaking one.

**Dashboard** (`src/legacy_engine/viz/deck_dashboard.py`, `build_deck_dashboard`): Tile B (matchup
spread) was already era-aware via `build_adaptive_matrix`, and its per-opponent `window` field
already differs from the primer's ban-regime field-basis window when there's a disturbance — that
divergence was real but UNLABELED. Added one doc paragraph to the `field_basis` primer text (the
"tile audit" surface) explicitly naming both horizon sources and stating the two tiles' windows
may legitimately differ and are never blended — divergence-as-diagnostic-surface, the project's
existing pattern for exactly this shape of disagreement (never silently reconciled).

**Tests**: `tests/test_sideboard.py::TestAdaptiveWindowSideboard` gained
`test_adaptive_windows_resolve_via_era_horizons` (seeds an `entity_eras` row for Control with a
date the real banlist could never produce; asserts the seeded date shows up in
`plan_windows["Combo"]` and `plan_window_label == "adaptive (per-opponent era-aware)"`) and
`test_adaptive_windows_byte_identical_without_era_data`. `tests/test_viz_deck_dashboard.py` gained
`TestDeckDashboardEraAwareWindows` with
`test_seeded_era_diverges_from_ban_regime_window_and_is_labeled` (seeds an era boundary, confirms
Tile B's window moves to it while the primer text explicitly names both horizon sources) and
`test_byte_identical_without_era_data`. Ran ruff on both touched source files (clean) and both
touched test files (pre-existing, unrelated findings only — none within lines I added or changed:
several long-standing `E402`/`E401`/`F841`/`F401` items elsewhere in `test_sideboard.py`/
`test_viz_deck_dashboard.py`, reported but not fixed, out of scope). Full suite:
`.venv/bin/python -m pytest -q` → all green (see final report), no more expected failures anywhere
in the epic's three items.

No production bugs found or parked during this story.
