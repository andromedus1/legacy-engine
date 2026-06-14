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
from legacy_engine.models.decklist import parse_decklist as _parse_decklist_impl

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Unit 1 — Deck/field input plumbing
# ---------------------------------------------------------------------------

# _COUNT_RE kept for any other callers in this file.
_COUNT_RE = re.compile(r"^(\d+)[xX]?\s+(.+)$")


def _parse_decklist(text: str) -> tuple[dict[str, int], dict[str, int]]:
    """Parse a plain-text decklist into (mainboard, sideboard).

    Thin wrapper around ``models.decklist.parse_decklist`` (the canonical
    implementation, promoted there so ``collection/`` can import it without a
    sideways ``collection → advisory`` dependency).  Error messages previously
    said ``_parse_decklist:``; the promoted function says ``parse_decklist:``
    — callers catching ``ValueError`` should match on the exception type, not
    the prefix string.

    Lines ``<count> <name>`` or ``<count>x <name>``; a line equal to
    ``Sideboard`` (case-insensitive) or a blank line after main cards starts
    the sideboard.  Ignores ``#``-prefixed comments and leading blank lines.
    Raises ``ValueError`` on a malformed line or an empty maindeck.
    """
    return _parse_decklist_impl(text)


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
    since: str | None = None,
    until: str | None = None,
) -> FieldDistribution:
    """Custom field from ``field_text`` (``<share> <archetype>`` lines) else the global field.

    ``since``/``until`` window the global field (half-open ``[since, until)``); both ``None`` =
    full corpus. A custom ``field_text`` is user-specified and unaffected by the window.
    """
    if field_text is None:
        return build_global_field(con, provenance=provenance, since=since, until=until)

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
    since: str | None = None,
    until: str | None = None,
    matrix=None,
) -> FieldReadReport:
    """Compose positioning + whattoplay + sideboard + audit trail into a FieldReadReport.

    ``since``/``until`` window the matchup matrix (half-open ``[since, until)``) so positioning is
    computed over the same window as the (already-windowed) ``field``; both ``None`` = full corpus.
    A precomputed ``matrix`` (e.g. the adaptive per-cell matrix) may be injected, in which case
    ``since``/``until`` are ignored for the matrix build.
    """
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
    if matrix is None:
        matrix = build_matrix(con, since=since, until=until)
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
                f"coverage={positioning.data_coverage:.2f}, "
                f"restricted={positioning.restricted} (excluded_share={positioning.excluded_share:.2f}), "
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
                    f"best_deck_score={best_deck_call.best_deck_score:.3f}, "
                    f"best_call_score={best_deck_call.best_call_score:.3f}, "
                    f"spread_variance={best_deck_call.spread_variance:.4f}, "
                    f"field_weighted_mean={best_deck_call.field_weighted_mean:.3f}, "
                    f"unweighted_mean={best_deck_call.unweighted_mean:.3f} "
                    f"(data-driven; {len(known_cells)} cells n≥30)"
                )
        except Exception as exc:
            warnings.append(f"best-deck-call failed: {exc}")
            audit.append(f"best-deck-call: ERROR — {exc}")

    # ── Sideboard ────────────────────────────────────────────────────────────
    sideboard_pkg = recommend_sideboard(
        con, field, mainboard, reserved=reserved, archetype=resolved_archetype
    )
    audit.append(
        f"sideboard: solver={sideboard_pkg.solver_used!r}, "
        f"budget={sideboard_pkg.budget}, "
        f"covered_weight={sideboard_pkg.covered_weight:.4f}, "
        f"cards={list(sideboard_pkg.cards.keys())}"
    )
    audit.append(f"sideboard heuristic note: {sideboard_pkg.heuristic_note}")
    if sideboard_pkg.warnings:
        audit.extend(f"sideboard warning: {w}" for w in sideboard_pkg.warnings)
    audit.append(
        f"sideboard value_informed={sideboard_pkg.value_informed}, "
        f"plan_window={sideboard_pkg.plan_window}, "
        f"matchup_plans_count={len(sideboard_pkg.matchup_plans)}"
    )
    if sideboard_pkg.matchup_plans:
        for opp, plan in sorted(sideboard_pkg.matchup_plans.items()):
            if plan.degraded:
                audit.append(f"  matchup_plan[{opp}]: degraded — {plan.note}")
            else:
                audit.append(
                    f"  matchup_plan[{opp}]: tier={plan.tier}, n_basis={plan.n_basis}, "
                    f"out={plan.side_out}, in={plan.side_in}"
                )

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
    if p.s_computable:
        scope = "covered sub-field" if p.restricted else "field"
        lines = [
            f"Positioning score (S, vs {scope}): {p.s_mean:.3f}",
            f"  95% credible interval: [{p.s_ci[0]:.3f}, {p.s_ci[1]:.3f}]",
        ]
    else:
        lines = ["Positioning score (S): not computable — no covered (n≥30) matchups in the field"]
    lines.append(f"  Field coverage: {p.data_coverage:.0%} of field has matchup data")
    if p.restricted:
        excl = ", ".join(sorted(p.excluded_archetypes))
        lines.append(
            f"  Excluded {p.excluded_share:.0%} with no data ({len(p.excluded_archetypes)}): {excl}"
        )
    lines += [
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
    ]

    # Coverage-aware positioning S (when supplied) — the headline number a user wants.
    pos = report.positioning
    if pos is not None:
        if not pos.s_computable:
            lines.append("  Positioning S: not computable (no covered matchups)")
        elif pos.restricted:
            lines.append(
                f"  Positioning S (vs covered sub-field): {pos.s_mean:.3f}  "
                f"(coverage {pos.data_coverage:.0%}, excluded {pos.excluded_share:.0%})"
            )
        else:
            lines.append(f"  Positioning S: {pos.s_mean:.3f}  (coverage {pos.data_coverage:.0%})")

    lines += [
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
            f"(best_deck={bdc.best_deck_score:.3f}, best_call={bdc.best_call_score:.3f}, "
            f"spread_var={bdc.spread_variance:.4f})"
        )
    else:
        lines.append("  Best-deck-call: N/A (archetype unresolved)")

    return "\n".join(lines)


