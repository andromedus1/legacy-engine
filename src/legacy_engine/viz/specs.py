"""Vega-Lite v6 spec builders for the four chart surfaces.

Each builder takes a prep model from ``viz/models.py`` and returns a hand-built
Vega-Lite spec dict.  No Altair.  No ``config`` key — the canonical dark theme is
injected at render time by ``strip_and_inject`` (foundation convention; vega-embed #27).

Builders:
- ``spec_metashare(BarModel)``        — horizontal bar, muted speculative, fringe greyed
- ``spec_matchup_heatmap(HeatmapModel)`` — rect+text layer, redyellowgreen, masked cells null/grey
- ``spec_tier_list(TierModel)``       — horizontal bars faceted by bucket (S/A/B)
- ``spec_trends(TrendModel)``         — line+point, ordinal x, gaps for None, thin-regime bands
"""

from __future__ import annotations

from legacy_engine.config import VL_SCHEMA_URL
from legacy_engine.viz.models import BarModel, HeatmapModel, TierModel, TrendModel


def _base(description: str, title: str) -> dict:
    """Return the minimal required Vega-Lite skeleton (schema + description + title)."""
    return {
        "$schema": VL_SCHEMA_URL,
        "description": description,
        "title": title,
    }


# ---------------------------------------------------------------------------
# spec_metashare — horizontal bar chart of meta shares
# ---------------------------------------------------------------------------


def spec_metashare(m: BarModel) -> dict:
    """Vega-Lite spec: horizontal bar chart of meta-share per archetype.

    Visual semantics:
    - y = archetype label (sorted descending by share — largest at top)
    - x = share (quantitative, formatted as %)
    - opacity 0.35 for speculative-tier bars (muted[i] True)
    - fill colour #9AA0A6 (muted axis-grey) for fringe / "Other" bars; default category colour otherwise
    - tooltip: archetype, share (%), tier
    - subtitle baked from model.subtitle
    """
    # Flatten rows so each bar is one datum.  The opacity and color conditions
    # are expressed as VL conditional encodings over the boolean fields.
    rows = []
    for i, label in enumerate(m.labels):
        rows.append({
            "archetype": label,
            "share": m.shares[i],
            "muted": m.muted[i],
            "fringe": m.fringe[i],
            "tier": str(m.tiers[i]),
        })

    spec = _base(
        description=f"Meta-share horizontal bar chart. {m.subtitle}",
        title={"text": m.title, "subtitle": m.subtitle},
    )
    spec.update({
        "data": {"values": rows},
        "mark": {"type": "bar", "cornerRadiusEnd": 3},
        "encoding": {
            "y": {
                "field": "archetype",
                "type": "nominal",
                "sort": {"field": "share", "order": "descending"},
                "title": "Archetype",
            },
            "x": {
                "field": "share",
                "type": "quantitative",
                "title": "Share",
                "axis": {"format": ".0%"},
            },
            "opacity": {
                "condition": {"test": "datum.muted", "value": 0.35},
                "value": 0.85,
            },
            "color": {
                "condition": {"test": "datum.fringe", "value": "#9AA0A6"},
                "value": "#56B4E9",
            },
            "tooltip": [
                {"field": "archetype", "type": "nominal", "title": "Archetype"},
                {"field": "share", "type": "quantitative", "title": "Share", "format": ".1%"},
                {"field": "tier", "type": "nominal", "title": "Tier"},
            ],
        },
    })
    return spec


# ---------------------------------------------------------------------------
# spec_matchup_heatmap — N×N win-rate grid with text overlay
# ---------------------------------------------------------------------------


