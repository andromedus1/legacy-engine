---
id: epic-stable-era-windows-era-ledger-run
kind: story
stage: done
tags: [analytics, methodology]
parent: epic-stable-era-windows-era-ledger
depends_on: [epic-stable-era-windows-era-ledger-store]
release_binding: v0.4.0
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Attribution + eras run pass + drift alarm

## Brief
Units C+D: boundary attribution (ban/release/unattributed, ±14d tolerance, affectedness-threshold check), the run_eras offline pass wiring series→detectors→ensemble→attribution→store, and the BOCPD tail drift alarm for high-share entities.

## Implementation
Parent feature `epic-stable-era-windows-era-ledger` — exact contracts + acceptance criteria there.

## Implementation notes

**Unit C — `analytics/eras/attribution.py`**
- `Attribution(kind, card, detail)` — frozen, closed-vocab (`ban`/`release`/`unattributed`),
  raises `ValueError` on an invalid `kind`.
- `attribute_boundaries(eras, *, ban_events, releases, series, tolerance_days=14)` attributes
  EVERY boundary in every entity's `EntityEras.boundaries` (accepted or not — the full audit
  trail, mirroring `explain_valid_since`'s per-event walk), keyed `(entity, date)`.
- Ban check: nearest `BAN_EVENTS` entry within tolerance; if the card is trackable in the
  entity's own flex band, requires ≥25% pre-boundary inclusion (reuses
  `affectedness.py`'s own bar as a literal constant); if the card is NOT trackable (too
  ubiquitous or too rare to ever enter the flex band — the Candelabra/Tron headline case, which
  runs at ~100% and therefore sits above the flex band's ceiling), falls back to date-match
  alone with an honest "inclusion unverified" note. A verified-but-below-threshold match falls
  through to the release check rather than forcing a "ban" verdict.
- Release check: only for a boundary carrying its own S1 `presence-adopt` signal (the only
  signal naming a `trigger_card`); matches when that card's injected release date is within
  tolerance.
- Neither matching → `"unattributed disturbance — possible unregistered B&R change"`.
- Ban is checked before release when a boundary could plausibly match both (verified: a
  boundary with both a nearby ban event and a matching adopt-signal release date resolves
  "ban").

**Unit D — `analytics/eras/run.py`**
- `run_eras(con, *, provenance=None, alpha=0.05, seed=0, release_source=None) -> ErasRunResult`
  wires `build_entity_series` → `detect_presence`/`detect_composition`/`detect_share` →
  `corroborate_winrate` → `derive_eras` → `attribute_boundaries` (ban events from
  `ingestion.banlist.BAN_EVENTS`) → `compute_drift_alarms` → `write_entity_eras`. `release_source`
  is an injected callable; the default (`_default_release_source`) probes the `cards` table for
  a `release_date`/`released_at` column via `PRAGMA table_info` and returns `{}` when absent —
  the current schema (`ingestion/store.py::CARDS_DDL`) has no such column, so release attribution
  honestly degrades to unavailable; ban-only attribution still covers the headline case.
- `compute_drift_alarms(series, eras, attributions) -> dict[str, AlarmFlag]` — public (not
  private) so it is directly unit-testable against the shared detection-package calibration
  fixtures without a DB. Beta-Binomial BOCPD (bocpd.py's own default `hazard_lambda=25.0`) on each
  entity's own `(decks, field_decks)` complete-bucket series; alarm-eligible only above a 2%
  overall field-share floor and `>= 4` complete buckets (guards bucket-0's cold-start
  `p_change=1.0` from ever landing in the "recent" window); fires when the max `p_change` over
  the last 3 complete buckets is `>= _ALARM_BAR` AND no `bh_accepted and not floor_rejected`
  boundary in that same recent window is attributed `ban`/`release` (an accepted-but-still-
  `unattributed` boundary does NOT suppress — that IS the alarm's job).
- `_ALARM_BAR = 0.5`, calibrated 2026-07-11 against `tests/analytics/eras/conftest.py`'s
  real-corpus fixtures: `tron_cliff_series`'s last complete bucket (the Candelabra cliff, 59→20
  decks/week) spikes `p_change` to ~0.9996; `stable_nonevent_series`'s last-3-bucket max is
  ~0.11 (periodic wobble, no true disturbance) — 0.5 sits with wide margin either side.
- `post_boundary_decks`/`parent` are threaded through `write_entity_eras`'s `run_meta` dict
  (Unit B's pinned signature has no dedicated params for either — `EntityEras` itself carries no
  `parent` field, and `post_boundary_decks` is the `eras list` confidence-tier sample size
  computed here from `series`).

**Tests**: `tests/analytics/eras/test_attribution.py` (14 new — ban verified/unverified-fallback,
release with/without an adopt signal, ban-priority-over-release, tolerance boundary at exactly
14/15 days both directions, full audit trail regardless of `bh_accepted`, closed-vocab).
`tests/analytics/eras/test_run.py` (16 new): `TestAlarmCalibration` exercises
`compute_drift_alarms` directly against the shared conftest fixtures (fires on the Tron cliff,
silent on a 20-entity stationary fleet, correctly suppressed only by an accepted+attributed
covering boundary, share-floor and short-series guards) — fast (no DB). `TestRunErasEndToEnd`
drives the full pipeline against a hermetic in-memory DuckDB corpus (18 weekly tournaments, an
implanted cliff dated exactly to the real 2026-05-18 Undercity Informer ban): Tron (runs the
banned card in 100% of decks, unverifiable, honest date-match fallback) attributes "ban"; Drift
(same cliff shape, same card at a trackable 15% — below the affectedness threshold) attributes
"unattributed" and its alarm fires; `write_entity_eras`/`read_entity_eras` round-trip matches the
in-memory result; two independent runs are deterministic. With only 3 synthetic entities,
BH-FDR's fleet-wide correction has no real statistical power (by design — a real corpus runs
~50-150 entities), so these assertions are structural (boundary present + correctly attributed)
rather than on `bh_accepted`; alarm-suppression-when-covered is pinned precisely in
`TestAlarmCalibration` instead. Runtime: ~4s for the full file (7,560 synthetic deck rows).

**Verification**: scoped (`-k "banlist or affectedness or trends or regime"`) still green
(unaffected by this story); `tests/analytics/eras/` 109 passed; full suite 2866 passed, 1 xfailed
(baseline 2813 + 1 xfail + net new tests across both stories so far); `ruff check` clean on all
changed/new files.

**Deviations**: none from the pinned Unit C/D contracts.
