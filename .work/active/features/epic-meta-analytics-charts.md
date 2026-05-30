---
id: epic-meta-analytics-charts
kind: feature
stage: review
tags: [analytics]
parent: epic-meta-analytics
depends_on: [epic-meta-analytics-metashare, epic-meta-analytics-matchup-matrix, epic-meta-analytics-trends]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-30
---

# Analytics Charts (tier list · meta share · matchup heatmap · trends)

## Brief
The rendering layer over the three analytics data producers. Render matplotlib charts (edh-engine's
charting pattern): a **meta-share chart** (per definition, online/paper), a **matchup heatmap** (the
`MatchupCell` matrix, color-scaled by shrunk rate, low-n cells visually muted/blanked to honor the n<30
display gate), a **tier-list** view (archetypes bucketed by share + confidence), and a **trends chart**
(share trajectories across ban-list regimes from `trends`). Charts must **render confidence honestly**:
suppressed/low-n cells are visibly distinct (not shown as a confident value), and every chart carries
the provenance/caveat line (matchup-n ≪ metashare-n; window; online/paper basis) so a saved image is
self-describing.

Owns the final wiring of the `report meta | matchups | tiers` CLI surface to actually emit charts (and
text summaries) to an output path, replacing the current `_not_implemented` stubs. Reads the computed
results from `metashare`, `matchup-matrix`, and `trends`; it does not recompute any statistic — purely
a presentation + CLI-output feature.

Does NOT compute any meta-share, matchup, or trend statistic (consumes them), and does NOT render
advisory outputs (that's `epic-advisory`'s report surface).

## Epic context
- Parent epic: `epic-meta-analytics`
- Position in epic: terminal feature — consumes `metashare`, `matchup-matrix`, and `trends`; renders
  and wires the CLI report surface. The epic's user-facing payoff.

## Inherited design decisions
- **Charts render confidence honestly**: low-n / suppressed cells visibly distinct; n<30 display gate respected visually.
- **Every chart is self-describing**: provenance/caveat line baked in (matchup-n ≪ metashare-n, window, online/paper basis).
- **Presentation only** — recompute nothing; consume `metashare` / `matchup-matrix` / `trends` outputs.
- Follow **edh-engine's matplotlib charting pattern**.

