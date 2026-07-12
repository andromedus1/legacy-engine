"""Vega-Lite v6 spec builders for the chart surfaces.

Each builder takes a prep model from ``viz/models.py`` and returns a hand-built
Vega-Lite spec dict.  No Altair.  No ``config`` key — the canonical dark theme is
injected at render time by ``strip_and_inject`` (foundation convention; vega-embed #27).

Builders:
- ``spec_metashare(BarModel)``              — horizontal bar, muted speculative, fringe greyed
- ``spec_matchup_heatmap(HeatmapModel)``    — rect+text layer, redyellowgreen, masked cells null/grey
- ``spec_tier_list(TierModel)``             — horizontal bars faceted by bucket (S/A/B)
- ``spec_trends(TrendModel)``               — line+point, ordinal x, gaps for None, thin-regime bands
- ``spec_matchup_row(rows, *, deck)``       — Tile B: per-deck matchup spread vs each opponent
- ``spec_positioning(ranking, *, subject)`` — Tile D: s_quantile bars, subject highlighted
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from legacy_engine.config import VL_SCHEMA_URL
from legacy_engine.viz.models import BarModel, HeatmapModel, TierModel, TrendModel

if TYPE_CHECKING:
    from legacy_engine.advisory.positioning import DeckRanking


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


def spec_metashare(m: BarModel, *, top_n: int = 12) -> dict:
    """Vega-Lite spec: horizontal bar chart of meta-share per archetype.

    Visual semantics:
    - y = archetype label, ordered by share descending, but with "Other" PINNED to the bottom — it
      aggregates the long tail and would otherwise float to the top by its size and dwarf real decks
    - capped to the ``top_n`` largest named archetypes (+ the "Other" row when present)
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

    # Display order: the top_n named archetypes by share desc, then "Other" pinned last.
    # The aggregate "Other" bar is large by construction; sorting the y-axis by value would
    # float it to the top and visually dominate the real archetypes, so we fix the order.
    other_rows = [r for r in rows if r["archetype"] == "Other"]
    named_rows = sorted(
        (r for r in rows if r["archetype"] != "Other"),
        key=lambda r: r["share"],
        reverse=True,
    )[:top_n]
    rows = named_rows + other_rows
    y_order = [r["archetype"] for r in rows]  # named (share desc) then "Other" last

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
                "sort": y_order,
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


# ---------------------------------------------------------------------------
# spec_matchup_row — Tile B: per-deck matchup spread (horizontal bar + CI + ref)
# ---------------------------------------------------------------------------

_MASKED_GREY = "#9AA0A6"   # grey for display==False cells (reuses heatmap constant)