def spec_matchup_heatmap(m: HeatmapModel) -> dict:
    """Vega-Lite spec: matchup heatmap (rect + text layer).

    Visual semantics:
    - rows = archetype_a (deck played); columns = archetype_b (opponent)
    - rect fill = p_shrunk on redyellowgreen scale [0, 0.5, 1]; masked/mirror cells → #9AA0A6 (grey)
    - text overlay = annotation string (e.g. "65%\n(n=42)", "mirror", "n=12", "—")
    - caveat baked into subtitle; title = model.title
    - masked cells (display=False or n=0) have p_shrunk = null → grey fill via condition
    """
    rows = []
    for i, arch_a in enumerate(m.archetypes):
        for j, arch_b in enumerate(m.archetypes):
            val = m.values[i][j]
            rows.append({
                "archetype_a": arch_a,
                "archetype_b": arch_b,
                "p_shrunk": val,           # None for masked/mirror
                "masked": m.masked[i][j],
                "mirror": m.mirror[i][j],
                "annotation": m.annotations[i][j],
            })

    archetype_order = m.archetypes  # preserve matrix order

    subtitle_text = m.caveat[:120] if m.caveat else "matchup matrix"

    spec = _base(
        description=f"Matchup heatmap. {m.title}. {m.caveat}",
        title={"text": m.title, "subtitle": subtitle_text},
    )

    rect_layer = {
        "mark": "rect",
        "encoding": {
            "x": {
                "field": "archetype_b",
                "type": "nominal",
                "title": "Opponent (archetype_b)",
                "sort": archetype_order,
            },
            "y": {
                "field": "archetype_a",
                "type": "nominal",
                "title": "Deck (archetype_a)",
                "sort": archetype_order,
            },
            "color": {
                "condition": {
                    "test": "datum.masked || datum.p_shrunk === null",
                    "value": "#9AA0A6",
                },
                "field": "p_shrunk",
                "type": "quantitative",
                "scale": {
                    "scheme": "redyellowgreen",
                    "domain": [0, 0.5, 1],
                },
                "legend": {"title": "Win rate (p_shrunk)"},
            },
        },
    }

    text_layer = {
        "mark": {
            "type": "text",
            "fontSize": 9,
            "lineBreak": "\n",
        },
        "encoding": {
            "x": {
                "field": "archetype_b",
                "type": "nominal",
                "sort": archetype_order,
            },
            "y": {
                "field": "archetype_a",
                "type": "nominal",
                "sort": archetype_order,
            },
            "text": {"field": "annotation", "type": "nominal"},
            "color": {
                "condition": {
                    "test": "datum.masked || datum.p_shrunk === null",
                    "value": "#333333",
                },
                "value": "#000000",
            },
        },
    }

    spec.update({
        "data": {"values": rows},
        "layer": [rect_layer, text_layer],
    })
    return spec


# ---------------------------------------------------------------------------
# spec_tier_list — horizontal bars faceted by bucket (S / A / B)
# ---------------------------------------------------------------------------


def spec_tier_list(m: TierModel) -> dict:
    """Vega-Lite spec: tier list as horizontal bars row-faceted by bucket (S/A/B).

    Visual semantics:
    - facet row = bucket (S at top, then A, then B)
    - x = share (quantitative, %)
    - y = archetype (nominal, sorted descending by share within each facet)
    - color per bucket: S=#D4AF37, A=#C0C0C0, B=#CD7F32
    - tooltip: archetype, share, tier (confidence)
    - subtitle from model.subtitle
    """
    rows = []
    bucket_order = ["S", "A", "B"]
    bucket_colors = {"S": "#D4AF37", "A": "#C0C0C0", "B": "#CD7F32"}

    for bucket in bucket_order:
        for arch, share, conf_tier in m.buckets[bucket]:
            rows.append({
                "bucket": bucket,
                "archetype": arch,
                "share": share,
                "tier": str(conf_tier),
                "color": bucket_colors[bucket],
            })

    spec = _base(
        description=f"Tier list: S/A/B archetypes by meta-share. {m.subtitle}",
        title={"text": m.title, "subtitle": m.subtitle},
    )

    if not rows:
        # Empty spec that still renders — just title + no data mark.
        spec.update({
            "data": {"values": []},
            "mark": "bar",
            "encoding": {
                "x": {"field": "share", "type": "quantitative"},
                "y": {"field": "archetype", "type": "nominal"},
            },
        })
        return spec

    spec.update({
        "data": {"values": rows},
        "facet": {
            "row": {
                "field": "bucket",
                "type": "nominal",
                "sort": bucket_order,
                "title": "Tier",
                "header": {"labelFontWeight": "bold", "labelFontSize": 13},
            },
        },
        "spec": {
            "mark": {"type": "bar", "cornerRadiusEnd": 3},
            "encoding": {
                "x": {
                    "field": "share",
                    "type": "quantitative",
                    "title": "Share",
                    "axis": {"format": ".0%"},
                },
                "y": {
                    "field": "archetype",
                    "type": "nominal",
                    "sort": {"field": "share", "order": "descending"},
                    "title": "Archetype",
                },
                "color": {
                    "field": "color",
                    "type": "nominal",
                    "scale": None,
                    "legend": None,
                },
                "tooltip": [
                    {"field": "archetype", "type": "nominal", "title": "Archetype"},
                    {"field": "share", "type": "quantitative", "title": "Share", "format": ".1%"},
                    {"field": "bucket", "type": "nominal", "title": "Bucket"},
                    {"field": "tier", "type": "nominal", "title": "Confidence"},
                ],
            },
        },
    })
    return spec