## Research briefs
- `docs/briefs/advisory-methods.md` — §1 presentation prior art (mtgdecks match-count headline, ≥2% row inclusion, per-cell n<30 hide, CI on every shown cell).
- `docs/briefs/legacy-metagame.md` — the meta as a sanity-check target for the rendered output.

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/charts.py`; the `report meta|matchups|tiers` CLI group; "edh-engine charting pattern".
- `docs/SPEC.md` — source-transparency / confidence-gating NFRs (charts are a surface that must honor them).

## Design decisions
(Resolved under autopilot delegation. Parent-epic + producer (`metashare`/`matchup-matrix`/`trends`)
decisions inherited as fixed. No strategic 50/50s — all pinned by the briefs / producers' public types /
codebase.)

- **Prep/render split is the load-bearing decision.** Each chart is two pieces: a **pure prep helper**
  that turns a producer's result into a render-model (labels, values, a per-cell/per-bar `muted`/`masked`
  flag, and the baked-in caveat string) — fully unit-testable — and a **thin matplotlib renderer** that
  draws the model to a PNG (smoke-tested only: file exists + non-empty). Rationale: the feature's whole
  point is *rendering confidence honestly* (n<30 cells suppressed, fringe distinct), and pixels aren't
  assertable — so the honesty logic MUST live in the testable prep layer, not buried in pyplot calls.
  Rejected: (B) render directly with no prep split — makes the suppression logic untestable; (C) a
  generic chart-strategy abstraction — unearned over 4 structurally-different charts.
- **Presentation only, recompute nothing.** Charts consume `MetaShareReport` (from `compute_metashare`/
  `compute_all`), `MatchupMatrix` (from `build_matrix`), and `TrendSeries` (from `compute_trends`). The
  tier-list **bins existing `raw` shares into S/A/B buckets** — a presentation transform over shares
  already computed, NOT a new statistic (honors "recompute nothing").
- **CLI = additive `--chart-dir DIR`** on `report meta|matchups|trends`, plus implementing the
  `report tiers` stub (text + optional chart). When `--chart-dir` is set, render one PNG per
  already-emitted report with a derived filename (e.g. `meta_raw_online.png`, `matchups_paper.png`,
  `trends_raw.png`, `tiers.png`); text still prints. Default `None` → text-only → **all existing
  report-command tests stay green** (additive, no rewrite — exactly metashare's "charts later" plan).
  Rejected single `--chart PATH` (the commands loop over definition×provenance bases → multiple outputs).
- **Headless backend**: `matplotlib.use("Agg")` at module import, before `pyplot` — file output, no
  display, deterministic in CI.
- **Confidence-honest rendering** (per inherited decisions): matchup heatmap masks `cell.display is
  False` cells (rendered gray/blank, value hidden) and `is_mirror` cells marked; meta-share `fringe`/
  "Other" bars visually distinct (hatch/low alpha); speculative-tier bars muted; trends `thin` regimes
  marked; **every figure carries a caveat/provenance subtitle** (matchup-n ≪ metashare-n; basis; window)
  baked from the producer's own caveat/labels so a saved PNG is self-describing.
- **Tier thresholds** (configurable, default): S ≥ 10%, A 5–10%, B 2–5%, sub-floor (< `min_share`) →
  untiered ("Other"). Each tiered archetype shows its confidence tier; speculative-n archetypes flagged.
- **Single-stride, no child stories** — one cohesive `charts.py` (shared Agg setup + style constants +
  prep/render pairs) plus CLI wiring in one file; the units share the module and the `cli.py` edits
  (write-overlap), so they're one coherent delivery. Mirrors how `metashare`/`trends` were delivered.

## Architectural choice

**One `charts.py` with a (prep-helper, renderer) pair per chart + additive CLI `--chart-dir` wiring.**
The feature is the presentation layer over three data producers. The chosen shape isolates every
confidence-honesty rule (low-n masking, fringe distinction, thin-regime marking, caveat baking) into
pure prep helpers returning render-models, which tests assert on directly; the matplotlib renderers stay
thin and are smoke-tested (PNG written, non-empty). Charts recompute nothing — they read
`MetaShareReport` / `MatchupMatrix` / `TrendSeries` and the already-computed `display`/`tier`/`fringe`/
`thin` flags. CLI output is additive: `--chart-dir` adds PNG emission to the existing text commands and
implements the lone remaining `report tiers` stub, with text-only behavior (and its tests) untouched
when the flag is absent.

## Implementation Units

### Unit 1: Matchup heatmap — prep + render (trickiest; designed first)

**File**: `src/legacy_engine/analytics/charts.py`

```python
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless, before pyplot
import matplotlib.pyplot as plt  # noqa: E402

from legacy_engine.analytics.matchup import MatchupMatrix
from legacy_engine.analytics.metashare import MetaShareReport
from legacy_engine.analytics.trends import TrendSeries
from legacy_engine.confidence import ConfidenceLevel

log = logging.getLogger(__name__)

# Tier-list share thresholds (presentation bins over raw share)
TIER_S_MIN = 0.10
TIER_A_MIN = 0.05
TIER_B_MIN = 0.02
# Visual treatment of confidence (alpha for muted/speculative, hatch for fringe/suppressed)
_SPECULATIVE_ALPHA = 0.35
_SUPPRESSED_HATCH = "////"


@dataclass
class HeatmapModel:
    """Render-model for the matchup heatmap — all honesty logic resolved here (testable)."""

    archetypes: list[str]
    values: list[list[float | None]]   # p_shrunk per (row a, col b); None = masked (suppressed/n=0)
    masked: list[list[bool]]           # True where cell.display is False or n==0 (drawn gray/blank)
    mirror: list[list[bool]]           # True for (a, a) cells
    annotations: list[list[str]]       # per-cell label: "57%\n(n=42)", "n=12", "—", "mirror"
    caveat: str                        # matrix.caveat, baked into the figure subtitle
    title: str


def _heatmap_model(matrix: MatchupMatrix) -> HeatmapModel:
    """Build the heatmap render-model from a MatchupMatrix — masks low-n/unobserved cells.

    A cell is masked (value=None, drawn gray) when ``not cell.display`` (n<30 gate) or ``n==0``.
    Mirror cells are flagged. Displayed cells use ``p_shrunk`` for color and annotate with the
    raw% + n. The caveat is taken verbatim from ``matrix.caveat``.
    """


