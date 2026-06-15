---
id: epic-meta-analytics-matchup-matrix
kind: feature
stage: done
tags: [analytics]
parent: epic-meta-analytics
depends_on: [epic-meta-analytics-match-results]
release_binding: v0.1.0
gate_origin: null
created: 2026-05-29
updated: 2026-06-14
---

# Matchup Matrix (Wilson + Beta-Binomial shrinkage + tiers)

## Brief
Turn the directed `(archetype_a, archetype_b) → {wins, losses, n}` aggregates from `match-results`
into a presentable matchup matrix of `MatchupCell`s. Per cell compute: the **raw rate** `p̂ = wins/n`
(always shown with `n`), a **Wilson score 95% CI** (the single default — Wald is forbidden; Jeffreys
as the n≤40 alternative), and a **Beta-Binomial shrunk estimate** `p̃ = (α+wins)/(α+β+n)` with a prior
centered at 50% and modest strength (α=β≈5–10) — so a 3–1 cell reads ~54%, not 75%, while a 200-game
cell is essentially unshrunk. **Display both raw and shrunk — shrinkage is never the only number
shown.** Fix **mirror cells at 50.0%, report n only** (no CI). Define and emit the `MatchupCell` model
(`{wins, n, p_raw, p_shrunk, ci_low, ci_high, tier}`) into `models/`.

Attach a **confidence tier** to each cell via the existing tiering, with the **display gate at n<30**
(advisory-methods resolves the ops brief's n<100 down to n<30 — n<100 is the *established* floor, while
30–99 carries usable directional signal the CI honestly bounds): n<30 **speculative** → hide the rate,
show "n=X, insufficient"; 30–99 **evolving** → shrunken rate + Wilson CI, flagged; ≥100 **established**
→ rate + CI, full confidence. Carry the **mandatory bimodal-coverage caveat**: matchup-n ≪ metashare-n
(only rounds-bearing events contribute), kept as a separate labeled field, with a provenance line on
every matrix. Row inclusion gated at ≥2%-of-matches (mtgdecks-style). Online/paper split honored.
Wires the `report matchups` CLI leaf. Prefer `statsmodels.stats.proportion.proportion_confint` for the
Wilson/Jeffreys CIs (hand-rolled Wilson acceptable fallback).

