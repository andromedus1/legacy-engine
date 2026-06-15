---
description: How every `viz` leaf command ends — build a Vega-Lite spec from a `_*_model(...)` adapter, mkdir the output dir, dispatch on output suffix to HTML/PNG renderers, and wrap render `ValueError` as `ClickException("Render failed: …")`. Read before adding a new viz CLI leaf.
type: pattern
kind: planning
updated: 2026-06-14
summary: |
  After the DB connection is closed, each viz leaf runs an identical tail: `spec = spec_*(_*_model(...))`,
  ensure the output dir, suffix-dispatch to `render_html_tile` (.html) / `render_png` (.png), and translate
  any `ValueError` from the render layer into a user-facing `ClickException` with the stable `Render failed:`
  prefix. A new chart type only supplies a `spec_*` + `_*_model` pair.
decisions:
  - "Spec construction happens AFTER `finally: con.close()` — rendering never holds the DB connection."
  - "Models are built via a `_*_model(...)` adapter (viz/models.py), never inlined in the CLI."
  - "Output target is chosen by `out_path.suffix.lower()`: .html -> render_html_tile, else -> render_png."
  - "The render layer signals failure with `ValueError`; the CLI wraps it as `ClickException(\"Render failed: …\")` — the only caught type, with a stable grep-able prefix."
---

# Pattern: Viz CLI spec-model-render-write tail

Every `viz` leaf command ends with the same four-step tail: build a Vega-Lite `spec` from a
`_*_model(...)` adapter, ensure the output directory, dispatch on the output-file suffix to the
HTML or PNG renderer, and wrap any render-layer `ValueError` into a `ClickException` with the
stable `Render failed:` prefix.

## Rationale
The `viz` commands deliberately separate three concerns — DB query (inside `try/finally:
con.close()`), pure spec construction (`viz/specs.py` + `viz/models.py` adapters), and rendering
(`viz/render.py`). The render layer raises `ValueError` on spec-validation / rendering failure; the
CLI uniformly translates that into a user-facing `ClickException` with a consistent, grep-able
prefix. Keeping the tail byte-identical across commands means the html/png contract and the error
surface stay consistent, and adding a new chart type is just supplying a `spec_*` + `_*_model` pair.

## Example (canonical)

**File**: `src/legacy_engine/cli.py` — `viz metashare` (cli.py:4688)
```python
spec = spec_metashare(_metashare_model(report))
out_path = Path(out)
out_path.parent.mkdir(parents=True, exist_ok=True)

try:
    if out_path.suffix.lower() == ".html":
        out_path.write_text(render_html_tile(spec), encoding="utf-8")
    else:
        out_path.write_bytes(render_png(spec))
except ValueError as exc:
    raise click.ClickException(f"Render failed: {exc}") from exc
```

The identical tail recurs at:
- `viz matchups` — `spec_matchup_heatmap(_heatmap_model(inputs.matrix))` (cli.py:4751)
- `viz trends` — `spec_trends(_trends_model(series))` (cli.py:4817)
- `viz tiers` — (cli.py:4883)

## When to use
- Adding a new `viz` leaf command that renders one Vega-Lite tile to either .html or .png.
- Any CLI command consuming the `viz/render.py` functions, which raise `ValueError` on bad specs.

## When NOT to use
- Multi-tile / dashboard rendering that batches several specs (the deck-dashboard path at
  `cli.py:4604` uses `render_png` differently — the single-spec assumption breaks).
- Non-viz commands whose failure modes aren't render `ValueError`s.

## Common violations
- Catching a broad `Exception` instead of `ValueError`, or using a message other than
  `Render failed:` — breaks the grep-able, consistent error surface.
- Building the `spec` before closing the DB connection — the spec step must come after
  `finally: con.close()` so rendering never holds the connection.
- Inlining model construction instead of going through a `_*_model(...)` adapter.
