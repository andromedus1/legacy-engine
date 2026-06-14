"""Deck-tuning refresh workflow (feature-deck-tuning-refresh-workflow).

Orchestrates the per-venue refresh loop that produces a ready-to-play tuning package
per data split (today: online / paper).  One call pulls current data and emits, per venue:

  1. Recommended maindeck (field-tuned, current-regime-aware via tune_deck).
  2. Recommended sideboard (15, field-tuned, via tune_deck's integrated recommend_sideboard).
  3. A concise plain-speak primer (via advisory.primer.generate_primer) explaining how the
     sideboard attacks each meaningful opponent — including the exact OUT/IN swaps and WHY.

Constraints honored:
  - Ban-regime-correct by default (current regime via _latest_regime_window + adaptive
    per-opponent ban-aware windows via recommend_sideboard's adaptive=True path).
  - Per-venue fields use ``build_global_field(con, provenance=venue.provenance)`` —
    each venue sees its own meta-share distribution.
  - Card-count-outlier deltas (build_deck_doctor_report) are attached as a structured
    annotation on the package; outlier cards are surfaced in the primer header.
  - Collection-aware filtering is OUT OF SCOPE for this delivery; the non-collection
    version ships here.

Architecture: gated-additive.  When a venue has zero decks, the package is marked
``data_absent=True`` rather than silently dropped — absence is information.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field

import duckdb

from legacy_engine.advisory.field import build_global_field
from legacy_engine.analytics.venue import DEFAULT_VENUES, Venue

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class VenueTuningPackage:
    """Tuning package for one venue.

    ``venue``:          the venue this package belongs to.
    ``maindeck``:       recommended maindeck (card -> copies, 60 cards).
    ``sideboard``:      recommended sideboard (card -> copies, ≤15 cards).
    ``primer``:         the plain-speak primer (SideboardPrimer).
    ``tuned_deck``:     the raw TunedDeck from tune_deck (carries swaps, value delta, etc.).
    ``outlier_deltas``: CardCountDelta list from build_deck_doctor_report (may be empty).
    ``window_label``:   human-readable label for the data window used.
    ``data_absent``:    True when the venue had zero decks in the corpus.
    ``warnings``:       any issues encountered during assembly.
    """

    venue: Venue
    archetype: str
    maindeck: dict[str, int]
    sideboard: dict[str, int]
    primer: object         # SideboardPrimer
    tuned_deck: object     # TunedDeck
    outlier_deltas: list   # list[CardCountDelta]
    window_label: str
    data_absent: bool = False
    warnings: list[str] = dc_field(default_factory=list)


@dataclass
class RefreshResult:
    """Full output of one advise-refresh run.

    ``packages``:  per-venue tuning packages, ordered by venue (online first, paper second).
    ``archetype``: the resolved archetype name.
    ``warnings``:  global warnings (cross-venue issues).
    """

    packages: list[VenueTuningPackage]
    archetype: str
    warnings: list[str] = dc_field(default_factory=list)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_refresh(
    con: duckdb.DuckDBPyConnection,
    maindeck: dict[str, int],
    sideboard_in: dict[str, int],
    *,
    archetype: str,
    venues: "list[Venue] | None" = None,
    since: "str | None" = None,
    until: "str | None" = None,
    lock_threshold: float = 0.65,
    max_swaps: int = 8,
) -> RefreshResult:
    """Run the full deck-tuning refresh workflow across all requested venues.

    For each venue:
      1. Build the per-venue field (``build_global_field`` with ``provenance=venue.provenance``).
      2. Call ``tune_deck`` to get the tuned 60+15 + per-matchup plans.
      3. Call ``build_deck_doctor_report`` for card-count-outlier deltas.
      4. Generate the plain-speak primer via ``generate_primer``.
      5. Package everything into a ``VenueTuningPackage``.

    Parameters
    ----------
    con
        DuckDB connection.
    maindeck
        Starting maindeck (card -> count, should sum to 60).
    sideboard_in
        Starting sideboard (may be empty — tune_deck will rebuild it).
    archetype
        Deck archetype (required — used for locked-core computation + sideboard empirical pool).
    venues
        Venue list; defaults to ``DEFAULT_VENUES`` (online, paper).
    since / until
        Explicit window; None → adaptive per-opponent ban-aware (recommended).
    lock_threshold
        Maindeck locked-core inclusion threshold (default 0.65).
    max_swaps
        Maximum greedy swap rounds (default 8).

    Returns
    -------
    RefreshResult
    """
    from legacy_engine.generation.tuning import tune_deck
    from legacy_engine.advisory.primer import generate_primer
    from legacy_engine.generation.card_distribution import build_deck_doctor_report

    if venues is None:
        venues = list(DEFAULT_VENUES)

    packages: list[VenueTuningPackage] = []
    global_warnings: list[str] = []

    for venue in venues:
        log.info("run_refresh: processing venue %r (%s)", venue.key, venue.label)

        pkg_warnings: list[str] = []

        # ── Step 1: Build per-venue field ─────────────────────────────────────
        # Absence of provenance filter → full corpus field (no-op for venues without provenance).
        try:
            field = build_global_field(con, provenance=venue.provenance)
        except Exception as exc:
            pkg_warnings.append(f"field build failed for venue {venue.key!r}: {exc}")
            # Zero-deck venue — no field data
            packages.append(VenueTuningPackage(
                venue=venue,
                archetype=archetype,
                maindeck=dict(maindeck),
                sideboard={},
                primer=_empty_primer(archetype, venue),
                tuned_deck=None,
                outlier_deltas=[],
                window_label="(field unavailable)",
                data_absent=True,
                warnings=pkg_warnings,
            ))
            continue

        # Check for empty venue
        if not field.shares:
            pkg_warnings.append(
                f"venue {venue.key!r} ({venue.label}) has no archetype data — no decks in corpus"
            )
            packages.append(VenueTuningPackage(
                venue=venue,
                archetype=archetype,
                maindeck=dict(maindeck),
                sideboard={},
                primer=_empty_primer(archetype, venue),
                tuned_deck=None,
                outlier_deltas=[],
                window_label="(no data for this venue)",
                data_absent=True,
                warnings=pkg_warnings,
            ))
            continue

        # ── Step 2: Tune the deck ─────────────────────────────────────────────
        try:
            tuned = tune_deck(
                con,
                archetype,
                maindeck,
                sideboard_in,
                field=field,
                since=since,
                until=until,
                lock_threshold=lock_threshold,
                max_swaps=max_swaps,
            )
        except Exception as exc:
            log.warning("run_refresh: tune_deck failed for venue %r: %s", venue.key, exc)
            pkg_warnings.append(f"tune_deck failed: {exc}")
            packages.append(VenueTuningPackage(
                venue=venue,
                archetype=archetype,
                maindeck=dict(maindeck),
                sideboard={},
                primer=_empty_primer(archetype, venue),
                tuned_deck=None,
                outlier_deltas=[],
                window_label="(tuning failed)",
                data_absent=False,
                warnings=pkg_warnings,
            ))
            continue

        # ── Step 3: Card-count-outlier deltas ────────────────────────────────
        # build_deck_doctor_report runs per board; call for main then side.
        outlier_deltas: list = []
        try:
            main_report = build_deck_doctor_report(
                con,
                tuned.maindeck,
                tuned.sideboard,
                archetype,
                since=since,
                until=until,
                board="main",
            )
            side_report = build_deck_doctor_report(
                con,
                tuned.maindeck,
                tuned.sideboard,
                archetype,
                since=since,
                until=until,
                board="side",
            )
            outlier_deltas = [
                d for d in main_report.deltas + side_report.deltas
                if d.is_outlier
            ]
        except Exception as exc:
            log.debug("run_refresh: build_deck_doctor_report failed for venue %r: %s", venue.key, exc)
            pkg_warnings.append(f"card-count outlier check skipped: {exc}")

        # ── Step 4: Generate plain-speak primer ───────────────────────────────
        window_label = tuned.plan_window_label or "current-regime (uniform)"
        try:
            primer = generate_primer(
                archetype=archetype,
                sideboard=tuned.sideboard,
                matchup_plans=tuned.matchup_plans,
                venue_label=venue.label,
                window_label=window_label,
                field_shares=dict(field.shares),
            )
        except Exception as exc:
            log.warning("run_refresh: generate_primer failed for venue %r: %s", venue.key, exc)
            pkg_warnings.append(f"primer generation failed: {exc}")
            primer = _empty_primer(archetype, venue)

        packages.append(VenueTuningPackage(
            venue=venue,
            archetype=archetype,
            maindeck=tuned.maindeck,
            sideboard=tuned.sideboard,
            primer=primer,
            tuned_deck=tuned,
            outlier_deltas=outlier_deltas,
            window_label=window_label,
            data_absent=False,
            warnings=pkg_warnings,
        ))

    return RefreshResult(
        packages=packages,
        archetype=archetype,
        warnings=global_warnings,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_refresh_result(result: RefreshResult) -> str:
    """Render a RefreshResult as human-readable text.

    One major section per venue, separated by dividers.  Each section includes:
    - Venue header + window label
    - Tuned maindeck (60)
    - Recommended sideboard (15)
    - Card-count outlier annotations (when present)
    - Swap log (from tune_deck)
    - Full plain-speak primer (all matchup blurbs)
    """
    sections: list[str] = []

    banner = (
        f"=== Deck Tuning Refresh: {result.archetype} ===\n"
        f"Venues: {', '.join(p.venue.label for p in result.packages)}"
    )
    sections.append(banner)

    if result.warnings:
        sections.append("Global warnings:\n" + "\n".join(f"  ! {w}" for w in result.warnings))

    for pkg in result.packages:
        sections.append(_render_venue_package(pkg))

    return "\n\n".join(sections)


def _render_venue_package(pkg: VenueTuningPackage) -> str:
    """Render one VenueTuningPackage as text."""
    divider = "=" * 70
    lines: list[str] = [
        divider,
        f"Venue: {pkg.venue.label}",
        f"Archetype: {pkg.archetype}",
        f"Data window: {pkg.window_label}",
    ]

    if pkg.warnings:
        for w in pkg.warnings:
            lines.append(f"  [warn] {w}")

    if pkg.data_absent:
        lines.append(
            "\n  (no data for this venue — zero decks in corpus for this provenance)"
        )
        return "\n".join(lines)

    td = pkg.tuned_deck
    if td is None:
        lines.append("\n  (tuning failed — see warnings above)")
        return "\n".join(lines)

    # ── Tuning metadata ───────────────────────────────────────────────────
    lines.append("")
    if getattr(td, "fell_back", False):
        lines.append(
            f"  [no-signal] No per-card matchup signal found — maindeck kept as consensus "
            f"input. Sideboard still built. ({td.reason})"
        )
    else:
        n_swaps = len(td.swaps)
        lines.append(
            f"  Tuning: {n_swaps} maindeck swap(s)  |  "
            f"value {td.value_before:.4f} → {td.value_after:.4f}"
        )
        if td.swaps:
            for i, (cut, add) in enumerate(td.swaps, 1):
                lines.append(f"    {i}. CUT {cut}  →  ADD {add}")

    # ── Maindeck ──────────────────────────────────────────────────────────
    lines.append("\nMaindeck (60):")
    for name, count in sorted(pkg.maindeck.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"  {count} {name}")

    # ── Sideboard ──────────────────────────────────────────────────────────
    lines.append("\nSideboard (15):")
    if pkg.sideboard:
        for name, count in sorted(pkg.sideboard.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"  {count} {name}")
    else:
        lines.append("  (no sideboard recommendations — no castable hosers for this deck's colors)")

    # ── Card-count outlier annotations ────────────────────────────────────
    if pkg.outlier_deltas:
        lines.append("\nCard-count outliers (vs field modal):")
        for delta in pkg.outlier_deltas:
            board_tag = f"[{delta.board}]"
            modal_pct = max(delta.field_dist.values(), default=0.0)
            lines.append(
                f"  {board_tag} {delta.name}: you run {delta.user_count}, "
                f"field modal is {delta.field_modal} "
                f"({modal_pct:.0%} of field at modal count)"
            )

    # ── Plain-speak primer ────────────────────────────────────────────────
    primer = pkg.primer
    if hasattr(primer, "primer_text") and primer.primer_text:
        lines.append("")
        lines.append(primer.primer_text)
    else:
        lines.append("\n(No primer generated)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper: empty primer for error / no-data cases
# ---------------------------------------------------------------------------

def _empty_primer(archetype: str, venue: "Venue") -> "object":
    """Return a minimal SideboardPrimer for venues with no data."""
    from legacy_engine.advisory.primer import SideboardPrimer
    return SideboardPrimer(
        archetype=archetype,
        venue_label=venue.label,
        window_label="(no data)",
        sideboard_list="  (no data for this venue)",
        blurbs=[],
        primer_text="(no primer — venue has no data in the corpus)",
        honesty_note="",
    )
