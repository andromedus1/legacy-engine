"""Dashboard layout — Tile/Dashboard dataclasses + HTML template renderer.

Provides the 12-column CSS grid model for a self-contained dark HTML dashboard page.
Chart tiles are embedded via ``vegaEmbed`` with the spec inlined as JSON.  HTML tiles
are inlined directly.  The dark page background matches the chart theme.

Usage::

    from legacy_engine.viz.layout import Tile, Dashboard, render_dashboard_html
    dash = Dashboard(title="Dimir Tempo", tiles=[...])
    html = render_dashboard_html(dash)
    Path("deck.html").write_text(html)
"""

from __future__ import annotations

import html as _html_escape
import json
from dataclasses import dataclass, field

from legacy_engine.config import VIZ_CDN_VEGA, VIZ_CDN_VEGA_EMBED, VIZ_CDN_VEGA_LITE
from legacy_engine.viz.theme import _BG, _TEXT, strip_and_inject


@dataclass
class Tile:
    """One slot in the dashboard 12-column grid.

    ``kind``     — "chart" or "html"
    ``title``    — tile heading (displayed above the tile)
    ``col_span`` — integer 1..12 (CSS ``grid-column: span N``)
    ``spec``     — Vega-Lite spec dict (chart tiles only; None for html tiles)
    ``html``     — raw HTML content (html tiles only; None for chart tiles)
    """

    kind: str          # "chart" | "html"
    title: str
    col_span: int      # 1..12
    spec: dict | None = None
    html: str | None = None


@dataclass
class Dashboard:
    """A titled collection of tiles that render as a 12-col dark HTML page."""

    title: str
    tiles: list[Tile] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PAGE_CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: {_BG};
    color: {_TEXT};
    font-family: 'Helvetica Neue', Arial, system-ui, sans-serif;
    padding: 1.5rem;
}}
h1.dashboard-title {{
    font-size: 1.6rem;
    font-weight: 700;
    margin-bottom: 1.25rem;
    color: {_TEXT};
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 1rem;
}}
.tile {{
    background: #1E2228;
    border-radius: 6px;
    padding: 1rem;
    overflow: hidden;
}}
.tile h2 {{
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #9AA0A6;
    margin-bottom: 0.75rem;
}}
.vega-embed {{
    width: 100%;
}}
""".strip()

_VEGA_EMBED_SNIPPET = """\
<script>
  document.addEventListener('DOMContentLoaded', function() {{
    var el = document.getElementById('{el_id}');
    var spec = {spec_json};
    vegaEmbed(el, spec, {{actions: false, renderer: 'svg'}}).catch(console.error);
  }});
</script>
"""


def _tile_html(tile: Tile, idx: int) -> str:
    """Render one tile slot to HTML (chart or html kind)."""
    tile_id = f"tile-{idx}"

    style = f"grid-column: span {tile.col_span};"
    lines = [f'<div class="tile" style="{style}">']
    if tile.title:
        safe_title = _html_escape.escape(tile.title)
        lines.append(f'  <h2>{safe_title}</h2>')

    if tile.kind == "chart" and tile.spec is not None:
        # Theme-inject the spec before inlining (HTML match PNG)
        prepared = strip_and_inject(tile.spec, variant="screen")
        spec_json = json.dumps(prepared, separators=(",", ":"))
        el_id = f"vega-{idx}"
        lines.append(f'  <div id="{el_id}" class="vega-embed"></div>')
        lines.append(
            _VEGA_EMBED_SNIPPET.format(el_id=el_id, spec_json=spec_json)
        )
    elif tile.kind == "html" and tile.html is not None:
        # HTML tile — embed directly
        lines.append(f'  <div class="html-tile-content">{tile.html}</div>')
    else:
        lines.append('  <div><em>(empty tile)</em></div>')

    lines.append("</div>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public renderer
# ---------------------------------------------------------------------------


def render_dashboard_html(dash: Dashboard, *, offline: bool = False) -> str:
    """Render a Dashboard to a self-contained dark HTML page.

    In CDN mode (default), the ``<head>`` includes three ``<script>`` tags
    pointing at ``vega@6``, ``vega-lite@6``, and ``vega-embed@7`` from
    ``config.VIZ_CDN_*``.  In offline mode (``offline=True``), a single
    inlined JS bundle from ``vl_convert.javascript_bundle()`` is used instead
    — no CDN references at all.

    Each chart tile embeds its spec as inline JSON and calls ``vegaEmbed``.
    HTML tiles are inlined verbatim.  The dark page background matches the
    canonical theme (``_BG``).

    Args:
        dash:    A ``Dashboard`` dataclass with title and tiles list.
        offline: Inline the vl_convert JS bundle (fully self-contained; no CDN).

    Returns:
        Full ``<!DOCTYPE html>`` document string.
    """
    # Build the <head> scripts section.
    if offline:
        import vl_convert as vlc  # lazy; only needed in offline mode
        bundle_js = vlc.javascript_bundle()
        scripts_html = f"<script>{bundle_js}</script>"
    else:
        scripts_html = "\n".join([
            f'<script src="{VIZ_CDN_VEGA}"></script>',
            f'<script src="{VIZ_CDN_VEGA_LITE}"></script>',
            f'<script src="{VIZ_CDN_VEGA_EMBED}"></script>',
        ])

    # Render tile HTML.
    tile_parts = [_tile_html(tile, idx) for idx, tile in enumerate(dash.tiles)]

    safe_title = _html_escape.escape(dash.title)

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{safe_title}</title>
  {scripts_html}
  <style>
{_PAGE_CSS}
  </style>
</head>
<body>
<h1 class="dashboard-title">{safe_title}</h1>
<div class="grid">
{chr(10).join(tile_parts)}
</div>
</body>
</html>"""
    return doc
