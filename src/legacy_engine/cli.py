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


def _window_opts(f):
    """Stack the regime-window options (mirrors ``_verbose``).

    Adds ``--since``/``--until`` (explicit half-open window), ``--regime`` (named/current ban
    regime), and ``--all-time`` (explicit full corpus). Precedence + the thin-regime degrade live
    in ``advisory.window.resolve_advisory_window``.
    """
    for opt in (
        click.option("--all-time", is_flag=True, default=False,
                     help="Use the full corpus (explicit; overrides --regime/--since/--until)."),
        click.option("--regime", default=None,
                     help="Ban regime to window to: 'current', or a label substring (e.g. 'Undercity')."),
        click.option("--until", default=None, help="Window end (YYYY-MM-DD, exclusive)."),
        click.option("--since", default=None, help="Window start (YYYY-MM-DD, inclusive)."),
    ):
        f = opt(f)
    return f


def _echo_window(res: "WindowResolution") -> None:
    """Echo the resolved window (+ degrade banner) for auditability."""
    from legacy_engine.advisory.window import WindowResolution  # noqa: F401

    if res.mode == "adaptive":
        click.echo("// window: adaptive (per-cell ban-aware matrix; field = current regime)")
    elif res.since is None and res.until is None:
        click.echo("// window: full-corpus")
    else:
        click.echo(f"// window: {res.since or '—'} .. {res.until or '—'}  ({res.requested_label})")
    if res.banner:
        click.echo(f"// {res.banner}")


_STALE_DAYS = 30  # newest event older than this (vs wall clock) → staleness advisory


def _staleness_age_days(max_date: str | None, today) -> int | None:
    """Days between ``max_date`` and ``today``, or ``None`` if unknown/unparseable.

    Wall-clock-free (``today`` is injected) so it is unit-testable; the CLI passes
    ``date.today()`` at the edge. Returns ``None`` for an empty corpus OR a non-ISO date string
    (real corpora mix plain dates with odd values) so the staleness advisory degrades silently
    rather than crashing the report.
    """
    if max_date is None:
        return None
    from datetime import date as _date

    try:
        return (today - _date.fromisoformat(max_date)).days
    except ValueError:
        return None


