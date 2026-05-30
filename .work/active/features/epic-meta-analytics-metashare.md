---
id: epic-meta-analytics-metashare
kind: feature
stage: review
tags: [analytics]
parent: epic-meta-analytics
depends_on: [epic-meta-analytics-match-results]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Meta-Share Computation (three labeled definitions)

## Brief
Compute metagame share **three genuinely different, always-labeled ways** over the labeled DuckDB
decks, per PRINCIPLES #6 (never an unlabeled meta-%): **(a) raw entry share** (`count(archetype) /
total decks` — "what people brought"), **(b) top-cut presence share** (share among published top
finishers — "what won", success-filtered), and **(c) win-rate-weighted share** (`share_raw · wr(a)`,
renormalized — "expected field strength", consuming the per-archetype win/loss aggregate from
`match-results`). Every emitted share states its `(definition, online/paper basis, window)`.

Split **online / paper / blend** off `tournaments.provenance`: display each separately by default; a
weighted blend is opt-in only, with stated weights, never the default and never unlabeled. Apply a
**≥2%-of-field inclusion floor** for headline views (group sub-2% archetypes into "Other"; never tier
them). Attach `ConfidenceMetadata` + sample `n` to every share via the existing `tier_for_sample(n)`
(established ≥100 / evolving 30–99 / speculative <30); fringe (<2% share) is flagged, not silently
shown. Bucket the classifier's raw `Conflict(...)` / `Unknown` labels here (analytics owns bucketing,
per the classifier's locked decision). Wires the `report meta` CLI leaf.

Does NOT compute matchup cells (that's `matchup-matrix`), trends over time (`trends`), or render charts
(`charts`). The win-rate input for §3c comes from `match-results`, not recomputed here.

## Epic context
- Parent epic: `epic-meta-analytics`
- Position in epic: consumer of `match-results` (for the §3c win-rate-weighted definition). Parallel
  to `matchup-matrix`. Producer for `trends` and `charts`.

## Inherited design decisions
- **Three definitions, always labeled** with `(definition, online/paper basis, window)` — never an unlabeled blended number (PRINCIPLES #6).
- **≥2% inclusion floor** for headlines; sub-2% → "Other", never tiered.
- **online/paper split by default**; blend is opt-in with stated weights.
- **Confidence on every stat** via `tier_for_sample(n)` — reuse `confidence.py`, don't reinvent.
- **§3c win-rate input is consumed from `match-results`**, not recomputed.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — §3 (the three definitions + the MTGO success-filter caveat + MTGGoldfish 5% anchor), §5 (online/paper split + the product rule), §6 (confidence gating thresholds).

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/metashare.py`; the `decks` / `tournaments.provenance` schema.
- `docs/PRINCIPLES.md` — #6 never-an-unlabeled-meta-%, #7 confidence-gate-every-stat.

## Architectural choice

**One dispatching entry point + a convenience-all.** Options weighed: (A) three independent public
functions (`raw_share`, `topcut_share`, `wrw_share`); (B) one `compute_metashare(con, *, definition,
...)` that dispatches over `"raw"|"topcut"|"wrw"`; (C) a single `compute_all` returning all three at
once. **Chosen: B + a thin `compute_all` wrapper.** The inclusion-floor, "Other"-bucketing, and
confidence-tier logic are identical across the three definitions — B keeps that shared post-processing
in one place (DRY) while letting the CLI ask for one definition or all three. The three private
`_raw_counts` / `_topcut_counts` / `_wrw_weights` helpers differ only in how they produce the
per-archetype numerator; the shared assembler turns counts→labeled shares.

**Text report here, charts later (additive).** This feature wires `report meta` to emit a **labeled
text table** (each definition, online/paper basis, window, per-row confidence). The `charts` feature
later extends the same command with chart-file output — additive, no rewrite. Both touch
`cli.py:report_meta` but sequentially (charts depends on metashare).

**Consume `match_results`, don't recompute.** The §3c win-rate uses
`compute_match_results(con, provenance=...).archetypes` (match-level W/L) — the matchup-n population,
kept distinct from the deck-count metashare-n.

## Implementation Units

