"""Field Read & Deck Recommendation report — assembler + renderers.

Composes ``positioning``, ``whattoplay``, and ``sideboard`` into a single
``FieldReadReport`` and provides text renderers for the combined report and
individual ``advise`` CLI leaves.  Recomputes nothing — collects each
component's own provenance into the audit trail.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import duckdb

from legacy_engine.advisory.field import FieldDistribution, build_custom_field, build_global_field
from legacy_engine.archetype.matcher import ArchetypeResult, classify
from legacy_engine.archetype.rules import load_ruleset
from legacy_engine.colors import compute_deck_colors
from legacy_engine.config import RULES_DIR

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Unit 1 — Deck/field input plumbing
# ---------------------------------------------------------------------------

_COUNT_RE = re.compile(r"^(\d+)[xX]?\s+(.+)$")


def _parse_decklist(text: str) -> tuple[dict[str, int], dict[str, int]]:
    """Parse a plain-text decklist into (mainboard, sideboard).

    Lines ``<count> <name>`` or ``<count>x <name>``; a line equal to
    ``Sideboard`` (case-insensitive) or a blank line after main cards starts
    the sideboard.  Ignores ``#``-prefixed comments and leading blank lines.
    Raises ``ValueError`` on a malformed line or an empty maindeck.
    """
    mainboard: dict[str, int] = {}
    sideboard: dict[str, int] = {}
    in_side = False
    seen_main_card = False

    for raw_line in text.splitlines():
        line = raw_line.strip()

        # Skip comments
        if line.startswith("#"):
            continue

        # Blank line: after we've seen at least one main card, switch to side
        if not line:
            if seen_main_card:
                in_side = True
            continue

        # "Sideboard" header (case-insensitive)
        if line.lower() == "sideboard":
            in_side = True
            continue

        m = _COUNT_RE.match(line)
        if m is None:
            raise ValueError(f"_parse_decklist: malformed line {line!r}")

        count = int(m.group(1))
        name = m.group(2).strip()

        if in_side:
            sideboard[name] = sideboard.get(name, 0) + count
        else:
            mainboard[name] = mainboard.get(name, 0) + count
            seen_main_card = True

    if not mainboard:
        raise ValueError("_parse_decklist: empty maindeck")

    return mainboard, sideboard


def _classify_deck(
    con: duckdb.DuckDBPyConnection,
    mainboard: dict[str, int],
    sideboard: dict[str, int],
) -> ArchetypeResult:
    """Resolve cards (local cards table), compute colors, load the ruleset, and classify."""
    from legacy_engine.advisory.whattoplay import _load_deck_cards

    cards_with_counts = _load_deck_cards(con, mainboard)
    card_objects = [card for card, _count in cards_with_counts]
    deck_colors = compute_deck_colors(card_objects)
    ruleset = load_ruleset(RULES_DIR)
    return classify(mainboard, sideboard, ruleset, deck_colors)


def _load_field(
    con: duckdb.DuckDBPyConnection,
    *,
    field_text: str | None,
    provenance: str | None = None,
) -> FieldDistribution:
    """Custom field from ``field_text`` (``<share> <archetype>`` lines) else the global field."""
    if field_text is None:
        return build_global_field(con, provenance=provenance)

    shares: dict[str, float] = {}
    for raw_line in field_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise ValueError(f"_load_field: malformed line {line!r} (expected '<share> <archetype>')")
        try:
            share = float(parts[0])
        except ValueError:
            raise ValueError(f"_load_field: non-numeric share {parts[0]!r} in line {line!r}")
        archetype = parts[1].strip()
        shares[archetype] = shares.get(archetype, 0.0) + share

    if not shares:
        raise ValueError("_load_field: no field entries parsed from field_text")

    return build_custom_field(shares)


# ---------------------------------------------------------------------------
# Unit 2 — FieldReadReport + assembler
# ---------------------------------------------------------------------------

_UNRESOLVED_KINDS = frozenset({"conflict", "unknown"})


@dataclass
class FieldReadReport:
    """Composed output of the Field Read & Deck Recommendation.

    ``positioning`` is ``None`` when the archetype is unresolved
    (Conflict/Unknown) — positioning needs a concrete archetype.
    ``best_deck_call`` is ``None`` under the same condition.
    ``audit`` carries every figure with its derivation, sample size, and
    a heuristic-vs-data-driven label.
    """

    deck_archetype: str
    field_source: str
    field_shares: dict[str, float]
    field_vuln_profile: dict[str, float]      # hate_equity: tag → field share attacked
    positioning: object | None                # PositioningResult (None if archetype unresolved)
    proactivity: object                       # ProactivityProfile
    vulnerability: frozenset[str]             # the deck's own tags
    best_deck_call: object | None             # BestDeckCall (None if archetype unresolved)
    sideboard: object                         # SideboardPackage
    audit: list[str]                          # audit-trail lines
    warnings: tuple[str, ...]


def build_field_read_report(
    con: duckdb.DuckDBPyConnection,
    mainboard: dict[str, int],
    sideboard_in: dict[str, int],
    field: FieldDistribution,
    *,
    archetype: str | None = None,
    reserved: int = 0,
    seed: int | None = None,
) -> FieldReadReport:
    """Compose positioning + whattoplay + sideboard + audit trail into a FieldReadReport."""
    from legacy_engine.advisory.positioning import positioning_score
    from legacy_engine.advisory.whattoplay import (
        best_deck_vs_best_call,
        field_vulnerability_tags,
        hate_equity,
        proactivity_score,
        vulnerability_tags_for_deck,
    )
    from legacy_engine.advisory.sideboard import recommend_sideboard
    from legacy_engine.analytics.matchup import build_matrix

    warnings: list[str] = []
    audit: list[str] = []

    # ── Archetype resolution ─────────────────────────────────────────────────
    if archetype is None:
        result = _classify_deck(con, mainboard, sideboard_in)
        resolved_archetype = result.archetype
        if result.kind in _UNRESOLVED_KINDS:
            warnings.append(
                f"Archetype unresolved ({resolved_archetype}): "
                "positioning and best-deck-call skipped. "
                "Use --archetype to override."
            )
            audit.append(
                f"archetype: unresolved ({resolved_archetype}) — classifier returned "
                f"kind={result.kind}; positioning=None; best_deck_call=None"
            )
    else:
        resolved_archetype = archetype
        audit.append(f"archetype: {resolved_archetype!r} (user-supplied override)")

    # Determine if we can run positioning/best-deck-call
    archetype_resolvable = not (
        archetype is None
        and any(w.startswith("Archetype unresolved") for w in warnings)
    )

    # ── Field audit ──────────────────────────────────────────────────────────
    audit.append(
        f"field_source: {field.field_source!r} "
        f"({len(field.shares)} archetypes; "
        f"counts={'present' if field.counts else 'none (point-shares)'})"
    )
    if field.warnings:
        audit.extend(f"field warning: {w}" for w in field.warnings)

    # ── Build matchup matrix once ────────────────────────────────────────────
    matrix = build_matrix(con)
    audit.append(
        f"matchup matrix: {len(matrix.archetypes)} archetypes, "
        f"{matrix.total_matches} decisive matches, "
        f"provenance={matrix.provenance!r}"
    )

    # ── Field vulnerability profile ──────────────────────────────────────────
    archetype_tags = field_vulnerability_tags(con, field)
    field_vuln_profile = hate_equity(field, archetype_tags)
    if field_vuln_profile:
        top_tags = sorted(field_vuln_profile.items(), key=lambda kv: kv[1], reverse=True)
        audit.append(
            "field vulnerability (hate-equity): "
            + "; ".join(f"{tag}={share:.1%}" for tag, share in top_tags[:5])
        )

    # ── Positioning ──────────────────────────────────────────────────────────
    positioning = None
    if archetype_resolvable:
        try:
            positioning = positioning_score(matrix, field, resolved_archetype, seed=seed)
            audit.append(
                f"positioning: s_mean={positioning.s_mean:.3f}, "
                f"s_ci=[{positioning.s_ci[0]:.3f}, {positioning.s_ci[1]:.3f}], "
                f"u_bar={positioning.u_bar:.3f}, "
                f"n_draws={positioning.n_draws}, "
                f"imputed={len(positioning.imputed)} opponents, "
                f"field_source={positioning.field_source!r}"
            )
            if positioning.warnings:
                audit.extend(f"positioning warning: {w}" for w in positioning.warnings)
        except Exception as exc:
            warnings.append(f"positioning failed: {exc}")
            audit.append(f"positioning: ERROR — {exc}")

    # ── Proactivity + vulnerability ──────────────────────────────────────────
    proactivity = proactivity_score(con, mainboard, archetype_tag=resolved_archetype)
    deck_vuln = vulnerability_tags_for_deck(con, mainboard)

    audit.append(
        f"proactivity: score={proactivity.score:.3f}, "
        f"proactive_mass={proactivity.proactive_mass:.2f}, "
        f"reactive_mass={proactivity.reactive_mass:.2f}, "
        f"low_curve_score={proactivity.low_curve_score:.3f} "
        "(heuristic: composition-derived)"
    )
    if proactivity.findings:
        audit.extend(f"proactivity finding: {f}" for f in proactivity.findings)
    audit.append(
        f"deck vulnerability tags: {sorted(deck_vuln) if deck_vuln else '(none)'}"
    )

    # ── Best-deck-call ───────────────────────────────────────────────────────
    best_deck_call = None
    if archetype_resolvable:
        try:
            best_deck_call = best_deck_vs_best_call(matrix, field, resolved_archetype)
            # Gate: only assert the label when matchup row has sufficient data
            row_archetype = resolved_archetype
            known_cells = [
                cell for (deck_a, opp), cell in matrix.cells.items()
                if deck_a == row_archetype and opp != row_archetype and cell.n >= 30
            ]
            if len(known_cells) == 0:
                audit.append(
                    f"best-deck-call: label={best_deck_call.label!r} "
                    f"(PROVISIONAL — no cells with n≥30 for {row_archetype!r})"
                )
                warnings.append(
                    f"best-deck-call for {row_archetype!r} is provisional: "
                    "no matchup cells meet the n≥30 threshold"
                )
            else:
                audit.append(
                    f"best-deck-call: label={best_deck_call.label!r}, "
                    f"spread_variance={best_deck_call.spread_variance:.4f}, "
                    f"field_weighted_mean={best_deck_call.field_weighted_mean:.3f}, "
                    f"unweighted_mean={best_deck_call.unweighted_mean:.3f} "
                    f"(data-driven; {len(known_cells)} cells n≥30)"
                )
        except Exception as exc:
            warnings.append(f"best-deck-call failed: {exc}")
            audit.append(f"best-deck-call: ERROR — {exc}")

    # ── Sideboard ────────────────────────────────────────────────────────────
    sideboard_pkg = recommend_sideboard(con, field, mainboard, reserved=reserved)
    audit.append(
        f"sideboard: solver={sideboard_pkg.solver_used!r}, "
        f"budget={sideboard_pkg.budget}, "
        f"covered_weight={sideboard_pkg.covered_weight:.4f}, "
        f"cards={list(sideboard_pkg.cards.keys())}"
    )
    audit.append(f"sideboard heuristic note: {sideboard_pkg.heuristic_note}")
    if sideboard_pkg.warnings:
        audit.extend(f"sideboard warning: {w}" for w in sideboard_pkg.warnings)

    return FieldReadReport(
        deck_archetype=resolved_archetype,
        field_source=field.field_source,
        field_shares=dict(field.shares),
        field_vuln_profile=field_vuln_profile,
        positioning=positioning,
        proactivity=proactivity,
        vulnerability=deck_vuln,
        best_deck_call=best_deck_call,
        sideboard=sideboard_pkg,
        audit=audit,
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Unit 3 — Text renderers
# ---------------------------------------------------------------------------


def _render_field_section(report: FieldReadReport) -> str:
    """Render the field composition section."""
    lines: list[str] = []
    lines.append(f"Field source: {report.field_source}")
    lines.append(f"Field composition ({len(report.field_shares)} archetypes):")
    for archetype, share in sorted(report.field_shares.items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"  {archetype:<30}  {share:>6.1%}")
    if report.field_vuln_profile:
        lines.append("Field vulnerability profile (hate-equity):")
        for tag, eq in sorted(report.field_vuln_profile.items(), key=lambda kv: kv[1], reverse=True):
            lines.append(f"  {tag:<28}  field share attacked: {eq:>6.1%}")
    return "\n".join(lines)


def _render_positioning(report: FieldReadReport) -> str:
    """Render the positioning section."""
    if report.positioning is None:
        return (
            f"Positioning: N/A — archetype unresolved ({report.deck_archetype})\n"
            "  Use --archetype to override and enable positioning."
        )
    p = report.positioning
    lines: list[str] = [
        f"Positioning score (S): {p.s_mean:.3f}",
        f"  95% credible interval: [{p.s_ci[0]:.3f}, {p.s_ci[1]:.3f}]",
        f"  Unweighted mean (u_bar): {p.u_bar:.3f}  [best-deck lens]",
        f"  MC draws: {p.n_draws}  |  field_source: {p.field_source}",
    ]
    if p.imputed:
        lines.append(f"  Imputed opponents ({len(p.imputed)}): {', '.join(sorted(p.imputed))}")
    if p.warnings:
        for w in p.warnings:
            lines.append(f"  [warn] {w}")
    return "\n".join(lines)


def _render_whattoplay(report: FieldReadReport) -> str:
    """Render the proactivity + vulnerability + best-deck-call section."""
    p = report.proactivity
    lines: list[str] = [
        "What to play:",
        f"  Archetype: {report.deck_archetype}",
        f"  Proactivity score: {p.score:.3f}  "
        f"(proactive_mass={p.proactive_mass:.2f}, reactive_mass={p.reactive_mass:.2f})",
        f"  Low-curve score: {p.low_curve_score:.3f}  [heuristic: composition-derived]",
    ]
    if p.findings:
        for f in p.findings:
            lines.append(f"  [finding] {f}")
    if report.vulnerability:
        lines.append(f"  Deck vulnerability tags: {', '.join(sorted(report.vulnerability))}")
    else:
        lines.append("  Deck vulnerability tags: (none)")

    if report.best_deck_call is not None:
        bdc = report.best_deck_call
        lines.append(
            f"  Best-deck-call: {bdc.label}  "
            f"(spread_variance={bdc.spread_variance:.4f}, "
            f"field_weighted_mean={bdc.field_weighted_mean:.3f})"
        )
    else:
        lines.append("  Best-deck-call: N/A (archetype unresolved)")

    return "\n".join(lines)


def _render_sideboard(report: FieldReadReport) -> str:
    """Render the sideboard section."""
    sb = report.sideboard
    lines: list[str] = [
        f"Recommended sideboard (solver={sb.solver_used}, budget={sb.budget}, "
        f"reserved={sb.reserved}):",
        f"  Field source: {sb.field_source}",
        f"  Covered weight: {sb.covered_weight:.4f}",
    ]
    if sb.cards:
        for card, copies in sorted(sb.cards.items(), key=lambda kv: kv[1], reverse=True):
            lines.append(f"  {copies}x {card}")
    else:
        lines.append("  (no sideboard recommendations — no castable hosers found)")
    lines.append(f"  Note: {sb.heuristic_note}")
    if sb.warnings:
        for w in sb.warnings:
            lines.append(f"  [warn] {w}")
    return "\n".join(lines)


def render_field_read(report: FieldReadReport) -> str:
    """Render the full Field Read & Deck Recommendation as labeled text.

    Sections: header → field composition → vulnerability profile →
    positioning → whattoplay → sideboard → audit trail.
    """
    sections: list[str] = []

    # Header
    sections.append(
        f"=== Field Read & Deck Recommendation: {report.deck_archetype} ===\n"
        f"Field source: {report.field_source}"
    )

    # Warnings
    if report.warnings:
        sections.append(
            "Warnings:\n" + "\n".join(f"  ! {w}" for w in report.warnings)
        )

    # Field
    sections.append(_render_field_section(report))

    # Positioning
    sections.append(_render_positioning(report))

    # Whattoplay
    sections.append(_render_whattoplay(report))

    # Sideboard
    sections.append(_render_sideboard(report))

    # Audit trail
    audit_lines = "\n".join(f"  {line}" for line in report.audit)
    sections.append(f"Audit trail:\n{audit_lines}")

    return "\n\n".join(sections)