def _echo_data_freshness(con, *, provenance: str | None = None) -> None:
    """Echo a data-currency header (deterministic) + a clock-based staleness advisory.

    The header (`// data as of <max date> (<N> decks)`) is a pure function of the corpus and
    never affects any computed figure. Only the optional staleness warning reads the wall clock,
    and it degrades silently if the date can't be parsed.
    """
    from datetime import date

    from legacy_engine.analytics.metashare import corpus_freshness

    max_date, deck_count = corpus_freshness(con, provenance=provenance)
    if max_date is None:
        click.echo("// data as of: (empty corpus)")
        return
    click.echo(f"// data as of {max_date} ({deck_count} decks)")
    age = _staleness_age_days(max_date, date.today())
    if age is not None and age > _STALE_DAYS:
        click.echo(f"// ⚠ newest event is {age} days old — data may be stale (run `refresh`)")


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
    "--venues",
    default=None,
    help="Comma-separated venue keys for side-by-side comparison (e.g. online,paper). "
         "Mutually exclusive with --provenance when --venues is set.",
)
@click.option(
    "--min-share",
    type=float,
    default=0.02,
    show_default=True,
    help="Minimum share (0..1) for an archetype to appear in headline rows; sub-floor → Other.",
)
@click.option(
    "--min-spread",
    type=float,
    default=0.0,
    show_default=True,
    help="Minimum divergence spread (0..1) for an archetype to appear in the Divergence block.",
)
@click.option(
    "--by-variant",
    is_flag=True,
    default=False,
    help="Split each archetype by variant tag (requires labeler to have been run with a variant registry).",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_window_opts
@_verbose
def report_meta(
    definition: str,
    provenance: str,
    venues: str | None,
    min_share: float,
    min_spread: float,
    by_variant: bool,
    db: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Metagame share (raw / top-cut / win-rate-weighted; online vs paper)."""
    _setup_logging(verbose)
    from legacy_engine.advisory.window import resolve_advisory_window
    from legacy_engine.analytics.metashare import MetaShareReport, compute_all, compute_metashare
    from legacy_engine.ingestion import store

    # --venues and --provenance (non-default) are mutually exclusive.
    if venues is not None and provenance != "all":
        raise click.ClickException(
            "--venues and --provenance are mutually exclusive: --venues compares several "
            "bases side by side; --provenance picks one basis. Use one or the other."
        )

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)

        # ── venues comparison mode ────────────────────────────────────────────
        if venues is not None:
            from legacy_engine.analytics.venue import resolve_venues, compute_venue_metashare, venue_divergence

            requested_keys = [k.strip() for k in venues.split(",") if k.strip()]
            venue_list = resolve_venues(con, requested_keys)

            definitions: list[str]
            if definition == "all":
                definitions = ["raw", "topcut", "wrw"]
            else:
                definitions = [definition]

            # Resolve a single window (venues mode uses one shared window).
            win = resolve_advisory_window(
                con, regime=regime, since=since, until=until, all_time=all_time,
                thin_floor=0, adaptive_default=False,
            )
            _echo_window(win)
            windowed = win.since is not None or win.until is not None

            for defn in definitions:
                if windowed and defn == "wrw":
                    click.echo("// skipping wrw under a window (win-rate weights are full-corpus only)")
                    continue
                if by_variant and defn == "wrw":
                    click.echo("// --by-variant is not supported for wrw (win-rate weights are archetype-level)")
                    continue

                # Per-venue tables
                venue_ms_list = compute_venue_metashare(
                    con, venue_list,
                    definition=defn,
                    min_share=min_share,
                    since=win.since,
                    until=win.until,
                )
                for vms in venue_ms_list:
                    click.echo(f"\n── Venue: {vms.venue.label} ──")
                    if vms.report is None:
                        click.echo(f"  (no data for venue '{vms.venue.key}')")
                    else:
                        _print_metashare_report(vms.report)

                # Divergence block (uses group_other=False reports from compute_venue_metashare)
                div = venue_divergence(venue_ms_list, min_spread=min_spread)
                _print_venue_divergence(div)

            return

        # ── legacy per-basis mode (--venues unset; byte-identical baseline) ──
        bases: list[str | None]
        if provenance == "all":
            bases = [None, "online", "paper"]
        else:
            bases = [provenance]

        definitions_leg: list[str]
        if definition == "all":
            definitions_leg = ["raw", "topcut", "wrw"]
        else:
            definitions_leg = [definition]

        for basis in bases:
            # Meta-share is deck-based (not matchup/rounds-based), so it does NOT degrade on
            # rounds-thinness — thin_floor=0. Per-row confidence tiers convey sample thinness.
            win = resolve_advisory_window(
                con, regime=regime, since=since, until=until, all_time=all_time,
                provenance=basis, thin_floor=0, adaptive_default=False,
            )
            _echo_window(win)
            windowed = win.since is not None or win.until is not None
            for defn in definitions_leg:
                if windowed and defn == "wrw":
                    click.echo("// skipping wrw under a window (win-rate weights are full-corpus only)")
                    continue
                # wrw does not support group_by_variant (weights are archetype-level).
                effective_by_variant = by_variant and defn != "wrw"
                if by_variant and defn == "wrw":
                    click.echo("// --by-variant is not supported for wrw (win-rate weights are archetype-level)")
                    continue
                report = compute_metashare(
                    con,
                    definition=defn,
                    provenance=basis,
                    min_share=min_share,
                    since=win.since,
                    until=win.until,
                    group_by_variant=effective_by_variant,
                )
                _print_metashare_report(report)
    finally:
        con.close()


_UNCLASSIFIED_MARKER = "‡"
_UNCLASSIFIED_FOOTNOTE = (
    f"{_UNCLASSIFIED_MARKER} unclassified — not positionable; excluded from advisory fields"
)


def _print_metashare_report(report: "MetaShareReport") -> None:
    """Render a meta-share report as a labeled text table."""
    from legacy_engine.analytics.metashare import MetaShareReport, _is_never_other  # noqa: F401

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

    saw_unclassified = False
    for entry in report.entries:
        fringe_marker = " *" if entry.fringe and entry.archetype != "Other" else "  "
        if _is_never_other(entry.archetype):
            unclassified_marker = f" {_UNCLASSIFIED_MARKER}"
            saw_unclassified = True
        else:
            unclassified_marker = ""
        click.echo(
            f"{entry.archetype:<30}  {entry.share:>6.1%}  {entry.n:>6}  "
            f"{entry.tier:<12}{fringe_marker}{unclassified_marker}"
        )

    if saw_unclassified:
        click.echo(_UNCLASSIFIED_FOOTNOTE)


def _print_venue_divergence(div: "VenueDivergence", *, top_n: int = 20) -> None:
    """Render a ``VenueDivergence`` as a labeled text divergence table."""
    from legacy_engine.analytics.venue import VenueDivergence  # noqa: F401

    venue_keys = [v.key for v in div.venues]
    venue_labels = [v.label for v in div.venues]

    click.echo(f"\n=== Venue Divergence [{div.definition.upper()}] ===")
    click.echo(f"Venues: {', '.join(venue_labels)}")

    if div.notes:
        for note in div.notes:
            click.echo(f"// {note}")

    if not div.rows:
        click.echo("(no archetypes with spread above threshold)")
        return

    # Column widths
    arch_w = max(max(len(r.archetype) for r in div.rows), 20)
    share_col_w = 12

    # Header
    header = f"  {'Archetype':<{arch_w}}"
    for label in venue_labels:
        short = label[:share_col_w - 1]
        header += f"  {short:>{share_col_w}}"
    header += f"  {'Spread':>8}"
    click.echo(header)
    click.echo("  " + "-" * (arch_w + (share_col_w + 2) * len(venue_keys) + 10))

    displayed = div.rows[:top_n]
    for row in displayed:
        line = f"  {row.archetype:<{arch_w}}"
        for vk in venue_keys:
            share = row.shares.get(vk, 0.0)
            tier = row.tiers.get(vk, "speculative")
            tier_marker = {"speculative": "?", "evolving": "~", "established": ""}.get(tier, "")
            cell = f"{share:>6.1%}{tier_marker}"
            line += f"  {cell:>{share_col_w}}"
        line += f"  {row.spread:>8.3f}"
        click.echo(line)

    if len(div.rows) > top_n:
        click.echo(f"  ... ({len(div.rows) - top_n} more rows below threshold)")

    click.echo("  Tier markers: ? = speculative (<30 decks), ~ = evolving (30–99)")


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
@_window_opts
@_verbose
def report_matchups(
    provenance: str,
    min_row_share: float,
    db: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Archetype matchup matrix with confidence intervals."""
    _setup_logging(verbose)
    from legacy_engine.advisory.window import build_advisory_inputs, resolve_advisory_window
    from legacy_engine.analytics.matchup import MatchupMatrix
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)
        bases: list[str | None]
        if provenance == "all":
            bases = [None, "online", "paper"]
        else:
            bases = [provenance]

        for basis in bases:
            win = resolve_advisory_window(
                con, regime=regime, since=since, until=until, all_time=all_time, provenance=basis,
            )
            _echo_window(win)
            inputs = build_advisory_inputs(con, win, provenance=basis, min_row_share=min_row_share)
            for line in inputs.audit:
                click.echo(line)
            matrix = inputs.matrix
            _print_matchup_matrix(matrix)
    finally:
        con.close()


def _print_matchup_matrix(matrix) -> None:  # type: legacy_engine.analytics.matchup.MatchupMatrix
    """Render a matchup matrix as a labeled text table."""
    from legacy_engine.analytics.metashare import _is_never_other

    basis_label = matrix.provenance if matrix.provenance else "all"
    click.echo(f"\n=== Matchup Matrix [{basis_label}] ===")
    click.echo(f"Total decisive matches: {matrix.total_matches}")
    click.echo(f"Caveat: {matrix.caveat}")

    if not matrix.archetypes:
        click.echo("(no archetypes meet the row-inclusion threshold)")
        return

    archetypes = matrix.archetypes
    has_unclassified = any(_is_never_other(a) for a in archetypes)
    col_width = max(len(a) for a in archetypes)
    col_width = max(col_width, 20)  # minimum column width for cell content
    row_label_width = max(len(a) for a in archetypes)
    if has_unclassified:
        row_label_width += 2  # room for the trailing " ‡" marker on unclassified rows

    # Header row
    header = " " * row_label_width + "  " + "  ".join(a.ljust(col_width) for a in archetypes)
    click.echo(header)
    click.echo("-" * len(header))

    for row_arch in archetypes:
        row_label = f"{row_arch} {_UNCLASSIFIED_MARKER}" if _is_never_other(row_arch) else row_arch
        row_parts = [row_label.ljust(row_label_width)]
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

    if has_unclassified:
        click.echo(_UNCLASSIFIED_FOOTNOTE)


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
@_verbose
def report_trends(
    definition: str,
    provenance: str,
    min_share: float,
    db: str | None,
    verbose: bool,
) -> None:
    """Meta-share evolution across ban-list regimes (version-stamped)."""
    _setup_logging(verbose)
    from legacy_engine.analytics.trends import compute_trends
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)
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
@_window_opts
@_verbose
def report_tiers(
    definition: str,
    provenance: str,
    min_share: float,
    db: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Tier list derived from the current metagame (S/A/B buckets by share)."""
    _setup_logging(verbose)
    from legacy_engine.advisory.window import resolve_advisory_window
    from legacy_engine.analytics.metashare import compute_metashare
    from legacy_engine.ingestion import store
    from legacy_engine.viz.models import _tier_model

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)
        # Tiers is an advisory "what to play now" surface, so it defaults to the CURRENT ban
        # regime (unlike descriptive `report meta`, which defaults to full corpus). This stops
        # tiers crowning a deck that is dead in the current regime. thin_floor=0: deck-based,
        # never degrades. --all-time / --regime / --since/--until override.
        if not (regime or since or until or all_time):
            regime = "current"
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time, thin_floor=0,
        )
        click.echo(f"// window: {win.requested_label}")

        # wrw is full-corpus only (win-rate weights aren't windowed). Since tiers now defaults
        # to the current regime, a bare `--definition wrw` would window → unsupported. Fail loud
        # with the escape hatch rather than crash (mirrors report meta's skip-under-window guard).
        windowed = win.since is not None or win.until is not None
        if windowed and definition == "wrw":
            raise click.ClickException(
                "windowed wrw is unsupported (win-rate weights are full-corpus only); "
                "use --all-time for a wrw tier list, or pick --definition raw/topcut."
            )

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
                since=win.since,
                until=win.until,
            )
            model = _tier_model(report)
            _print_tier_list(model)
    finally:
        con.close()


def _print_tier_list(model: "TierModel") -> None:
    """Render a tier model as a labeled text tier list."""
    from legacy_engine.viz.models import TierModel  # noqa: F401

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
@_window_opts
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
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Under-explored archetypes: high positioning S, low meta-share (deck-gen mode 3)."""
    _setup_logging(verbose)
    from legacy_engine.advisory.window import build_advisory_inputs, resolve_advisory_window
    from legacy_engine.advisory.gaps import compute_archetype_gaps
    from legacy_engine.ingestion import store

    basis = None if provenance == "all" else provenance

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time, provenance=basis,
        )
        _echo_window(win)
        inputs = build_advisory_inputs(con, win, provenance=basis)
        for line in inputs.audit:
            click.echo(line)
        # Adaptive mode → adaptive matrix + current-regime field window; uniform/full → matching window.
        report = compute_archetype_gaps(
            con,
            definition=definition,
            provenance=basis,
            share_weight=share_weight,
            min_coverage=min_coverage,
            risk_quantile=risk_quantile,
            min_share=min_share,
            seed=seed,
            since=inputs.field_since,
            until=inputs.field_until,
            matrix=inputs.matrix,
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
        _echo_data_freshness(con)
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


@report.command("subgroup")
@click.option("--archetype", required=True, help="Parent archetype to split (e.g. 'Dimir Tempo').")
@click.option(
    "--signature",
    required=True,
    help="Signature card whose presence defines the with-subgroup (e.g. \"Mishra's Bauble\").",
)
@click.option(
    "--board",
    type=click.Choice(["main", "side"], case_sensitive=False),
    default="main",
    show_default=True,
    help="Board to check for the signature card.",
)
@click.option("--since", default=None, help="Window start (YYYY-MM-DD, inclusive).")
@click.option("--until", default=None, help="Window end (YYYY-MM-DD, exclusive).")
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper"], case_sensitive=False),
    default=None,
    help="Filter to online or paper events (default: all).",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def report_subgroup(
    archetype: str,
    signature: str,
    board: str,
    since: str | None,
    until: str | None,
    provenance: str | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Subgroup-diff analysis — split an archetype on a signature card.

    Shows the avg-copies difference between decks with vs without the signature card,
    sorted by |delta|.  This is the validated discovery tool for identifying sub-archetype
    variants worth registering.

    Example: legacy-engine report subgroup --archetype "Dimir Tempo" --signature "Mishra's Bauble"
    """
    _setup_logging(verbose)
    from legacy_engine.analytics.subgroup import subgroup_compositions
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)
        split = subgroup_compositions(
            con,
            archetype,
            signature,
            board=board,
            since=since,
            until=until,
            provenance=provenance,
        )
    finally:
        con.close()

    _print_subgroup_report(split)


def _print_subgroup_report(split: "SubgroupSplit") -> None:
    """Render a SubgroupSplit as a labeled diff table."""
    from legacy_engine.analytics.subgroup import SubgroupSplit  # noqa: F401

    click.echo(
        f"\n=== Subgroup Diff: {split.archetype!r} split on {split.signature_card!r} "
        f"({split.board}board) ==="
    )
    click.echo(
        f"  with-subgroup:    n={split.n_with}  [{split.tier_with}]"
    )
    click.echo(
        f"  without-subgroup: n={split.n_without}  [{split.tier_without}]"
    )

    if split.thin:
        click.echo(
            "  // ⚠ thin subgroup(s) — one or both subgroups have n < 30 (speculative tier); "
            "deltas are present-and-honest, not hidden, but treat magnitudes as unreliable"
        )

    if not split.diffs:
        click.echo("  (no card data for this archetype/board/window)")
        return

    click.echo(
        f"\n  {'Card':<35}  {'with-avg':>9}  {'without-avg':>11}  {'delta':>8}"
    )
    click.echo("  " + "-" * 70)

    for d in split.diffs:
        sign = "+" if d.delta > 0 else ""
        click.echo(
            f"  {d.name:<35}  {d.avg_with:>9.3f}  {d.avg_without:>11.3f}  "
            f"{sign}{d.delta:>7.3f}"
        )

    click.echo(
        "\n  NOTE: presence-correlational only — not a causal attribution. "
        "Use this to identify candidate signature cards for the variant registry."
    )


@report.command("variants")
@click.option(
    "--archetype",
    default=None,
    help="Filter to this parent archetype (shows all parents when omitted).",
)
@click.option(
    "--registry",
    "registry_path",
    default=None,
    type=click.Path(dir_okay=False),
    help="Path to a variant registry JSON (defaults to data/variants/legacy.json).",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def report_variants(
    archetype: str | None,
    registry_path: str | None,
    db: str | None,
    verbose: bool,
) -> None:
    """List registered variants and their current meta share within each parent archetype.

    Shows, per variant: deck count carrying the tag and share of the parent archetype's decks
    in the latest ban-regime window.  Parents with zero matching decks are flagged (drift warning).

    Example: legacy-engine report variants
    Example: legacy-engine report variants --archetype "Dimir Tempo"
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.archetype.variants import load_variant_registry
    from legacy_engine.generation.consensus import _latest_regime_window
    from legacy_engine.ingestion import store

    # Resolve registry path.
    if registry_path is None:
        from legacy_engine.config import VARIANTS_REGISTRY_PATH
        default_path = VARIANTS_REGISTRY_PATH
        if not default_path.exists():
            raise click.ClickException(
                f"No variant registry found at {default_path}. "
                "Pass --registry to specify one."
            )
        reg_path = default_path
    else:
        reg_path = Path(registry_path)

    try:
        registry = load_variant_registry(reg_path)
    except Exception as exc:
        raise click.ClickException(f"Failed to load variant registry: {exc}") from exc

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)
        since, until = _latest_regime_window()

        # Collect all parents in scope.
        parents = sorted({r.parent for r in registry.variants})
        if archetype:
            if archetype not in parents:
                click.echo(
                    f"// Warning: archetype {archetype!r} has no registered variants."
                )
                return
            parents = [archetype]

        click.echo(
            f"\n=== Variant Registry [{registry.version}] "
            f"window: {since or 'open'} .. {until or 'current'} ==="
        )

        for parent in parents:
            rules = registry.for_parent(parent)
            default_name = registry.defaults.get(parent)

            # Total decks for this parent in the window.
            total_row = con.execute(
                """
                SELECT count(*) FROM decks d
                JOIN tournaments t ON t.id = d.tournament_id
                WHERE d.archetype = ?
                  AND (? IS NULL OR t.date >= ?)
                  AND (? IS NULL OR t.date < ?)
                """,
                [parent, since, since, until, until],
            ).fetchone()
            total_parent = int(total_row[0]) if total_row else 0

            click.echo(f"\n  {parent}  (total decks in window: {total_parent})")
            if total_parent == 0:
                click.echo("    // ⚠ no decks match this parent — registry may be drifted")

            for rule in rules:
                tagged_row = con.execute(
                    """
                    SELECT count(*) FROM decks d
                    JOIN tournaments t ON t.id = d.tournament_id
                    WHERE d.archetype = ?
                      AND d.variant = ?
                      AND (? IS NULL OR t.date >= ?)
                      AND (? IS NULL OR t.date < ?)
                    """,
                    [parent, rule.name, since, since, until, until],
                ).fetchone()
                tagged_n = int(tagged_row[0]) if tagged_row else 0
                share_str = (
                    f"{tagged_n / total_parent:.1%}" if total_parent > 0 else "n/a"
                )
                click.echo(f"    {rule.name:<30}  n={tagged_n:>5}  share={share_str}")

            # Show the default complement if declared.
            if default_name:
                default_row = con.execute(
                    """
                    SELECT count(*) FROM decks d
                    JOIN tournaments t ON t.id = d.tournament_id
                    WHERE d.archetype = ?
                      AND d.variant = ?
                      AND (? IS NULL OR t.date >= ?)
                      AND (? IS NULL OR t.date < ?)
                    """,
                    [parent, default_name, since, since, until, until],
                ).fetchone()
                default_n = int(default_row[0]) if default_row else 0
                share_str = (
                    f"{default_n / total_parent:.1%}" if total_parent > 0 else "n/a"
                )
                click.echo(
                    f"    {default_name:<30}  n={default_n:>5}  share={share_str}  (default complement)"
                )
    finally:
        con.close()


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
@_window_opts
@_verbose
def advise_positioning(
    deck: str,
    archetype: str | None,
    field_file: str | None,
    candidates_file: str | None,
    reserved: int,
    seed: int | None,
    db: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Score a deck's expected win rate against the weighted field."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.positioning import (
        _PBEST_SUPPRESS_COVERAGE,
        positioning_score,
        rank_decks,
    )
    from legacy_engine.advisory.report import _classify_deck, _load_field, _parse_decklist
    from legacy_engine.advisory.window import build_advisory_inputs, resolve_advisory_window
    from legacy_engine.ingestion import store

    deck_text = Path(deck).read_text()
    mainboard, sideboard_cards = _parse_decklist(deck_text)
    field_text = Path(field_file).read_text() if field_file else None

    con = store.connect(db) if db else store.connect()
    try:
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time,
        )
        _echo_window(win)
        inputs = build_advisory_inputs(con, win)
        for line in inputs.audit:
            click.echo(line)
        matrix = inputs.matrix
        field = _load_field(con, field_text=field_text, since=inputs.field_since, until=inputs.field_until)

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
                # Suppress P(best) when coverage ≈ 0 — the value is imputation noise that
                # otherwise reads as a spuriously confident ranking signal.
                if cov < _PBEST_SUPPRESS_COVERAGE:
                    pbest_str = "P(best)=n/a [cov≈0]"
                else:
                    pbest_str = f"P(best)={ranking.p_best[d]:.3f}"
                click.echo(
                    f"  {d:<35}  S={ranking.s_mean[d]:.3f}  "
                    f"CI=[{lo:.3f},{hi:.3f}]  {pbest_str}  "
                    f"{q_label}={ranking.s_quantile[d]:.3f}  cov={cov:.2f}{low_flag}"
                )
        else:
            pos = positioning_score(matrix, field, resolved_archetype, seed=seed)
            click.echo(f"\n=== Positioning: {pos.deck_archetype} (field_source={pos.field_source}) ===")
            if pos.s_computable:
                scope = "covered sub-field" if pos.restricted else "field"
                click.echo(f"  S (meta-positioning, vs {scope}): {pos.s_mean:.3f}")
                click.echo(f"  95% CI: [{pos.s_ci[0]:.3f}, {pos.s_ci[1]:.3f}]")
            else:
                click.echo("  S (meta-positioning): not computable — no covered (n≥30) matchups in the field")
            click.echo(f"  Field coverage: {pos.data_coverage:.0%} of field has matchup data")
            if pos.restricted:
                excl = ", ".join(sorted(pos.excluded_archetypes))
                click.echo(
                    f"  Excluded {pos.excluded_share:.0%} with no data "
                    f"({len(pos.excluded_archetypes)}): {excl}"
                )
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
    "--archetype",
    default=None,
    help="Override archetype classification (used for adaptive per-opponent windows).",
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
@_window_opts
@_verbose
def advise_sideboard(
    deck: str,
    archetype: str | None,
    field_file: str | None,
    reserved: int,
    solver: str,
    db: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Recommend a sideboard package for an expected field."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import _classify_deck, _load_field, _parse_decklist
    from legacy_engine.advisory.sideboard import recommend_sideboard
    from legacy_engine.advisory.window import resolve_advisory_window
    from legacy_engine.ingestion import store

    deck_text = Path(deck).read_text()
    mainboard, _sideboard_cards = _parse_decklist(deck_text)
    field_text = Path(field_file).read_text() if field_file else None

    con = store.connect(db) if db else store.connect()
    try:
        # Resolve window. Sideboard plans default to adaptive (per-opponent ban-aware);
        # uniform/full modes disable adaptive and use the resolved since/until instead.
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time,
        )
        _echo_window(win)

        # Determine whether to use adaptive per-opponent windows.
        use_adaptive = win.mode == "adaptive"
        plan_since = win.since
        plan_until = win.until

        field = _load_field(con, field_text=field_text)

        resolved_archetype = archetype
        if resolved_archetype is None:
            result = _classify_deck(con, mainboard, _sideboard_cards)
            resolved_archetype = result.archetype
            click.echo(f"// Classified archetype: {resolved_archetype} (kind={result.kind})")

        pkg = recommend_sideboard(
            con, field, mainboard,
            reserved=reserved,
            solver=solver,
            archetype=resolved_archetype,
            since=plan_since,
            until=plan_until,
            adaptive=use_adaptive,
        )

        # Echo adaptive audit line when adaptive mode resolved actual windows.
        if pkg.plan_window_label:
            click.echo(f"// plan window: {pkg.plan_window_label}")
        if pkg.plan_windows:
            affected = sorted(
                (opp, w[0]) for opp, w in pkg.plan_windows.items()
                if w[0] is not None and opp != resolved_archetype
            )
            if affected:
                parts = "; ".join(f"{opp} since {s}" for opp, s in affected)
                click.echo(f"// adaptive plan windows — {parts}; all others full-corpus")
            else:
                click.echo("// adaptive plan windows — no archetype ban-affected; all opponents full-corpus")

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
                    click.echo(f"    vs {opp}: {plan.note}")
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
@click.option("--seed", type=int, default=None, help="RNG seed for deterministic positioning S.")
@_window_opts
@_verbose
def advise_whattoplay(
    deck: str,
    archetype: str | None,
    field_file: str | None,
    db: str | None,
    seed: int | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Field read and deck recommendation."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import _classify_deck, _load_field, _parse_decklist, _render_whattoplay
    from legacy_engine.advisory.whattoplay import proactivity_score, vulnerability_tags_for_deck
    from legacy_engine.advisory.window import build_advisory_inputs, resolve_advisory_window
    from legacy_engine.ingestion import store

    deck_text = Path(deck).read_text()
    mainboard, sideboard_cards = _parse_decklist(deck_text)
    field_text = Path(field_file).read_text() if field_file else None

    con = store.connect(db) if db else store.connect()
    try:
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time,
        )
        _echo_window(win)
        inputs = build_advisory_inputs(con, win)
        for line in inputs.audit:
            click.echo(line)
        field = _load_field(con, field_text=field_text, since=inputs.field_since, until=inputs.field_until)

        resolved_archetype = archetype
        if resolved_archetype is None:
            result = _classify_deck(con, mainboard, sideboard_cards)
            resolved_archetype = result.archetype
            click.echo(f"Classified archetype: {resolved_archetype} (kind={result.kind})")

        from legacy_engine.advisory.report import FieldReadReport
        from legacy_engine.advisory.whattoplay import best_deck_vs_best_call, field_vulnerability_tags, hate_equity

        matrix = inputs.matrix
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

        bdc = best_deck_vs_best_call(matrix, field, resolved_archetype)

        # Coverage-aware positioning S — the headline number; reuses the honest
        # (auto-restricted / not-computable) positioning_score from the foundation feature.
        from legacy_engine.advisory.positioning import positioning_score
        positioning = positioning_score(matrix, field, resolved_archetype, seed=seed)

        report = FieldReadReport(
            deck_archetype=resolved_archetype,
            field_source=field.field_source,
            field_shares=dict(field.shares),
            field_vuln_profile=field_vuln_profile,
            positioning=positioning,
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
    "--venues",
    default=None,
    help="Comma-separated venue keys for per-venue Field Reads (e.g. online,paper). "
         "Mutually exclusive with --field (a custom field has no venue axis).",
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
@_window_opts
@_verbose
def advise_report(
    deck: str,
    archetype: str | None,
    field_file: str | None,
    venues: str | None,
    reserved: int,
    seed: int | None,
    db: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
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
        render_cross_venue_positioning,
    )
    from legacy_engine.advisory.window import build_advisory_inputs, resolve_advisory_window
    from legacy_engine.ingestion import store

    # --field and --venues are mutually exclusive: a custom field has no venue axis.
    if field_file is not None and venues is not None:
        raise click.ClickException(
            "--field and --venues are mutually exclusive: a custom field file has no "
            "venue axis. Use --venues for per-venue corpus fields, or --field for a "
            "single custom field."
        )

    deck_text = Path(deck).read_text()
    mainboard, sideboard_cards = _parse_decklist(deck_text)
    field_text = Path(field_file).read_text() if field_file else None

    con = store.connect(db) if db else store.connect()
    try:
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time,
        )
        _echo_window(win)
        inputs = build_advisory_inputs(con, win)
        for line in inputs.audit:
            click.echo(line)

        # ── venues comparison mode ────────────────────────────────────────────
        if venues is not None:
            from legacy_engine.analytics.venue import resolve_venues

            requested_keys = [k.strip() for k in venues.split(",") if k.strip()]
            venue_list = resolve_venues(con, requested_keys)

            per_venue_reports: dict[str, "FieldReadReport"] = {}
            for venue in venue_list:
                click.echo(f"\n{'─' * 60}")
                click.echo(f"── Venue: {venue.label} ──")
                click.echo(f"{'─' * 60}")
                v_field = _load_field(
                    con,
                    field_text=None,
                    provenance=venue.provenance,
                    since=inputs.field_since,
                    until=inputs.field_until,
                )
                v_report = build_field_read_report(
                    con,
                    mainboard,
                    sideboard_cards,
                    v_field,
                    archetype=archetype,
                    reserved=reserved,
                    seed=seed,
                    matrix=inputs.matrix,
                )
                click.echo(render_field_read(v_report, con=con))
                per_venue_reports[venue.key] = v_report

            # Cross-venue positioning footer
            if per_venue_reports:
                click.echo(f"\n{'─' * 60}")
                click.echo(render_cross_venue_positioning(per_venue_reports))
            return

        # ── legacy single-field mode (--venues unset; byte-identical baseline) ──
        field = _load_field(con, field_text=field_text, since=inputs.field_since, until=inputs.field_until)
        report = build_field_read_report(
            con,
            mainboard,
            sideboard_cards,
            field,
            archetype=archetype,
            reserved=reserved,
            seed=seed,
            matrix=inputs.matrix,
        )
        click.echo(render_field_read(report, con=con))
    finally:
        con.close()