def _render_sideboard_plans(sb) -> list[str]:
    """Render per-matchup OUT/IN plans as text lines (only when value_informed)."""
    from legacy_engine.advisory.sideboard import _VALUE_DISCLAIMER

    if not sb.value_informed or not sb.matchup_plans:
        return []
    lines: list[str] = ["  Per-matchup plans (presence-correlational):"]
    for opp, plan in sorted(sb.matchup_plans.items()):
        if plan.degraded:
            lines.append(f"    vs {opp}: thin data — no per-matchup plan (rely on 15 composition)")
        else:
            out_str = ", ".join(
                f"{c}x {card}" for card, c in sorted(plan.side_out.items())
            ) or "(none)"
            in_str = ", ".join(
                f"{c}x {card}" for card, c in sorted(plan.side_in.items())
            ) or "(none)"
            lines.append(
                f"    vs {opp} [{plan.tier}, n≥{plan.n_basis}]: "
                f"OUT {out_str} | IN {in_str}"
            )
    lines.append(f"  [disclaimer] {_VALUE_DISCLAIMER}")
    return lines


def _interaction_annotation(card_name: str, con: duckdb.DuckDBPyConnection) -> str | None:
    """Return a short oracle-grounded interaction annotation for a hate card, or None.

    Gated-additive: only fires for graveyard-touching cards from the HOSER_CATALOG.
    When interaction facts are absent or the card doesn't touch graveyards the function
    returns None — callers render identically to the pre-feature baseline.

    This is the Unit 2 + 3 wiring: oracle_text grounds the advisory rationale so the
    primer can say "one-sided graveyard hate, synergy-safe" rather than producing
    a wrong self-harm claim from memory.

    ``con`` is the DuckDB connection used to look up real oracle_text from the cards
    table — no hardcoded text cache, no memory-based reasoning.
    """
    try:
        from legacy_engine.interaction_facts import interaction_facts, verify_graveyard_claim
        from legacy_engine.advisory.sideboard import HOSER_CATALOG
        from legacy_engine.models.card import Card

        hoser = HOSER_CATALOG.get(card_name)
        if hoser is None or "graveyard-reliant" not in hoser.attacks:
            return None

        # Look up the real oracle_text from the DB — no hardcoded cache.
        # If the card isn't in the DB, degrade gracefully (return None, never crash).
        row = con.execute(
            "SELECT oracle_text, type_line FROM cards WHERE name = ?",
            [card_name],
        ).fetchone()
        if row is None or not row[0]:
            return None

        oracle_text, type_line = row[0], row[1] or ""
        card = Card(name=card_name, type_line=type_line, oracle_text=oracle_text)
        facts = interaction_facts(card)

        if not facts.touches_graveyard:
            return None

        # Build annotation
        parts: list[str] = []
        scope_desc = {
            "opponent-only": "one-sided (opponent's yard only)",
            "targeted": "targeted (aim at opponent)",
            "symmetric": "symmetric" + ("" if not facts.graveyard_count_reduction else " exile"),
            "self-only": "self-only (your own engine)",
            "none": None,
        }.get(facts.affects)
        if scope_desc:
            parts.append(scope_desc)

        if facts.self_graveyard_safe:
            parts.append("synergy-safe")
        else:
            parts.append("hurts own yard too")

        if facts.permanence in ("static", "activated"):
            parts.append(facts.permanence)

        annotation = ", ".join(p for p in parts if p)

        # Unit 3 guard: run verify_graveyard_claim to check for incorrect self-harm claims.
        # If the card is safe but was being claimed to harm own yard, annotate accordingly.
        check = verify_graveyard_claim(card, claims_self_harm=False)
        if check.ok and facts.self_graveyard_safe:
            # Confirmed safe — annotation stands
            pass
        elif not check.ok:
            # Guard found something unexpected; append evidence note
            annotation += " [review oracle_text]"

        if facts.confidence.level == "speculative":
            annotation += " [scope uncertain]"

        return f"[{annotation}]" if annotation else None

    except Exception:
        # Gated: any failure → return None, render identically to baseline
        return None