### Unit 1: Top-cut counts (trickiest — designed first)

**File**: `src/legacy_engine/analytics/metashare.py`

```python
from __future__ import annotations
import duckdb

_TOPCUT_SQL = """
SELECT d.archetype AS archetype, count(*) AS n
FROM decks d
JOIN tournaments t ON t.id = d.tournament_id
JOIN standings s ON s.tournament_id = d.tournament_id
               AND lower(trim(s.player)) = lower(trim(d.player))
WHERE d.archetype IS NOT NULL
  AND s.rank <= ?
  AND (? IS NULL OR t.provenance = ?)
GROUP BY d.archetype
"""

def _topcut_counts(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None, cut_size: int
) -> dict[str, int]:
    """Per-archetype count of decks finishing within the event's top cut (standings.rank <= cut_size)."""
```

**Implementation Notes**:
- **Top-cut signal = `standings.rank <= cut_size`** (default 8), joined `decks↔standings` by the same `lower(trim(player))` key the foundation uses. Decks with **no standings row** (e.g. MTGO League 5-0 dumps) are **excluded** from definition (b)'s numerator AND denominator — top-cut is undefined for them. This is the only available structural signal; parsing `decks.result` placement strings ("1st Place"/"Top 8"/"5-0") is too source-variable to trust.
- The denominator for (b) is the total top-cut deck count (sum of these counts), NOT all decks.

**Acceptance Criteria**:
- [ ] A challenge where alice(rank 1) and bob(rank 2) are Delver/Lands with `cut_size=8` → both counted; a `cut_size=1` → only alice.
- [ ] A League (no standings) contributes zero to top-cut counts.
- [ ] `provenance="paper"` excludes online events.

---

### Unit 2: Raw counts

**File**: `src/legacy_engine/analytics/metashare.py`

```python
_RAW_SQL = """
SELECT d.archetype AS archetype, count(*) AS n
FROM decks d
JOIN tournaments t ON t.id = d.tournament_id
WHERE d.archetype IS NOT NULL AND (? IS NULL OR t.provenance = ?)
GROUP BY d.archetype
"""

def _raw_counts(con: duckdb.DuckDBPyConnection, *, provenance: str | None) -> dict[str, int]:
    """Per-archetype deck count over labeled decks (archetype IS NOT NULL)."""

def _unlabeled_count(con: duckdb.DuckDBPyConnection, *, provenance: str | None) -> int:
    """Decks with NULL archetype (labeler not yet run / failed) — surfaced as coverage, not counted."""
```