# ── identify: player identity, strength, and history ──
@main.group()
def identify() -> None:
    """Player identity, strength scoring, and archetype-history tracking."""


@identify.command("suggest")
@click.option(
    "--min-overlap",
    type=int,
    default=4,
    show_default=True,
    help="Minimum normalized-stem prefix length for two handles to be considered a candidate cluster.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def identify_suggest(
    min_overlap: int,
    db: str | None,
    verbose: bool,
) -> None:
    """Propose candidate alias clusters for human curation.

    Emits heuristic-suggested handle clusters (normalized-stem overlap + never co-occurring
    in the same event on the same day) to stdout for the curator to review and paste into
    data/players/aliases.json.  This command writes nothing; all merges are manual.

    Example: legacy-engine identify suggest
    """
    _setup_logging(verbose)
    from legacy_engine.analytics.players.identity import suggest_aliases
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        suggestions = suggest_aliases(con, min_overlap=min_overlap)
    finally:
        con.close()

    if not suggestions:
        click.echo("(no alias clusters found)")
        return

    click.echo(f"// {len(suggestions)} candidate alias cluster(s) — review before adding to aliases.json:")
    click.echo("")
    for s in suggestions:
        click.echo(f"  Cluster ({s.reason}):")
        for raw, norm in zip(s.handles, s.handles_norm):
            click.echo(f"    {raw!r}  (normalized: {norm!r})")
        click.echo("")