# ---------------------------------------------------------------------------
# spec_trends — multi-line share trajectory across regimes
# ---------------------------------------------------------------------------


def spec_trends(m: TrendModel) -> dict:
    """Vega-Lite spec: meta-share trends (line + point) across ban-list regimes.

    Visual semantics:
    - x = regime label (ordinal, chronological order — Vega-Lite ``"sort": null`` preserves insertion order)
    - y = share (quantitative, %)
    - color = archetype (nominal, categorical palette from injected theme)
    - None cells OMITTED entirely so the line breaks (never emits share=0 for a gap)
    - rect band layer for thin regimes (orange, low alpha)
    - tooltip: regime, archetype, share
    - subtitle from model.subtitle
    """
    # Build data rows — omit None cells entirely (line gaps).
    rows = []
    for archetype in m.archetypes:
        for k, label in enumerate(m.regime_labels):
            val = m.series[archetype][k]
            if val is None:
                continue  # gap — never emit share=0
            rows.append({
                "regime": label,
                "archetype": archetype,
                "share": val,
                "regime_order": k,  # numeric for sorting
            })

    # Thin-regime band rows (one rect per thin regime).
    thin_bands = []
    for k, label in enumerate(m.regime_labels):
        if m.thin_regimes[k]:
            thin_bands.append({"regime": label})

    regime_order = m.regime_labels  # preserve chronological order

    spec = _base(
        description=f"Meta-share trends across ban-list regimes. {m.subtitle}",
        title={"text": m.title, "subtitle": m.subtitle},
    )

    line_layer = {
        "data": {"values": rows},
        "mark": {"type": "line", "point": True, "strokeWidth": 2},
        "encoding": {
            "x": {
                "field": "regime",
                "type": "ordinal",
                "sort": regime_order,
                "title": "Ban-list Regime",
                "axis": {"labelAngle": -30, "labelFontSize": 9},
            },
            "y": {
                "field": "share",
                "type": "quantitative",
                "title": "Share",
                "axis": {"format": ".0%"},
            },
            "color": {
                "field": "archetype",
                "type": "nominal",
                "title": "Archetype",
            },
            "tooltip": [
                {"field": "regime", "type": "ordinal", "title": "Regime"},
                {"field": "archetype", "type": "nominal", "title": "Archetype"},
                {"field": "share", "type": "quantitative", "title": "Share", "format": ".1%"},
            ],
        },
    }

    layers = []

    if thin_bands:
        band_layer = {
            "data": {"values": thin_bands},
            "mark": {"type": "rect", "opacity": 0.12, "color": "orange"},
            "encoding": {
                "x": {
                    "field": "regime",
                    "type": "ordinal",
                    "sort": regime_order,
                },
                "x2": {
                    "field": "regime",
                    "type": "ordinal",
                    "sort": regime_order,
                    "band": 1,
                },
            },
        }
        layers.append(band_layer)

    layers.append(line_layer)

    spec.update({
        "layer": layers,
    })
    return spec
