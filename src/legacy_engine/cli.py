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
@_verbose
def report_meta(verbose: bool) -> None:
    """Metagame share (raw / top-cut / win-rate-weighted; online vs paper)."""
    _setup_logging(verbose)
    _not_implemented("report meta")


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
@_verbose
def report_matchups(
    provenance: str,
    min_row_share: float,
    db: str | None,
    verbose: bool,
) -> None:
    """Archetype matchup matrix with confidence intervals."""
    _setup_logging(verbose)
    from legacy_engine.analytics.matchup import MatchupMatrix, build_matrix
    from legacy_engine.ingestion import store

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


@report.command("tiers")
@_verbose
def report_tiers(verbose: bool) -> None:
    """Tier list derived from the current metagame."""
    _setup_logging(verbose)
    _not_implemented("report tiers")


# ── advise: meta attack / advisory ──
@main.group()
def advise() -> None:
    """Meta attack / advisory — how to attack the field."""


@advise.command("positioning")
@_verbose
def advise_positioning(verbose: bool) -> None:
    """Score a deck's expected win rate against the weighted field."""
    _setup_logging(verbose)
    _not_implemented("advise positioning")


@advise.command("sideboard")
@_verbose
def advise_sideboard(verbose: bool) -> None:
    """Recommend a sideboard package for an expected field."""
    _setup_logging(verbose)
    _not_implemented("advise sideboard")


@advise.command("whattoplay")
@_verbose
def advise_whattoplay(verbose: bool) -> None:
    """Field read and deck recommendation."""
    _setup_logging(verbose)
    _not_implemented("advise whattoplay")


if __name__ == "__main__":
    main()
