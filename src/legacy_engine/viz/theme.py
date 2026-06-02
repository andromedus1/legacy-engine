"""Canonical dark theme for legacy-engine Vega-Lite charts.

Provides the Okabe-Ito categorical palette (colorblind-safe, with #000000 swapped
for a light tone so every category is visible on a dark background), the shared
``screen`` / ``print`` dark theme dicts, and the ``strip_and_inject`` transformer
that must be applied to every spec before rendering.
"""

from __future__ import annotations

import copy

# Okabe-Ito categorical, colorblind-safe, with the original #000000 swapped for a
# light tone so every category stays visible on the dark background.
CATEGORICAL: list[str] = [
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
    "#E6E6E6",  # was #000000
]

_BG = "#15181C"      # dark background
_TEXT = "#E6E6E6"    # light primary text
_AXIS = "#9AA0A6"    # light-grey axis labels
_GRID = "#2A2E33"    # subtle dark gridlines
_DOMAIN = "#3A3F45"


def _variant(*, title_size: int, label_size: int) -> dict:
    return {
        "background": _BG,
        "font": "'Helvetica Neue', Arial, system-ui, sans-serif",
        "title": {"fontWeight": 600, "color": _TEXT, "fontSize": title_size},
        "axis": {
            "labelColor": _AXIS,
            "titleColor": _TEXT,
            "labelFontSize": label_size,
            "titleFontSize": label_size,
            "tickColor": _DOMAIN,
            "domainColor": _DOMAIN,
            "gridColor": _GRID,
        },
        "legend": {"labelColor": _TEXT, "titleColor": _TEXT},
        "view": {"stroke": "transparent"},
        "range": {"category": CATEGORICAL, "diverging": "redyellowgreen"},
    }


THEME: dict[str, dict] = {
    "screen": _variant(title_size=15, label_size=12),  # interactive HTML
    "print": _variant(title_size=18, label_size=14),   # static PNG
}


def strip_and_inject(spec: dict, *, variant: str = "screen") -> dict:
    """Deep-copy, drop any top-level config (vega-embed #27), inject the canonical theme.

    Args:
        spec: A Vega-Lite spec dict (not mutated).
        variant: One of ``"screen"`` (interactive HTML) or ``"print"`` (static PNG).

    Returns:
        A new dict with ``config`` replaced by ``THEME[variant]``.
    """
    out = copy.deepcopy(spec)
    out.pop("config", None)
    out["config"] = THEME[variant]
    return out
