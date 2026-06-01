"""CLI entry point for legacy-engine.

A skeleton of nested Click command groups mirroring the architecture's pillars.
Leaf commands are stubs that fail loudly until their feature lands, so the
command surface is real and discoverable from day one.
"""

from __future__ import annotations

import logging
import sys
from typing import NoReturn

import click


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


def _not_implemented(command: str) -> NoReturn:
    raise click.ClickException(f"not implemented: {command}")


_verbose = click.option("-v", "--verbose", is_flag=True, help="Verbose logging")


@click.group()
def main() -> None:
    """legacy-engine — Magic: The Gathering Legacy analytics."""


# ── seed: fetch + cache external data ──
@main.group()
def seed() -> None:
    """Fetch and cache external data (no runtime network calls elsewhere)."""


@seed.command("cards")
@_verbose
def seed_cards(verbose: bool) -> None:
    """Download Scryfall oracle bulk and build the card index."""
    _setup_logging(verbose)
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.scryfall import ScryfallClient
    from legacy_engine.models.card import Card

    with ScryfallClient() as client:
        client.download_bulk_data()
        index = client.load_card_index()

    # Materialize the cards table (dual storage: in-memory index + DuckDB).
    unique = {raw["name"]: raw for raw in index.values()}
    cards = [Card.from_scryfall(raw) for raw in unique.values()]
    con = store.connect()
    try:
        # Rebuild (drop + recreate) so a re-seed is a clean full refresh — INSERT OR IGNORE
        # face-alias rows otherwise can't be refreshed once present (stale aliases would persist).
        store.rebuild(con)
        loaded = store.load_cards(con, cards)
    finally:
        con.close()
    click.echo(f"Indexed {len(index)} names; loaded {loaded} cards into DuckDB")


@seed.command("cache")
@_verbose
def seed_cache(verbose: bool) -> None:
    """Mirror the fbettega tournament cache and ingest Legacy events into DuckDB."""
    _setup_logging(verbose)
    from legacy_engine.ingestion import cache, store

    cache.mirror_cache()
    con = store.connect()
    try:
        n = cache.ingest_cache(con)
    finally:
        con.close()
    click.echo(f"Ingested {n} Legacy tournaments into DuckDB")


@seed.command("rules")
@_verbose
def seed_rules(verbose: bool) -> None:
    """Vendor the MTGOFormatData archetype rules (pinned SHA)."""
    _setup_logging(verbose)
    from legacy_engine.ingestion.rules_vendor import refresh_rules

    sha = refresh_rules()
    click.echo(f"Vendored MTGOFormatData rules @ {sha or '(sha unresolved)'}")


@seed.command("banlist")
@_verbose
def seed_banlist(verbose: bool) -> None:
    """Report the current Legacy ban-list snapshot."""
    _setup_logging(verbose)
    from legacy_engine.ingestion.banlist import current_banlist

    snap = current_banlist()
    click.echo(f"Legacy ban list as of {snap.as_of}: {len(snap.banned)} cards banned")


# ── refresh: incremental update of mirrored sources ──
@main.command()
@_verbose
def refresh(verbose: bool) -> None:
    """Incrementally refresh all mirrored sources."""
    _setup_logging(verbose)
    _not_implemented("refresh")


# ── label: archetype classification ──
@main.command()
@_verbose
def label(verbose: bool) -> None:
    """Label ingested decklists with archetypes."""
    _setup_logging(verbose)
    from legacy_engine.archetype.labeler import label_decks
    from legacy_engine.archetype.rules import load_ruleset
    from legacy_engine.config import RULES_DIR
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.scryfall import ScryfallClient

    ruleset = load_ruleset(RULES_DIR)
    con = store.connect()
    try:
        with ScryfallClient() as client:
            client.load_card_index()
            n = label_decks(con, ruleset, client.get_card)
    finally:
        con.close()
    click.echo(f"Labeled {n} decks")


# ── report: meta & performance analytics ──
@main.group()
def report() -> None:
    """Meta & performance reports."""