@identify.command("strong")
@click.option(
    "--since",
    default=None,
    help="Window start (YYYY-MM-DD, inclusive). Defaults to latest ban-regime.",
)
@click.option(
    "--until",
    default=None,
    help="Window end (YYYY-MM-DD, exclusive). Defaults to latest ban-regime.",
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper"], case_sensitive=False),
    default=None,
    help="Filter to online or paper events (default: all).",
)
@click.option(
    "--min-events",
    type=int,
    default=3,
    show_default=True,
    help="Minimum distinct events to qualify as strong.",
)
@click.option(
    "--min-tier",
    "min_tier",
    type=click.Choice(["speculative", "evolving", "established"], case_sensitive=False),
    default="evolving",
    show_default=True,
    help="Minimum confidence tier to qualify as strong.",
)
@click.option(
    "--min-win-rate",
    type=float,
    default=0.55,
    show_default=True,
    help="Minimum shrunk match-win-rate to qualify as strong.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def identify_strong(
    since: str | None,
    until: str | None,
    provenance: str | None,
    min_events: int,
    min_tier: str,
    min_win_rate: float,
    db: str | None,
    verbose: bool,
) -> None:
    """List players who clear the strength gate in the requested window.

    Defaults to the latest ban-regime window (same as generate consensus).
    Shows player_id, display name, events, match record, shrunk win-rate, and tier.

    Example: legacy-engine identify strong
    Example: legacy-engine identify strong --min-events 5 --min-win-rate 0.60
    """
    _setup_logging(verbose)
    from legacy_engine.analytics.players.identity import load_alias_map
    from legacy_engine.analytics.players.strength import compute_player_records, is_strong
    from legacy_engine.generation.consensus import _latest_regime_window
    from legacy_engine.ingestion import store

    eff_since = since
    eff_until = until
    if eff_since is None and eff_until is None:
        eff_since, eff_until = _latest_regime_window()

    alias_map = load_alias_map()
    con = store.connect(db) if db else store.connect()
    try:
        records = compute_player_records(
            con,
            alias_map=alias_map,
            since=eff_since,
            until=eff_until,
            provenance=provenance,
        )
    finally:
        con.close()

    strong_records = [
        rec for rec in records.values()
        if is_strong(rec, min_events=min_events, min_tier=min_tier, min_win_rate=min_win_rate)
    ]
    strong_records.sort(key=lambda r: -r.win_rate_shrunk)

    click.echo(
        f"\n=== Strong Players "
        f"[window: {eff_since or 'open'} .. {eff_until or 'current'}] ==="
    )
    click.echo(
        f"Gate: ≥{min_events} events, ≥{min_tier} tier, ≥{min_win_rate:.0%} shrunk WR"
    )
    click.echo(f"{'Player':<30}  {'Events':>6}  {'W-L-D':>10}  {'WR_shrunk':>9}  {'Tier':<12}")
    click.echo("-" * 75)

    if not strong_records:
        click.echo("(no players cleared the gate in this window)")
        return

    for rec in strong_records:
        wld = f"{rec.match_wins}-{rec.match_losses}-{rec.match_draws}"
        click.echo(
            f"{rec.display:<30}  {rec.events:>6}  {wld:>10}  "
            f"{rec.win_rate_shrunk:>9.3f}  {rec.tier:<12}"
        )


