"""Render paths for Vega-Lite specs — PNG (offline raster) and HTML (self-contained).

Both paths call ``strip_and_inject`` before handing the spec to vl_convert, so the
canonical dark theme is always applied and any conflicting top-level ``config`` from
the caller is silently discarded (vega-embed #27).

``vl_convert.ValueError`` propagates to the caller; the CLI layer wraps it as a
``click.ClickException`` (dashboard feature).
"""

from __future__ import annotations

import vl_convert as vlc

from legacy_engine.config import VIZ_PNG_SCALE, VIZ_VL_VERSION
from legacy_engine.viz.theme import strip_and_inject


def render_png(
    spec: dict,
    *,
    variant: str = "print",
    scale: float = VIZ_PNG_SCALE,
) -> bytes:
    """Render a Vega-Lite spec dict to PNG bytes (offline, no browser).

    Args:
        spec: A Vega-Lite spec dict.
        variant: Theme variant to apply — ``"print"`` (default, larger fonts for PNG).
        scale: Device-pixel scale factor; defaults to ``VIZ_PNG_SCALE`` (2.0 for crisp raster).

    Returns:
        Raw PNG bytes.

    Raises:
        ValueError: If vl_convert rejects the spec as structurally invalid.
    """
    prepared = strip_and_inject(spec, variant=variant)
    return vlc.vegalite_to_png(prepared, scale=scale, vl_version=VIZ_VL_VERSION)


def render_html_tile(
    spec: dict,
    *,
    variant: str = "screen",
) -> str:
    """Render a Vega-Lite spec dict to a self-contained interactive HTML document.

    The returned string includes all JS (vega-embed bundled inline) and is safe to
    write directly to a ``.html`` file or embed in a dashboard template.

    Args:
        spec: A Vega-Lite spec dict.
        variant: Theme variant to apply — ``"screen"`` (default, for interactive HTML).

    Returns:
        Full HTML document string.

    Raises:
        ValueError: If vl_convert rejects the spec as structurally invalid.
    """
    prepared = strip_and_inject(spec, variant=variant)
    return vlc.vegalite_to_html(prepared, bundle=True, vl_version=VIZ_VL_VERSION)
