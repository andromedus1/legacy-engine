---
id: epic-deck-viz-platform-foundation
kind: feature
stage: drafting
tags: [viz]
parent: epic-deck-viz-platform
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
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

Adds the runtime dependency `vl-convert-python>=1.9,<2` and the dev/test dependency `jsonschema`, plus
the viz constants in `config.py` (`VIZ_DIR`, `VIZ_PNG_SCALE`, CDN version triple, palette constants —
no I/O on import). Establishes the **test-time** validation harness: a helper that schema-validates an
emitted spec against the real Vega-Lite v6 schema with `jsonschema`, plus the JSON-snapshot fixture
convention every later builder will use. A non-empty-bytes PNG smoke test exercises the vl-convert
integration end to end.

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
- **No runtime validator / correction-loop** — validation is test-time (`jsonschema` against the real
  VL v6 schema) + JSON snapshots. (Brief §1, §2.2, §3.4.)
- **Strip-and-inject is mandatory** and baked into BOTH render paths so HTML and PNG match (Brief §3.2).
- **Two theme variants** (`screen`/`print`), Okabe-Ito categorical + `redyellowgreen` diverging
  (heatmap keeps the MTG-conventional scale; categorical uses colorblind-safe Okabe-Ito) (Brief §3.3).
- Patterns: `constants-only-config` (all viz constants in `config.py`, mkdir at write time),
  result/record types as `@dataclass` not `LegacyEngineModel` (`pydantic-base-model` deviation note).

## Design decisions
- **Theme = dark + minimal** (Andrew, `--only-questions`). The screen/HTML variant uses a **dark
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