Does NOT do the per-archetype rounds join or result parsing (that's `match-results`), the positioning
score / Bayesian MC (that's `epic-advisory`), or chart rendering (`charts`).

## Epic context
- Parent epic: `epic-meta-analytics`
- Position in epic: consumer of `match-results`. Parallel to `metashare`. Producer of the
  `MatchupCell`s that `charts` (heatmap) and downstream `epic-advisory` consume.

## Inherited design decisions
- **Wilson CI as the single default**; Jeffreys for n≤40; Wald forbidden.
- **Beta-Binomial shrinkage** prior centered 50%, α=β≈5–10; **show raw AND shrunk**, never shrunk alone.
- **Mirror fixed at 50.0%**, n only, no CI.
- **Display gate n<30** (hide rate); 30–99 evolving (flagged); ≥100 established — reuse `tier_for_sample`.
- **matchup-n separate from metashare-n** + mandatory bimodal-coverage provenance caveat on every matrix.

## Research briefs
- `docs/briefs/advisory-methods.md` — §1 (matchup-matrix estimation: Wilson formula, Jeffreys, Beta-Binomial shrinkage, the confidence-tier table, the n<30 display gate, the bimodal-coverage caveat, mtgdecks ≥2% row inclusion).
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — §4.3/§4.5 (bimodal coverage, external-matrix cross-check is validation-only), §6 (gating).

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/matchup.py`; `models/` `MatchupCell` + `ConfidenceMetadata`.
- `docs/SPEC.md` — `MatchupCell` entity; confidence-gating + source-transparency NFRs.
- `docs/PRINCIPLES.md` — #7 confidence-gate-every-stat.

## Architectural choice

**Self-describing `MatchupCell`.** Options weighed: (A) cell carries only raw `{wins, n}`, a separate
render layer derives CI/shrinkage/tier/display; (B) cell carries the fully computed stats + a `display`
flag, so it's self-describing; (C) compute lazily via properties. **Chosen: B.** The matchup matrix is
consumed by both `charts` (heatmap) and the downstream `epic-advisory` (positioning score reads cells) —
"Contracts Before Implementations" + "Match API to Consumer" say compute once and hand consumers a
complete, honest cell. A render layer that re-derives (A) would duplicate the n<30 gate logic across
charts and advisory; lazy (C) hides the gate behind property calls. B puts every gate decision in the
cell at build time.

**Additive `mirror_n` on `MatchResults`.** The brief requires mirror cells to "report n only," but
`match-results` carries only a global `coverage.mirror_matches`. Per that feature's documented,
non-breaking fallback, this feature adds a per-archetype `mirror_n: dict[str, int]` to `MatchResults`
and populates it in `compute_match_results` (one extra dict, incremented per mirror match) — additive,
no existing field changes, existing tests unaffected. This is the only edit this feature makes to the
`match-results` module.

**Text report here, heatmap later (additive).** Wires `report matchups` to a labeled text matrix;
`charts` adds the heatmap image over the same `MatchupMatrix` object.

## Implementation Units

### Unit 1: Additive `mirror_n` on MatchResults

**File**: `src/legacy_engine/analytics/match_results.py` (additive only)

**Implementation Notes**:
- Add field `mirror_n: dict[str, int]` to the `MatchResults` dataclass (default-constructed empty in `compute_match_results`).
- In the mirror branch of `compute_match_results`, `mr_mirror[arch1] = mr_mirror.get(arch1, 0) + 1` alongside the existing `coverage.mirror_matches += 1` and the +1/+1 marginal.
- Touch nothing else. Add one test to `tests/test_match_results.py` asserting `mirror_n` populates for a two-same-archetype pairing and stays empty otherwise.

**Acceptance Criteria**:
- [ ] Two Delver players paired → `MatchResults.mirror_n == {"Delver": 1}`; `coverage.mirror_matches == 1` (unchanged behavior).
- [ ] All 171 existing tests still pass (additive field, no behavior change).

---

### Unit 2: Stats primitives — CI + shrinkage (trickiest — designed first)

**File**: `src/legacy_engine/analytics/matchup.py`

```python
from __future__ import annotations
from statsmodels.stats.proportion import proportion_confint

SHRINK_ALPHA = 7.5  # Beta prior centered 0.5, strength α+β=15 (brief: α=β≈5–10)
SHRINK_BETA = 7.5
JEFFREYS_MAX_N = 40

def wilson_or_jeffreys_ci(wins: int, n: int, *, alpha: float = 0.05) -> tuple[float, float]:
    """95% CI for wins/n. Jeffreys for n<=40 (coherent with the shrinkage prior), Wilson otherwise.

    Returns (low, high) in [0,1]. n==0 → (0.0, 1.0) (no information).
    """

def beta_binomial_shrink(wins: int, n: int, *, a: float = SHRINK_ALPHA, b: float = SHRINK_BETA) -> float:
    """Posterior-mean shrinkage toward 0.5: (a+wins)/(a+b+n). n==0 → 0.5 (the prior mean)."""
```

**Implementation Notes**:
- `wilson_or_jeffreys_ci`: dispatch on `n <= JEFFREYS_MAX_N` → `proportion_confint(wins, n, alpha=alpha, method="jeffreys")` else `method="wilson"`. Guard `n==0` → `(0.0, 1.0)` (statsmodels divides by n).
- `beta_binomial_shrink`: pure arithmetic; a 3–1 cell → (7.5+3)/(15+4)=0.553 (≈54%, matches the brief's worked number); a 200-game 120–80 cell → ≈0.558 (essentially unshrunk).

**Acceptance Criteria**:
- [ ] `beta_binomial_shrink(3,4)` ≈ 0.553; `beta_binomial_shrink(120,200)` ≈ 0.558; `beta_binomial_shrink(0,0)==0.5`.
- [ ] `wilson_or_jeffreys_ci(3,4)` uses Jeffreys (n≤40); `wilson_or_jeffreys_ci(120,200)` uses Wilson; both ⊂ [0,1] and low<high.
- [ ] `wilson_or_jeffreys_ci(0,0) == (0.0, 1.0)`.

---

### Unit 3: MatchupCell model

**File**: `src/legacy_engine/models/matchup.py`

```python
from __future__ import annotations
from legacy_engine.confidence import ConfidenceLevel
from legacy_engine.models.base import LegacyEngineModel

class MatchupCell(LegacyEngineModel):
    """One directed matchup estimate: archetype_a vs archetype_b. Self-describing — carries the
    computed stats AND the display decision so consumers (charts, advisory) never re-derive the gate."""
    archetype_a: str
    archetype_b: str
    wins: int
    n: int                       # matchup-n (decisive a-vs-b matches); NOT metashare-n
    p_raw: float | None          # wins/n; None when n==0
    p_shrunk: float | None       # Beta-Binomial posterior mean; None when n==0 (or 0.5 prior)
    ci_low: float | None
    ci_high: float | None
    tier: ConfidenceLevel        # tier_for_sample(n)
    is_mirror: bool = False      # mirror → p fixed 0.5, no CI
    display: bool = True         # False when n<30 (speculative gate): hide rate, show "n=X, insufficient"
```

**Implementation Notes**:
- Pydantic `LegacyEngineModel` (consumer-facing, exported from `models/`), unlike the internal `match_results` dataclasses — per the locked epic decision.
- Export from `models/__init__.py` (`MatchupCell`).

**Acceptance Criteria**:
- [ ] `MatchupCell` round-trips through Pydantic; `from legacy_engine.models import MatchupCell` works.

---

### Unit 4: Cell builder

**File**: `src/legacy_engine/analytics/matchup.py`

```python
from legacy_engine.confidence import tier_for_sample
from legacy_engine.models.matchup import MatchupCell

DISPLAY_GATE_N = 30  # n<30 → speculative; hide the rate

def build_cell(archetype_a: str, archetype_b: str, wins: int, n: int) -> MatchupCell: ...
def build_mirror_cell(archetype: str, n: int) -> MatchupCell: ...
```

**Implementation Notes**:
- `build_cell`: `tier = tier_for_sample(n)`; `display = n >= DISPLAY_GATE_N`; `p_raw = wins/n if n else None`; `p_shrunk = beta_binomial_shrink(wins,n)`; `(ci_low,ci_high) = wilson_or_jeffreys_ci(wins,n)`. **Both p_raw and p_shrunk always populated** when n>0 (never shrunk-only — brief).
- `build_mirror_cell`: `is_mirror=True`, `p_raw=p_shrunk=0.5`, `ci_low=ci_high=None`, `wins=n//2` (cosmetic), `tier=tier_for_sample(n)`, `display = n >= DISPLAY_GATE_N`.

**Acceptance Criteria**:
- [ ] `build_cell("D","L",3,4)`: `display is False` (n<30), `tier=="speculative"`, p_raw≈0.75, p_shrunk≈0.553, CI set.
- [ ] `build_cell("D","L",60,100)`: `display is True`, `tier=="established"`.
- [ ] `build_cell("D","L",20,40)`: `tier=="evolving"`, `display is False` (40>30 → wait: n=40 ≥30 → display True; tier evolving).
- [ ] `build_mirror_cell("D",50)`: `is_mirror`, `p_raw==0.5`, `ci_low is None`.

---

### Unit 5: Matrix builder

**File**: `src/legacy_engine/analytics/matchup.py`

```python
from dataclasses import dataclass
from legacy_engine.analytics.match_results import compute_match_results

_CAVEAT = ("Matchup data is computed only from rounds-bearing events (Challenges + paper); "
           "matchup-n is a separate, smaller sample than meta-share-n. Cells with n<30 are hidden.")

@dataclass
class MatchupMatrix:
    cells: dict[tuple[str, str], MatchupCell]  # (archetype_a, archetype_b), incl. mirror (a,a)
    provenance: str | None
    total_matches: int          # coverage.decisive_matched
    archetypes: list[str]       # included rows (>= min_row_share of matches), sorted
    caveat: str                 # the mandatory bimodal-coverage provenance line

def build_matrix(
    con, *, provenance: str | None = None, min_row_share: float = 0.02
) -> MatchupMatrix: ...
```

**Implementation Notes**:
- Call `mr = compute_match_results(con, provenance=provenance)`.
- **Row inclusion**: per-archetype match involvement = `mr.archetypes[a].n`; include archetype `a` if `n_a / (2*total_matches)` ≥ `min_row_share` (each decisive match contributes to two marginal counts, so the involvement denominator is `2*total_matches`); always document what was dropped.
- For each ordered pair `(a,b)` of included archetypes with `a != b`: build a cell from `mr.matchups.get((a,b))` (wins, n); skip pairs with no tally (n==0 → still emit a cell with n=0, display False, so the matrix is complete/rectangular).
- For each included `a`: `build_mirror_cell(a, mr.mirror_n.get(a, 0))`.
- `total_matches = mr.coverage.decisive_matched`; `caveat = _CAVEAT`.

**Acceptance Criteria**:
- [ ] A corpus with Delver-beats-Lands 2-1 yields `cells[("Delver","Lands")].wins==1, n==1` and a symmetric `cells[("Lands","Delver")].n==1, wins==0`.
- [ ] An archetype below `min_row_share` of matches is excluded from `archetypes` and gets no cells.
- [ ] Mirror cell present for each included archetype with `is_mirror` and the right n.
- [ ] `total_matches` equals the decisive-match count; `caveat` is non-empty.

---

### Unit 6: CLI `report matchups`

**File**: `src/legacy_engine/cli.py` (replace the `report_matchups` `_not_implemented` stub)

**Implementation Notes**:
- Options: `--provenance [online|paper|all]` (default all → print each basis separately), `--min-row-share` (default 0.02), `--db` path. Lazy import; `_setup_logging(verbose)` first.
- Output: a labeled text matrix — header with total match count + the caveat line; rows/cols = included archetypes; each cell shows the shrunk rate + n, or "n=X (insufficient)" when `display is False`; mirror shows "50% (mirror)".

**Acceptance Criteria**:
- [ ] `legacy-engine report matchups` prints the total-match headline + caveat and a matrix; low-n cells render as insufficient, not as a confident rate.

---

### Unit 7: Exports

**Files**: `src/legacy_engine/models/__init__.py` (add `MatchupCell`); `src/legacy_engine/analytics/__init__.py` (add `build_matrix`, `MatchupMatrix`, `build_cell`, `wilson_or_jeffreys_ci`, `beta_binomial_shrink`).

## Implementation Order

1. **Unit 1** (additive `mirror_n`) — first; unblocks the mirror cell and is isolated/additive.
2. **Unit 2** (CI + shrinkage) — trickiest stats; pure functions, fully unit-testable.
3. **Unit 3** (MatchupCell model) — the contract shape.
4. **Unit 4** (cell builder) — composes 2+3 with the tier/display gate.
5. **Unit 5** (matrix builder) — consumes `match_results` + Unit 4; the integration core.
6. **Unit 6** (CLI) — wire `report matchups`.
7. **Unit 7** (exports).

## Testing

### Unit tests: `tests/test_matchup.py` (+ one case appended to `tests/test_match_results.py` for Unit 1)
House pattern (raw dicts → store → `:memory:`; manual `UPDATE decks SET archetype`; `TestX` classes).
- `TestStats` — `beta_binomial_shrink` worked numbers + n=0 prior; `wilson_or_jeffreys_ci` method dispatch at n=40 boundary, [0,1] containment, n=0 → (0,1).
- `TestCellBuilder` — tier + display gate at n=29/30/100, p_raw/p_shrunk both set, mirror cell shape.
- `TestMatrixBuilder` — directed symmetry, n=0 complete-matrix cells, row-inclusion threshold drops a fringe archetype, mirror cells present with correct n (proves the Unit-1 `mirror_n` seam), `total_matches` + caveat.
- `TestReportMatchupsCLI` — `CliRunner` asserts headline + caveat + low-n "insufficient" rendering.

### Integration points
- Seam with `match_results`: `build_matrix` consumes `compute_match_results(...).matchups` + `.mirror_n` + `.coverage` — a test loads a corpus end-to-end and asserts the cells, proving the additive `mirror_n` field flows through.
- Seam with `confidence`: cell `tier` comes from `tier_for_sample`; display gate constant `DISPLAY_GATE_N=30` matches the speculative threshold.
- Seam with `models`: `MatchupCell` exported and Pydantic-valid.

## Risks

- **Reopening the done `match-results`** for the additive `mirror_n` field: risk of regressing its 171 tests. **Mitigation**: field is additive with an empty default; the mirror branch already exists, we only add one dict increment; Unit 1 adds a dedicated test and re-runs the full suite. **Fallback**: if reopening proves unexpectedly invasive, render mirror cells with `n=0`/no-n and log the limitation (degraded but non-blocking).
- **statsmodels CI at extreme cells** (wins=0 or wins=n): Jeffreys/Wilson both stay in [0,1] (verified — that's why Wald is forbidden), but n=0 must be guarded before the call. **Mitigation**: explicit n==0 → (0,1) guard; tests cover 0/n and n/n.
- **Rectangular vs sparse matrix**: emitting n=0 cells for every unobserved pair keeps the matrix complete for charts but could be large with many archetypes. **Mitigation**: row inclusion (≥2%) bounds the archetype set to ~15–30; an N×N matrix at N≤30 is trivial.

## Design decisions
(Resolved under autopilot; parent-epic + `match-results` decisions inherited as fixed.)
- **Beta-Binomial prior α=β=7.5** (strength 15, centered 0.5); **both p_raw and p_shrunk always shown** (never shrunk-only).
- **CI: Jeffreys for n≤40, Wilson for n>40** (Jeffreys coherent with the shrinkage prior at small n); n=0 → (0,1).
- **Display gate n<30 → `display=False`** (hide rate, show n); tier via `tier_for_sample` (speculative/evolving/established).
- **Mirror: p=0.5, `is_mirror=True`, no CI**, per-archetype n via the **additive `MatchResults.mirror_n`** field (the documented non-breaking match-results extension).
- **Row inclusion ≥2% of matches** (per-archetype marginal involvement / 2·total_matches); unobserved pairs emitted as n=0 cells for a complete matrix.
- **`MatchupCell` is self-describing** (computed stats + display flag), Pydantic in `models/`.
- **Mandatory bimodal-coverage caveat** string attached to every `MatchupMatrix`.
- **`report matchups` text here; `charts` heatmap later** (additive over the same matrix object).
- **Single-stride, no child stories** — one model + one analytics module + CLI + one additive match-results field; tightly coupled.

## Implementation notes

### Files created
- `src/legacy_engine/analytics/matchup.py` — Units 2, 4, 5: stats primitives (`wilson_or_jeffreys_ci`, `beta_binomial_shrink`), cell builders (`build_cell`, `build_mirror_cell`), matrix builder (`MatchupMatrix`, `build_matrix`).
- `src/legacy_engine/models/matchup.py` — Unit 3: `MatchupCell` Pydantic model.
- `tests/test_matchup.py` — 47 new tests across `TestMirrorN`, `TestStats`, `TestMatchupCellModel`, `TestCellBuilder`, `TestMatrixBuilder`, `TestReportMatchupsCLI`.

### Files modified
- `src/legacy_engine/analytics/match_results.py` — Unit 1: added `field` import, `mirror_n: dict[str, int]` field to `MatchResults`, increment in mirror branch of `compute_match_results`.
- `src/legacy_engine/models/__init__.py` — Unit 7: export `MatchupCell`.
- `src/legacy_engine/analytics/__init__.py` — Unit 7: export `MatchupMatrix`, `build_matrix`, `build_cell`, `build_mirror_cell`, `wilson_or_jeffreys_ci`, `beta_binomial_shrink`.
- `src/legacy_engine/cli.py` — Unit 6: replaced `report_matchups` stub with real implementation (`--provenance`, `--min-row-share`, `--db` options; labeled text matrix output).
- `tests/test_match_results.py` — appended two Unit-1 tests (`test_mirror_n_populated_for_same_archetype_pairing`, `test_mirror_n_empty_for_non_mirror_pairing`).
- `tests/test_cli.py` — removed `report matchups` from `test_leaf_stubs_not_implemented` parametrize list (command is now implemented).

### Test count
- Baseline: 171 tests. After removing one stub parametrize case: 170.
- New tests added: 47 (in `test_matchup.py` + appended to `test_match_results.py`).
- Final: **217 tests, all passing**.

### Deviations from spec (with rationale)
1. **`beta_binomial_shrink(120, 200)` ≈ 0.593, not 0.558 as stated in the spec.** The formula `(a+wins)/(a+b+n)` with α=β=7.5 yields `127.5/215 ≈ 0.593`. The spec's `≈0.558` appears to be a transcription error (it matches `(5+120)/(10+200)` with a different prior). The implementation follows the stated formula and constants exactly; tests assert against the formula, not the erroneous approximation.
2. **`MatchResults` uses `field(default_factory=dict)` for `mirror_n`.** The spec described this as "added to the dataclass"; using `field()` is the correct Python way to add a mutable default to a `@dataclass`, avoiding the mutable-default-argument pitfall.
3. **`store.connect` does not call `init_schema` automatically.** The CLI `report matchups` command follows the same pattern as all other CLI commands and does not call `init_schema` — schema creation is the responsibility of `seed cache`. The empty-DB CLI test calls `init_schema` manually to simulate a seeded DB.

### Adjacent issues parked
- The spec's `MatchupCell.p_shrunk: float | None` documentation mentions `None when n==0 (or 0.5 prior)` — slight contradiction. When `n==0`, `p_shrunk` is `None` (not 0.5) for non-mirror cells; mirror cells always get `p_raw=p_shrunk=0.5` regardless of n. This is the correct behavior per the brief (mirror is a special case).
- `report matchups --db` flag requires an existing file (`exists=True`). The default path (DUCKDB_PATH) may not exist in a fresh env; this is consistent with all other CLI commands that read from the DB.
- The text matrix renderer is functional but not polished for wide terminals — this is intentional per the spec ("charts adds the heatmap later over the same matrix object").

## Review (2026-05-29)

**Verdict**: Approve

**Blockers**: none
**Important**: none
**Nits**:
- Row-inclusion denominator (`matchup.py:187`): `denom = 2 * total_matches` counts only non-mirror decisive matches, but the numerator `rec.n` includes each archetype's mirror contributions (+1/+1 per mirror). Shares are thus slightly inflated when mirrors exist — affects only which archetypes clear the 2% *display threshold*, never a displayed rate. Negligible impact (mirrors are a small fraction; over-inclusion is the safe direction). Left as-is; a future refinement could use `denom = sum(rec.n for rec in mr.archetypes.values())`.
- `build_matrix(con, ...)` lacks a `con` type annotation (other module fns type it `duckdb.DuckDBPyConnection`).

**Notes**:
- Verified the implementer's spec-vs-formula catch: `beta_binomial_shrink(120,200)=0.593` is correct per `(7.5+120)/(15+200)`; the design's `0.558` was my transcription error. Implementation correctly follows the formula. Confirmed `shrink(3,4)=0.5526`, `shrink(0,0)=0.5`, `ci(0,0)=(0.0,1.0)`, `ci(3,4)` uses Jeffreys.
- Verified the `tests/test_cli.py` change is legitimate: `report matchups` removed only from the *not-implemented stub* parametrize; the group-help coverage test still asserts it appears under `report --help`.
- SQL flows through `match_results`' parameterized join (no injection). CLI renders confidence honestly (low-n → "insufficient", mirror → "50% (mirror)"), carries the bimodal caveat. `MatchupCell` self-describing + Pydantic in `models/` per the locked decision. 47 tests; foundation (architecture's `matchup.py`/`MatchupCell`) already matched — no doc drift.
