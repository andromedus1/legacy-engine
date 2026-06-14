---
id: feature-analytics-reporting-completeness
kind: feature
stage: done
tags: [analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-14
---

# Analytics Reporting Completeness

## Brief

A handful of analytics reports have coverage gaps or missing affordances that surfaced during
dogfooding — none individually large, but cohesive enough to design and ship together. All sit in the
Meta & Performance pillar (`analytics/` + `report` CLI) and are additive reporting features, not
behavioral changes to existing math. `/agile-workflow:feature-design` decomposes into child stories.

## Member findings (absorbed from backlog — full text in git history)

- **wrw-windowed** [analytics]: win-rate-weighted meta share (`--definition wrw`) is full-corpus only
  ('skipping wrw under a window') so it can't be windowed to a regime. Make wrw windowable.
- **trends-biggest-movers** [analytics]: `report trends` emits a dense 7-regime × ~28-archetype matrix
  with no digest. Add a 'biggest movers' summary of what actually changed between regimes.
- **head-to-head-matchup-lookup** [analytics]: inspecting one matchup requires reading the full matrix;
  add a direct head-to-head lookup (e.g. `report matchups --a <x> --b <y>`).
- **affectedness-explain** [analytics]: the per-deck ban-affectedness `valid_since` (e.g. why
  Doomsday's window is 2024-12-16) is computed but uninspectable. Add an explain mode that shows the
  derivation (which ban event × which card frequencies drove it).

## Implementation notes

Kept as one feature (4 cohesive units, no child stories warranted — all are additive affordances with
no shared state between units).

**1. wrw-windowed**
- `_wrw_weights` in `analytics/metashare.py` gained `since`/`until` kwargs, passed to both
  `_raw_counts` and `compute_match_results` so deck weights and win-rates are scoped to the same
  window.
- Removed the `NotImplementedError` guard in `compute_metashare` (the guard was the only blocking
  obstacle; the math is coherent once both legs are windowed).
- CLI: removed two "skipping wrw under a window" guards (venues mode + per-basis mode) and the dead
  `windowed` variable assignments. Five existing tests that asserted the old raise/skip behavior were
  updated to assert the new pass behavior.
- CLI surface: `report meta --definition wrw --regime current` now works.

**2. trends-biggest-movers**
- Pure function `biggest_movers(series, *, n=5, between=None) → list[BiggestMover]` added to
  `analytics/trends.py`. Compares the two most recent regimes by default; `between=(prev, curr)`
  selects a specific pair. Absent archetypes treated as 0 share (captures entries and exits). Sorted
  by `|delta|` descending, top-N sliced. No DB access.
- `BiggestMover` is a frozen dataclass carrying `archetype`, `delta`, `prev_share`, `curr_share`,
  `prev_regime`, `curr_regime`.
- CLI: `report trends --movers N` appends a digest block after the trajectory table.
- Helper `_print_biggest_movers` renders prev/curr/delta columns with "new"/"gone" for entries/exits.

**3. head-to-head-matchup-lookup**
- Pure function `lookup_head_to_head(matrix, a, b) → MatchupCell | None` added to
  `analytics/matchup.py`. Returns `None` for excluded archetypes; otherwise returns the directed cell
  (which may have `display=False` for speculative data — honest, not hidden).
- CLI: `report matchups --a <x> --b <y>` adds head-to-head mode. `--a`/`--b` must appear together
  (mutual validation). Renders p_raw, p_shrunk, 95% CI, tier, and the reverse direction.
  The full-matrix path is byte-identical when `--a`/`--b` are absent.

**4. affectedness-explain**
- `AffectednessExplanation` (frozen dataclass) + `explain_valid_since(con, archetype, ...)` added to
  `analytics/affectedness.py`. Iterates `_cards_by_ban_date()`, runs one query per ban event to count
  pre-ban decks and how many ran any banned card. Returns chronological list of explanations.
- `valid_since` = `max(ban_date where affected=True)` — consistent with `archetype_valid_since`.
- CLI: new `report affectedness --archetype X` command. Shows a per-ban-event table with inclusion
  rate and `YES ***` marker for affecting bans. Requires `--archetype`.

**Tests**: 34 new tests in `tests/test_analytics_reporting_completeness.py`. Full suite: 1991 passed
(1957 baseline + 34 new). Ruff clean on all changed analytics files and the new test file.