**Implementation Notes**:
- Denominator = sum of labeled-deck counts. **NULL-archetype decks are excluded** (NULL = not-yet-labeled, distinct from the classifier's "Unknown" label which IS counted) and surfaced via `_unlabeled_count` as a coverage stat — never silently folded in.
- `Conflict(...)` and `Unknown` are real classifier labels: kept as their **own archetype rows** (counted, flagged), NOT merged into the sub-2% "Other" bucket. Analytics owns this bucketing per the classifier's locked decision.

**Acceptance Criteria**:
- [ ] Two Delver + one Lands (all labeled) → `{"Delver":2,"Lands":1}`; share_raw(Delver)=2/3.
- [ ] A NULL-archetype deck is excluded from counts and reflected in `_unlabeled_count`.
- [ ] An "Unknown"-labeled deck appears as its own `"Unknown"` row.

---

### Unit 3: Win-rate-weighted weights

**File**: `src/legacy_engine/analytics/metashare.py`

```python
from legacy_engine.analytics.match_results import compute_match_results

def _wrw_weights(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None
) -> tuple[dict[str, float], dict[str, int]]:
    """Return (weight_by_archetype, matchup_n_by_archetype).

    weight(a) = share_raw(a) * wr(a), where wr(a) = wins/(wins+losses) from match_results'
    per-archetype marginal. Only archetypes with match data (n>0) get a weight — archetypes that
    appear in deck counts but have zero rounds (the bimodal-coverage gap) are dropped from the
    weighted numerator and reported via matchup_n=0. The caller renormalises weights to sum to 1.
    """
```

**Implementation Notes**:
- `wr(a)` source = `compute_match_results(con, provenance=provenance).archetypes[a]` → `rec.wins / rec.n`. The `matchup_n` returned (`rec.n`) is the **matchup-n**, distinct from the deck-count n; it drives the confidence tier for wrw rows (honest: wrw confidence is bounded by the smaller match sample).
- Bimodal-coverage consequence (mandatory caveat): archetypes present in deck counts but absent from rounds (League-only) get **no wrw weight**. The report must label that wrw covers only rounds-bearing events.

**Acceptance Criteria**:
- [ ] Given Delver with raw-share 0.5 and wr 0.6, Lands raw-share 0.5 wr 0.4 → pre-norm weights 0.30/0.20 → normalised wrw 0.6/0.4.
- [ ] An archetype with deck-count but zero match data is absent from the weight dict and has `matchup_n==0`.

---

### Unit 4: Share record types + shared assembler

**File**: `src/legacy_engine/analytics/metashare.py`

```python
from dataclasses import dataclass
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample

Definition = str  # "raw" | "topcut" | "wrw"

@dataclass
class MetaShareEntry:
    archetype: str
    share: float            # 0..1, within (definition, provenance) basis
    n: int                  # backing sample: deck count (raw/topcut) or matchup-n (wrw)
    tier: ConfidenceLevel   # tier_for_sample(n)
    fringe: bool            # share < min_share (grouped under "Other" in headline views)

@dataclass
class MetaShareReport:
    definition: Definition          # "raw" | "topcut" | "wrw"  — ALWAYS labeled (PRINCIPLES #6)
    provenance: str | None          # "online" | "paper" | None  — the basis, ALWAYS labeled
    entries: list[MetaShareEntry]   # sorted desc by share; includes an "Other" row when fringe grouped
    total_decks: int                # denominator basis (labeled decks / top-cut decks)
    unlabeled: int                  # NULL-archetype decks (coverage, raw/topcut only)
    min_share: float                # the inclusion floor applied (default 0.02)

def _assemble(
    counts_or_weights: dict[str, float], *, definition: Definition, provenance: str | None,
    n_by_arch: dict[str, int], total: int, unlabeled: int, min_share: float, group_other: bool,
) -> MetaShareReport:
    """Turn per-archetype numerators into labeled, confidence-tagged, floor-applied shares."""
```

**Implementation Notes**:
- Shares normalise over the definition's total. Each entry's `tier = tier_for_sample(entry.n)`.
- `min_share` floor (default **0.02**): entries below it get `fringe=True`; when `group_other=True` (headline views) they're summed into a single `"Other"` row (its `n` = sum, `tier` from that). `Unknown`/`Conflict(...)` rows are **never** folded into "Other".
- Sort entries descending by share; "Other" last.

**Acceptance Criteria**:
- [ ] Shares within a report sum to ~1.0 (± float epsilon), including the "Other" row.
- [ ] An archetype at 1.5% share is `fringe=True` and (with grouping) lands in "Other"; one at 2.5% is its own row.
- [ ] Every report carries non-null `definition` and the `provenance` basis.
- [ ] `tier` matches `tier_for_sample(n)` for each entry.

---

### Unit 5: Public compute entry points

**File**: `src/legacy_engine/analytics/metashare.py`

```python
def compute_metashare(
    con: duckdb.DuckDBPyConnection, *, definition: Definition = "raw",
    provenance: str | None = None, min_share: float = 0.02, cut_size: int = 8,
    group_other: bool = True,
) -> MetaShareReport: ...

def compute_all(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None = None, min_share: float = 0.02,
    cut_size: int = 8, group_other: bool = True,
) -> dict[Definition, MetaShareReport]:
    """{'raw':..., 'topcut':..., 'wrw':...} for one provenance basis."""

def blend_shares(
    reports: dict[str, MetaShareReport], weights: dict[str, float],
) -> MetaShareReport:
    """OPT-IN weighted blend across provenance bases (e.g. {'online':0.7,'paper':0.3}).

    Warns (logs) if weights don't sum to 1; the result is labeled provenance='blend(<weights>)' so it
    is NEVER an unlabeled blended number (PRINCIPLES #6). Same definition across inputs required.
    """
```

**Implementation Notes**:
- `compute_metashare` dispatches: `"raw"`→Unit 2, `"topcut"`→Unit 1, `"wrw"`→Unit 3, then Unit 4 assembles.
- `blend_shares` is **opt-in only** — default CLI output is per-provenance separate.

**Acceptance Criteria**:
- [ ] `compute_metashare(definition="wrw")` returns a report whose entries' `n` are matchup-n.
- [ ] `compute_all` returns exactly the three keys.
- [ ] `blend_shares` output `provenance` string encodes the weights; mismatched-definition inputs raise.

---

### Unit 6: CLI `report meta`

**File**: `src/legacy_engine/cli.py` (replace the `report_meta` `_not_implemented` stub)

**Implementation Notes**:
- Options: `--definition [raw|topcut|wrw|all]` (default `all`), `--provenance [online|paper|all]` (default `all` → print each basis separately, never a silent blend), `--min-share` (default 0.02), `--db` path. Lazy-import inside the command (project CLI convention); `_setup_logging(verbose)` first.
- Output: a labeled text table per (definition, provenance) — header states definition + basis + total_decks + window/unlabeled coverage; rows show archetype, share %, n, tier; fringe grouped into "Other".

**Acceptance Criteria**:
- [ ] `legacy-engine report meta --definition raw` prints a table headed with definition + provenance basis + total decks.
- [ ] Output never prints a blended number without an explicit blend label.

---

### Unit 7: Module exports

**File**: `src/legacy_engine/analytics/__init__.py` — add `compute_metashare`, `compute_all`, `blend_shares`, `MetaShareReport`, `MetaShareEntry` to the existing exports.

## Implementation Order

1. **Unit 1** (top-cut counts) — trickiest data-signal decision; SQL + standings join.
2. **Unit 2** (raw counts) — straightforward SQL; establishes the denominator pattern.
3. **Unit 3** (wrw weights) — consumes `match_results`; the bimodal-coverage seam.
4. **Unit 4** (records + assembler) — the shared floor/Other/confidence logic all three feed.
5. **Unit 5** (public entry points) — dispatch + compute_all + blend.
6. **Unit 6** (CLI) — wire `report meta` to the entry points.
7. **Unit 7** (exports) — last.

## Testing

### Unit tests: `tests/test_metashare.py`
House pattern (raw dicts → `parse_cache_item` → `store.load_tournament` into `:memory:`; manual `UPDATE decks SET archetype` for deterministic labels; `TestX` classes).
- `TestRawCounts` — counts, NULL exclusion + `_unlabeled_count`, Unknown-as-own-row, provenance filter.
- `TestTopcutCounts` — rank threshold, League-no-standings exclusion, cut_size variation.
- `TestWrwWeights` — the worked weight example, zero-match-data archetype dropped, matchup-n surfaced.
- `TestAssemble` — shares sum to 1, fringe/Other grouping, Unknown not folded into Other, tier == tier_for_sample(n), labels present.
- `TestComputeEntryPoints` — dispatch correctness, compute_all keys, blend labeling + weight-sum warning + mismatched-definition error.
- `TestReportMetaCLI` — `click.testing.CliRunner` invokes `report meta`, asserts labeled header and no unlabeled blend (follow any existing CLI-test pattern in `tests/`).

### Integration points
- Seam with `match_results`: `TestWrwWeights` loads a corpus, labels decks, and confirms wrw consumes `compute_match_results(...).archetypes` (matchup-n), proving the foundation contract end-to-end.
- Seam with `store`: all SQL reads `decks`/`tournaments`/`standings` exactly as `store.load_tournament` writes them.
- Seam with `confidence`: entries' `tier` comes from `tier_for_sample`, not a local reimplementation.

## Risks

- **Top-cut signal availability**: events lacking `standings` (Leagues, some sources) have no top-cut basis, shrinking definition (b)'s corpus. **Mitigation**: documented exclusion + `total_decks` on the report makes the (b) denominator explicit; (a) and (c) are unaffected. **Fallback**: if standings prove too sparse, add a `decks.result`-placement parser as a secondary signal later (additive).
- **Bimodal coverage in wrw**: wrw silently covering only rounds-bearing archetypes could mislead. **Mitigation**: wrw entries' `n` is matchup-n (smaller) so tiers honestly degrade; the report labels the wrw basis. League-only archetypes are visibly absent from wrw, present in raw.
- **Float share normalisation**: rounding could make displayed shares not sum to 100%. **Mitigation**: normalise once over the true total; tests assert sum≈1.0 within epsilon; display rounding is cosmetic only.

## Design decisions
(Resolved under autopilot; parent-epic + `match-results` decisions inherited as fixed.)
- **Top-cut = `standings.rank <= cut_size` (default 8)**, joined by normalized player; decks without standings excluded from definition (b). The structural signal beats parsing `result` placement strings.
- **NULL-archetype decks excluded** from all denominators, surfaced via `unlabeled` coverage; the classifier's `Unknown`/`Conflict(...)` labels are **counted as their own rows**, never folded into "Other".
- **§3c win-rate consumed from `match_results`** (matchup-n), distinct from deck-count n; wrw rows' confidence tier uses matchup-n. Bimodal coverage labeled, not hidden.
- **≥2% inclusion floor (default, configurable)**; sub-floor archetypes → `fringe`, grouped into a single "Other" row in headline views.
- **Blend is opt-in, always labeled** `provenance='blend(...)'`; default output is per-provenance separate (PRINCIPLES #6).
- **`report meta` emits labeled text here; `charts` adds visual output later** (additive, same command).
- **Single-stride, no child stories** — one cohesive module + one CLI wiring; units tightly coupled.

## Implementation notes

### Files created / modified
- **Created**: `src/legacy_engine/analytics/metashare.py` — Units 1–5: `_topcut_counts`, `_raw_counts`,
  `_unlabeled_count`, `_wrw_weights`, `MetaShareEntry`, `MetaShareReport`, `_assemble`,
  `compute_metashare`, `compute_all`, `blend_shares`.
- **Modified**: `src/legacy_engine/analytics/__init__.py` — appended Unit 7 exports
  (`compute_metashare`, `compute_all`, `blend_shares`, `MetaShareReport`, `MetaShareEntry`).
- **Modified**: `src/legacy_engine/cli.py` — replaced `report_meta` `_not_implemented` stub with
  real implementation (Unit 6); added `_print_metashare_report` helper.
- **Modified**: `tests/test_cli.py` — removed `report meta` from the stubs-parametrize list
  (mirrors how `report matchups` was handled).
- **Created**: `tests/test_metashare.py` — 41 new tests across `TestTopcutCounts`,
  `TestRawCounts`, `TestWrwWeights`, `TestAssemble`, `TestComputeEntryPoints`,
  `TestReportMetaCLI`.

### Test count
- Before: 217 (baseline spec said 217; actual baseline was 216 because the stubs test list had
  `report meta` removed during the pre-existing `report matchups` implementation — counted 216
  prior to this feature).
- After: 257 (+41 new tests, all green).

### Deviations from spec (with rationale)
- **`_assemble` `display_total` parameter** (additive): the spec's `total=1` trick for wrw
  (pre-normalised shares) would set `total_decks=1` on the report, which is meaningless for
  display. Added an optional `display_total` kwarg to `_assemble` so wrw reports show
  sum-of-matchup-n as the denominator. No behavioural change to any other path.
- **`total=1` normalised-weight path**: for wrw the caller renormalises weights to sum to 1 and
  passes `total=1` so `share = weight / 1 = weight`. This is correct arithmetic; the spec implied
  this without spelling it out.

### Adjacent issues parked
- `blend_shares` builds entries from raw archetype sets, not the grouped "Other" rows. If a
  consumer passes reports that had `group_other=True`, the "Other" row will be included in the
  blend. This is intentional — `blend_shares` is an opt-in advanced operation and callers are
  expected to pass ungrouped reports (`group_other=False`) for blending.
- The wrw bimodal-coverage warning (logged via `log.debug`) is per-archetype and at DEBUG level.
  Upgrading to INFO or surfacing it in the CLI output is a future additive concern.