@report.command("meta")
@click.option(
    "--definition",
    type=click.Choice(["raw", "topcut", "wrw", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Which meta-share definition(s) to compute.",
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Filter to online/paper events, or all (prints each basis when 'all').",
)
@click.option(
    "--min-share",
    type=float,
    default=0.02,
    show_default=True,
    help="Minimum share (0..1) for an archetype to appear in headline rows; sub-floor → Other.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@click.option(
    "--chart-dir",
    type=click.Path(file_okay=False),
    default=None,
    help="If set, render PNG charts into this directory.",
)
@_verbose
def report_meta(
    definition: str,
    provenance: str,
    min_share: float,
    db: str | None,
    chart_dir: str | None,
    verbose: bool,
) -> None:
    """Metagame share (raw / top-cut / win-rate-weighted; online vs paper)."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.analytics.metashare import MetaShareReport, compute_all, compute_metashare
    from legacy_engine.ingestion import store

    if chart_dir:
        from legacy_engine.analytics.charts import render_metashare
        chart_out = Path(chart_dir)
        chart_out.mkdir(parents=True, exist_ok=True)

    con = store.connect(db) if db else store.connect()
    try:
        bases: list[str | None]
        if provenance == "all":
            bases = [None, "online", "paper"]
        else:
            bases = [provenance]

        definitions: list[str]
        if definition == "all":
            definitions = ["raw", "topcut", "wrw"]
        else:
            definitions = [definition]

        for basis in bases:
            for defn in definitions:
                report = compute_metashare(
                    con,
                    definition=defn,
                    provenance=basis,
                    min_share=min_share,
                )
                _print_metashare_report(report)
                if chart_dir:
                    fname = _chart_filename("meta", defn, basis)
                    out = render_metashare(report, chart_out / fname)
                    click.echo(f"Chart written: {out}")
    finally:
        con.close()


def _print_metashare_report(report: "MetaShareReport") -> None:
    """Render a meta-share report as a labeled text table."""
    from legacy_engine.analytics.metashare import MetaShareReport  # noqa: F401

    basis_label = report.provenance if report.provenance else "all"
    click.echo(f"\n=== Meta Share [{report.definition.upper()}] basis={basis_label} ===")
    click.echo(f"Total decks (denominator): {report.total_decks}")
    if report.unlabeled > 0:
        click.echo(f"Unlabeled (NULL archetype, excluded): {report.unlabeled}")
    click.echo(f"Inclusion floor: {report.min_share:.1%}")
    click.echo(f"{'Archetype':<30}  {'Share':>7}  {'n':>6}  {'Tier':<12}")
    click.echo("-" * 62)

    if not report.entries:
        click.echo("(no archetypes meet the inclusion threshold)")
        return

    for entry in report.entries:
        fringe_marker = " *" if entry.fringe and entry.archetype != "Other" else "  "
        click.echo(
            f"{entry.archetype:<30}  {entry.share:>6.1%}  {entry.n:>6}  {entry.tier:<12}{fringe_marker}"
        )


@report.command("matchups")
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Filter to online/paper events, or all (prints each basis when 'all').",
)
@click.option(
    "--min-row-share",
    type=float,
    default=0.02,
    show_default=True,
    help="Minimum share of matches for an archetype to appear as a row/column.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@click.option(
    "--chart-dir",
    type=click.Path(file_okay=False),
    default=None,
    help="If set, render PNG charts into this directory.",
)
@_verbose
def report_matchups(
    provenance: str,
    min_row_share: float,
    db: str | None,
    chart_dir: str | None,
    verbose: bool,
) -> None:
    """Archetype matchup matrix with confidence intervals."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.analytics.matchup import MatchupMatrix, build_matrix
    from legacy_engine.ingestion import store

    if chart_dir:
        from legacy_engine.analytics.charts import render_matchup_heatmap
        chart_out = Path(chart_dir)
        chart_out.mkdir(parents=True, exist_ok=True)

    con = store.connect(db) if db else store.connect()
    try:
        bases: list[str | None]
        if provenance == "all":
            bases = [None, "online", "paper"]
        else:
            bases = [provenance]

        for basis in bases:
            matrix = build_matrix(con, provenance=basis, min_row_share=min_row_share)
            _print_matchup_matrix(matrix)
            if chart_dir:
                fname = _chart_filename("matchups", "matchups", basis)
                out = render_matchup_heatmap(matrix, chart_out / fname)
                click.echo(f"Chart written: {out}")
    finally:
        con.close()


def _print_matchup_matrix(matrix) -> None:  # type: legacy_engine.analytics.matchup.MatchupMatrix
    """Render a matchup matrix as a labeled text table."""

    basis_label = matrix.provenance if matrix.provenance else "all"
    click.echo(f"\n=== Matchup Matrix [{basis_label}] ===")
    click.echo(f"Total decisive matches: {matrix.total_matches}")
    click.echo(f"Caveat: {matrix.caveat}")

    if not matrix.archetypes:
        click.echo("(no archetypes meet the row-inclusion threshold)")
        return

    archetypes = matrix.archetypes
    col_width = max(len(a) for a in archetypes)
    col_width = max(col_width, 20)  # minimum column width for cell content
    row_label_width = max(len(a) for a in archetypes)

    # Header row
    header = " " * row_label_width + "  " + "  ".join(a.ljust(col_width) for a in archetypes)
    click.echo(header)
    click.echo("-" * len(header))

    for row_arch in archetypes:
        row_parts = [row_arch.ljust(row_label_width)]
        for col_arch in archetypes:
            cell = matrix.cells.get((row_arch, col_arch))
            if cell is None:
                part = "n/a"
            elif cell.is_mirror:
                part = f"50% (mirror, n={cell.n})" if cell.display else f"n={cell.n} (mirror)"
            elif not cell.display:
                part = f"n={cell.n} (insufficient)"
            else:
                pct = f"{cell.p_shrunk:.1%}" if cell.p_shrunk is not None else "n/a"
                part = f"{pct} (n={cell.n})"
            row_parts.append(part.ljust(col_width))
        click.echo("  ".join(row_parts))


@report.command("trends")
@click.option(
    "--definition",
    type=click.Choice(["raw", "topcut"], case_sensitive=False),
    default="raw",
    show_default=True,
    help="Which meta-share definition to compute per regime.",
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Filter to online/paper events, or all (prints each basis when 'all').",
)
@click.option(
    "--min-share",
    type=float,
    default=0.02,
    show_default=True,
    help="Minimum share (0..1) for an archetype to appear; sub-floor rows are omitted per regime.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@click.option(
    "--chart-dir",
    type=click.Path(file_okay=False),
    default=None,
    help="If set, render PNG charts into this directory.",
)
@_verbose
def report_trends(
    definition: str,
    provenance: str,
    min_share: float,
    db: str | None,
    chart_dir: str | None,
    verbose: bool,
) -> None:
    """Meta-share evolution across ban-list regimes (version-stamped)."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.analytics.trends import compute_trends
    from legacy_engine.ingestion import store

    if chart_dir:
        from legacy_engine.analytics.charts import render_trends
        chart_out = Path(chart_dir)
        chart_out.mkdir(parents=True, exist_ok=True)

    con = store.connect(db) if db else store.connect()
    try:
        bases: list[str | None]
        if provenance == "all":
            bases = [None, "online", "paper"]
        else:
            bases = [provenance]

        for basis in bases:
            series = compute_trends(
                con,
                definition=definition,
                provenance=basis,
                min_share=min_share,
            )
            _print_trend_series(series)
            if chart_dir:
                fname = _chart_filename("trends", definition, basis)
                out = render_trends(series, chart_out / fname)
                click.echo(f"Chart written: {out}")
    finally:
        con.close()


def _print_trend_series(series: "TrendSeries") -> None:
    """Render a meta-share trend series as a trajectory table (archetypes × regimes)."""
    from legacy_engine.analytics.trends import TrendSeries  # noqa: F401

    basis_label = series.provenance if series.provenance else "all"
    click.echo(f"\n=== Meta Trends [{series.definition.upper()}] basis={basis_label} ===")

    if not series.regimes:
        click.echo("(no events in corpus — nothing to trend)")
        return

    # Print regime sub-headers
    for regime in series.regimes:
        since_str = regime.since.isoformat() if regime.since else "—"
        until_str = regime.until.isoformat() if regime.until else "current"
        thin_banner = "  ⚠ THIN (flagged evolving)" if regime.thin else ""
        click.echo(
            f"  Regime: {regime.label!r}  [{since_str} → {until_str}]"
            f"  events={regime.event_count}  span={regime.span_days}d{thin_banner}"
        )

    click.echo("")

    if not series.archetypes:
        click.echo("(no archetypes meet the inclusion threshold in any regime)")
        return

    # Build trajectory table: archetype rows × regime columns
    # Column widths: archetype col + one col per regime (share%)
    arch_col_w = max(len(a) for a in series.archetypes)
    arch_col_w = max(arch_col_w, 12)

    # Abbreviated regime column headers
    regime_headers = []
    for r in series.regimes:
        since_str = r.since.isoformat() if r.since else "baseline"
        regime_headers.append(since_str)

    col_w = max(max(len(h) for h in regime_headers), 10)

    # Header row
    header_parts = [f"{'Archetype':<{arch_col_w}}"]
    for h in regime_headers:
        header_parts.append(h.rjust(col_w))
    click.echo("  ".join(header_parts))
    click.echo("-" * (arch_col_w + (col_w + 2) * len(series.regimes)))

    for archetype in series.archetypes:
        row_parts = [f"{archetype:<{arch_col_w}}"]
        for regime in series.regimes:
            cell = series.cells.get((regime.label, archetype))
            if cell is None:
                row_parts.append("—".rjust(col_w))
            else:
                thin_marker = "*" if regime.thin else " "
                row_parts.append(f"{cell.share:>6.1%}{thin_marker}".rjust(col_w))
        click.echo("  ".join(row_parts))


@report.command("tiers")
@click.option(
    "--definition",
    type=click.Choice(["raw", "topcut", "wrw"], case_sensitive=False),
    default="raw",
    show_default=True,
    help="Which meta-share definition to use for tier binning.",
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Filter to online/paper events, or all (prints each basis when 'all').",
)
@click.option(
    "--min-share",
    type=float,
    default=0.02,
    show_default=True,
    help="Minimum share (0..1) for an archetype to appear in the report.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@click.option(
    "--chart-dir",
    type=click.Path(file_okay=False),
    default=None,
    help="If set, render PNG charts into this directory.",
)
@_verbose
def report_tiers(
    definition: str,
    provenance: str,
    min_share: float,
    db: str | None,
    chart_dir: str | None,
    verbose: bool,
) -> None:
    """Tier list derived from the current metagame (S/A/B buckets by share)."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.analytics.charts import _tier_model, render_tier_list
    from legacy_engine.analytics.metashare import compute_metashare
    from legacy_engine.ingestion import store

    if chart_dir:
        chart_out = Path(chart_dir)
        chart_out.mkdir(parents=True, exist_ok=True)

    con = store.connect(db) if db else store.connect()
    try:
        bases: list[str | None]
        if provenance == "all":
            bases = [None, "online", "paper"]
        else:
            bases = [provenance]

        for basis in bases:
            report = compute_metashare(
                con,
                definition=definition,
                provenance=basis,
                min_share=min_share,
            )
            model = _tier_model(report)
            _print_tier_list(model)
            if chart_dir:
                fname = _chart_filename("tiers", definition, basis)
                out = render_tier_list(report, chart_out / fname)
                click.echo(f"Chart written: {out}")
    finally:
        con.close()


def _print_tier_list(model: "TierModel") -> None:
    """Render a tier model as a labeled text tier list."""
    from legacy_engine.analytics.charts import TierModel  # noqa: F401

    click.echo(f"\n=== {model.title} ===")
    click.echo(model.subtitle)
    for tier_key in ("S", "A", "B"):
        entries = model.buckets[tier_key]
        click.echo(f"\n  Tier {tier_key}:")
        if not entries:
            click.echo("    (none)")
        else:
            for archetype, share, conf_tier in entries:
                click.echo(f"    {archetype:<30}  {share:>6.1%}  [{conf_tier}]")


@report.command("gaps")
@click.option(
    "--definition",
    type=click.Choice(["raw", "topcut", "wrw"], case_sensitive=False),
    default="raw",
    show_default=True,
    help="Meta-share definition for the popularity term + candidate set.",
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Filter to online/paper events, or all.",
)
@click.option(
    "--share-weight",
    type=float,
    default=1.0,
    show_default=True,
    help="Popularity penalty weight in gap_score = S − weight·share.",
)
@click.option(
    "--min-coverage",
    type=float,
    default=0.5,
    show_default=True,
    help="Exclude archetypes whose matchup data_coverage is below this (thin S). Reported, not hidden.",
)
@click.option(
    "--risk-quantile",
    type=float,
    default=0.25,
    show_default=True,
    help="Lower quantile of S used as the risk-adjusted column (lower = more conservative).",
)
@click.option(
    "--min-share",
    type=float,
    default=0.0,
    show_default=True,
    help="Minimum meta-share for an archetype to be considered a candidate.",
)
@click.option("--seed", type=int, default=None, help="Seed for the Monte-Carlo positioning (determinism).")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def report_gaps(
    definition: str,
    provenance: str,
    share_weight: float,
    min_coverage: float,
    risk_quantile: float,
    min_share: float,
    seed: int | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Under-explored archetypes: high positioning S, low meta-share (deck-gen mode 3)."""
    _setup_logging(verbose)
    from legacy_engine.advisory.gaps import compute_archetype_gaps
    from legacy_engine.ingestion import store

    basis = None if provenance == "all" else provenance

    con = store.connect(db) if db else store.connect()
    try:
        report = compute_archetype_gaps(
            con,
            definition=definition,
            provenance=basis,
            share_weight=share_weight,
            min_coverage=min_coverage,
            risk_quantile=risk_quantile,
            min_share=min_share,
            seed=seed,
        )
        _print_gap_report(report)
    finally:
        con.close()


def _print_gap_report(report: "GapReport") -> None:
    """Render a GapReport as a labeled text table; report thin-data exclusions explicitly."""
    from legacy_engine.advisory.gaps import GapReport  # noqa: F401

    q_label = f"Sq{report.risk_quantile:.2f}"
    click.echo(
        f"\n=== Archetype Gaps (field={report.field_source}, "
        f"gap = S − {report.share_weight:g}·share) ==="
    )
    click.echo(
        f"  {'archetype':<30}  {'gap':>7}  {'S':>6}  {q_label:>7}  {'share':>6}  {'cov':>5}  tier"
    )
    if not report.gaps:
        click.echo("  (no positionable archetypes cleared the coverage gate)")
    for g in report.gaps:
        click.echo(
            f"  {g.archetype:<30}  {g.gap_score:>7.3f}  {g.s_mean:>6.3f}  "
            f"{g.s_quantile:>7.3f}  {g.share:>6.1%}  {g.data_coverage:>5.2f}  [{g.tier}]"
        )
    if report.excluded_low_coverage:
        click.echo(
            f"\n  Excluded {len(report.excluded_low_coverage)} archetype(s) for thin matchup "
            f"data (coverage < {report.min_coverage:g}): "
            f"{', '.join(report.excluded_low_coverage)}"
        )


@report.command("cards")
@click.option("--archetype", default=None, help="Restrict to cards an archetype plays (via card_frequencies).")
@click.option("--vs", "opponent", default=None, help="Show per-matchup value vs this opponent; else shows marginal.")
@click.option("--board", default="main", show_default=True, help="Board to query: main or side.")
@click.option(
    "--min-tier",
    type=click.Choice(["speculative", "evolving", "established"], case_sensitive=False),
    default="speculative",
    show_default=True,
    help="Suppress rows below this confidence tier; prints a note when rows are hidden.",
)
@click.option("--since", default=None, help="ISO date lower bound (inclusive) for tournament window.")
@click.option("--until", default=None, help="ISO date upper bound (inclusive) for tournament window.")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def report_cards(
    archetype: str | None,
    opponent: str | None,
    board: str,
    min_tier: str,
    since: str | None,
    until: str | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Per-card win-rate (presence-correlational — NOT causal).

    Shows how a card's decks perform relative to the archetype's baseline win-rate.
    Thin cells (below --min-tier) are suppressed with a note, never fabricated.
    """
    _setup_logging(verbose)

    from legacy_engine.analytics.card_value import CardValue, card_value_marginal, card_value_matchup, card_values_vs
    from legacy_engine.analytics.match_results import compute_card_winrates
    from legacy_engine.ingestion import store

    _TIER_ORDER = {"speculative": 0, "evolving": 1, "established": 2}
    min_tier_rank = _TIER_ORDER[min_tier.lower()]

    con = store.connect(db) if db else store.connect()
    try:
        # Resolve the effective window ONCE so the card list and the win-rate
        # values share the same window. card_frequencies defaults None -> latest
        # ban regime; compute_card_winrates treats None as the full corpus — so
        # we must pin both sides to the same window or an --archetype report
        # would scope the card list to one window and the values to another.
        if since is None and until is None:
            from legacy_engine.generation.consensus import _latest_regime_window
            effective_since, effective_until = _latest_regime_window()
        else:
            effective_since, effective_until = since, until

        r = compute_card_winrates(con, since=effective_since, until=effective_until)

        # Determine the set of cards to report.
        if archetype is not None:
            from legacy_engine.generation.consensus import card_frequencies
            card_freqs = card_frequencies(
                con, archetype, board=board, since=effective_since, until=effective_until
            )
            cards = [cf.name for cf in card_freqs]
            if not cards:
                click.echo(f"No cards found for archetype={archetype!r} board={board!r} in the given window.")
                return
        else:
            # All cards observed on the requested board in the corpus.
            cards = sorted({card for card, brd in r.marginal if brd == board})

        if not cards:
            click.echo(f"No cards found for board={board!r}.")
            return

        # Build CardValue objects for each card.
        if opponent is not None:
            values = card_values_vs(r, cards, board, opponent)
        else:
            values = {card: card_value_marginal(r, card, board) for card in cards}

        # Filter + render.
        tier_label = "all" if min_tier == "speculative" else f">= {min_tier}"
        vs_label = f" vs {opponent!r}" if opponent else " (marginal)"
        click.echo(f"\n=== Card Win-Rates [board={board}{vs_label}, tier={tier_label}] ===")
        click.echo("NOTE: presence-correlational — NOT causal. See registered 75, not game-by-game play.")
        window_label = (
            f"{effective_since or 'start'} → {effective_until or 'now'}"
            if (effective_since or effective_until)
            else "all dates"
        )
        click.echo(f"Window: {window_label}  |  decisive matches in window: {r.coverage.decisive_matched}")
        click.echo(f"{'Card':<35}  {'Board':<5}  {'n':>6}  {'p_raw':>7}  {'p_shrunk':>8}  {'lift':>7}  {'tier':<12}")
        click.echo("-" * 90)

        suppressed = 0
        printed = 0
        for card in sorted(values.keys()):
            cv = values[card]
            tier_rank = _TIER_ORDER[cv.tier]
            if tier_rank < min_tier_rank:
                suppressed += 1
                continue
            p_raw_str = f"{cv.p_raw:.3f}" if cv.p_raw is not None else "n/a"
            lift_str = f"{cv.lift:+.3f}"
            click.echo(
                f"{card:<35}  {cv.board:<5}  {cv.n:>6}  {p_raw_str:>7}  "
                f"{cv.p_shrunk:>8.3f}  {lift_str:>7}  {cv.tier:<12}"
            )
            printed += 1

        if suppressed > 0:
            click.echo(
                f"\n  {suppressed} row(s) below {min_tier!r} gate — suppressed "
                f"(use --min-tier speculative to show all). Data present; not fabricated."
            )
        if printed == 0 and suppressed == 0:
            click.echo("(no card data for the specified slice)")
    finally:
        con.close()


def _chart_filename(kind: str, definition: str, provenance: str | None) -> str:
    """Derive a chart filename from the kind, definition, and provenance basis.

    Examples: meta_raw_online.png, matchups_all.png, trends_raw.png, tiers_raw_paper.png.
    """
    basis = provenance if provenance else "all"
    if kind == "matchups":
        return f"matchups_{basis}.png"
    return f"{kind}_{definition}_{basis}.png"


# ── advise: meta attack / advisory ──
@main.group()
def advise() -> None:
    """Meta attack / advisory — how to attack the field."""


@advise.command("positioning")
@click.option(
    "--deck",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to a plain-text decklist file.",
)
@click.option(
    "--archetype",
    default=None,
    help="Override archetype classification.",
)
@click.option(
    "--field",
    "field_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a custom field file (<share> <archetype> lines).",
)
@click.option(
    "--candidates",
    "candidates_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a file listing candidate archetypes (one per line) for ranking.",
)
@click.option(
    "--reserved",
    type=int,
    default=0,
    show_default=True,
    help="Sideboard slots to reserve (for --report mode; ignored here).",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="RNG seed for deterministic MC output.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def advise_positioning(
    deck: str,
    archetype: str | None,
    field_file: str | None,
    candidates_file: str | None,
    reserved: int,
    seed: int | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Score a deck's expected win rate against the weighted field."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.positioning import positioning_score, rank_decks
    from legacy_engine.advisory.report import _classify_deck, _load_field, _parse_decklist
    from legacy_engine.analytics.matchup import build_matrix
    from legacy_engine.ingestion import store

    deck_text = Path(deck).read_text()
    mainboard, sideboard_cards = _parse_decklist(deck_text)
    field_text = Path(field_file).read_text() if field_file else None

    con = store.connect(db) if db else store.connect()
    try:
        field = _load_field(con, field_text=field_text)
        matrix = build_matrix(con)

        resolved_archetype = archetype
        if resolved_archetype is None:
            result = _classify_deck(con, mainboard, sideboard_cards)
            resolved_archetype = result.archetype
            click.echo(f"Classified archetype: {resolved_archetype} (kind={result.kind})")

        if candidates_file:
            candidates = [
                ln.strip() for ln in Path(candidates_file).read_text().splitlines()
                if ln.strip() and not ln.startswith("#")
            ]
            ranking = rank_decks(matrix, field, candidates, seed=seed)
            q_label = f"Q{ranking.quantile_level:.2f}"
            click.echo(f"\n=== Deck Ranking (field_source={ranking.field_source}, sort={q_label}) ===")
            for d in ranking.decks:
                lo, hi = ranking.s_ci[d]
                cov = ranking.data_coverage[d]
                low_flag = " [low_coverage]" if d in ranking.low_coverage else ""
                click.echo(
                    f"  {d:<35}  S={ranking.s_mean[d]:.3f}  "
                    f"CI=[{lo:.3f},{hi:.3f}]  P(best)={ranking.p_best[d]:.3f}  "
                    f"{q_label}={ranking.s_quantile[d]:.3f}  cov={cov:.2f}{low_flag}"
                )
        else:
            pos = positioning_score(matrix, field, resolved_archetype, seed=seed)
            click.echo(f"\n=== Positioning: {pos.deck_archetype} (field_source={pos.field_source}) ===")
            click.echo(f"  S (meta-positioning): {pos.s_mean:.3f}")
            click.echo(f"  95% CI: [{pos.s_ci[0]:.3f}, {pos.s_ci[1]:.3f}]")
            click.echo(f"  Unweighted mean (u_bar): {pos.u_bar:.3f}")
            click.echo(f"  MC draws: {pos.n_draws}")
            if pos.imputed:
                click.echo(f"  Imputed opponents ({len(pos.imputed)}): {', '.join(sorted(pos.imputed))}")
            for w in pos.warnings:
                click.echo(f"  [warn] {w}")
    finally:
        con.close()


@advise.command("sideboard")
@click.option(
    "--deck",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to a plain-text decklist file.",
)
@click.option(
    "--field",
    "field_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a custom field file (<share> <archetype> lines).",
)
@click.option(
    "--reserved",
    type=int,
    default=0,
    show_default=True,
    help="Sideboard slots reserved for flex/maindeck-overlap.",
)
@click.option(
    "--solver",
    type=click.Choice(["ilp", "greedy"], case_sensitive=False),
    default="ilp",
    show_default=True,
    help="Solver to use: ilp (exact, primary) or greedy (fallback).",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def advise_sideboard(
    deck: str,
    field_file: str | None,
    reserved: int,
    solver: str,
    db: str | None,
    verbose: bool,
) -> None:
    """Recommend a sideboard package for an expected field."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import _load_field, _parse_decklist
    from legacy_engine.advisory.sideboard import recommend_sideboard
    from legacy_engine.ingestion import store

    deck_text = Path(deck).read_text()
    mainboard, _sideboard = _parse_decklist(deck_text)
    field_text = Path(field_file).read_text() if field_file else None

    con = store.connect(db) if db else store.connect()
    try:
        field = _load_field(con, field_text=field_text)
        pkg = recommend_sideboard(con, field, mainboard, reserved=reserved, solver=solver)
        click.echo(f"\n=== Sideboard Recommendation (solver={pkg.solver_used}, field_source={pkg.field_source}) ===")
        click.echo(f"  Budget: {pkg.budget}  |  Reserved: {pkg.reserved}")
        click.echo(f"  Covered weight: {pkg.covered_weight:.4f}")
        if pkg.cards:
            for card, copies in sorted(pkg.cards.items(), key=lambda kv: kv[1], reverse=True):
                click.echo(f"  {copies}x {card}")
        else:
            click.echo("  (no recommendations — no castable hosers for this deck's colors)")
        click.echo(f"  Note: {pkg.heuristic_note}")
        for w in pkg.warnings:
            click.echo(f"  [warn] {w}")
        # --- Per-matchup OUT/IN plans (only when value_informed) ---
        if pkg.value_informed and pkg.matchup_plans:
            click.echo("\n  Per-matchup plans (presence-correlational — see disclaimer):")
            for opp, plan in sorted(pkg.matchup_plans.items()):
                if plan.degraded:
                    click.echo(f"    vs {opp}: thin data — no per-matchup plan (rely on 15 composition)")
                else:
                    out_str = ", ".join(
                        f"{c}x {card}" for card, c in sorted(plan.side_out.items())
                    ) or "(none)"
                    in_str = ", ".join(
                        f"{c}x {card}" for card, c in sorted(plan.side_in.items())
                    ) or "(none)"
                    click.echo(
                        f"    vs {opp} [{plan.tier}, n≥{plan.n_basis}]: "
                        f"OUT {out_str} | IN {in_str}"
                    )
            from legacy_engine.advisory.sideboard import _VALUE_DISCLAIMER
            click.echo(f"\n  [disclaimer] {_VALUE_DISCLAIMER}")
    finally:
        con.close()


@advise.command("whattoplay")
@click.option(
    "--deck",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to a plain-text decklist file.",
)
@click.option(
    "--archetype",
    default=None,
    help="Override archetype classification.",
)
@click.option(
    "--field",
    "field_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a custom field file (<share> <archetype> lines).",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def advise_whattoplay(
    deck: str,
    archetype: str | None,
    field_file: str | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Field read and deck recommendation."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import _classify_deck, _load_field, _parse_decklist, _render_whattoplay
    from legacy_engine.advisory.whattoplay import proactivity_score, vulnerability_tags_for_deck
    from legacy_engine.ingestion import store

    deck_text = Path(deck).read_text()
    mainboard, sideboard_cards = _parse_decklist(deck_text)
    field_text = Path(field_file).read_text() if field_file else None

    con = store.connect(db) if db else store.connect()
    try:
        field = _load_field(con, field_text=field_text)

        resolved_archetype = archetype
        if resolved_archetype is None:
            result = _classify_deck(con, mainboard, sideboard_cards)
            resolved_archetype = result.archetype
            click.echo(f"Classified archetype: {resolved_archetype} (kind={result.kind})")

        from legacy_engine.advisory.report import FieldReadReport
        from legacy_engine.advisory.whattoplay import best_deck_vs_best_call, field_vulnerability_tags, hate_equity
        from legacy_engine.analytics.matchup import build_matrix

        matrix = build_matrix(con)
        archetype_tags = field_vulnerability_tags(con, field)
        field_vuln_profile = hate_equity(field, archetype_tags)

        proactivity = proactivity_score(con, mainboard, archetype_tag=resolved_archetype)
        deck_vuln = vulnerability_tags_for_deck(con, mainboard)

        # Build a minimal report shell for the renderer
        from legacy_engine.advisory.sideboard import SideboardPackage
        from legacy_engine.advisory.sideboard import PickTrace
        dummy_sb = SideboardPackage(
            cards={}, trace=[], covered_weight=0.0, budget=15, reserved=0,
            solver_used="none", field_source=field.field_source,
            heuristic_note="(not computed in whattoplay mode)", warnings=(),
        )

        from legacy_engine.advisory.whattoplay import BestDeckCall
        bdc = best_deck_vs_best_call(matrix, field, resolved_archetype)

        report = FieldReadReport(
            deck_archetype=resolved_archetype,
            field_source=field.field_source,
            field_shares=dict(field.shares),
            field_vuln_profile=field_vuln_profile,
            positioning=None,
            proactivity=proactivity,
            vulnerability=deck_vuln,
            best_deck_call=bdc,
            sideboard=dummy_sb,
            audit=[],
            warnings=(),
        )
        click.echo(_render_whattoplay(report))
    finally:
        con.close()


@advise.command("report")
@click.option(
    "--deck",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to a plain-text decklist file.",
)
@click.option(
    "--archetype",
    default=None,
    help="Override archetype classification.",
)
@click.option(
    "--field",
    "field_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a custom field file (<share> <archetype> lines).",
)
@click.option(
    "--reserved",
    type=int,
    default=0,
    show_default=True,
    help="Sideboard slots reserved for flex/maindeck-overlap.",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="RNG seed for deterministic MC output.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def advise_report(
    deck: str,
    archetype: str | None,
    field_file: str | None,
    reserved: int,
    seed: int | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Full Field Read & Deck Recommendation (positioning + what-to-play + sideboard + audit)."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import (
        _load_field,
        _parse_decklist,
        build_field_read_report,
        render_field_read,
    )
    from legacy_engine.ingestion import store

    deck_text = Path(deck).read_text()
    mainboard, sideboard_cards = _parse_decklist(deck_text)
    field_text = Path(field_file).read_text() if field_file else None

    con = store.connect(db) if db else store.connect()
    try:
        field = _load_field(con, field_text=field_text)
        report = build_field_read_report(
            con,
            mainboard,
            sideboard_cards,
            field,
            archetype=archetype,
            reserved=reserved,
            seed=seed,
        )
        click.echo(render_field_read(report))
    finally:
        con.close()


# ── generate: deck generation ──
@main.group()
def generate() -> None:
    """Deck generation — consensus baseline and field-tuned decklists."""


@generate.command("consensus")
@click.option("--archetype", required=True, help="Archetype name to generate a consensus deck for.")
@click.option(
    "--since",
    default=None,
    help="Start of corpus window (YYYY-MM-DD, inclusive). Defaults to latest ban-regime.",
)
@click.option(
    "--until",
    default=None,
    help="End of corpus window (YYYY-MM-DD, exclusive). Defaults to latest ban-regime.",
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper"], case_sensitive=False),
    default=None,
    help="Filter to online or paper events (default: all).",
)
@click.option(
    "--export",
    "export_fmt",
    type=click.Choice(["moxfield", "archidekt", "mtggoldfish", "text", "dec"], case_sensitive=False),
    default=None,
    help="Also emit the decklist in the specified import format.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def generate_consensus(
    archetype: str,
    since: str | None,
    until: str | None,
    provenance: str | None,
    export_fmt: str | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Generate a consensus baseline decklist for an archetype.

    Aggregates modal card choices across all archetype decks in the corpus window
    and reconciles to a legal, exactly-60 maindeck + ≤15 sideboard.

    Example: legacy-engine generate consensus --archetype "Izzet Delver"
    """
    _setup_logging(verbose)

    from legacy_engine.generation.consensus import build_consensus
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        deck = build_consensus(
            con,
            archetype,
            since=since,
            until=until,
            provenance=provenance,
        )
    finally:
        con.close()

    if deck.sample_n == 0:
        raise click.ClickException(
            f"No decks found for archetype {archetype!r} in the window "
            f"[{deck.window[0] or 'open'}, {deck.window[1] or 'open'})."
        )

    # Print the decklist in the default readable format.
    click.echo(f"// Consensus deck: {deck.archetype}")
    window_since = deck.window[0] or "open"
    window_until = deck.window[1] or "current"
    click.echo(f"// Window: [{window_since}, {window_until})  sample_n={deck.sample_n}")
    click.echo("")

    # Maindeck — sorted by count desc, then name for stable output.
    for name, count in sorted(deck.maindeck.items(), key=lambda kv: (-kv[1], kv[0])):
        click.echo(f"{count} {name}")

    if deck.sideboard:
        click.echo("")
        click.echo("Sideboard")
        for name, count in sorted(deck.sideboard.items(), key=lambda kv: (-kv[1], kv[0])):
            click.echo(f"{count} {name}")

    # Footer.
    main_total = sum(deck.maindeck.values())
    side_total = sum(deck.sideboard.values())
    click.echo(f"\n// Maindeck: {main_total}  Sideboard: {side_total}")

    if deck.legality_errors:
        for err in deck.legality_errors:
            click.echo(f"// [LEGALITY] {err}", err=True)
    else:
        click.echo("// Legality: OK")

    # Optional export format output.
    if export_fmt:
        from legacy_engine.generation.export import format_decklist
        click.echo("\n// --- Export ---")
        click.echo(format_decklist(deck.maindeck, deck.sideboard, fmt=export_fmt))


@generate.command("tune")
@click.option(
    "--deck",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to a plain-text decklist file (consensus shell or user list).",
)
@click.option(
    "--archetype",
    default=None,
    help="Archetype name; if omitted the deck is classified automatically.",
)
@click.option(
    "--field",
    "field_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a custom field file (<share> <archetype> lines).",
)
@click.option(
    "--since",
    default=None,
    help="Start of corpus window (YYYY-MM-DD, inclusive). Defaults to latest ban-regime.",
)
@click.option(
    "--until",
    default=None,
    help="End of corpus window (YYYY-MM-DD, exclusive). Defaults to latest ban-regime.",
)
@click.option(
    "--lock-threshold",
    type=float,
    default=0.65,
    show_default=True,
    help="Inclusion fraction at or above which a maindeck card is locked (0..1).",
)
@click.option(
    "--max-swaps",
    type=int,
    default=8,
    show_default=True,
    help="Maximum number of greedy maindeck swap rounds.",
)
@click.option(
    "--export",
    "export_fmt",
    type=click.Choice(["moxfield", "archidekt", "mtggoldfish", "text", "dec"], case_sensitive=False),
    default=None,
    help="Also emit the tuned 60+15 in the specified import format.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def generate_tune(
    deck: str,
    archetype: str | None,
    field_file: str | None,
    since: str | None,
    until: str | None,
    lock_threshold: float,
    max_swaps: int,
    export_fmt: str | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Tune a deck shell against the current field (mode 2).

    Reads a plain-text decklist (consensus or user-supplied), identifies the
    archetype, partitions maindeck into locked-core and flex slots, then greedily
    swaps flex cards toward better field-weighted coverage.  Re-runs the sideboard
    recommender for the 15 after tuning.

    Prints: tuned 60+15, ordered swap log, coverage before/after, positioning S
    (archetype context — unchanged by card swaps), and a fallback note when the
    field data is too thin to tune.

    Example: legacy-engine generate tune --deck shell.txt --archetype "Izzet Delver"
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import _classify_deck, _load_field, _parse_decklist
    from legacy_engine.generation.tuning import tune_deck
    from legacy_engine.ingestion import store

    deck_text = Path(deck).read_text()
    maindeck, starting_side = _parse_decklist(deck_text)
    field_text = Path(field_file).read_text() if field_file else None

    con = store.connect(db) if db else store.connect()
    try:
        field = _load_field(con, field_text=field_text)

        resolved_archetype = archetype
        if resolved_archetype is None:
            result = _classify_deck(con, maindeck, starting_side)
            resolved_archetype = result.archetype
            click.echo(f"Classified archetype: {resolved_archetype} (kind={result.kind})")

        tuned = tune_deck(
            con,
            resolved_archetype,
            maindeck,
            starting_side,
            field=field,
            since=since,
            until=until,
            lock_threshold=lock_threshold,
            max_swaps=max_swaps,
        )
    finally:
        con.close()

    # ── Header ───────────────────────────────────────────────────────────────
    click.echo(f"\n// Tuned deck: {tuned.archetype}")

    # Primary objective: per-card field-weighted value (the real swap driver).
    click.echo(
        f"// Value (per-card field-weighted lift): "
        f"{tuned.value_before:.4f} → {tuned.value_after:.4f}"
        + (" [no-signal: no swaps made]" if tuned.objective == "no-signal-skip" else "")
    )

    # Coverage: audit context only (NOT the swap driver).
    click.echo(f"// Coverage (audit): {tuned.coverage_before:.4f} → {tuned.coverage_after:.4f}")

    if tuned.positioning_s is not None:
        click.echo(
            f"// Positioning S(archetype)={tuned.positioning_s:.3f} "
            "[archetype context; unchanged by card swaps]"
        )
    else:
        click.echo("// Positioning S: n/a (archetype absent from matchup matrix)")

    if tuned.fell_back:
        click.echo(f"// [FALLBACK] {tuned.reason}")
    else:
        click.echo(f"// {tuned.reason}")

    click.echo("")

    # ── Maindeck ─────────────────────────────────────────────────────────────
    for name, count in sorted(tuned.maindeck.items(), key=lambda kv: (-kv[1], kv[0])):
        click.echo(f"{count} {name}")

    # ── Sideboard ─────────────────────────────────────────────────────────────
    if tuned.sideboard:
        click.echo("")
        click.echo("Sideboard")
        for name, count in sorted(tuned.sideboard.items(), key=lambda kv: (-kv[1], kv[0])):
            click.echo(f"{count} {name}")

    # ── Footer ────────────────────────────────────────────────────────────────
    main_total = sum(tuned.maindeck.values())
    side_total = sum(tuned.sideboard.values())
    click.echo(f"\n// Maindeck: {main_total}  Sideboard: {side_total}")

    # ── Swap log ──────────────────────────────────────────────────────────────
    if tuned.swaps:
        click.echo("\n// Swap log:")
        for i, (cut, added) in enumerate(tuned.swaps, 1):
            click.echo(f"//   {i}. CUT {cut}  →  ADD {added}")
    else:
        click.echo("\n// Swap log: (no swaps made)")

    # ── Per-matchup OUT/IN plans (from reworked sideboard recommender) ────────
    if tuned.matchup_plans:
        click.echo("\n// Per-matchup sideboard plans:")
        for opp, plan in sorted(tuned.matchup_plans.items()):
            if plan.degraded:
                click.echo(
                    f"//   vs {opp}: thin data — no per-matchup plan "
                    "(rely on 15 composition)"
                )
            else:
                out_str = ", ".join(
                    f"{c}x {card}" for card, c in sorted(plan.side_out.items())
                ) or "(none)"
                in_str = ", ".join(
                    f"{c}x {card}" for card, c in sorted(plan.side_in.items())
                ) or "(none)"
                click.echo(
                    f"//   vs {opp} [{plan.tier}, n>={plan.n_basis}]: "
                    f"OUT {out_str} | IN {in_str}"
                )
        # Presence-correlational disclaimer
        click.echo(
            "// [disclaimer] Per-card win-rates are PRESENCE-CORRELATIONAL "
            "(registered 75 for resolved matches), not causal. "
            "OUT/IN plans are a data-guided starting point, not a deterministic prescription."
        )

    # ── Legality ──────────────────────────────────────────────────────────────
    if tuned.legality_errors:
        for err in tuned.legality_errors:
            click.echo(f"// [LEGALITY] {err}", err=True)
    else:
        click.echo("// Legality: OK")

    # ── Optional export format ────────────────────────────────────────────────
    if export_fmt:
        from legacy_engine.generation.export import format_decklist
        click.echo("\n// --- Export ---")
        click.echo(format_decklist(tuned.maindeck, tuned.sideboard, fmt=export_fmt))


# ── export: decklist formatting ──
@main.group()
def export() -> None:
    """Decklist export — format any decklist for import into Moxfield, Archidekt, etc."""


@export.command("deck")
@click.option(
    "--deck",
    "deck_file",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to a plain-text decklist file.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["moxfield", "archidekt", "mtggoldfish", "text", "dec"], case_sensitive=False),
    default="moxfield",
    show_default=True,
    help="Export format.",
)
@click.option(
    "--out",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write output to a file instead of stdout.",
)
@_verbose
def export_deck(
    deck_file: str,
    fmt: str,
    out: str | None,
    verbose: bool,
) -> None:
    """Export a decklist file as standard import text.

    Reads a ``<qty> <Card Name>`` decklist and emits it in the target format,
    suitable for import into Moxfield, Archidekt, MTGGoldfish, or .dec tools.

    Example: legacy-engine export deck --deck list.txt --format archidekt
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import _parse_decklist
    from legacy_engine.generation.export import format_decklist

    deck_text = Path(deck_file).read_text()
    try:
        maindeck, sideboard = _parse_decklist(deck_text)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    output = format_decklist(maindeck, sideboard, fmt=fmt)

    if out:
        Path(out).write_text(output)
        click.echo(f"Written to {out}")
    else:
        click.echo(output)


if __name__ == "__main__":
    main()