@identify.command("track")
@click.argument("player")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def identify_track(
    player: str,
    db: str | None,
    verbose: bool,
) -> None:
    """Show per-regime archetype history for PLAYER.

    PLAYER is a handle or canonical player_id (resolved through aliases.json).
    Shows which archetypes the player registered in each ban-list regime and how
    many decks per archetype.

    Example: legacy-engine identify track "bosh95"
    Example: legacy-engine identify track "Andrea Mengucci"
    """
    _setup_logging(verbose)
    from legacy_engine.analytics.players.history import player_archetype_history
    from legacy_engine.analytics.players.identity import load_alias_map, resolve_player
    from legacy_engine.ingestion import store

    alias_map = load_alias_map()
    player_id = resolve_player(player, alias_map)

    con = store.connect(db) if db else store.connect()
    try:
        history = player_archetype_history(con, player_id, alias_map=alias_map)
    finally:
        con.close()

    if not history:
        click.echo(f"No archetype history found for player {player!r} (id={player_id!r}).")
        return

    display_name = player_id if player_id == player else f"{player} → {player_id}"
    click.echo(f"\n=== Archetype History: {display_name} ===")
    click.echo(f"{'Regime':<25}  {'Archetype':<35}  {'Decks':>5}")
    click.echo("-" * 70)

    current_regime = None
    for row in history:
        if row.regime_label != current_regime:
            if current_regime is not None:
                click.echo("")
            current_regime = row.regime_label
        arch_label = row.archetype if row.archetype is not None else "(unlabeled)"
        click.echo(f"{row.regime_label:<25}  {arch_label:<35}  {row.deck_count:>5}")


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
    "--variant",
    default=None,
    help="Scope the pool to decks with this variant tag (e.g. 'Bauble'). Requires labeler with registry.",
)
@click.option(
    "--players",
    default=None,
    help="Comma-separated player handles/ids to restrict the deck pool to (explicit player filter).",
)
@click.option(
    "--strong",
    is_flag=True,
    default=False,
    help="Restrict the pool to strong players for this archetype+window (computed via strong_player_set).",
)
@click.option(
    "--min-events",
    type=int,
    default=3,
    show_default=True,
    help="Minimum distinct events for a player to qualify as strong (--strong only).",
)
@click.option(
    "--min-tier",
    "min_strength_tier",
    type=click.Choice(["speculative", "evolving", "established"], case_sensitive=False),
    default="evolving",
    show_default=True,
    help="Minimum confidence tier for a player to qualify as strong (--strong only).",
)
@click.option(
    "--min-win-rate",
    type=float,
    default=0.55,
    show_default=True,
    help="Minimum shrunk win-rate for a player to qualify as strong (--strong only).",
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
    variant: str | None,
    players: str | None,
    strong: bool,
    min_events: int,
    min_strength_tier: str,
    min_win_rate: float,
    export_fmt: str | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Generate a consensus baseline decklist for an archetype.

    Aggregates modal card choices across all archetype decks in the corpus window
    and reconciles to a legal, exactly-60 maindeck + ≤15 sideboard.

    Use --variant to scope the pool to a specific sub-archetype variant (e.g. "Bauble").
    Requires that the labeler has been run with a variant registry.

    Use --players "h1,h2" to restrict the pool to specific players.
    Use --strong to restrict to players who clear the strength gate for this archetype+window.
    When both are supplied, --players wins (explicit beats derived).

    Example: legacy-engine generate consensus --archetype "Izzet Delver"
    Example: legacy-engine generate consensus --archetype "Dimir Tempo" --variant "Bauble"
    Example: legacy-engine generate consensus --archetype "Dimir Tempo" --strong
    Example: legacy-engine generate consensus --archetype "Dimir Tempo" --players "bosh95,mengucci"
    """
    _setup_logging(verbose)

    from legacy_engine.analytics.players.identity import load_alias_map
    from legacy_engine.generation.consensus import build_consensus
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        # Resolve the player filter.
        alias_map = load_alias_map()
        player_set: set[str] | None = None

        if players is not None and strong:
            log.info(
                "generate consensus: both --players and --strong supplied; "
                "--players wins (explicit beats derived)"
            )

        if players is not None:
            # Explicit --players wins.
            player_set = {h.strip() for h in players.split(",") if h.strip()}
        elif strong:
            from legacy_engine.analytics.players.strength import (
                compute_player_records,
                strong_player_set,
            )
            from legacy_engine.generation.consensus import _latest_regime_window

            # Use the same window as the consensus query.
            eff_since = since
            eff_until = until
            if eff_since is None and eff_until is None:
                eff_since, eff_until = _latest_regime_window()

            records = compute_player_records(
                con,
                alias_map=alias_map,
                since=eff_since,
                until=eff_until,
            )
            player_set = strong_player_set(
                records,
                min_events=min_events,
                min_tier=min_strength_tier,
                min_win_rate=min_win_rate,
            )
            click.echo(
                f"// --strong: {len(player_set)} strong player(s) found for window "
                f"[{eff_since or 'open'}, {eff_until or 'current'})"
            )
            if not player_set:
                raise click.ClickException(
                    "No players cleared the strength gate for this archetype+window. "
                    "Try relaxing --min-events, --min-tier, or --min-win-rate, "
                    "or use --all-time for a wider window."
                )

        deck = build_consensus(
            con,
            archetype,
            since=since,
            until=until,
            provenance=provenance,
            variant=variant,
            players=player_set,
            alias_map=alias_map if player_set is not None else None,
        )
    finally:
        con.close()

    if deck.sample_n == 0:
        raise click.ClickException(
            f"No decks found for archetype {archetype!r} in the window "
            f"[{deck.window[0] or 'open'}, {deck.window[1] or 'open'})."
        )

    # Print the decklist in the default readable format.
    from legacy_engine.confidence import tier_for_sample
    deck_label = f"{deck.archetype} / {variant}" if variant else deck.archetype
    if player_set is not None:
        deck_label += f" [player-filtered: {len(player_set)} player(s)]"
    click.echo(f"// Consensus deck: {deck_label}")
    window_since = deck.window[0] or "open"
    window_until = deck.window[1] or "current"
    sample_tier = tier_for_sample(deck.sample_n)
    click.echo(
        f"// window: regime current [{window_since}..{window_until}]  "
        f"sample_n={deck.sample_n} [{sample_tier}]  "
        "(uniform current-regime window — deck composition surface)"
    )
    if sample_tier == "speculative":
        click.echo(
            f"// ⚠ thin sample (n={deck.sample_n}) — modal card choices and inclusion %s are "
            "unreliable; treat this list as speculative"
        )
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

    # Legality errors — distinguish the thin-pool banner from real legality failures.
    thin_banners = [e for e in deck.legality_errors if e.startswith("⚠ THIN")]
    real_errors = [e for e in deck.legality_errors if not e.startswith("⚠ THIN")]
    for banner in thin_banners:
        click.echo(f"// {banner}")
    if real_errors:
        for err in real_errors:
            click.echo(f"// [LEGALITY] {err}", err=True)
    elif not thin_banners:
        click.echo("// Legality: OK")
    else:
        click.echo("// Legality: OK (thin pool — see banner above)")

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
    "--players",
    default=None,
    help="Comma-separated player handles/ids to restrict the consensus seed pool to.",
)
@click.option(
    "--strong",
    is_flag=True,
    default=False,
    help="Restrict the consensus seed pool to strong players for this archetype+window.",
)
@click.option(
    "--min-events",
    type=int,
    default=3,
    show_default=True,
    help="Minimum distinct events for a player to qualify as strong (--strong only).",
)
@click.option(
    "--min-tier",
    "min_strength_tier",
    type=click.Choice(["speculative", "evolving", "established"], case_sensitive=False),
    default="evolving",
    show_default=True,
    help="Minimum confidence tier for a player to qualify as strong (--strong only).",
)
@click.option(
    "--min-win-rate",
    type=float,
    default=0.55,
    show_default=True,
    help="Minimum shrunk win-rate for a player to qualify as strong (--strong only).",
)
@click.option(
    "--export",
    "export_fmt",
    type=click.Choice(["moxfield", "archidekt", "mtggoldfish", "text", "dec"], case_sensitive=False),
    default=None,
    help="Also emit the tuned 60+15 in the specified import format.",
)
@click.option(
    "--discover",
    "discover",
    is_flag=True,
    default=False,
    help="Also suggest adjacent swap-in candidates (deck-gen mode 3; exploratory, labeled, never auto-swapped).",
)
@click.option(
    "--discover-cap",
    type=int,
    default=5,
    show_default=True,
    help="Max exploratory discovery suggestions to show (--discover only).",
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
    players: str | None,
    strong: bool,
    min_events: int,
    min_strength_tier: str,
    min_win_rate: float,
    export_fmt: str | None,
    discover: bool,
    discover_cap: int,
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
    from legacy_engine.analytics.players.identity import load_alias_map
    from legacy_engine.generation.tuning import tune_deck
    from legacy_engine.ingestion import store

    deck_text = Path(deck).read_text()
    maindeck, starting_side = _parse_decklist(deck_text)
    field_text = Path(field_file).read_text() if field_file else None

    con = store.connect(db) if db else store.connect()
    discovery = None
    try:
        field = _load_field(con, field_text=field_text)

        resolved_archetype = archetype
        if resolved_archetype is None:
            result = _classify_deck(con, maindeck, starting_side)
            resolved_archetype = result.archetype
            click.echo(f"Classified archetype: {resolved_archetype} (kind={result.kind})")

        # Resolve the player filter.
        alias_map_tune = load_alias_map()
        player_set_tune: set[str] | None = None

        if players is not None and strong:
            log.info(
                "generate tune: both --players and --strong supplied; "
                "--players wins (explicit beats derived)"
            )

        if players is not None:
            player_set_tune = {h.strip() for h in players.split(",") if h.strip()}
        elif strong:
            from legacy_engine.analytics.players.strength import (
                compute_player_records,
                strong_player_set,
            )
            from legacy_engine.generation.consensus import _latest_regime_window

            eff_since_s = since
            eff_until_s = until
            if eff_since_s is None and eff_until_s is None:
                eff_since_s, eff_until_s = _latest_regime_window()

            records = compute_player_records(
                con,
                alias_map=alias_map_tune,
                since=eff_since_s,
                until=eff_until_s,
            )
            player_set_tune = strong_player_set(
                records,
                min_events=min_events,
                min_tier=min_strength_tier,
                min_win_rate=min_win_rate,
            )
            click.echo(
                f"// --strong: {len(player_set_tune)} strong player(s) found for window "
                f"[{eff_since_s or 'open'}, {eff_until_s or 'current'})"
            )
            if not player_set_tune:
                raise click.ClickException(
                    "No players cleared the strength gate for this archetype+window. "
                    "Try relaxing --min-events, --min-tier, or --min-win-rate."
                )

        # When --discover, compute the heavy per-card win-rate aggregate ONCE and reuse it
        # for both the tuner (injected) and discovery, avoiding a second full-corpus scan.
        shared_rates = None
        if discover:
            from legacy_engine.analytics.match_results import compute_card_winrates
            eff_since, eff_until = since, until
            if eff_since is None and eff_until is None:
                from legacy_engine.generation.consensus import _latest_regime_window
                eff_since, eff_until = _latest_regime_window()
            shared_rates = compute_card_winrates(con, since=eff_since, until=eff_until)

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
            card_winrates=shared_rates,
            players=player_set_tune,
            alias_map=alias_map_tune if player_set_tune is not None else None,
        )

        if discover:
            from legacy_engine.generation.discovery import discover_candidates
            discovery = discover_candidates(
                con,
                resolved_archetype,
                maindeck,
                starting_side,
                field=field,
                rates=shared_rates,
                cap=discover_cap,
                lock_threshold=lock_threshold,
                since=since,
                until=until,
            )
    finally:
        con.close()

    # ── Header ───────────────────────────────────────────────────────────────
    click.echo(f"\n// Tuned deck: {tuned.archetype}")
    # Fix A: echo window divergence — list window is current-regime, matchup math is adaptive.
    # This is an intentional, defensible divergence; state it loudly, not silently.
    click.echo(
        f"// NOTE: tuning uses two windows: consensus/card-frequency list = "
        f"current-regime (uniform); matchup math = adaptive (per-opponent ban-aware). "
        "This divergence is intentional — the list reflects what is played NOW; "
        "matchup depth borrows prior-regime data. Both are labeled here."
    )

    # Primary objective: per-card field-weighted value (the real swap driver).
    click.echo(
        f"// Value (per-card field-weighted lift): "
        f"{tuned.value_before:.4f} → {tuned.value_after:.4f}"
        + (" [no-signal: no swaps made]" if tuned.objective == "no-signal-skip" else "")
    )
    click.echo(f"// Δvalue = {tuned.value_after - tuned.value_before:+.4f}")

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
        click.echo(
            "// (per-card lift is presence-correlational, not causal; magnitudes are small — "
            "treat swap ordering as indicative, not precise)"
        )
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

    # ── Discovery (exploratory; mode 3) — distinct section, never auto-swapped ──
    if discovery is not None:
        _print_discovery(discovery)

    # ── Optional export format ────────────────────────────────────────────────
    if export_fmt:
        from legacy_engine.generation.export import format_decklist
        click.echo("\n// --- Export ---")
        click.echo(format_decklist(tuned.maindeck, tuned.sideboard, fmt=export_fmt))


@generate.command("doctor")
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
    "--board",
    type=click.Choice(["main", "side", "both"], case_sensitive=False),
    default="main",
    show_default=True,
    help="Which board(s) to compare against the field.",
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
    "--all-time",
    is_flag=True,
    default=False,
    help="Use the full corpus (disables ban-regime windowing).",
)
@click.option(
    "--min-tier",
    type=click.Choice(["speculative", "evolving", "established"], case_sensitive=False),
    default="speculative",
    show_default=True,
    help="Suppress the whole report below this confidence tier; prints a note when suppressed.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def generate_doctor(
    deck: str,
    archetype: str | None,
    board: str,
    since: str | None,
    until: str | None,
    all_time: bool,
    min_tier: str,
    db: str | None,
    verbose: bool,
) -> None:
    """Doctor a decklist against the field's per-card copy-count distributions.

    For each card in the user's list, shows how the field distributes its copy
    counts and flags where the user's count is an outlier (off the field consensus).
    Defaults to the latest ban-regime window (same as ``generate consensus``).

    Example: legacy-engine generate doctor --deck mylist.txt --archetype "Izzet Delver"
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import _classify_deck, _parse_decklist
    from legacy_engine.generation.card_distribution import build_deck_doctor_report
    from legacy_engine.ingestion import store

    deck_text = Path(deck).read_text()
    main_counts, side_counts = _parse_decklist(deck_text)

    # Resolve the effective window in the CLI layer so the orchestrator always receives
    # explicit dates (never the (None, None) that would trigger _latest_regime_window() again).
    #   --all-time     → full corpus: (None, None) — but we pass all_time=True to the builder
    #   --since/--until → explicit window (passed through as-is)
    #   neither flag   → latest ban-regime: resolve here, same as generate consensus
    if all_time:
        effective_since: str | None = None
        effective_until: str | None = None
    elif since is not None or until is not None:
        effective_since = since
        effective_until = until
    else:
        # Default: latest ban-regime — same SSOT as generate consensus.
        from legacy_engine.generation.consensus import _latest_regime_window
        effective_since, effective_until = _latest_regime_window()

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)

        resolved_archetype = archetype
        if resolved_archetype is None:
            result = _classify_deck(con, main_counts, side_counts)
            resolved_archetype = result.archetype
            click.echo(f"// Classified archetype: {resolved_archetype} (kind={result.kind})")

        boards_to_run: list[str]
        if board == "both":
            boards_to_run = ["main", "side"]
        else:
            boards_to_run = [board]

        for b in boards_to_run:
            report = build_deck_doctor_report(
                con,
                main_counts,
                side_counts,
                resolved_archetype,
                since=effective_since,
                until=effective_until,
                board=b,
                apply_default_window=not all_time,
            )
            _render_deck_doctor(report, min_tier=min_tier)
    finally:
        con.close()


