---
id: epic-regime-aware-advisory-windowing-core
kind: feature
stage: done
tags: [advisory, analytics, correctness]
parent: epic-regime-aware-advisory
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Windowing Core (v1 plumbing)

## Brief

The analytics/advisory plumbing that makes regime windowing *possible* — the foundation v1 step.
Thread a date window (`since`/`until`) through the matchup/positioning chain so the matrix can be
built over any window, mirroring the windowing `compute_card_winrates` already has:

- **`analytics/match_results.compute_match_results`** — add `since`/`until` (reuse the same
  date-bounded rounds-join CTE shape `compute_card_winrates` already uses; the dup/uniq_decks guard
  CTE is shared SSOT in this module).
- **`analytics/matchup.build_matrix`** — pass `since`/`until` through to `compute_match_results`.
- **`advisory/gaps.compute_archetype_gaps`** — thread `since`/`until` into both its `build_matrix`
  and `build_global_field` calls (it currently is un-windowed).
- A small **regime resolver** (e.g. `analytics/trends.resolve_regime(name|"current") -> (since, until)`)
  that maps a regime name (or "current") to a window via the existing `regime_windows()` SSOT.

`positioning_score` / `rank_decks` need NO new params — they consume a pre-built `matrix` + `field`,
so windowing happens at matrix/field build time and flows in. Behavior stays **full-corpus by
default** (all new params default to `None` = today's behavior); this feature ships no default change
and no CLI — it is pure additive plumbing so existing tests stay green untouched.

Does NOT cover: the CLI flags / regime UX / thin-regime degrade banner (→ `cli-surface`), nor the
adaptive per-cell windowing (→ `adaptive`). It only makes a uniformly-windowed matrix buildable.

## Epic context
- Parent epic: `epic-regime-aware-advisory`
- Position in epic: foundation feature — `cli-surface` and `adaptive` both build on this windowing.

## Inherited design decisions
- **Full-corpus default preserved in v1** (the default flip is v2/`adaptive`'s job) — all windowing
  params default to `None`.
- Window resolution reuses `analytics.trends.regime_windows` (the dated-ban-regime SSOT); no new ban-date source.

## Research briefs
- `docs/briefs/card-adjacency-and-discovery.md` (windowing/`CardWinRates` reuse context); the epic body.

## Foundation references
- `src/legacy_engine/analytics/match_results.py` — `compute_match_results` (+ the windowed
  `compute_card_winrates` to mirror), the shared dup/uniq_decks CTE.
- `src/legacy_engine/analytics/matchup.py` — `build_matrix`.
- `src/legacy_engine/analytics/trends.py` — `regime_windows` (resolver source).
- `src/legacy_engine/advisory/gaps.py` — `compute_archetype_gaps` (window threading).

## Design decisions
Resolved with judgment during feature-design (autopilot delegation); mechanical, not strategic:
- **Half-open `[since, until)` window semantics** (`>= since AND < until`) — matches `analytics.trends.regime_windows`
  and `generation.consensus.card_frequencies` (the dominant convention). NOTE: the sibling
  `compute_card_winrates` uses inclusive `<= until` — a pre-existing minor discrepancy. NOT changed here
  (would risk a `card_value` regression); flagged for a possible follow-up. Regime boundaries are exact ban
  dates, so half-open avoids double-counting a boundary day across adjacent regimes.
- **`build_global_field` is windowed too** — gaps windowing is only coherent if BOTH its matrix and its field
  use the same window, so `build_global_field` gains `since/until` threaded into its existing
  `compute_metashare(..., since, until)` call. (Windowed `wrw` raises `NotImplementedError`, but the field
  default is `raw` — fine.)
- **Regime resolver lives in `analytics/trends.py`** (next to `regime_windows`, its only data source).
  `"current"` → the last (open-ended) regime window; a named regime → matched by label substring; unknown →
  `ValueError` (fail-loud).
- **Additive, full-corpus default preserved** — every new param defaults to `None`; the `(? IS NULL OR …)`
  predicates are no-ops when unset, so existing callers + tests are byte-identical.

## Architectural choice
Mirror the windowing that `compute_card_winrates` already established in the same module: add the two
date predicates to the shared rounds-join so the date filter rides on the SAME cardinality-safe
dup/uniq_decks CTE (no parser divergence, no second code path). Windowing happens at **aggregate-build
time** (`compute_match_results` → `build_matrix`; `compute_metashare` → `build_global_field`); the
positioning consumers (`positioning_score`, `rank_decks`) take a pre-built matrix + field and need NO
changes — the window flows in through their inputs. Rejected: a separate windowed-matrix code path
(divergence risk); windowing inside positioning (wrong layer — would re-window per call).

## Implementation Units

### Unit 1: `compute_match_results` windowing
**File**: `src/legacy_engine/analytics/match_results.py`
```python
def compute_match_results(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None = None,
    since: str | None = None, until: str | None = None,
) -> MatchResults: ...
# _JOIN_SQL gains, after the provenance predicate:
#   AND (? IS NULL OR t.date >= ?)
#   AND (? IS NULL OR t.date <  ?)
# params: [provenance, provenance, since, since, until, until]
```
**Implementation Notes**: half-open `[since, until)`. The `_JOIN_SQL` constant is shared only by this
function; editing it is safe. `MatchResults` already carries `provenance`; no new result field needed
(window is the caller's context). Mirror the exact predicate ordering used in `_CARD_WINRATES_SQL` for
readability parity.
**Acceptance Criteria**:
- [ ] `compute_match_results(con)` (no window) returns byte-identical results to before (regression).
- [ ] A window excluding all rounds → empty `matchups`, `coverage.decisive_matched == 0`.
- [ ] A window covering only regime R returns only matches dated in `[since, until)`.

---

### Unit 2: `build_matrix` windowing
**File**: `src/legacy_engine/analytics/matchup.py`
```python
def build_matrix(con, *, provenance=None, min_row_share=0.02,
                 since: str | None = None, until: str | None = None) -> MatchupMatrix:
    mr = compute_match_results(con, provenance=provenance, since=since, until=until)
```
**Acceptance Criteria**:
- [ ] `build_matrix(con)` unchanged (regression). `build_matrix(con, since=…, until=…)` builds over the window.

---

### Unit 3: `build_global_field` windowing
**File**: `src/legacy_engine/advisory/field.py`
```python
def build_global_field(con, *, definition="raw", provenance=None, min_share=0.0,
                       since: str | None = None, until: str | None = None) -> FieldDistribution:
    report = compute_metashare(con, definition=definition, provenance=provenance,
                               min_share=min_share, group_other=False, since=since, until=until)
```
**Acceptance Criteria**:
- [ ] `build_global_field(con)` unchanged (regression). Windowed call narrows the field shares/counts to the window.

---

### Unit 4: `compute_archetype_gaps` windowing
**File**: `src/legacy_engine/advisory/gaps.py`
```python
def compute_archetype_gaps(con, *, definition="raw", provenance=None, share_weight=1.0,
                           min_coverage=0.5, risk_quantile=0.25, min_share=0.0, seed=None,
                           since: str | None = None, until: str | None = None) -> GapReport:
    field  = build_global_field(con, definition=definition, provenance=provenance,
                                min_share=min_share, since=since, until=until)
    matrix = build_matrix(con, provenance=provenance, since=since, until=until)
```
**Acceptance Criteria**:
- [ ] `compute_archetype_gaps(con, seed=…)` unchanged (regression). Windowed call ranks over windowed matrix+field.

---

### Unit 5: regime resolver
**File**: `src/legacy_engine/analytics/trends.py`
```python
def resolve_regime(name: str = "current") -> tuple[str | None, str | None]:
    """Map a regime name to a half-open (since, until) window via ``regime_windows()``.
    "current" → the last (until=None) window; a label substring → that regime; unknown → ValueError."""
```
**Implementation Notes**: returns ISO date strings (or None for an open bound), ready to pass straight
into the windowed functions above. `"current"` mirrors `consensus._latest_regime_window`'s "last window"
selection (reuse that logic / call it where sensible to stay SSOT).
**Acceptance Criteria**:
- [ ] `resolve_regime("current")` returns the latest regime's `(since, None)`.
- [ ] A label substring (e.g. `"Undercity"`) resolves to that regime's window.
- [ ] An unknown name raises `ValueError`.

## Implementation Order
1. **Unit 1** (`compute_match_results`) — the core; everything else threads through it.
2. **Unit 2** (`build_matrix`) + **Unit 3** (`build_global_field`) — passthroughs.
3. **Unit 4** (`compute_archetype_gaps`) — composes 2+3.
4. **Unit 5** (`resolve_regime`) — independent; consumed by `cli-surface` next feature.

## Testing
### Unit tests: `tests/test_match_results.py` (+ `test_matchup.py`, `test_gaps.py`, `test_trends.py`)
- `compute_match_results`: no-window regression equals prior; windowed corpus (use `make_rounds_corpus`
  whose tournaments are dated `2026-01-0N` — window `[2026-01-01, 2026-01-03)` includes only repeats 1–2)
  yields the expected reduced decisive count; empty window → zero coverage.
- `build_matrix` / `build_global_field` / `compute_archetype_gaps`: regression (no-window == prior) + a
  windowed call narrows results.
- `resolve_regime`: current → last window; substring match; unknown → ValueError.
### Integration
- Build a windowed matrix + windowed global field over the same window and confirm `rank_decks` consumes
  them unchanged (positioning needs no new params — the window flows through its inputs).

## Risks
- **Half-open vs `compute_card_winrates`'s inclusive `<=`** — the two aggregates will treat a boundary-day
  match differently. Acceptable (boundary days are rare; regimes are the dominant convention). **Fallback**:
  align `card_winrates` to half-open in a follow-up if it ever matters; out of scope here to avoid a
  `card_value` regression.
- **`build_global_field` windowed `wrw`** — `compute_metashare` raises `NotImplementedError` for windowed
  `wrw`. The field default is `raw`, so the default path is safe; a caller passing `definition="wrw"` +
  window would hit the existing guard. **Fallback**: none needed — the guard is correct behavior.

## Implementation notes
- Files changed: `analytics/match_results.py` (compute_match_results +since/until; `_JOIN_SQL` gains the half-open date predicates), `analytics/matchup.py` (build_matrix passthrough), `advisory/field.py` (build_global_field passthrough → compute_metashare), `advisory/gaps.py` (compute_archetype_gaps +since/until into both build_global_field + build_matrix; docstring de-"un-windowed"), `analytics/trends.py` (new `resolve_regime`; also removed 2 pre-existing dead imports MetaShareEntry/tier_for_sample).
- Tests added: `tests/test_regime_windowing_core.py` (13: compute_match_results×4 incl half-open-exclusive-upper, build_matrix/field×3, gaps×2, resolve_regime×4).
- Suite: 1020 passing (was 1007, +13). `ruff check` clean on all touched files (incl. the 2 dead-import removals).
- Discrepancies from design: none. Built Units 1–5 as specified. Half-open `[since, until)` confirmed by `test_half_open_upper_is_exclusive`. All new params default `None` → byte-identical no-window path (regression tests green).
- Adjacent issues parked: none (the `compute_card_winrates` inclusive-`<=` discrepancy is documented in the design as an accepted, out-of-scope follow-up).

## Review record
- **Verdict: Approve** (deep lane, fresh-context Opus sub-agent — NOT cross-model; Codex out of credits). 228 tests green across the 6 touched modules.
- Verified: param order in `_JOIN_SQL` execute matches `?` positions exactly (the Blocker risk — clean); no-window path byte-identical (`None` predicates short-circuit true); all new params default None; no caller breakage; positioning correctly untouched. Half-open `[since,until)` proven by the boundary test (non-vacuous); divergence from `compute_card_winrates`' inclusive `<=` is real + intentionally out-of-scope. gaps threads the window into BOTH field and matrix (no mismatch). `resolve_regime` substring match is safe (ambiguity → ValueError; "current" intercepted before substring). Dead-import removal safe (not re-exported).
- No Blockers, no Important. Nits: (1) `metashare.py` docstring + the windowed-wrw `NotImplementedError` text still say "match_results is not windowed" — now stale doc-rot (behavior still correct) → fold the 1-line fix into `cli-surface`; (2) impl-notes "13 vs 14 tests" cosmetic (it's 13).
