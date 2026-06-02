"""Per-deck dashboard composer.

Assembles the five tiles (+ primer) for one archetype into a ``Dashboard``
ready for ``render_dashboard_html``.  Attack-focused layout order:

  1. Primer/header (col_span 12) — auto-generated summary sentences
  2. Matchup spread — Tile B (col_span 12, wide top)
  3. Positioning     — Tile D (col_span 6, left)
  4. Meta-share      — Tile A (col_span 6, right)
  5. Trends          — Tile C (col_span 12)
  6. Consensus       — Tile E (col_span 12, bottom)

Data plumbing:
- Adaptive per-cell matrix via ``build_adaptive_matrix`` (NOT ``build_advisory_inputs``)
  so each matchup row carries its ``cell_windows`` date for the Tile B tooltip.
- Field from ``build_global_field`` over ``resolve_regime("current")`` window.
- Ranking from ``rank_decks`` over the full candidate set.
- ``positioning_score`` for the subject deck (u_bar overlay on Tile D).
- Meta-share via ``compute_metashare``; trends via ``compute_trends``.
- Consensus via ``build_consensus`` + ``card_frequencies`` (main + side).
"""

from __future__ import annotations

import html as _html_escape
import logging

from legacy_engine.viz.layout import Dashboard, Tile
from legacy_engine.viz.models import _metashare_model, _trends_model
from legacy_engine.viz.specs import (
    spec_matchup_row,
    spec_metashare,
    spec_positioning,
    spec_trends,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# _consensus_html — Tile E
# ---------------------------------------------------------------------------

_LOCK_ALPHA = 0.22   # background-color alpha for "lock" cards (inclusion >= 0.65)
_FLEX_ALPHA = 0.08   # background-color alpha for "flex" cards (inclusion < 0.65)
_LOCK_THRESHOLD = 0.65


def _inclusion_bg(pct: float) -> str:
    """CSS background-color string for a card row, shaded by inclusion_pct."""
    alpha = _LOCK_ALPHA if pct >= _LOCK_THRESHOLD else _FLEX_ALPHA
    # Use a blue-grey tint on the dark background
    return f"rgba(86,180,233,{alpha:.2f})"


def _consensus_html(deck: str, main_freqs: list, side_freqs: list) -> str:
    """Render the consensus two-column HTML tile (Tile E).

    Each card row is shaded by inclusion_pct (lock = solid, flex = faint).
    Shows sample_n (inferred from first card), the data window, and any
    legality errors.
    """
    def _card_rows(freqs: list) -> str:
        if not freqs:
            return "<tr><td colspan='2' style='color:#9AA0A6;padding:4px 0'><em>(none)</em></td></tr>"
        rows = []
        for cf in freqs:
            bg = _inclusion_bg(cf.inclusion_pct)
            safe_name = _html_escape.escape(cf.name)
            pct_str = f"{cf.inclusion_pct:.0%}"
            rows.append(
                f"<tr style='background:{bg}'>"
                f"<td style='padding:3px 6px;color:#E6E6E6'>{cf.modal_count} {safe_name}</td>"
                f"<td style='padding:3px 6px;text-align:right;color:#9AA0A6'>{pct_str}</td>"
                f"</tr>"
            )
        return "\n".join(rows)

    main_rows_html = _card_rows(main_freqs)
    side_rows_html = _card_rows(side_freqs)

    safe_deck = _html_escape.escape(deck)

    return f"""
<div style="font-size:0.82rem;line-height:1.4">
  <div style="display:flex;gap:1.5rem;align-items:flex-start">
    <div style="flex:1;min-width:0">
      <div style="font-weight:600;color:#9AA0A6;margin-bottom:0.4rem;text-transform:uppercase;font-size:0.75rem">Maindeck (60)</div>
      <table style="width:100%;border-collapse:collapse">
        {main_rows_html}
      </table>
    </div>
    <div style="flex:1;min-width:0">
      <div style="font-weight:600;color:#9AA0A6;margin-bottom:0.4rem;text-transform:uppercase;font-size:0.75rem">Sideboard (15)</div>
      <table style="width:100%;border-collapse:collapse">
        {side_rows_html}
      </table>
    </div>
  </div>
  <div style="margin-top:0.5rem;color:#9AA0A6;font-size:0.75rem">
    Shading: lock (≥{_LOCK_THRESHOLD:.0%} inclusion) = solid · flex = faint
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# _primer_summary — auto-generated prose tile
# ---------------------------------------------------------------------------

def _primer_summary(
    archetype: str,
    meta,
    matchup_rows: list[dict],
    ranking,
    subj,
) -> str:
    """Generate a short auto-summary of the deck's meta position.

    Confidence-gated: every sentence is conditional on having sufficient data.
    Never fabricates numbers on thin data — degrades to "insufficient data" phrases.

    Args:
        archetype:     The archetype label.
        meta:          MetaShareReport from compute_metashare.
        matchup_rows:  List of per-opponent row dicts (same as passed to spec_matchup_row).
        ranking:       DeckRanking from rank_decks (may be None if field is empty).
        subj:          PositioningResult for the subject deck (may be None).

    Returns:
        HTML string with a few summary sentences.
    """
    safe_arch = _html_escape.escape(archetype)
    lines: list[str] = []

    # ── Meta-share ────────────────────────────────────────────────────────────
    meta_entry = None
    if meta is not None:
        for entry in meta.entries:
            if entry.archetype == archetype:
                meta_entry = entry
                break

    if meta_entry is not None:
        rank_idx = None
        for i, e in enumerate(meta.entries, 1):
            if e.archetype == archetype:
                rank_idx = i
                break
        pct = f"{meta_entry.share:.1%}"
        tier_label = str(meta_entry.tier)
        rank_str = f"#{rank_idx}" if rank_idx else "unranked"
        lines.append(
            f"<strong>{safe_arch}</strong> holds {pct} meta-share "
            f"({rank_str} of {len(meta.entries)} archetypes; tier: {_html_escape.escape(tier_label)})."
        )
    else:
        lines.append(
            f"<strong>{safe_arch}</strong>: insufficient meta-share data — "
            "archetype absent from the current corpus window."
        )

    # ── Best / worst matchups (established cells only) ────────────────────────
    displayed = [r for r in matchup_rows if r.get("display") and r.get("p_shrunk") is not None]
    if displayed:
        best = max(displayed, key=lambda r: r["p_shrunk"])
        worst = min(displayed, key=lambda r: r["p_shrunk"])
        best_opp = _html_escape.escape(best["opponent"])
        worst_opp = _html_escape.escape(worst["opponent"])
        best_pct = f"{best['p_shrunk']:.0%}"
        worst_pct = f"{worst['p_shrunk']:.0%}"
        best_n = best.get("n", "?")
        worst_n = worst.get("n", "?")
        lines.append(
            f"Best matchup: <strong>{best_opp}</strong> ({best_pct}, n={best_n}). "
            f"Worst matchup: <strong>{worst_opp}</strong> ({worst_pct}, n={worst_n})."
        )
    else:
        lines.append(
            "Matchup data: insufficient established cells (n&lt;30 for all opponents) — "
            "matchup reads withheld."
        )

    # ── Positioning rank + S ──────────────────────────────────────────────────
    if ranking is not None and archetype in ranking.decks:
        rank_pos = ranking.decks.index(archetype) + 1
        s_val = ranking.s_mean.get(archetype, 0.0)
        s_q = ranking.s_quantile.get(archetype, 0.0)
        cov = ranking.data_coverage.get(archetype, 0.0)
        low_cov = archetype in ranking.low_coverage
        cov_note = " [low data coverage — S estimate less reliable]" if low_cov else ""
        lines.append(
            f"Positioning: ranked #{rank_pos} of {len(ranking.decks)} candidates "
            f"(S={s_val:.3f}, q{ranking.quantile_level:.2f}={s_q:.3f}; "
            f"data_coverage={cov:.2f}{cov_note})."
        )
    elif subj is not None and subj.data_coverage == 0.0:
        lines.append(
            "Positioning: insufficient matchup data — S estimate unreliable "
            f"(data_coverage=0.0). {_html_escape.escape(archetype)} not ranked."
        )
    else:
        lines.append(
            "Positioning: archetype absent from candidate field — positioning rank unavailable."
        )

    # ── Data caveat ──────────────────────────────────────────────────────────
    lines.append(
        "<em style='color:#9AA0A6;font-size:0.78rem'>"
        "All stats are empirical (matchup data from MTGO rounds-bearing events). "
        "Cells with n&lt;30 are masked. Confidence tiers: established ≥100, evolving 30–99, speculative &lt;30."
        "</em>"
    )

    return (
        '<div style="font-size:0.88rem;line-height:1.6;color:#E6E6E6">'
        + " ".join(f"<p>{line}</p>" for line in lines)
        + "</div>"
    )


# ---------------------------------------------------------------------------
# build_deck_dashboard — main entry point
# ---------------------------------------------------------------------------


def build_deck_dashboard(
    con,
    archetype: str,
    *,
    provenance: str | None = None,
    regime: str = "current",
    seed: int | None = 0,
) -> Dashboard:
    """Build a per-deck Dashboard composing five tiles + a primer for ``archetype``.

    Tiles in attack-focused order:
    1. Primer   (col_span 12) — auto-generated summary
    2. Tile B   (col_span 12) — matchup spread vs each opponent
    3. Tile D   (col_span 6)  — positioning ranking
    4. Tile A   (col_span 6)  — meta-share
    5. Tile C   (col_span 12) — trends
    6. Tile E   (col_span 12) — consensus decklist

    Args:
        con:         DuckDB connection.
        archetype:   Archetype label (must be a known labeled archetype).
        provenance:  "online", "paper", or None (all).
        regime:      Ban-regime name; "current" (default) uses the latest regime.
        seed:        RNG seed for deterministic MC (default 0).

    Returns:
        A ``Dashboard`` instance ready for ``render_dashboard_html``.
    """
    from legacy_engine.analytics.matchup import build_adaptive_matrix
    from legacy_engine.analytics.metashare import compute_metashare
    from legacy_engine.analytics.trends import compute_trends, resolve_regime
    from legacy_engine.advisory.field import build_global_field
    from legacy_engine.advisory.positioning import positioning_score, rank_decks
    from legacy_engine.generation.consensus import build_consensus, card_frequencies
    from legacy_engine.viz.models import _metashare_model, _trends_model

    # ── 1. Adaptive matrix (carries cell_windows for Tile B tooltips) ─────────
    adaptive = build_adaptive_matrix(con, provenance=provenance)
    matrix = adaptive.matrix

    # ── 2. Regime window for field / meta / trends ─────────────────────────────
    try:
        cur_since, cur_until = resolve_regime(regime)
    except ValueError as exc:
        log.warning("build_deck_dashboard: resolve_regime(%r) failed: %s — using full corpus", regime, exc)
        cur_since, cur_until = None, None

    # ── 3. Field + ranking ─────────────────────────────────────────────────────
    field = build_global_field(con, since=cur_since, until=cur_until, provenance=provenance)
    candidates = sorted(field.shares)

    if candidates:
        ranking = rank_decks(
            matrix, field, candidates,
            risk_averse=True,
            seed=seed,
        )
    else:
        log.warning("build_deck_dashboard: field is empty — ranking unavailable")
        ranking = None

    # Subject positioning score for u_bar overlay
    try:
        subj = positioning_score(matrix, field, archetype, seed=seed)
        u_bar = subj.u_bar
    except Exception as exc:  # noqa: BLE001
        log.warning("build_deck_dashboard: positioning_score failed for %r: %s", archetype, exc)
        subj = None
        u_bar = None

    # ── 4. Meta-share (Tile A) ────────────────────────────────────────────────
    meta = compute_metashare(
        con,
        since=cur_since,
        until=cur_until,
        provenance=provenance,
    )

    # ── 5. Matchup spread (Tile B) ────────────────────────────────────────────
    matchup_rows: list[dict] = []
    for opp in matrix.archetypes:
        cell = matrix.cells.get((archetype, opp))
        window = adaptive.cell_windows.get((archetype, opp))
        if cell is None:
            matchup_rows.append({
                "opponent": opp,
                "p_shrunk": None,
                "ci_low": None,
                "ci_high": None,
                "n": 0,
                "tier": "speculative",
                "display": False,
                "window": window or "full corpus",
            })
        else:
            matchup_rows.append({
                "opponent": opp,
                "p_shrunk": cell.p_shrunk,
                "ci_low": cell.ci_low,
                "ci_high": cell.ci_high,
                "n": cell.n,
                "tier": str(cell.tier),
                "display": bool(cell.display) and not cell.is_mirror,
                "window": window or "full corpus",
            })

    # ── 6. Trends (Tile C) ────────────────────────────────────────────────────
    try:
        trends = compute_trends(con, provenance=provenance)
    except Exception as exc:  # noqa: BLE001
        log.warning("build_deck_dashboard: compute_trends failed: %s", exc)
        trends = None

    # ── 7. Consensus (Tile E) ──────────────────────────────────────────────────
    try:
        cons = build_consensus(con, archetype, since=cur_since, until=cur_until, provenance=provenance)
        mf = card_frequencies(con, archetype, board="main", since=cur_since, until=cur_until)
        sf = card_frequencies(con, archetype, board="side", since=cur_since, until=cur_until)
    except Exception as exc:  # noqa: BLE001
        log.warning("build_deck_dashboard: consensus/card_freq failed for %r: %s", archetype, exc)
        cons = None
        mf = []
        sf = []

    # ── 8. Spec builders ──────────────────────────────────────────────────────
    # Tile A — meta-share spec
    meta_spec = spec_metashare(_metashare_model(meta))

    # Tile B — matchup spread spec
    matchup_spec = spec_matchup_row(matchup_rows, deck=archetype)

    # Tile C — trends spec (fallback to empty spec if unavailable)
    if trends is not None:
        trends_spec = spec_trends(_trends_model(trends))
    else:
        from legacy_engine.config import VL_SCHEMA_URL
        trends_spec = {
            "$schema": VL_SCHEMA_URL,
            "description": "Trends unavailable.",
            "data": {"values": []},
            "mark": "text",
            "encoding": {},
        }

    # Tile D — positioning spec
    if ranking is not None:
        pos_spec = spec_positioning(ranking, subject=archetype, u_bar=u_bar)
    else:
        from legacy_engine.config import VL_SCHEMA_URL
        pos_spec = {
            "$schema": VL_SCHEMA_URL,
            "description": "Positioning unavailable — field is empty.",
            "data": {"values": []},
            "mark": "text",
            "encoding": {},
        }

    # Tile E — consensus HTML
    consensus_html = _consensus_html(archetype, mf, sf)

    # Primer HTML
    primer_html = _primer_summary(archetype, meta, matchup_rows, ranking, subj)

    # ── 9. Assemble tiles in attack-focused order ─────────────────────────────
    tiles = [
        Tile(kind="html", title="Deck Summary", col_span=12, html=primer_html),
        Tile(kind="chart", title="Matchup Spread", col_span=12, spec=matchup_spec),
        Tile(kind="chart", title="Positioning", col_span=6, spec=pos_spec),
        Tile(kind="chart", title="Meta Share", col_span=6, spec=meta_spec),
        Tile(kind="chart", title="Trends", col_span=12, spec=trends_spec),
        Tile(kind="html", title="Consensus Decklist", col_span=12, html=consensus_html),
    ]

    return Dashboard(title=f"{archetype} — Deck Dashboard", tiles=tiles)
