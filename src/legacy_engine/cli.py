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
            click.echo(f"\n=== Deck Ranking (field_source={ranking.field_source}) ===")
            for d in ranking.decks:
                lo, hi = ranking.s_ci[d]
                click.echo(
                    f"  {d:<35}  S={ranking.s_mean[d]:.3f}  "
                    f"CI=[{lo:.3f},{hi:.3f}]  P(best)={ranking.p_best[d]:.3f}"
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


if __name__ == "__main__":
    main()