def _render_deck_doctor(report: "DeckDoctorReport", *, min_tier: str = "speculative") -> None:
    """Render a DeckDoctorReport as a human-readable text block.

    Format mirrors the validated hand output in the feature spec:
      - Header with archetype, window, sample_n, and tier.
      - OUTLIERS section.
      - ON CONSENSUS section.
      - NOT RUN BY THE FIELD section.
      - Footer disclaimer note.

    When ``tier_for_sample(report.decks_total)`` is below ``min_tier``, the whole
    report is suppressed and a note is printed (matches ``report cards`` honesty contract).
    """
    from legacy_engine.confidence import tier_for_sample
    from legacy_engine.generation.card_distribution import DeckDoctorReport  # noqa: F401

    _tier_order = {"speculative": 0, "evolving": 1, "established": 2}
    sample_tier = tier_for_sample(report.decks_total)

    # Tier suppression: suppress the whole report when below the min_tier gate.
    min_tier_rank = _tier_order[min_tier.lower()]
    actual_tier_rank = _tier_order[sample_tier]
    if actual_tier_rank < min_tier_rank:
        click.echo(
            f"\n// Deck Doctor [{report.archetype}] ({report.board}): SUPPRESSED — "
            f"sample_n={report.decks_total} [{sample_tier}] is below --min-tier {min_tier}. "
            "Data present; not fabricated."
        )
        return

    # Header.
    window_since = report.window[0] or "open"
    window_until = report.window[1] or "current"
    header = (
        f"=== Deck Doctor: {report.archetype}  "
        f"[regime {window_since} → {window_until}]  "
        f"sample_n={report.decks_total} [{sample_tier}] ==="
    )
    click.echo(f"\n{header}")

    if report.decks_total == 0:
        click.echo(f"// No decks found for archetype {report.archetype!r} in this window.")
        return

    if sample_tier == "speculative":
        click.echo(
            f"// ⚠ thin sample (n={report.decks_total}) — distributions are unreliable; "
            "treat outlier flags as speculative"
        )

    # Split deltas into outliers and on-consensus.
    outliers = [d for d in report.deltas if d.is_outlier]
    on_consensus = [d for d in report.deltas if not d.is_outlier]

    def _dist_str(d) -> str:  # d: CardCountDelta
        """Format the top-3 buckets by share descending, e.g. '(3: 68%, 4: 23%)'."""
        top = sorted(d.field_dist.items(), key=lambda kv: -kv[1])[:3]
        parts = [f"{cnt}: {share:.0%}" for cnt, share in top]
        return "(" + ", ".join(parts) + ")"

    def _annotation(d) -> str:  # d: CardCountDelta
        """Short annotation: explains why something is flagged or a real camp."""
        if d.is_outlier:
            return f"[only {d.user_share:.0%} run {d.user_count} — outlier]"
        elif d.delta != 0 and d.user_share >= 0.15:
            return f"[{d.user_share:.0%} run {d.user_count} — a real camp]"
        return ""

    name_w = max(
        (len(d.name) for d in report.deltas),
        default=20,
    )
    name_w = max(name_w, 20)

    def _row(d) -> str:  # d: CardCountDelta
        delta_str = f"Δ{d.delta:+d}" if d.delta != 0 else "Δ 0"
        annotation = _annotation(d)
        return (
            f"  {d.name:<{name_w}}  you run {d.user_count:<3}  "
            f"field mode {d.field_modal:<3}  {_dist_str(d):<30}  "
            f"{delta_str:<5}  {annotation}"
        ).rstrip()

    if outliers:
        click.echo("\nOUTLIERS (your count is off the field consensus):")
        for d in outliers:
            click.echo(_row(d))
    else:
        click.echo("\nOUTLIERS: (none — your counts align with the field)")

    if on_consensus:
        click.echo("\nON CONSENSUS:")
        for d in on_consensus:
            click.echo(_row(d))

    if report.not_in_field:
        click.echo(
            f"\nNOT RUN BY THE FIELD (this archetype, {report.board}): "
            + ", ".join(report.not_in_field)
        )

    click.echo(
        f"\n// distribution compared against the whole {report.archetype!r} pool "
        "(no sub-archetype/variant split yet)"
    )


