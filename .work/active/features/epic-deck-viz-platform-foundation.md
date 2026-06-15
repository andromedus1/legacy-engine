---
id: epic-deck-viz-platform-foundation
kind: feature
stage: done
tags: [viz]
parent: epic-deck-viz-platform
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-06-01
updated: 2026-06-14
---

# viz/ Foundation — theme, strip-and-inject, render, validation

## Brief
The bottom of the `viz/` stack that every other feature builds on: the canonical theme, the
strip-and-inject step, the two render paths, and the test-time validation harness. Delivers
`viz/theme.py` (the `screen` + `print` theme dicts sharing palette/fonts, differing only in
background + font sizing; the Okabe-Ito categorical palette + `redyellowgreen` diverging scale) plus
`strip_and_inject(spec, variant)` (deep-copy → pop top-level `config` → inject the theme dict, per
vega-embed #27), and `viz/render.py` with `render_png(spec) -> bytes` (via
`vl_convert.vegalite_to_png(spec, scale=VIZ_PNG_SCALE, vl_version="6.4")`) and
`render_html_tile(spec) -> str` (via `vl_convert.vegalite_to_html(spec, bundle=True)`, self-contained).

Adds the runtime dependency `vl-convert-python>=1.9,<2`, plus the viz constants in `config.py`
(`VIZ_DIR`, `VIZ_PNG_SCALE`, VL version, `$schema` URL, CDN version triple — no I/O on import; theme
color tokens live in `viz/theme.py`). Establishes the **test-time** validation harness: a shared
`assert_renders(spec)` helper (render → non-empty PNG bytes via the real Vega-Lite compiler in
vl-convert — the structural gate) plus the JSON-snapshot fixture convention every later builder will use.
(No `jsonschema` dep — see `## Design decisions`.)

