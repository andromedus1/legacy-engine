---
id: epic-meta-analytics-trends
kind: feature
stage: done
tags: [analytics]
parent: epic-meta-analytics
depends_on: [epic-meta-analytics-metashare]
release_binding: v0.1.0
gate_origin: null
created: 2026-05-29
updated: 2026-06-14
---

# Meta Trends Across Ban-List Regimes (version-stamped)

## Brief
Track how the metagame evolves over time, **segmented by ban-list regime**. Partition the corpus into
windows bounded by `BanListSnapshot` `banned_date`s (a B&R announcement opens a new regime; an
archetype can be born or killed at that date — PRINCIPLES #5 legality-is-live-data), and compute the
meta-share series (per `metashare`'s definitions) within each regime / time window. Emit a
version-stamped trend series: for each archetype, its share trajectory across regimes, so a reader can
see "Archetype X was 12% pre-ban, 3% after". Stamp every series point with the regime it belongs to and
the window's event count, and flag short/thin windows `evolving` with a banner (per the ops brief's
corpus-window gate: <~4 events or <2 weeks → flagged).

Reuses `metashare` for the per-window computation rather than re-deriving share logic; this feature owns
the **time/regime partitioning and the version-stamping**, not the share math. Honors the online/paper
split. Wires the `report tiers` trend view (the tier-list-over-time surface) and/or a dedicated trends
CLI leaf as feature-design decides.

Does NOT compute matchup trends (matchup evolution is out of scope for MVP — the matchup sample is too
sparse per-regime to be honest; revisit later), nor render charts (`charts` consumes this series).

## Epic context
- Parent epic: `epic-meta-analytics`
- Position in epic: consumer of `metashare` (per-window share computation). Producer of the
  version-stamped trend series that `charts` renders.

## Inherited design decisions
- **Segment by ban-list regime** (B&R `banned_date` boundaries), version-stamped — reuse `BanListSnapshot` from ingestion.
- **Reuse `metashare` per-window**, don't re-derive share math.
- **Short-window gating**: <~4 events or <2 weeks → flag the window `evolving` + banner.
- **Meta-share trends only for MVP**; matchup trends deferred (per-regime matchup sample too sparse).

## Research briefs
- `docs/briefs/legacy-metagame.md` — the current meta + meta-evolution direction; ban-list regimes as the natural segmentation.
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — §6 (corpus-window gating thresholds), §2 (version-stamping discipline via the manifest).

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/trends.py`; `ingestion/banlist.py` `BanListSnapshot`.
- `docs/PRINCIPLES.md` — #5 legality-is-live-data (version-stamp on B&R), #7 confidence-gate.

## Design decisions
(Resolved under autopilot delegation. Parent-epic + `metashare` decisions inherited as fixed. No
strategic 50/50s — all pinned by the briefs / banlist module / metashare's additive design.)

- **Reuse mechanism = optional date window threaded into `metashare`** (additive). `compute_metashare`
  and its `_raw_counts` / `_topcut_counts` / `_unlabeled_count` helpers gain `since: str | None = None`
  and `until: str | None = None` (ISO `YYYY-MM-DD`), compared against `tournaments.date` (a VARCHAR of
  ISO dates — lexicographic order == chronological). Half-open `[since, until)`. Defaults `None` →
  no filter → **all 257 existing metashare tests stay green**. This is the literal "reuse metashare
  per-window, don't re-derive" the epic mandated. Rejected alternatives: (B) trends builds a filtered
  temp view — metashare hardcodes `FROM decks/tournaments`, can't shadow base tables cleanly, more
  invasive than A; (C) trends re-derives windowed share SQL — violates the inherited no-re-derive rule.
- **Trend definitions = `raw` (default) + `topcut`** — both window purely within metashare's own
  tables. **`wrw` deferred for trends**: it consumes `compute_match_results` (un-windowed), so a windowed
  wrw would pair a windowed numerator with an all-time win-rate (incoherent), and per-regime match
  samples are too thin to present honestly — the same sparsity rationale the epic used to defer
  *matchup* trends. Guarded: `compute_metashare(definition="wrw", since/until set)` raises
  `NotImplementedError` rather than silently producing an incoherent number.
- **Regime boundaries from `banlist.BAN_EVENTS`** — each distinct B&R date opens a new regime;
  half-open windows `[date_i, date_{i+1})`; a `(None, first_date)` baseline regime and a
  `(last_date, None)` current regime bookend. Multi-card dates (e.g. 2024-12-16 Psychic Frog + Vexing
  Bauble) are grouped into one boundary. Reuses the existing `BAN_EVENTS` source of truth — no
  re-listing of ban dates here (SSOT).
- **Window gating** (ops-brief corpus-window gate): a regime is `thin` when `event_count < 4` OR the
  data span (max−min event date in-window) `< 14 days`. Thin regimes are flagged and their per-cell
  confidence tier is **capped at `evolving`** (a thin window may never claim `established`), with a
  banner in the CLI output. Empty regimes (zero in-window events) are omitted from the series (logged
  at debug), not shown as zeroes.
- **Version-stamping**: every regime window carries its `(label, since, until, opening_events,
  event_count, span_days, thin)`; every cell carries `(archetype, share, n, tier)`. This is the
  "Archetype X was 12% pre-ban, 3% after" trajectory, each point stamped with the regime it belongs to.
- **CLI = dedicated `report trends` leaf** (not overloading `report tiers`, which is the tier-list /
  charts surface). `report tiers` stays a stub for `charts`.
- **Undated / non-ISO tournaments** can't be placed in a window (`NULL >= since` is false in SQL) →
  excluded from windowed views. Acceptable: corpus dates are ISO `YYYY-MM-DD` (verified in fixtures +
  `TournamentResult.date`); the exclusion is logged, never silently folded.
- **Single-stride, no child stories** — one cohesive `trends.py` module + an additive `metashare.py`
  edit + one CLI wiring; the units are tightly coupled (compute_trends needs the windowing + regimes;
  CLI needs compute_trends). Mirrors how `metashare` was delivered.

## Architectural choice

**Additive date-window on metashare + a thin partitioner in `trends`.** The feature owns *time/regime
partitioning and version-stamping*, not share math. The cleanest realization gives `metashare` an
optional half-open date window (additive, default-None) and makes `trends` a partitioner that (1)
derives regime windows from `BAN_EVENTS`, (2) calls `compute_metashare` once per non-empty regime with
that window, (3) stamps each result with its regime + corpus-window stats, capping thin windows at
`evolving`. Share math, the inclusion floor, "Other" grouping, and confidence tiers all stay in
metashare — trends never reimplements them. `wrw` trends are deferred (and guarded) because windowing
match-results coherently is out of MVP scope and the per-regime match sample is too sparse to be honest.

## Implementation Units

### Unit 1: Regime partitioning (trickiest — designed first)

**File**: `src/legacy_engine/analytics/trends.py`

```python
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import duckdb

from legacy_engine.confidence import ConfidenceLevel, tier_for_sample
from legacy_engine.ingestion.banlist import BAN_EVENTS

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegimeWindow:
    """One ban-list regime — a half-open [since, until) date window opened by a B&R action.

    ``since``/``until`` are ``None`` only for the open-ended baseline / current bookends.
    ``opening_events`` is the tuple of cards banned on ``since`` (empty for the baseline regime).
    The ``event_count``/``span_days``/``thin`` fields are populated by ``compute_trends`` once the
    corpus is queried for this window (they are 0/False on a bare partition).
    """

    label: str
    since: date | None
    until: date | None
    opening_events: tuple[str, ...]
    event_count: int = 0
    span_days: int = 0
    thin: bool = False


def regime_windows() -> list[RegimeWindow]:
    """Partition time into ban-list regimes from ``BAN_EVENTS`` (the SSOT for dated B&R actions).

    Each distinct ban date opens a regime; windows are half-open ``[date_i, date_{i+1})`` so a
    tournament dated exactly on a ban date belongs to the NEW regime. A ``(None, first_date)``
    baseline regime and a ``(last_date, None)`` current regime bookend the series.
    """
```

**Implementation Notes**:
- Group `BAN_EVENTS` by date → sorted unique dates, each mapping to the tuple of cards banned then.
- Baseline regime: `since=None, until=dates[0]`, `opening_events=()`, label `"baseline (pre-{dates[0]})"`.
- Interior/current regime `i`: `since=dates[i-1], until=dates[i]` (or `None` for the last),
  `opening_events=cards[dates[i-1]]`, label `"after {', '.join(cards)} ({dates[i-1]})"`; the last
  appends `" — current"`.
- Pure function of `BAN_EVENTS` — deterministic, no DB. **Does not re-list ban dates** (SSOT).

**Acceptance Criteria**:
- [ ] First window is the baseline `(None, BAN_EVENTS earliest date)` with empty `opening_events`.
- [ ] Last window is `(latest ban date, None)` and its label ends with "current".
- [ ] A date shared by two bans (2024-12-16: Psychic Frog + Vexing Bauble) yields ONE boundary whose
      `opening_events` has both cards.
- [ ] Windows are contiguous and half-open: `window[i].until == window[i+1].since`.

---

### Unit 2: Date-window on metashare (additive edit)

**File**: `src/legacy_engine/analytics/metashare.py` (modify — additive, default-None)

```python
# _RAW_SQL / _TOPCUT_SQL / _UNLABELED_SQL each gain a half-open date predicate:
#   AND (? IS NULL OR t.date >= ?) AND (? IS NULL OR t.date < ?)
# params append: [..., since, since, until, until]

def _raw_counts(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None,
    since: str | None = None, until: str | None = None,
) -> dict[str, int]: ...

def _topcut_counts(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None, cut_size: int,
    since: str | None = None, until: str | None = None,
) -> dict[str, int]: ...

def _unlabeled_count(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None,
    since: str | None = None, until: str | None = None,
) -> int: ...

def compute_metashare(
    con: duckdb.DuckDBPyConnection, *, definition: Definition = "raw",
    provenance: str | None = None, min_share: float = 0.02, cut_size: int = 8,
    group_other: bool = True, since: str | None = None, until: str | None = None,
) -> MetaShareReport: ...
```

**Implementation Notes**:
- `since`/`until` are ISO `YYYY-MM-DD` strings (or `None`). Half-open `[since, until)`. Compared
  against `tournaments.date` (VARCHAR ISO → lexicographic == chronological).
- Thread into `raw` and `topcut` branches. **wrw guard** at the top of `compute_metashare`:
  `if definition == "wrw" and (since is not None or until is not None): raise NotImplementedError("windowed wrw is unsupported — match_results is not windowed; use raw/topcut for trends")`.
- `compute_all` is left unchanged (no window param) — trends calls `compute_metashare` per definition,
  never `compute_all`, so the wrw-raise trap is avoided.
- Every existing call site passes neither kwarg → identical behavior (defaults `None`).

**Acceptance Criteria**:
- [ ] `_raw_counts(..., since="2025-01-01", until="2025-02-01")` counts only decks in events dated in
      `[2025-01-01, 2025-02-01)`; an event on `2025-02-01` is excluded, one on `2025-01-01` included.
- [ ] `compute_metashare(...)` with no window kwargs returns byte-identical results to today (regression).
- [ ] `compute_metashare(definition="wrw", since="2025-01-01")` raises `NotImplementedError`.

---

### Unit 3: Trend record types + `compute_trends`

**File**: `src/legacy_engine/analytics/trends.py`

```python
Definition = str  # "raw" | "topcut" (wrw deferred for trends)

_THIN_MIN_EVENTS = 4
_THIN_MIN_SPAN_DAYS = 14


@dataclass
class TrendCell:
    archetype: str
    share: float
    n: int
    tier: ConfidenceLevel   # capped at "evolving" when its regime is thin


@dataclass
class TrendSeries:
    definition: Definition          # "raw" | "topcut" — ALWAYS labeled (PRINCIPLES #6)
    provenance: str | None          # basis — ALWAYS labeled
    regimes: list[RegimeWindow]     # chronological, only regimes with >=1 in-window event
    cells: dict[tuple[str, str], TrendCell]   # (regime.label, archetype) -> cell
    archetypes: list[str]           # union across regimes, sorted by most-recent-regime share desc

    def trajectory(self, archetype: str) -> list[TrendCell | None]:
        """Per-regime cells for one archetype (None where it's absent that regime)."""
        return [self.cells.get((r.label, archetype)) for r in self.regimes]


def _window_event_stats(
    con: duckdb.DuckDBPyConnection, *, since: date | None, until: date | None, provenance: str | None,
) -> tuple[int, int]:
    """Return (event_count, span_days) for tournaments in [since, until) on this provenance basis."""


def _cap_thin(tier: ConfidenceLevel, *, thin: bool) -> ConfidenceLevel:
    """A thin window may never claim 'established' — cap it at 'evolving'."""
    return "evolving" if (thin and tier == "established") else tier


def compute_trends(
    con: duckdb.DuckDBPyConnection, *, definition: Definition = "raw",
    provenance: str | None = None, min_share: float = 0.02, cut_size: int = 8,
    min_events: int = _THIN_MIN_EVENTS, min_span_days: int = _THIN_MIN_SPAN_DAYS,
) -> TrendSeries:
    """Version-stamped meta-share trajectory across ban-list regimes.

    For each non-empty regime, calls ``compute_metashare`` with the regime's date window
    (``group_other=False`` so archetypes stay comparable across regimes), stamps the result with
    corpus-window stats, and caps thin-window confidence at 'evolving'. ``definition`` must be
    'raw' or 'topcut' — 'wrw' raises ValueError (deferred; per-regime match sample too sparse).
    """
```

**Implementation Notes**:
- Validate `definition in {"raw", "topcut"}` else `ValueError` pointing at the deferral rationale.
- `_window_event_stats`: `SELECT count(*), min(date), max(date) FROM tournaments WHERE
  (? IS NULL OR date >= ?) AND (? IS NULL OR date < ?) AND (? IS NULL OR provenance = ?)`. `span_days`
  = `(date.fromisoformat(max) - date.fromisoformat(min)).days` (0 when count<=1).
- For each regime: compute stats; **skip if `event_count == 0`** (log debug, omit from series).
  Else `thin = event_count < min_events or span_days < min_span_days`; build the `RegimeWindow` with
  stats via `dataclasses.replace`; call `compute_metashare(con, definition=definition,
  provenance=provenance, since=regime.since.isoformat() if regime.since else None,
  until=regime.until.isoformat() if regime.until else None, min_share=min_share, cut_size=cut_size,
  group_other=False)`; turn each `MetaShareEntry` into a `TrendCell` with `tier=_cap_thin(entry.tier, thin)`.
- `archetypes` sorted by share in the most-recent regime that contains them (desc), so the headline
  reads newest-meta-first.

**Acceptance Criteria**:
- [ ] Over a corpus spanning 3 regimes, `compute_trends` returns a series whose `regimes` are exactly
      the non-empty windows in chronological order.
- [ ] An archetype present in regime A (12%) and regime B (3%) has both cells with the right shares,
      each stamped to its regime.
- [ ] A regime with 2 events (or a <14-day span) is `thin=True` and every cell's tier is capped at
      `evolving` (never `established`).
- [ ] `trajectory(archetype)` returns `None` for a regime where the archetype is absent.
- [ ] `compute_trends(definition="wrw")` raises `ValueError`.

---

### Unit 4: CLI `report trends`

**File**: `src/legacy_engine/cli.py` (add a new `report` leaf + `_print_trend_series` helper)

```python
@report.command("trends")
# --definition [raw|topcut] (default raw), --provenance [online|paper|all] (default all),
# --min-share (default 0.02), --db
def report_trends(definition: str, provenance: str, min_share: float, db: str | None, verbose: bool) -> None:
    """Meta-share evolution across ban-list regimes (version-stamped)."""
```

**Implementation Notes**:
- Mirror `report_meta`: `_setup_logging(verbose)` first; lazy-import inside the command; `--provenance all`
  prints each basis (`None`/`online`/`paper`) separately, never a silent blend.
- `_print_trend_series`: header states `definition`, basis; then per regime a sub-header line with the
  regime label, `since→until`, `event_count`, and a `⚠ THIN (flagged evolving)` banner when `thin`.
  Render the trajectory as a table (archetype rows × regime columns, cells = `share%` with a thin
  marker), or per-regime blocks — whichever reads cleanly; the trajectory table is preferred so the
  "X was 12% → 3%" story is one row.

**Acceptance Criteria**:
- [ ] `legacy-engine report trends --definition raw` prints a header labeled with definition + basis
      and one labeled column/block per non-empty regime.
- [ ] Thin regimes show a banner; output never prints an unlabeled or blended number.

---

### Unit 5: Module exports

**File**: `src/legacy_engine/analytics/__init__.py` — export `RegimeWindow`, `TrendCell`,
`TrendSeries`, `regime_windows`, `compute_trends` (and add to `__all__`).

## Implementation Order

1. **Unit 2** (metashare window) — additive foundation everything else needs; run the full metashare
   suite after to prove the no-window regression.
2. **Unit 1** (regime partitioning) — pure function, no DB; trickiest boundary logic.
3. **Unit 3** (records + `compute_trends`) — the partitioner that joins Units 1+2.
4. **Unit 4** (CLI) — wire `report trends`.
5. **Unit 5** (exports) — last.

## Testing

### Unit tests: `tests/test_trends.py`
House style (raw dicts → `parse_cache_item` → `store.load_tournament` into `:memory:`; `UPDATE decks
SET archetype` for deterministic labels; `TestX` classes). Fixtures span regime boundaries — e.g.
events dated `2024-09-01` (after Grief 2024-08-26, before Psychic Frog 2024-12-16), `2025-01-15`,
`2026-05-25` (after the 2026-05-18 Undercity Informer ban → current regime).

- `TestRegimeWindows` — baseline + current bookends, half-open contiguity, multi-card date grouping,
  labels.
- `TestMetashareWindowing` — `_raw_counts`/`_topcut_counts`/`_unlabeled_count` with `since`/`until`;
  boundary inclusivity (on-`since` in, on-`until` out); no-window regression equals today; wrw windowed
  raises `NotImplementedError`. (Lives here or appended to `test_metashare.py`.)
- `TestComputeTrends` — multi-regime shares, per-regime stamping, thin flag + tier cap, empty-regime
  omission, `trajectory` None-holes, `definition="wrw"` → ValueError.
- `TestReportTrendsCLI` — `CliRunner` invokes `report trends`; asserts labeled header, per-regime
  blocks, thin banner, no unlabeled/blended number.

### Integration points
- Seam with `metashare`: `compute_trends` consumes `compute_metashare`'s windowed output — a test loads
  a multi-regime corpus and confirms a regime's cells equal `compute_metashare(..., since, until)` for
  the same window (proves reuse, not re-derivation).
- Seam with `banlist`: `regime_windows()` boundaries equal the distinct `BAN_EVENTS` dates (SSOT).
- Seam with `confidence`: cell tiers come from `tier_for_sample` (then thin-capped), not a local reimpl.
- Seam with `store`: all SQL reads `tournaments.date`/`decks` exactly as `store.load_tournament` writes.

## Risks

- **ISO date-string comparison in SQL**: windowing assumes `tournaments.date` is `YYYY-MM-DD`
  (lexicographic == chronological). **Verified** against fixtures + `TournamentResult.date`.
  **Mitigation**: undated/non-ISO events fail `>= since` and are excluded from windows, logged as
  coverage — never silently folded. **Fallback**: if a source emits non-ISO dates, normalize at
  ingestion (additive, out of scope here).
- **Sparse per-regime corpus** → most regimes thin → a series of `evolving`-flagged points. This is the
  honest outcome, not a bug: the thin gate + tier cap + banner make it explicit; empty regimes are
  omitted. (Parent epic already flagged coarse regimes as acceptable for MVP.)
- **Windowed-wrw incoherence**: guarded twice — `compute_metashare` raises `NotImplementedError` if
  windowed-wrw is requested, and `compute_trends` raises `ValueError` for `definition="wrw"`. No silent
  incoherent number can escape.

## Implementation notes

### Files created
- `src/legacy_engine/analytics/trends.py` — new module containing `RegimeWindow`, `regime_windows()`,
  `TrendCell`, `TrendSeries`, `_window_event_stats`, `_cap_thin`, `compute_trends`
- `tests/test_trends.py` — 40 new tests across `TestRegimeWindows`, `TestMetashareWindowing`,
  `TestComputeTrends`, `TestReportTrendsCLI`

### Files modified
- `src/legacy_engine/analytics/metashare.py` — Units 1–2 SQL constants and helpers updated to accept
  `since`/`until` kwargs (additive, default `None`); `compute_metashare` gains the same kwargs plus
  the wrw-window guard (`NotImplementedError`)
- `src/legacy_engine/analytics/__init__.py` — added `RegimeWindow`, `TrendCell`, `TrendSeries`,
  `regime_windows`, `compute_trends` to imports and `__all__`
- `src/legacy_engine/cli.py` — added `report_trends` command and `_print_trend_series` helper before
  the `report tiers` stub

### Test counts
- Baseline: 257 tests passing
- After implementation: 297 tests passing (40 new trend tests added)
- All 257 existing tests still green (metashare regression gate confirmed)

### Deviations from spec
- **None.** Implemented exactly to spec. Implementation order followed: Unit 2 → Unit 1 → Unit 3 →
  Unit 4 → Unit 5.

### One minor implementation note
- `test_empty_corpus_returns_empty_series` initializes the schema explicitly via `init_schema(con)`
  before calling `compute_trends`. This matches house style: `store.connect(":memory:")` does not
  automatically create tables — they are created lazily by `load_tournament`. The test fixture
  reflects the real precondition (schema initialized, no data loaded). This is not a design deviation.

### Adjacent issues parked
- `report tiers` stub remains intentionally untouched per spec ("DO NOT touch it").
- `wrw` trends deferred as designed; the double guard (NotImplementedError in metashare +
  ValueError in compute_trends) is in place.

## Review (2026-05-30)

**Verdict**: Approve

**Blockers**: none
**Important**: none
**Nits**:
- `trends.py:22` imports `MetaShareEntry` but never references it (only `compute_metashare` is used). Harmless dead import (no ruff configured); drop it on next touch.

**Notes**:
- Metashare windowing is genuinely additive: `since`/`until` default `None`, param ordering correct, `compute_all` untouched. The no-window path is byte-identical — `test_no_window_regression_equals_unwindowed` proves it, and all 257 prior tests stay green (297 total).
- Reuse-not-re-derive is verified, not asserted: `test_archetype_shares_match_per_regime_metashare` confirms each regime's cells equal `compute_metashare(..., since, until)` for the same window. `trends` owns only partitioning + version-stamping; share math, the floor, "Other", and tiers all stay in `metashare`.
- Honesty gates intact: thin windows (`<4 events or <14-day span`) flagged + tier capped at `evolving` via `_cap_thin`; empty regimes omitted (not zeroed); both incoherent-wrw paths guarded (`NotImplementedError` in metashare, `ValueError` in `compute_trends`). Every series carries `(definition, provenance)` labels (PRINCIPLES #6); CLI never prints an unlabeled/blended number.
- Regime boundaries derive from `BAN_EVENTS` (SSOT) — no re-listing; half-open `[since, until)` so an event on a ban date lands in the new regime (tested). All SQL parameterized (`?`), no injection. No foundation-doc drift (`analytics/trends.py` matches ARCHITECTURE).