def spec_matchup_row(rows: list[dict], *, deck: str) -> dict:
    """Vega-Lite spec: per-deck matchup spread (Tile B).

    ``rows`` is a list of dicts, each with:
      opponent, p_shrunk, ci_low, ci_high, n, tier, display, window

    Visual semantics:
    - y = opponent (sorted by p_shrunk desc where display; masked opponents at bottom)
    - x = p_shrunk (quantitative; null for masked cells)
    - bar fill = p_shrunk colour when display==True; grey (#9AA0A6) when display==False
    - CI rule from ci_low to ci_high (only for displayed cells)
    - reference rule at 0.5 (dotted)
    - tooltip: p_raw (omitted here — not in rows; use p_shrunk%), n, tier, window
    - masked cells show annotation "n=X insufficient" on the y-axis area
    """
    # Build flat rows for Vega-Lite; add sort_key so masked rows go to bottom.
    vl_rows = []
    for r in rows:
        p = r.get("p_shrunk")
        display = bool(r.get("display", False))
        n = r.get("n", 0)
        tier = str(r.get("tier", ""))
        window = r.get("window") or "full corpus"
        vl_rows.append({
            "opponent": r["opponent"],
            "p_raw": r.get("p_raw"),
            "p_shrunk": p if display and p is not None else None,
            "ci_low": r.get("ci_low") if display else None,
            "ci_high": r.get("ci_high") if display else None,
            "n": n,
            "tier": tier,
            "display": display,
            "window": window,
            # sort key: displayed by rate desc, then masked (None sorts low in VL)
            "sort_key": (p if display and p is not None else -1.0),
        })

    spec = _base(
        description=f"Matchup spread for {deck}: win rate vs each opponent. Masked cells have insufficient data (n<30).",
        title={"text": f"Matchup Spread — {deck}", "subtitle": "Grey bars = n<30 insufficient; error bars = 95% CI"},
    )

    # Bar layer — displayed cells only
    bar_layer = {
        "mark": {"type": "bar", "cornerRadiusEnd": 3},
        "encoding": {
            "y": {
                "field": "opponent",
                "type": "nominal",
                "sort": {"field": "sort_key", "order": "descending"},
                "title": "Opponent",
            },
            "x": {
                "field": "p_shrunk",
                "type": "quantitative",
                "title": "Win rate (p_shrunk)",
                "axis": {"format": ".0%"},
                "scale": {"domain": [0, 1]},
            },
            "color": {
                "condition": {"test": "!datum.display || datum.p_shrunk === null", "value": _MASKED_GREY},
                "value": "#56B4E9",
            },
            "opacity": {
                "condition": {"test": "!datum.display || datum.p_shrunk === null", "value": 0.4},
                "value": 0.85,
            },
            "tooltip": [
                {"field": "opponent", "type": "nominal", "title": "Opponent"},
                {"field": "p_shrunk", "type": "quantitative", "title": "Win rate (shrunk)", "format": ".1%"},
                {"field": "p_raw", "type": "quantitative", "title": "Win rate (raw)", "format": ".1%"},
                {"field": "n", "type": "quantitative", "title": "n (matches)"},
                {"field": "tier", "type": "nominal", "title": "Tier"},
                {"field": "window", "type": "nominal", "title": "Data window (since)"},
            ],
        },
    }

    # CI rule layer — only for displayed cells (ci_low/ci_high non-null)
    ci_layer = {
        "mark": {"type": "rule", "strokeWidth": 2, "color": "#E69F00"},
        "encoding": {
            "y": {
                "field": "opponent",
                "type": "nominal",
                "sort": {"field": "sort_key", "order": "descending"},
            },
            "x": {
                "field": "ci_low",
                "type": "quantitative",
                "scale": {"domain": [0, 1]},
            },
            "x2": {"field": "ci_high"},
        },
        "transform": [{"filter": "datum.display && datum.ci_low !== null"}],
    }

    # Reference rule at 0.5 (even match)
    ref_data = [{"ref": 0.5}]
    ref_layer = {
        "data": {"values": ref_data},
        "mark": {"type": "rule", "strokeDash": [4, 4], "color": "#9AA0A6", "opacity": 0.8},
        "encoding": {
            "x": {"field": "ref", "type": "quantitative"},
        },
    }

    spec.update({
        "data": {"values": vl_rows},
        "layer": [bar_layer, ci_layer, ref_layer],
    })
    return spec


# ---------------------------------------------------------------------------
# spec_positioning — Tile D: s_quantile bars, subject highlighted, CI rules
# ---------------------------------------------------------------------------