This feature does NOT author any chart specs (that's charts-migration + dashboard) and does NOT build
the dashboard page or CLI. It is pure plumbing + conventions.

## Epic context
- Parent epic: `epic-deck-viz-platform`
- Position in epic: **foundation feature** — charts-migration and dashboard both depend on its theme,
  strip-and-inject, render paths, and validation/snapshot convention.

## Inherited design decisions
- **vl-convert-python is the single render dependency** — `vegalite_to_png` (PNG) + `vegalite_to_html`
  (self-contained HTML). Pin `>=1.9,<2`; pass dicts directly; `vl_version="6.4"`.
- **Author specs as hand-built Vega-Lite v6 dicts, not Altair.**
- **No runtime validator / correction-loop** — validation is test-time (the real Vega-Lite compiler via
  vl-convert `render`) + JSON snapshots. (Brief §1, §2.2, §3.4; the `jsonschema` mechanism the brief
  suggested was dropped — see `## Design decisions`.)
- **Strip-and-inject is mandatory** and baked into BOTH render paths so HTML and PNG match (Brief §3.2).
- **Two theme variants** (`screen`/`print`), Okabe-Ito categorical + `redyellowgreen` diverging
  (heatmap keeps the MTG-conventional scale; categorical uses colorblind-safe Okabe-Ito) (Brief §3.3).
- Patterns: `constants-only-config` (all viz constants in `config.py`, mkdir at write time),
  result/record types as `@dataclass` not `LegacyEngineModel` (`pydantic-base-model` deviation note).

## Design decisions
- **Theme = dark + minimal** (the maintainer, `--only-questions`). The screen/HTML variant uses a **dark
  background with light text and thin light-grey axes**, minimal chrome. This **overrides the brief's
  transparent/white screen spec** (Brief §3.3). Keep two variants (`screen`/`print`) but both in the
  dark family by default; a light/white `print` variant may be added later only if shareable-on-white
  PNGs are wanted. Implementation notes for `theme.py`:
  - On a dark bg the Okabe-Ito categorical palette's black `#000000` entry is invisible — swap it for a
    light tone (e.g. near-white/light-grey) so every category stays legible.
  - Flip title/axis/legend text + gridline colors to light tones (invert the brief's neutral-grey set).
  - Verify the `redyellowgreen` win-rate heatmap and the masked-cell grey both read well on dark.
- (No other open forks at this tier — schema-validation mechanism for the `jsonschema` test, vendored
  VL-v6 schema vs relying on vl-convert's own render-time validation, and exact render signatures are
  feature-design judgment calls.)

## Research briefs
- [docs/briefs/deck-viz-platform.md](../../../docs/briefs/deck-viz-platform.md) — §2 (vl-convert facts +
  API), §3.1–3.4 (module conventions, strip-and-inject algorithm, theme fields, test-time validation).

## Foundation references
- `docs/ARCHITECTURE.md` — the committed `viz/` module section (presentation layer) + the Dependencies
  table (vl-convert-python, drop-matplotlib-later note).

## Design decisions (added at feature-design, autopilot judgment)
- **Validation = vl-convert render + JSON snapshots; NO `jsonschema` dep.** `vl_convert.vegalite_to_png`
  runs the actual Vega-Lite compiler and raises `ValueError` on a structurally invalid spec — strictly
  stronger than validating against a hand-vendored VL schema, and needs no ~MB schema file and no network
  (honours the no-network-at-test ethos). So the structural gate is a shared `assert_renders(spec)`
  helper (render → assert non-empty PNG bytes); spec-shape stability is JSON snapshot fixtures. This
  supersedes the brief's "jsonschema against the VL v6 schema" note — `jsonschema` is NOT added as a dep.
- **Theme color tokens live in `viz/theme.py`** (styling, tightly bound to the `THEME` dicts), not
  `config.py`. `config.py` holds only the structural constants (dir, scale, VL version, CDN triple,
  `$schema` URL) per `constants-only-config`.
- **Tests are flat** (`tests/test_viz_theme.py`, `tests/test_viz_render.py`) — the project keeps a flat
  `tests/` dir, no per-package subdirs.
- **PNG uses the `print` variant, HTML uses `screen`** — both dark per the maintainer's decision; the only delta
  is font sizing (print larger). vl-convert ValueError propagates (the CLI layer wraps it later).

## Architectural choice
Thin plumbing module: `viz/theme.py` (theme dicts + `strip_and_inject`) and `viz/render.py` (two render
functions wrapping `vl_convert`), with structural constants in `config.py`. No `viz/models.py` yet — the
chart-prep model dataclasses arrive with the charts-migration feature; the foundation authors no specs.
Considered (A) one combined `viz/core.py` — rejected, the theme/render split mirrors the ARCHITECTURE
module map and keeps `strip_and_inject` unit-testable without invoking the renderer; (B) a class-based
`Renderer` — rejected, free functions match the project's module-function idiom (analytics/advisory are
function-first, dataclass records). Chosen: free functions + module-level `THEME` dict.

## Implementation Units

### Unit 1: viz constants in config.py
**File**: `src/legacy_engine/config.py` (append a `# ── Visualization ──` section)
```python
# ── Visualization ──
VIZ_DIR = DATA_DIR / "viz"                 # default output dir; mkdir at write time, never on import
VIZ_PNG_SCALE = 2.0                        # vl_convert PNG scale multiplier (2x for crisp raster)
VIZ_VL_VERSION = "6.4"                     # vl_convert vl_version pin (bundled set tops out at 6.4)
VL_SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v6.json"  # spec "$schema" value
VIZ_CDN_VEGA = "https://cdn.jsdelivr.net/npm/vega@6"               # dashboard template (later feature)
VIZ_CDN_VEGA_LITE = "https://cdn.jsdelivr.net/npm/vega-lite@6"     # matches vl-convert's bundled JS
VIZ_CDN_VEGA_EMBED = "https://cdn.jsdelivr.net/npm/vega-embed@7"
```
**Acceptance Criteria**:
- [ ] `import legacy_engine.config` creates no directories / makes no network calls (existing
  `test_config.py` invariant still holds).
- [ ] All paths absolute + rooted at `PROJECT_ROOT`.

### Unit 2: viz/theme.py — dark theme + strip-and-inject
**File**: `src/legacy_engine/viz/theme.py`
```python
from __future__ import annotations
import copy

# Okabe-Ito categorical, colorblind-safe, with the original #000000 swapped for a light
# tone so every category stays visible on the dark background.
CATEGORICAL: list[str] = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7", "#E6E6E6",   # was #000000
]
_BG = "#15181C"          # dark background
_TEXT = "#E6E6E6"        # light primary text
_AXIS = "#9AA0A6"        # light-grey axis labels
_GRID = "#2A2E33"        # subtle dark gridlines
_DOMAIN = "#3A3F45"

def _variant(*, title_size: int, label_size: int) -> dict:
    return {
        "background": _BG,
        "font": "'Helvetica Neue', Arial, system-ui, sans-serif",
        "title": {"fontWeight": 600, "color": _TEXT, "fontSize": title_size},
        "axis": {"labelColor": _AXIS, "titleColor": _TEXT, "labelFontSize": label_size,
                 "titleFontSize": label_size, "tickColor": _DOMAIN, "domainColor": _DOMAIN,
                 "gridColor": _GRID},
        "legend": {"labelColor": _TEXT, "titleColor": _TEXT},
        "view": {"stroke": "transparent"},
        "range": {"category": CATEGORICAL, "diverging": "redyellowgreen"},
    }

THEME: dict[str, dict] = {
    "screen": _variant(title_size=15, label_size=12),   # interactive HTML
    "print":  _variant(title_size=18, label_size=14),   # static PNG
}

def strip_and_inject(spec: dict, *, variant: str = "screen") -> dict:
    """Deep-copy, drop any top-level config (vega-embed #27), inject the canonical theme."""
    out = copy.deepcopy(spec)
    out.pop("config", None)
    out["config"] = THEME[variant]
    return out
```
**Implementation Notes**:
- Only the **top-level** `config` is stripped (Layer-1, matches ds-engine); inline `mark.color` overrides
  are a builder concern, not handled here.
- `redyellowgreen` diverging is kept for the win-rate heatmap (MTG-conventional); verify legibility on
  `_BG` during charts-migration.
**Acceptance Criteria**:
- [ ] `strip_and_inject({"config": {"x": 1}, "mark": "bar"})["config"] == THEME["screen"]` and the
  input dict is not mutated.
- [ ] Both variants' `background == "#15181C"` (dark); neither is white/transparent.
- [ ] `"#000000" not in THEME[v]["range"]["category"]` for both variants; len == 8.
- [ ] `THEME["print"]["title"]["fontSize"] > THEME["screen"]["title"]["fontSize"]`.

### Unit 3: viz/render.py — the two render paths
**File**: `src/legacy_engine/viz/render.py`
```python
from __future__ import annotations
import vl_convert as vlc
from legacy_engine.config import VIZ_PNG_SCALE, VIZ_VL_VERSION
from legacy_engine.viz.theme import strip_and_inject

def render_png(spec: dict, *, variant: str = "print", scale: float = VIZ_PNG_SCALE) -> bytes:
    """Render a Vega-Lite spec dict to PNG bytes (offline, no browser). Raises ValueError on bad spec."""
    prepared = strip_and_inject(spec, variant=variant)
    return vlc.vegalite_to_png(prepared, scale=scale, vl_version=VIZ_VL_VERSION)

def render_html_tile(spec: dict, *, variant: str = "screen") -> str:
    """Render a Vega-Lite spec dict to a self-contained interactive HTML document (vega-embed inlined)."""
    prepared = strip_and_inject(spec, variant=variant)
    return vlc.vegalite_to_html(prepared, bundle=True, vl_version=VIZ_VL_VERSION)
```
**Implementation Notes**:
- `vl_convert` accepts a dict directly (no `json.dumps`).
- Let `vlc`'s `ValueError` propagate — the `viz` CLI group (dashboard feature) wraps it as a
  `click.ClickException`.
**Acceptance Criteria**:
- [ ] `render_png(minimal_spec)` returns `bytes` starting with the PNG magic `b"\x89PNG"`.
- [ ] `render_html_tile(minimal_spec)` returns a `str` containing `<!DOCTYPE html>` and the chart data.
- [ ] A spec carrying a conflicting top-level `config` still renders (strip-and-inject removed it).

### Unit 4: viz/__init__.py
**File**: `src/legacy_engine/viz/__init__.py`
```python
from legacy_engine.viz.render import render_html_tile, render_png
from legacy_engine.viz.theme import THEME, strip_and_inject
__all__ = ["THEME", "strip_and_inject", "render_png", "render_html_tile"]
```

### Unit 5: pyproject dependency
**File**: `pyproject.toml` — add to `dependencies`:
```toml
"vl-convert-python>=1.9,<2",
```
**Implementation Notes**: install into `.venv` so the render tests run locally + in CI (cp37-abi3
manylinux/macos-arm64 wheels exist; no build toolchain needed). Do NOT add matplotlib removal here —
that is the charts-migration feature's final unit.
**Acceptance Criteria**:
- [ ] `python -c "import vl_convert"` succeeds in `.venv` and CI.

### Unit 6: tests
**Files**: `tests/test_viz_theme.py`, `tests/test_viz_render.py`; a `make_vl_spec` factory fixture in
`tests/conftest.py`.
```python
# conftest.py — minimal valid Vega-Lite bar spec for render/theme tests
@pytest.fixture
def make_vl_spec():
    def _make(**kwargs) -> dict:
        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
            "description": "test bar",
            "data": {"values": [{"a": "x", "b": 3}, {"a": "y", "b": 5}]},
            "mark": "bar",
            "encoding": {"x": {"field": "a", "type": "nominal"},
                         "y": {"field": "b", "type": "quantitative"}},
        }
        spec.update(kwargs)
        return spec
    return _make
```
- `test_viz_theme.py`: the four theme/strip_and_inject acceptance criteria (pure, no vl_convert import).
- `test_viz_render.py`: the three render criteria (imports `vl_convert`; this is the structural-validation
  gate — `assert_renders` = render_png returns PNG-magic bytes). Provide a shared `assert_renders(spec)`
  helper (in conftest) that charts-migration + dashboard reuse on every builder.

## Implementation Order
1. **Unit 1 (config constants)** — no deps; everything references them.
2. **Unit 5 (pyproject dep)** — install vl_convert so render code + tests run.
3. **Unit 2 (theme.py)** — pure; testable without the renderer.
4. **Unit 3 (render.py)** — depends on theme + config + vl_convert.
5. **Unit 4 (__init__)** — re-export surface.
6. **Unit 6 (tests)** — theme tests after Unit 2; render tests + `assert_renders`/`make_vl_spec` after Unit 3.

## Testing
- **Unit (`tests/test_viz_theme.py`)**: strip-and-inject pop+inject+no-mutate; dark bg both variants; no
  black in palette; print fonts > screen fonts.
- **Integration (`tests/test_viz_render.py`)**: render_png → PNG-magic bytes; render_html_tile →
  self-contained HTML string; conflicting-config spec still renders. This doubles as the structural
  validation gate (real Vega-Lite compiler via vl_convert).
- **Test data**: `make_vl_spec` factory (minimal valid bar) + `assert_renders` helper, both in conftest,
  reused by downstream viz features.

## Risks
- **vl-convert wheel must install in CI** (pytest on 3.13). — **Fallback**: abi3 manylinux/macos-arm64
  wheels exist, so this is low risk; if CI ever lacks the wheel, guard the render tests with a
  `pytest.importorskip("vl_convert")` rather than deleting them (keeps the suite green; theme tests still
  run). Default: install it; do NOT skip, since render IS the validation gate.
- **Dark-theme legibility** of `redyellowgreen` + masked-grey on `#15181C` — **Fallback**: tunable via the
  `_BG`/`_GRID` tokens; visually confirmed during charts-migration/dashboard, not blocking foundation.

## Child stories
None — single-stride plumbing feature (~6 tightly-coupled units, one implementation pass). The design IS
the work; stories would be pure overhead.

## Implementation notes

**What landed (all 6 units):**
- `src/legacy_engine/config.py` — `# ── Visualization ──` section appended with 7 constants (`VIZ_DIR`, `VIZ_PNG_SCALE`, `VIZ_VL_VERSION`, `VL_SCHEMA_URL`, `VIZ_CDN_VEGA`, `VIZ_CDN_VEGA_LITE`, `VIZ_CDN_VEGA_EMBED`). No I/O on import; existing `test_config.py` still green.
- `src/legacy_engine/viz/theme.py` — `CATEGORICAL` (8-entry Okabe-Ito, `#000000` → `#E6E6E6`), `_variant()` builder, `THEME` dict with `"screen"` (title 15 / label 12) and `"print"` (title 18 / label 14) variants (both dark bg `#15181C`), and `strip_and_inject(spec, *, variant="screen") -> dict`.
- `src/legacy_engine/viz/render.py` — `render_png(spec, *, variant="print", scale=VIZ_PNG_SCALE) -> bytes` and `render_html_tile(spec, *, variant="screen") -> str` via `vl_convert`; both call `strip_and_inject` first; `ValueError` propagates.
- `src/legacy_engine/viz/__init__.py` — re-exports `THEME`, `strip_and_inject`, `render_png`, `render_html_tile`.
- `pyproject.toml` — `"vl-convert-python>=1.9,<2"` added to `[project] dependencies`.
- `tests/conftest.py` — `make_vl_spec` factory fixture and `assert_renders(spec)` helper added.
- `tests/test_viz_theme.py` — 14 pure unit tests (strip_and_inject + THEME invariants + CATEGORICAL).
- `tests/test_viz_render.py` — 12 integration tests exercising the real Vega-Lite compiler via vl_convert.

**vl-convert version installed:** `vl-convert-python==1.9.0.post1` (wheel: `cp37-abi3-macosx_11_0_arm64`).

**Test count delta:** 1043 → 1076 (+33 tests, all passing).

## Review record
- **Verdict: Approve** (deep lane, fresh-context Claude sub-agent — Codex out of credits, so same-model not cross-model). Commit `c16d262`. All six review axes pass: strip_and_inject (no mutation, top-level-config only), dark theme (bg #15181C, 8-color palette with black→#E6E6E6, light text/axes, print fonts > screen), render_png/render_html_tile (correct vl_convert calls, variant defaults print/screen, ValueError propagates), constants-only-config (no I/O on import), test integrity (33 viz tests exercise the real Vega-Lite compiler — no mocks, no vacuous asserts), patterns conform. No blockers, no important findings. The stale-jsonschema-prose doc nit was fixed in this pass. Suite 1076 green. Advanced review → done.