def render_matchup_heatmap(matrix: MatchupMatrix, out_path: Path | str) -> Path:
    """Render the matchup heatmap to a PNG at ``out_path``; returns the path written.

    Color-scales displayed cells by ``p_shrunk`` (diverging around 0.5); masked cells gray;
    figure carries the title + provenance + ``matrix.caveat`` subtitle. Empty matrix → a
    placeholder figure stating no data (still a valid PNG)."""
```

**Implementation Notes**:
- Mask predicate is `not cell.display or cell.n == 0` — reuses the producer's `display` flag (the n<30
  gate already computed in `build_cell`); charts never re-derive the gate.
- Diverging colormap centered at 0.5 (e.g. `RdYlGn`) over `p_shrunk`; masked cells painted a neutral
  gray via a masked numpy array or per-cell patch; mirror cells annotated "mirror" (no color claim).
- `plt.close(fig)` after every save (no figure leak across the multi-basis CLI loop).

**Acceptance Criteria**:
- [ ] `_heatmap_model` masks every cell with `n < 30` (`display is False`) and every `n==0` cell; sets
      `values[i][j] is None` there and `masked[i][j] is True`.
- [ ] A displayed cell (n≥30) has `values[i][j] == cell.p_shrunk` and an annotation containing its n.
- [ ] Mirror cells `(a, a)` have `mirror[i][i] is True`.
- [ ] `model.caveat == matrix.caveat` (the bimodal-coverage warning is carried through).
- [ ] `render_matchup_heatmap(matrix, tmp)` writes a non-empty PNG; an empty matrix still writes a PNG.

---

### Unit 2: Meta-share chart — prep + render

**File**: `src/legacy_engine/analytics/charts.py`

```python
@dataclass
class BarModel:
    labels: list[str]
    shares: list[float]
    muted: list[bool]        # speculative-tier → muted alpha
    fringe: list[bool]       # fringe / "Other" → distinct hatch
    tiers: list[ConfidenceLevel]
    subtitle: str            # "definition=RAW  basis=online  total_decks=420"
    title: str


def _metashare_model(report: MetaShareReport) -> BarModel:
    """Bar-chart model from a MetaShareReport — speculative bars muted, fringe/Other hatched."""


def render_metashare(report: MetaShareReport, out_path: Path | str) -> Path:
    """Horizontal bar chart of shares; muted speculative bars, hatched fringe/Other; labeled subtitle."""
```

**Implementation Notes**:
- `muted[i] = entry.tier == "speculative"`; `fringe[i] = entry.fringe or entry.archetype == "Other"`.
- Subtitle baked from `report.definition` / `report.provenance` / `report.total_decks` — the chart is
  self-describing and never an unlabeled share (PRINCIPLES #6).

**Acceptance Criteria**:
- [ ] A speculative-tier entry → `muted[i] is True`; an "Other"/fringe entry → `fringe[i] is True`.
- [ ] `subtitle` contains the definition and provenance basis.
- [ ] `render_metashare` writes a non-empty PNG (incl. an empty report → placeholder PNG).

---

### Unit 3: Tier-list — prep + text + render

**File**: `src/legacy_engine/analytics/charts.py`

```python
@dataclass
class TierModel:
    buckets: dict[str, list[tuple[str, float, ConfidenceLevel]]]  # "S"/"A"/"B" -> [(arch, share, tier)]
    subtitle: str
    title: str


def _tier_model(
    report: MetaShareReport, *, s_min: float = TIER_S_MIN, a_min: float = TIER_A_MIN,
    b_min: float = TIER_B_MIN,
) -> TierModel:
    """Bucket a raw MetaShareReport's entries into S/A/B tiers by share (sub-b_min → untiered)."""


def render_tier_list(report: MetaShareReport, out_path: Path | str, **thresholds) -> Path:
    """Render the tier list as a labeled column-per-tier PNG; confidence shown per archetype."""