def _render_sideboard(report: FieldReadReport, con: duckdb.DuckDBPyConnection | None = None) -> str:
    """Render the sideboard section.

    ``con`` is optional — when provided, oracle_text for graveyard hosers is looked
    up from the DB and an interaction annotation is appended.  When absent (e.g. unit
    tests that don't exercise the annotation path), the annotation is silently skipped,
    preserving byte-identical baseline output.
    """
    sb = report.sideboard
    lines: list[str] = [
        f"Recommended sideboard (solver={sb.solver_used}, budget={sb.budget}, "
        f"reserved={sb.reserved}):",
        f"  Field source: {sb.field_source}",
        f"  Covered weight: {sb.covered_weight:.4f}",
    ]
    if sb.cards:
        for card, copies in sorted(sb.cards.items(), key=lambda kv: kv[1], reverse=True):
            annotation = _interaction_annotation(card, con) if con is not None else None
            suffix = f"  {annotation}" if annotation else ""
            lines.append(f"  {copies}x {card}{suffix}")
    else:
        lines.append("  (no sideboard recommendations — no castable hosers found)")
    lines.append(f"  Note: {sb.heuristic_note}")
    if sb.warnings:
        for w in sb.warnings:
            lines.append(f"  [warn] {w}")
    # Append per-matchup plans when value_informed
    lines.extend(_render_sideboard_plans(sb))
    return "\n".join(lines)


def render_cross_venue_positioning(reports: dict[str, "FieldReadReport"]) -> str:
    """Render a compact cross-venue positioning delta footer.

    Shows the deck's positioning S and best-deck-call per venue side by side —
    the decision-relevant divergence ("your deck is well-positioned online but
    poorly in paper").  ``reports`` maps ``venue.key`` to a ``FieldReadReport``
    (already built per venue by the CLI orchestrator; this function is a pure
    text renderer, no recompute).

    Only emits rows for venues where positioning was computed (not None).
    """
    if not reports:
        return ""

    lines: list[str] = ["── Cross-venue positioning delta ──"]

    # Header row
    venue_keys = list(reports.keys())
    col_w = 14
    header = f"  {'Metric':<28}" + "".join(f"  {k:<{col_w}}" for k in venue_keys)
    lines.append(header)
    lines.append("  " + "-" * (28 + (col_w + 2) * len(venue_keys)))

    # Positioning S row
    s_parts = [f"  {'Positioning S':<28}"]
    for k in venue_keys:
        r = reports[k]
        pos = r.positioning
        if pos is None:
            s_parts.append(f"  {'N/A':<{col_w}}")
        elif not pos.s_computable:
            s_parts.append(f"  {'no data':<{col_w}}")
        else:
            scope_note = "*" if pos.restricted else ""
            s_parts.append(f"  {pos.s_mean:.3f}{scope_note:<{col_w - 5}}")
    lines.append("".join(s_parts))

    # Coverage row
    cov_parts = [f"  {'Coverage':<28}"]
    for k in venue_keys:
        r = reports[k]
        pos = r.positioning
        if pos is None:
            cov_parts.append(f"  {'N/A':<{col_w}}")
        else:
            cov_parts.append(f"  {pos.data_coverage:.0%}{'':>{col_w - 4}}")
    lines.append("".join(cov_parts))

    # Best-deck-call row
    bdc_parts = [f"  {'Best-deck-call':<28}"]
    for k in venue_keys:
        r = reports[k]
        bdc = r.best_deck_call
        if bdc is None:
            bdc_parts.append(f"  {'N/A':<{col_w}}")
        else:
            label = bdc.label[:col_w]
            bdc_parts.append(f"  {label:<{col_w}}")
    lines.append("".join(bdc_parts))

    lines.append("  (* = restricted to covered sub-field)")

    return "\n".join(lines)


def render_field_read(report: FieldReadReport, con: duckdb.DuckDBPyConnection | None = None) -> str:
    """Render the full Field Read & Deck Recommendation as labeled text.

    Sections: header → field composition → vulnerability profile →
    positioning → whattoplay → sideboard → audit trail.

    ``con`` is optional — when supplied, oracle_text-grounded interaction annotations
    are appended to graveyard hosers in the sideboard section.  When absent the output
    is byte-identical to the pre-feature baseline (gated-additive).
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
    sections.append(_render_sideboard(report, con=con))

    # Audit trail
    audit_lines = "\n".join(f"  {line}" for line in report.audit)
    sections.append(f"Audit trail:\n{audit_lines}")

    return "\n\n".join(sections)