def spec_positioning(
    ranking: "DeckRanking",
    *,
    subject: str,
    u_bar: float | None = None,
) -> dict:
    """Vega-Lite spec: positioning ranking (Tile D).

    ``ranking`` is a ``DeckRanking`` from ``advisory.positioning.rank_decks``.
    The subject deck is highlighted via a Vega-Lite condition on ``datum.deck == subject``.
    Coverage-caveated decks (S imputation-dominated) are rendered at reduced opacity —
    the same threshold that earns the ``S*`` caveat label in the CLI, so the visual cue
    is threshold-consistent.

    Visual semantics:
    - y = deck (sorted best→worst by s_quantile)
    - x = s_quantile (quantitative)
    - bar color condition: subject = #D55E00 (orange-red), others = #56B4E9 (blue)
    - opacity condition: coverage_caveated = 0.35, normal = 0.85
    - CI rule from s_ci low to high, yellow
    - optional u_bar overlay (dotted rule, best-deck lens)
    - tooltip: deck, s_mean, s_quantile, p_best, coverage, tier (from data_coverage)
    """
    q_level = ranking.quantile_level
    coverage_caveated = ranking.coverage_caveated

    vl_rows = []
    for deck in ranking.decks:
        s_q = ranking.s_quantile[deck]
        s_mean = ranking.s_mean[deck]
        ci_lo, ci_hi = ranking.s_ci[deck]
        p_best = ranking.p_best[deck]
        cov = ranking.data_coverage[deck]
        is_subj = deck == subject
        is_caveated = deck in coverage_caveated
        vl_rows.append({
            "deck": deck,
            "s_quantile": s_q,
            "s_mean": s_mean,
            "ci_low": ci_lo,
            "ci_high": ci_hi,
            "p_best": p_best,
            "data_coverage": cov,
            "is_subject": is_subj,
            "coverage_caveated": is_caveated,
            "sort_key": s_q,
        })

    subtitle = (
        f"field_source={ranking.field_source}  "
        f"sort=S(q{q_level:.2f})  "
        f"subject={subject!r}"
    )
    spec = _base(
        description=(
            f"Positioning ranking: s_quantile bars for candidate decks. "
            f"Subject={subject!r} highlighted. Coverage-caveated decks faded."
        ),
        title={"text": "Positioning Ranking", "subtitle": subtitle},
    )

    bar_layer = {
        "mark": {"type": "bar", "cornerRadiusEnd": 3},
        "encoding": {
            "y": {
                "field": "deck",
                "type": "nominal",
                "sort": {"field": "sort_key", "order": "descending"},
                "title": "Archetype",
            },
            "x": {
                "field": "s_quantile",
                "type": "quantitative",
                "title": f"S (q{q_level:.2f})",
                "axis": {"format": ".3f"},
                "scale": {"zero": False},
            },
            "color": {
                "condition": {"test": "datum.is_subject", "value": "#D55E00"},
                "value": "#56B4E9",
            },
            "opacity": {
                "condition": {"test": "datum.coverage_caveated", "value": 0.35},
                "value": 0.85,
            },
            "tooltip": [
                {"field": "deck", "type": "nominal", "title": "Archetype"},
                {"field": "s_mean", "type": "quantitative", "title": "S (mean)", "format": ".4f"},
                {"field": "s_quantile", "type": "quantitative", "title": f"S (q{q_level:.2f})", "format": ".4f"},
                {"field": "p_best", "type": "quantitative", "title": "P(best)", "format": ".3f"},
                {"field": "data_coverage", "type": "quantitative", "title": "Data coverage", "format": ".2f"},
            ],
        },
    }

    ci_layer = {
        "mark": {"type": "rule", "strokeWidth": 2, "color": "#E69F00"},
        "encoding": {
            "y": {
                "field": "deck",
                "type": "nominal",
                "sort": {"field": "sort_key", "order": "descending"},
            },
            "x": {
                "field": "ci_low",
                "type": "quantitative",
            },
            "x2": {"field": "ci_high"},
        },
    }

    layers: list[dict] = [bar_layer, ci_layer]

    if u_bar is not None:
        u_ref_layer = {
            "data": {"values": [{"u_bar": u_bar}]},
            "mark": {
                "type": "rule",
                "strokeDash": [6, 3],
                "color": "#009E73",
                "opacity": 0.9,
                "tooltip": f"Unweighted mean (u_bar) = {u_bar:.3f}",
            },
            "encoding": {
                "x": {"field": "u_bar", "type": "quantitative"},
            },
        }
        layers.append(u_ref_layer)

    spec.update({
        "data": {"values": vl_rows},
        "layer": layers,
    })
    return spec