```

**Implementation Notes**:
- Excludes the "Other" row and `_is_never_other` labels from tiering (they aren't archetypes to tier).
- Pure binning over `entry.share`; no new statistic. Each entry keeps its `tier` for honest display.

**Acceptance Criteria**:
- [ ] An archetype at 12% lands in "S"; 7% → "A"; 3% → "B"; 1% → untiered (absent from buckets).
- [ ] Each bucket entry carries the archetype's confidence tier.
- [ ] `render_tier_list` writes a non-empty PNG.

---

### Unit 4: Trends chart — prep + render

**File**: `src/legacy_engine/analytics/charts.py`

```python
@dataclass
class TrendModel:
    regime_labels: list[str]
    archetypes: list[str]
    series: dict[str, list[float | None]]  # archetype -> share per regime (None where absent)
    thin_regimes: list[bool]               # per-regime thin flag (marked on the x-axis)
    subtitle: str
    title: str


def _trends_model(series: TrendSeries) -> TrendModel:
    """Line-chart model from a TrendSeries — one line per archetype across regimes; thin regimes flagged."""


def render_trends(series: TrendSeries, out_path: Path | str) -> Path:
    """Multi-line share-trajectory chart across ban-list regimes; thin regimes visually marked."""
```

**Implementation Notes**:
- Reuse `series.trajectory(archetype)` for each line; `None` cells create gaps (don't plot 0).
- `thin_regimes[k] = series.regimes[k].thin`; mark thin x-positions (e.g. shaded band / "⚠" tick label).

**Acceptance Criteria**:
- [ ] `series[arch]` has one entry per regime, `None` where the archetype is absent that regime.
- [ ] `thin_regimes` mirrors each regime's `thin` flag.
- [ ] `render_trends` writes a non-empty PNG (empty series → placeholder PNG).

---

### Unit 5: CLI wiring (`--chart-dir` + implement `report tiers`)

**File**: `src/legacy_engine/cli.py`

**Implementation Notes**:
- Add an optional `--chart-dir` (`click.Path(file_okay=False)`) to `report meta`, `report matchups`,
  `report trends`. When set: `Path(chart_dir).mkdir(parents=True, exist_ok=True)`; after printing each
  report/matrix/series, call the matching `render_*` with a derived filename and echo the written path.
- Implement the `report tiers` stub: options `--definition` (default `raw`), `--provenance`,
  `--min-share`, `--db`, `--chart-dir`. Compute `compute_metashare(con, definition=..., provenance=...)`,
  print a text tier list via a new `_print_tier_list(_tier_model(report))`, and render a PNG when
  `--chart-dir` is set. Lazy imports inside the command; `_setup_logging(verbose)` first (project CLI
  pattern).
- Filename helper `_chart_filename(kind, definition, provenance) -> str` → e.g.
  `meta_raw_online.png`, `matchups_all.png`, `trends_raw.png`, `tiers_raw_paper.png`.

**Acceptance Criteria**:
- [ ] `report tiers` (no `--chart-dir`) prints a labeled text tier list (no longer raises
      `_not_implemented`).
- [ ] `report meta --chart-dir D` writes one PNG per (definition, basis) into `D` and still prints text.
- [ ] Omitting `--chart-dir` leaves every command's text output (and existing tests) unchanged.
- [ ] `report tiers --chart-dir D` writes `tiers_*.png`.

---

### Unit 6: Module exports

**File**: `src/legacy_engine/analytics/__init__.py` — export `render_matchup_heatmap`,
`render_metashare`, `render_tier_list`, `render_trends` (and the model dataclasses
`HeatmapModel`, `BarModel`, `TierModel`, `TrendModel`); add to `__all__`.

## Implementation Order

1. **Unit 1** (heatmap prep+render) — trickiest masking/colour logic + the module's Agg setup and style
   constants; everything else follows its prep/render pattern.
2. **Unit 2** (meta-share) — establishes the bar-model pattern.
3. **Unit 3** (tier-list) — prep + text + render.
4. **Unit 4** (trends) — multi-line model.
5. **Unit 5** (CLI) — wire `--chart-dir` across commands + implement `report tiers`.
6. **Unit 6** (exports) — last.

## Testing

### Unit tests: `tests/test_charts.py`
House style (raw dicts → `parse_cache_item` → `store.load_tournament` into `:memory:`; `UPDATE decks SET
archetype`; `TestX` classes; `CliRunner` for CLI). Tests target the **prep helpers** for honesty logic
and **smoke-render** for the matplotlib layer.

- `TestHeatmapModel` — low-n (`display is False`) and `n==0` cells masked; displayed cells carry
  `p_shrunk` + n annotation; mirror cells flagged; `caveat` carried from the matrix.
- `TestMetashareModel` — speculative bars muted; fringe/"Other" flagged; subtitle labeled.
- `TestTierModel` — S/A/B bucket boundaries (12%→S, 7%→A, 3%→B, 1%→untiered); confidence carried;
  "Other"/never-other excluded.
- `TestTrendModel` — per-regime series with `None` gaps; `thin_regimes` mirrors regime flags.
- `TestRenderSmoke` — each `render_*` writes a non-empty PNG to `tmp_path`; empty inputs still write a
  valid (placeholder) PNG; assert `out_path.exists()` and `out_path.stat().st_size > 0`.
- `TestReportTiersCLI` / `TestChartDirCLI` — `report tiers` prints a labeled tier list; `--chart-dir`
  writes expected filenames for meta/matchups/trends/tiers; omitting it preserves text-only output.

### Integration points
- Seam with producers: prep helpers consume `MetaShareReport`/`MatchupMatrix`/`TrendSeries` exactly as
  their producers emit them (a test builds each via the real `compute_*`/`build_matrix` and feeds the
  prep helper) — proves charts recompute nothing.
- Seam with `cli`: `--chart-dir` tests use `CliRunner` against the real DB-backed commands.
- Update `tests/test_cli.py`: remove `report tiers` from the `_not_implemented` stubs-parametrize list
  (mirrors how `report meta`/`report matchups` were handled when implemented).

## Risks

- **Pixels aren't assertable**: a renderer could "succeed" (write a PNG) while drawing the wrong thing.
  **Mitigation**: all honesty logic lives in the pure prep helpers, which are asserted directly;
  renderers are thin and only smoke-tested. **Fallback**: if a rendering regression slips through,
  the prep-model is the contract — fix the renderer to match the (tested) model.
- **Matplotlib figure leaks** across the multi-basis CLI loop → memory growth / state bleed.
  **Mitigation**: `plt.close(fig)` after every save; renderers create their own `fig, ax`.
- **CI headless rendering**: a non-Agg backend would fail without a display. **Mitigation**:
  `matplotlib.use("Agg")` forced at import (before any `pyplot` import), verified by the smoke tests
  running in the suite.
- **Empty / sparse inputs** (no decks, suppressed-everything matrix): **Mitigation**: every renderer
  handles empty by writing a labeled placeholder PNG rather than raising; tested.

## Implementation notes

A prior worker created `src/legacy_engine/analytics/charts.py` (594 lines) with all four
prep helpers, renderers, and model dataclasses fully implemented.  This worker completed
CLI wiring (Unit 5) and the test suite (Unit 6 was already done).

### Files created
- `tests/test_charts.py` — 48 new tests covering all six test classes from the spec.

### Files modified
- `src/legacy_engine/cli.py` — added `--chart-dir` option to `report meta`, `report matchups`,
  `report trends`; replaced `report tiers` `_not_implemented` stub with full implementation;
  added `_print_tier_list` and `_chart_filename` helpers.
- `tests/test_cli.py` — removed `report tiers` from the `_not_implemented` stubs parametrize list.
- `.work/active/features/epic-meta-analytics-charts.md` — stage `implementing → review`; these notes.

### Test counts
- Baseline: 297 passing.
- After: 344 passing (297 baseline − 1 removed tiers-stub test + 48 new test_charts tests = 344).

### Deviations from spec
- **`_chart_filename` for matchups**: the spec example shows `matchups_all.png` (no definition
  segment).  The `report matchups` command has no `--definition` option, so the helper drops
  the definition segment for `kind="matchups"` and produces `matchups_{basis}.png`.  All other
  kinds follow `{kind}_{definition}_{basis}.png` as specified.
- **`_con()` helper in tests**: the spec did not call out that `:memory:` connections need
  `init_schema` called explicitly (unlike file-based connections loaded via `store.load_tournament`).
  The helper was updated to call `init_schema` so empty-corpus tests work correctly; no behaviour
  change to production code.

### Adjacent issues parked
- None identified.