def _print_discovery(result: "DiscoveryResult") -> None:
    """Render the exploratory discovery section — distinct from the proven swap log."""
    from legacy_engine.generation.discovery import DiscoveryResult  # noqa: F401

    gate_label = "/".join(result.gate)
    click.echo(f"\n// === Discovery (exploratory — gate: {gate_label} tier) ===")
    if not result.suggestions:
        click.echo("//   (no adjacent candidate cleared the transfer gate)")
    for s in result.suggestions:
        sb = " [in SB]" if s.in_sideboard else ""
        roles = ", ".join(sorted(s.matched_roles))
        click.echo(
            f"//   {s.name}{sb}  value={s.transferred_value:.4f}  "
            f"roles=[{roles}]  cmc={s.cmc:g}  pmi={s.pmi:.3f}  n={s.n_total}"
        )
        top = sorted(s.per_opponent.items(), key=lambda kv: -kv[1].lift)[:3]
        for opp, cv in top:
            click.echo(f"//       vs {opp}: lift={cv.lift:+.3f}  n={cv.n}  [{cv.tier}]")

    # Honest accounting — no silent caps.
    notes: list[str] = []
    if result.capped_out:
        notes.append(f"{result.capped_out} more eligible (raise --discover-cap)")
    if result.omitted_below_gate:
        notes.append(f"{result.omitted_below_gate} transferable candidate(s) below the gate")
    if result.omitted_synergy:
        notes.append(
            f"{len(result.omitted_synergy)} synergy-role candidate(s) omitted — no honest "
            f"cross-field transfer; need in-shell/goldfish validation: "
            f"{', '.join(result.omitted_synergy)}"
        )
    for n in notes:
        click.echo(f"//   - {n}")
    click.echo(f"//   [disclaimer] {result.disclaimer}")


# ── viz: chart / dashboard rendering ──
@main.group()
def viz() -> None:
    """Visualization — render per-deck dashboards and individual chart tiles."""


