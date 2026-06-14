"""Plain-speak sideboard primer generator (feature-deck-tuning-refresh-workflow).

Turns the per-matchup ``MatchupPlan`` OUT/IN data from ``recommend_sideboard`` + the
recommended sideboard into readable prose per opponent.  This is the "plain-speak primer"
deliverable: not a stat dump, but a synthesized "here's how you beat X, and here's what
comes in/out" writeup that a player can read at the table.

Architecture (objective-search-split pattern):
  - ``generate_primer`` is a PURE function over the recommendation data.  No DB calls.
    Takes the recommended sideboard, the matchup_plans dict, the archetype name, and an
    optional window label.  Returns a ``SideboardPrimer`` with one ``MatchupBlurb`` per
    opponent.
  - All honesty wiring is here: thin/no-data matchups are explicitly labeled; presence-
    correlational plans are never dressed up as causal facts; confident plans say WHY the
    swap makes sense, not just WHAT happens.

Honesty contract (drawn from feature spec + PRINCIPLES):
  - Degraded plans (plan.degraded=True or plan.n_basis=0): MUST label as
    "reasoning-based, not data-derived" — never fabricate matchup numbers.
  - Data-thin plans (tier="speculative"): MUST label as speculative, suggest relying on
    15 composition, NEVER state a win-rate.
  - Data-informed plans (tier in "evolving"/"established"): MAY describe the swap rationale
    in terms of "cards that underperform vs <opp>" and "sideboard answers for <opp>", but
    MUST include the presence-correlational disclaimer.
  - Each blurb MUST include the exact OUT/IN swaps (or say "no targeted swaps") so the
    player has actionable instructions.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MatchupBlurb:
    """Plain-speak writeup for one matchup.

    ``opponent``:      archetype name.
    ``prose``:         the human-readable paragraph(s) explaining the matchup plan.
    ``side_out_str``:  formatted OUT summary (e.g. "2x Dead Weight, 1x Thoughtseize").
    ``side_in_str``:   formatted IN summary (e.g. "2x Surgical Extraction, 1x Leyline of the Void").
    ``data_quality``:  one of "established", "evolving", "speculative", "reasoning-based".
    ``n_basis``:       minimum matchup-cell n behind the plan (0 for degraded/no-data).
    ``degraded``:      True when no per-card data — guidance is reasoning-based.
    """

    opponent: str
    prose: str
    side_out_str: str
    side_in_str: str
    data_quality: str
    n_basis: int
    degraded: bool


@dataclass
class SideboardPrimer:
    """Complete plain-speak primer for one venue tuning package.

    ``archetype``:       the deck's archetype.
    ``venue_label``:     venue label (e.g. "Online (MTGO)", "Paper").
    ``window_label``:    the window/regime label (e.g. "adaptive (per-opponent ban-aware)").
    ``sideboard_list``:  the recommended 15 as a formatted string.
    ``blurbs``:          one ``MatchupBlurb`` per opponent, ordered by field share (desc).
    ``primer_text``:     fully assembled text output (rendered from blurbs).
    ``honesty_note``:    global disclaimer carried by every primer.
    """

    archetype: str
    venue_label: str
    window_label: str
    sideboard_list: str
    blurbs: list[MatchupBlurb] = dc_field(default_factory=list)
    primer_text: str = ""
    honesty_note: str = ""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PRESENCE_CORRELATIONAL_DISCLAIMER = (
    "Per-card win-rates are presence-correlational (registered 75 for resolved matches), "
    "not causal. Swap suggestions are a data-guided starting point, not a deterministic "
    "prescription."
)

_DATA_TIERS: frozenset[str] = frozenset({"evolving", "established"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_primer(
    archetype: str,
    sideboard: dict[str, int],
    matchup_plans: "dict[str, object]",   # str -> MatchupPlan
    *,
    venue_label: str = "",
    window_label: str = "",
    field_shares: "dict[str, float] | None" = None,
) -> SideboardPrimer:
    """Generate a plain-speak primer from the tuned package data.

    Pure function — no DB, no I/O.  Takes only pre-computed data structures.

    Parameters
    ----------
    archetype
        The deck's archetype name.
    sideboard
        The recommended 15 (card -> copies).
    matchup_plans
        ``dict[opponent -> MatchupPlan]`` as returned by ``recommend_sideboard`` /
        ``tune_deck``.  May be empty when no per-card data cleared the gate.
    venue_label
        Human-readable venue label (for header).
    window_label
        Regime/window label (for transparency about what data window was used).
    field_shares
        Optional ``{opponent -> share}`` for ordering blurbs by field share (desc).
        When None the matchup_plan dict order is used.

    Returns
    -------
    SideboardPrimer
        Ready to render; ``primer_text`` is the fully assembled output.
    """
    # Format the sideboard list for the primer header.
    if sideboard:
        sb_lines = [
            f"  {copies}x {card}"
            for card, copies in sorted(sideboard.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        sideboard_list = "\n".join(sb_lines)
    else:
        sideboard_list = "  (no sideboard recommendations)"

    # Order opponents by field share (desc) for readability; tie-break alphabetically.
    ordered_opponents = _order_opponents(matchup_plans, field_shares)

    blurbs: list[MatchupBlurb] = []
    for opp in ordered_opponents:
        plan = matchup_plans[opp]
        blurb = _build_blurb(opp, plan, sideboard)
        blurbs.append(blurb)

    primer_text = _render_primer(
        archetype=archetype,
        venue_label=venue_label,
        window_label=window_label,
        sideboard_list=sideboard_list,
        blurbs=blurbs,
        has_any_plans=bool(matchup_plans),
    )

    return SideboardPrimer(
        archetype=archetype,
        venue_label=venue_label,
        window_label=window_label,
        sideboard_list=sideboard_list,
        blurbs=blurbs,
        primer_text=primer_text,
        honesty_note=_PRESENCE_CORRELATIONAL_DISCLAIMER,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _order_opponents(
    matchup_plans: "dict[str, object]",
    field_shares: "dict[str, float] | None",
) -> list[str]:
    """Return opponents ordered by field share desc, tie-break alphabetically."""
    if field_shares is not None:
        return sorted(
            matchup_plans.keys(),
            key=lambda opp: (-field_shares.get(opp, 0.0), opp),
        )
    return sorted(matchup_plans.keys())


def _format_swap_dict(swap: "dict[str, int]", label: str) -> str:
    """Format a side_out or side_in dict as 'Nx Card, Mx Card ...'."""
    if not swap:
        return f"{label}: (none)"
    parts = [
        f"{copies}x {card}"
        for card, copies in sorted(swap.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return f"{label}: {', '.join(parts)}"


def _build_blurb(
    opponent: str,
    plan: "object",   # MatchupPlan
    sideboard: dict[str, int],
) -> MatchupBlurb:
    """Build one MatchupBlurb from a MatchupPlan.

    Honesty logic:
    - degraded=True (no per-card data): label as reasoning-based, never fabricate numbers.
    - tier="speculative" (data present but thin): label as thin, suppress swap details.
    - tier in "evolving"/"established": describe the swap rationale honestly.
    """
    # Attribute access is duck-typed; MatchupPlan is a frozen dataclass.
    degraded: bool = getattr(plan, "degraded", True)
    tier: str = getattr(plan, "tier", "speculative")
    n_basis: int = getattr(plan, "n_basis", 0)
    side_out: dict = getattr(plan, "side_out", {})
    side_in: dict = getattr(plan, "side_in", {})
    note: str = getattr(plan, "note", "")

    out_str = _format_swap_dict(side_out, "OUT")
    in_str = _format_swap_dict(side_in, "IN")

    if degraded or n_basis == 0:
        data_quality = "reasoning-based"
        prose = _prose_degraded(opponent, tier, note, sideboard)
    elif tier == "speculative":
        data_quality = "speculative"
        prose = _prose_speculative(opponent, n_basis, note, sideboard)
    elif tier in _DATA_TIERS and side_out:
        data_quality = tier
        prose = _prose_data_informed(opponent, tier, n_basis, side_out, side_in, note)
    else:
        # Data present, gate cleared, but no swap identified (e.g. no dead flex cards found)
        data_quality = tier
        prose = _prose_no_swap_needed(opponent, tier, n_basis, sideboard, note)

    return MatchupBlurb(
        opponent=opponent,
        prose=prose,
        side_out_str=out_str,
        side_in_str=in_str,
        data_quality=data_quality,
        n_basis=n_basis,
        degraded=degraded,
    )


def _prose_degraded(
    opponent: str,
    tier: str,
    note: str,
    sideboard: dict[str, int],
) -> str:
    """Prose for a degraded (reasoning-based, not data-derived) matchup."""
    # Identify what the sideboard provides against this opponent structurally —
    # no per-card matchup math, so we speak to general sideboard composition.
    sb_has_graveyard = any(
        c in sideboard for c in (
            "Surgical Extraction", "Faerie Macabre", "Leyline of the Void",
            "Endurance", "Containment Priest", "Grafdigger's Cage", "Nihil Spellbomb",
        )
    )
    sb_has_combo_hate = any(
        c in sideboard for c in (
            "Force of Will", "Flusterstorm", "Mindbreak Trap", "Thoughtseize", "Duress",
        )
    )
    sb_has_mana_hate = any(
        c in sideboard for c in (
            "Blood Moon", "Back to Basics", "Wasteland",
        )
    )

    sb_notes: list[str] = []
    if sb_has_graveyard:
        sb_notes.append("graveyard disruption")
    if sb_has_combo_hate:
        sb_notes.append("interaction for combo / storm")
    if sb_has_mana_hate:
        sb_notes.append("mana disruption")

    sb_desc = (
        "The recommended 15 includes " + ", ".join(sb_notes) + " that can apply pressure."
        if sb_notes else
        "Rely on the maindeck-aware 15 composition."
    )

    reason_note = ""
    if note:
        # Surface the honest note from _plan_matchups (may say "even pooling to X, thin")
        reason_note = f" ({note})"

    return (
        f"vs {opponent}: no per-card matchup data cleared the confidence gate{reason_note}. "
        f"This guidance is reasoning-based, not data-derived — treat it as a starting framework, "
        f"not a prescription. "
        f"{sb_desc} "
        f"No targeted OUT/IN swaps are recommended without data backing."
    )


def _prose_speculative(
    opponent: str,
    n_basis: int,
    note: str,
    sideboard: dict[str, int],
) -> str:
    """Prose for a speculative-tier plan (data present but thin, n < 30)."""
    return (
        f"vs {opponent}: data is present but thin (n={n_basis}, speculative tier — "
        f"fewer than 30 decisive matches in this window). "
        f"Specific swap suggestions are withheld because thin-sample per-card rates are "
        f"unreliable as individual prescriptions. "
        f"Rely on the maindeck-aware 15 composition and the general sideboard structure. "
        f"No targeted OUT/IN swaps are surfaced at this confidence level."
    )


def _prose_data_informed(
    opponent: str,
    tier: str,
    n_basis: int,
    side_out: dict,
    side_in: dict,
    note: str,
) -> str:
    """Prose for a data-informed plan (evolving/established tier, swaps found)."""
    tier_desc = "sufficient data (evolving)" if tier == "evolving" else "solid data (established)"

    # Describe why cards are coming out.
    out_parts = [f"{copies}x {card}" for card, copies in sorted(side_out.items(), key=lambda kv: (-kv[1], kv[0]))]
    in_parts = [f"{copies}x {card}" for card, copies in sorted(side_in.items(), key=lambda kv: (-kv[1], kv[0]))]
    out_str = ", ".join(out_parts)
    in_str = ", ".join(in_parts)
    n_swaps = sum(side_out.values())

    return (
        f"vs {opponent}: {tier_desc}, n>={n_basis} matches. "
        f"The data indicates {n_swaps} swap(s) improve the post-board configuration. "
        f"OUT: {out_str}. "
        f"IN: {in_str}. "
        f"The outgoing cards show below-baseline performance in this matchup; "
        f"the incoming cards show positive lift. "
        f"[These are presence-correlational signals — not causal proof. "
        f"Adjust based on your read of the game state.]"
    )


def _prose_no_swap_needed(
    opponent: str,
    tier: str,
    n_basis: int,
    sideboard: dict[str, int],
    note: str,
) -> str:
    """Prose when data cleared the gate but no beneficial swap was identified."""
    tier_desc = "sufficient data (evolving)" if tier == "evolving" else "solid data (established)"
    return (
        f"vs {opponent}: {tier_desc}, n>={n_basis} matches. "
        f"No targeted OUT/IN swaps were identified — either no flex cards show "
        f"significantly negative lift, or no sideboard card shows significantly positive lift "
        f"for this matchup specifically. "
        f"The maindeck is already well-configured for this opponent; "
        f"rely on the general sideboard 15 without targeted swaps."
    )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def _render_primer(
    *,
    archetype: str,
    venue_label: str,
    window_label: str,
    sideboard_list: str,
    blurbs: list[MatchupBlurb],
    has_any_plans: bool,
) -> str:
    """Assemble the full primer text."""
    lines: list[str] = []

    # Header
    venue_str = f" [{venue_label}]" if venue_label else ""
    lines.append(f"=== Sideboard Primer: {archetype}{venue_str} ===")
    if window_label:
        lines.append(f"Data window: {window_label}")
    lines.append("")

    # Sideboard
    lines.append("Recommended sideboard (15):")
    lines.append(sideboard_list)
    lines.append("")

    # Per-matchup blurbs
    if not blurbs:
        lines.append(
            "No per-matchup data available. Rely on the 15 composition for general coverage."
        )
    else:
        lines.append("Per-matchup guide:")
        lines.append("-" * 60)
        for blurb in blurbs:
            lines.append("")
            # Data quality badge
            quality_badge = f"[{blurb.data_quality}]" if blurb.data_quality else ""
            lines.append(f"  {blurb.opponent}  {quality_badge}")
            # Prose (wrap for readability — one long paragraph per matchup)
            lines.append(f"  {blurb.prose}")
            # Explicit swap summary (always shown)
            if not blurb.degraded:
                lines.append(f"  {blurb.side_out_str}")
                lines.append(f"  {blurb.side_in_str}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Note: {_PRESENCE_CORRELATIONAL_DISCLAIMER}")

    return "\n".join(lines)