@viz.command("deck")
@click.argument("archetype")
@click.option(
    "--out",
    required=True,
    help=(
        "Output path: a .html file → full dashboard HTML; "
        "a directory → one PNG per chart tile."
    ),
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Filter to online/paper events, or all.",
)
@click.option(
    "--regime",
    default="current",
    show_default=True,
    help="Ban regime to window the field/meta to (default: current).",
)
@click.option("--offline", is_flag=True, default=False,
              help="Inline the vl_convert JS bundle (no CDN, fully self-contained HTML).")
@click.option("--seed", type=int, default=0, show_default=True,
              help="RNG seed for deterministic Monte-Carlo positioning.")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def viz_deck(
    archetype: str,
    out: str,
    provenance: str,
    regime: str,
    offline: bool,
    seed: int,
    db: str | None,
    verbose: bool,
) -> None:
    """Render a per-deck dashboard for ARCHETYPE.

    --out file.html  — full dark HTML dashboard (CDN vega-embed by default; --offline for self-contained).
    --out <dir>      — one PNG per chart tile (whole-page PNG is out of scope).

    Example: legacy-engine viz deck "Dimir Tempo" --out deck.html
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.ingestion import store
    from legacy_engine.viz.deck_dashboard import build_deck_dashboard
    from legacy_engine.viz.layout import render_dashboard_html
    from legacy_engine.viz.render import render_png

    basis = None if provenance == "all" else provenance
    con = store.connect(db) if db else store.connect()
    try:
        dash = build_deck_dashboard(
            con, archetype,
            provenance=basis,
            regime=regime,
            seed=seed,
        )
    finally:
        con.close()

    out_path = Path(out)

    # Determine output mode from path
    is_dir = out_path.suffix == "" or out_path.is_dir()

    if is_dir:
        # Write one PNG per chart tile
        out_path.mkdir(parents=True, exist_ok=True)
        written = 0
        for idx, tile in enumerate(dash.tiles):
            if tile.kind != "chart" or tile.spec is None:
                continue
            safe_name = tile.title.replace(" ", "_").lower()
            png_path = out_path / f"{idx:02d}_{safe_name}.png"
            try:
                png_bytes = render_png(tile.spec)
            except ValueError as exc:
                raise click.ClickException(
                    f"Failed to render tile {tile.title!r} as PNG: {exc}"
                ) from exc
            png_path.write_bytes(png_bytes)
            click.echo(f"  Wrote {png_path}")
            written += 1
        click.echo(f"Rendered {written} chart tile(s) to {out_path}")
    else:
        # Render full HTML dashboard
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            html_str = render_dashboard_html(dash, offline=offline)
        except ValueError as exc:
            raise click.ClickException(f"Failed to render dashboard HTML: {exc}") from exc
        out_path.write_text(html_str, encoding="utf-8")
        click.echo(f"Dashboard written to {out_path} ({len(html_str):,} chars)")


@viz.command("meta")
@click.option("--out", required=True, help="Output path: .html → self-contained tile; .png → PNG.")
@click.option(
    "--definition",
    type=click.Choice(["raw", "topcut", "wrw"], case_sensitive=False),
    default="raw",
    show_default=True,
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper", "all"], case_sensitive=False),
    default="all",
    show_default=True,
)
@click.option("--min-share", type=float, default=0.02, show_default=True)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
)
@_window_opts
@_verbose
def viz_meta(
    out: str,
    definition: str,
    provenance: str,
    min_share: float,
    db: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Render a meta-share chart to .html or .png."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.analytics.metashare import compute_metashare
    from legacy_engine.advisory.window import resolve_advisory_window
    from legacy_engine.ingestion import store
    from legacy_engine.viz.models import _metashare_model
    from legacy_engine.viz.render import render_html_tile, render_png
    from legacy_engine.viz.specs import spec_metashare

    basis = None if provenance == "all" else provenance
    con = store.connect(db) if db else store.connect()
    try:
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time,
            provenance=basis, thin_floor=0, adaptive_default=False,
        )
        _echo_window(win)
        report = compute_metashare(
            con,
            definition=definition,
            provenance=basis,
            min_share=min_share,
            since=win.since,
            until=win.until,
        )
    finally:
        con.close()

    spec = spec_metashare(_metashare_model(report))
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if out_path.suffix.lower() == ".html":
            out_path.write_text(render_html_tile(spec), encoding="utf-8")
        else:
            out_path.write_bytes(render_png(spec))
    except ValueError as exc:
        raise click.ClickException(f"Render failed: {exc}") from exc

    click.echo(f"Written to {out_path}")


@viz.command("matchups")
@click.option("--out", required=True, help="Output path: .html → self-contained tile; .png → PNG.")
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper", "all"], case_sensitive=False),
    default="all",
    show_default=True,
)
@click.option("--min-row-share", type=float, default=0.02, show_default=True)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
)
@_window_opts
@_verbose
def viz_matchups(
    out: str,
    provenance: str,
    min_row_share: float,
    db: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Render the matchup heatmap to .html or .png."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.window import build_advisory_inputs, resolve_advisory_window
    from legacy_engine.ingestion import store
    from legacy_engine.viz.models import _heatmap_model
    from legacy_engine.viz.render import render_html_tile, render_png
    from legacy_engine.viz.specs import spec_matchup_heatmap

    basis = None if provenance == "all" else provenance
    con = store.connect(db) if db else store.connect()
    try:
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time, provenance=basis,
        )
        _echo_window(win)
        inputs = build_advisory_inputs(con, win, provenance=basis, min_row_share=min_row_share)
    finally:
        con.close()

    spec = spec_matchup_heatmap(_heatmap_model(inputs.matrix))
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if out_path.suffix.lower() == ".html":
            out_path.write_text(render_html_tile(spec), encoding="utf-8")
        else:
            out_path.write_bytes(render_png(spec))
    except ValueError as exc:
        raise click.ClickException(f"Render failed: {exc}") from exc

    click.echo(f"Written to {out_path}")


@viz.command("trends")
@click.option("--out", required=True, help="Output path: .html → self-contained tile; .png → PNG.")
@click.option(
    "--definition",
    type=click.Choice(["raw", "topcut"], case_sensitive=False),
    default="raw",
    show_default=True,
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper", "all"], case_sensitive=False),
    default="all",
    show_default=True,
)
@click.option("--min-share", type=float, default=0.02, show_default=True)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
)
@_verbose
def viz_trends(
    out: str,
    definition: str,
    provenance: str,
    min_share: float,
    db: str | None,
    verbose: bool,
) -> None:
    """Render the meta-share trends chart to .html or .png."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.analytics.trends import compute_trends
    from legacy_engine.ingestion import store
    from legacy_engine.viz.models import _trends_model
    from legacy_engine.viz.render import render_html_tile, render_png
    from legacy_engine.viz.specs import spec_trends

    basis = None if provenance == "all" else provenance
    con = store.connect(db) if db else store.connect()
    try:
        series = compute_trends(
            con,
            definition=definition,
            provenance=basis,
            min_share=min_share,
        )
    finally:
        con.close()

    spec = spec_trends(_trends_model(series))
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if out_path.suffix.lower() == ".html":
            out_path.write_text(render_html_tile(spec), encoding="utf-8")
        else:
            out_path.write_bytes(render_png(spec))
    except ValueError as exc:
        raise click.ClickException(f"Render failed: {exc}") from exc

    click.echo(f"Written to {out_path}")


@viz.command("tiers")
@click.option("--out", required=True, help="Output path: .html → self-contained tile; .png → PNG.")
@click.option(
    "--definition",
    type=click.Choice(["raw", "topcut", "wrw"], case_sensitive=False),
    default="raw",
    show_default=True,
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper", "all"], case_sensitive=False),
    default="all",
    show_default=True,
)
@click.option("--min-share", type=float, default=0.02, show_default=True)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
)
@_verbose
def viz_tiers(
    out: str,
    definition: str,
    provenance: str,
    min_share: float,
    db: str | None,
    verbose: bool,
) -> None:
    """Render the tier list chart to .html or .png."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.analytics.metashare import compute_metashare
    from legacy_engine.ingestion import store
    from legacy_engine.viz.models import _tier_model
    from legacy_engine.viz.render import render_html_tile, render_png
    from legacy_engine.viz.specs import spec_tier_list

    basis = None if provenance == "all" else provenance
    con = store.connect(db) if db else store.connect()
    try:
        report = compute_metashare(
            con,
            definition=definition,
            provenance=basis,
            min_share=min_share,
        )
    finally:
        con.close()

    spec = spec_tier_list(_tier_model(report))
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if out_path.suffix.lower() == ".html":
            out_path.write_text(render_html_tile(spec), encoding="utf-8")
        else:
            out_path.write_bytes(render_png(spec))
    except ValueError as exc:
        raise click.ClickException(f"Render failed: {exc}") from exc

    click.echo(f"Written to {out_path}")


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
