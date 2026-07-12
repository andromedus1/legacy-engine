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

log = logging.getLogger(__name__)


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


def _provenance_opt(f):
    """Attach ``--provenance online|paper`` to an advise leaf.

    Filters the expected field (and matchup matrix) to online-only or paper-only events.
    Absent (default) → current global behavior, byte-identical.
    When ``--field`` is also supplied, provenance still filters the matchup matrix but the
    custom field is used as-is (a hand-rolled field has no provenance axis).
    """
    return click.option(
        "--provenance",
        type=click.Choice(["online", "paper"], case_sensitive=False),
        default=None,
        help=(
            "Filter the expected field and matchup matrix to online or paper events only. "
            "Absent → combined global field (current default). "
            "When --field is also given, provenance filters only the matchup matrix."
        ),
    )(f)


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


@seed.command("prices")
@click.option("--force", is_flag=True, default=False, help="Force re-download even if already current.")
@_verbose
def seed_prices(force: bool, verbose: bool) -> None:
    """Download Scryfall default_cards bulk and load per-printing prices into DuckDB.

    Downloads the ~547 MB default_cards bulk (one object per printing, English/printed-language)
    into data/scryfall/default_cards.json, then streams it into the card_prices table.  Re-running
    is a no-op until Scryfall publishes a new bulk (updated_at skip-if-current).

    The card_prices table is separate from the cards table — the oracle/seed-cards path is
    completely unchanged (gated-additive).
    """
    _setup_logging(verbose)
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.scryfall import ScryfallClient

    with ScryfallClient() as client:
        client.download_prices_bulk(force=force)
        updated_at = client.prices_updated_at()

        con = store.connect()
        try:
            store.rebuild_prices(con)
            n_loaded = store.load_prices(con, client.iter_price_rows())
        finally:
            con.close()

    # Count priced rows.
    con2 = store.connect()
    try:
        n_priced = con2.execute(
            "SELECT count(*) FROM card_prices WHERE is_paper = TRUE AND usd IS NOT NULL"
        ).fetchone()[0]
    finally:
        con2.close()

    date_str = (updated_at or "unknown")[:10]
    click.echo(
        f"Loaded {n_loaded:,} printings ({n_priced:,} priced) as of {date_str}"
    )


def _echo_price_freshness(updated_at: str | None) -> None:
    """Echo a price-data-currency header (mirrors ``_echo_data_freshness`` for tournament data)."""
    from datetime import date

    if updated_at is None:
        click.echo("// prices: not seeded (run `legacy seed prices`)")
        return
    date_str = updated_at[:10]
    click.echo(f"// prices as of {date_str}")
    try:
        age = (date.today() - date.fromisoformat(date_str)).days
    except ValueError:
        age = None
    if age is not None and age > _STALE_DAYS:
        click.echo(
            f"// ⚠ price data is {age} days old — consider running `legacy seed prices`"
        )


# ── refresh: incremental update of mirrored sources ──
@main.group()
def refresh() -> None:
    """Incrementally refresh mirrored sources (cache, rules, cards, prices)."""


@refresh.command("all")
@click.option("--prices", "refresh_prices", is_flag=True, default=False,
              help="Also re-pull prices bulk (skipped by default; ~547 MB).")
@_verbose
def refresh_all(refresh_prices: bool, verbose: bool) -> None:
    """Refresh all mirrored sources: cache + rules + optionally prices."""
    _setup_logging(verbose)
    from legacy_engine.ingestion import cache, store
    from legacy_engine.ingestion.rules_vendor import refresh_rules

    # Re-mirror the tournament cache and re-ingest.
    cache.mirror_cache()
    con = store.connect()
    try:
        n = cache.ingest_cache(con)
    finally:
        con.close()
    click.echo(f"Refreshed tournament cache: {n} Legacy tournaments")

    # Vendor the archetype rules.
    sha = refresh_rules()
    click.echo(f"Refreshed MTGOFormatData rules @ {sha or '(sha unresolved)'}")

    # Optionally refresh prices (opt-in: the bulk is ~547 MB).
    if refresh_prices:
        from legacy_engine.ingestion.scryfall import ScryfallClient

        with ScryfallClient() as client:
            client.download_prices_bulk()
            updated_at = client.prices_updated_at()
            con = store.connect()
            try:
                store.rebuild_prices(con)
                n_loaded = store.load_prices(con, client.iter_price_rows())
            finally:
                con.close()
        date_str = (updated_at or "unknown")[:10]
        click.echo(f"Refreshed prices: {n_loaded:,} printings as of {date_str}")
    else:
        click.echo("// prices not refreshed (pass --prices to include)")


@refresh.command("cards")
@click.option("--force", is_flag=True, default=False,
              help="Force a bulk re-download even if Scryfall reports no change.")
@click.option("--horizon-days", type=int, default=30, show_default=True,
              help="How many days ahead to consider a set 'upcoming' in the scan.")
@click.option("--lookback-days", type=int, default=14, show_default=True,
              help="How many days back to consider a set 'recently released' in the scan.")
@_verbose
def refresh_cards(force: bool, horizon_days: int, lookback_days: int, verbose: bool) -> None:
    """Release-aware incremental card refresh (diff-producing, non-destructive).

    Scans Scryfall /sets to identify recently-released and upcoming sets, then
    forces a bulk re-pull when a recently-released set is found (or when --force
    is passed). Ingests with load_cards_diff so new card names are captured and
    reported without rebuilding (no data loss).

    This is the scheduler entry point: `legacy refresh cards` is idempotent — re-running
    after no new sets produces an empty diff. `seed cards` remains the from-scratch path.
    """
    _setup_logging(verbose)
    from datetime import date

    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.releases import fetch_sets, upcoming_and_recent
    from legacy_engine.ingestion.scryfall import ScryfallClient
    from legacy_engine.models.card import Card

    with ScryfallClient() as client:
        # ── Step 1: run the release scan (advisory, informs whether to force) ──
        today = date.today()
        try:
            sets_list = fetch_sets(client)
            scan = upcoming_and_recent(
                sets_list,
                today=today,
                horizon_days=horizon_days,
                lookback_days=lookback_days,
            )
            has_recent = bool(scan.recently_released)
            click.echo(
                f"// Release scan: {len(scan.upcoming)} upcoming, "
                f"{len(scan.recently_released)} recently released"
            )
            if scan.recently_released:
                click.echo(
                    "// Recently released: "
                    + ", ".join(f"{s.name} ({s.released_at})" for s in scan.recently_released)
                )
            if scan.upcoming:
                click.echo(
                    "// Upcoming: "
                    + ", ".join(f"{s.name} ({s.released_at})" for s in scan.upcoming[:3])
                    + ("…" if len(scan.upcoming) > 3 else "")
                )
        except Exception as exc:
            click.echo(f"// Release scan failed ({exc}); proceeding with --force={force}")
            has_recent = False

        # ── Step 2: decide whether to force a re-pull ──────────────────────────
        should_force = force or has_recent
        if not should_force:
            click.echo("// No recently-released sets found; skipping bulk re-pull "
                       "(pass --force to override)")

        # ── Step 3: download bulk (skip-if-current unless forced) ──────────────
        client.download_bulk_data(force=should_force)
        updated_at = None
        try:
            import json
            from legacy_engine.ingestion.scryfall import METADATA_PATH
            if METADATA_PATH.exists():
                updated_at = json.loads(METADATA_PATH.read_text()).get("updated_at")
        except Exception:
            pass

        # ── Step 4: ingest with diff (non-destructive INSERT OR REPLACE) ───────
        index = client.load_card_index()
        unique = {raw["name"]: raw for raw in index.values()}
        cards = [Card.from_scryfall(raw) for raw in unique.values()]

        con = store.connect()
        try:
            diff = store.load_cards_diff(con, cards, scryfall_updated_at=updated_at)
        finally:
            con.close()

        # ── Persist the diff for report new-cards / speculate --new ──────────
        store.persist_ingest_diff(diff)

    # ── Step 5: report the diff ──────────────────────────────────────────────
    date_str = (updated_at or "unknown")[:10]
    click.echo(f"// Bulk as of {date_str}  |  total cards: {diff.total_after:,}")
    if diff.new_names:
        click.echo(f"\n{len(diff.new_names)} new card(s) ingested:")
        for name in diff.new_names[:50]:
            click.echo(f"  + {name}")
        if len(diff.new_names) > 50:
            click.echo(f"  … ({len(diff.new_names) - 50} more)")
    else:
        click.echo("No new cards (diff is empty — card universe is current).")


# ── label: archetype classification ──
@main.command()
@_verbose
def label(verbose: bool) -> None:
    """Label ingested decklists with archetypes."""
    _setup_logging(verbose)
    from legacy_engine.archetype.labeler import label_decks
    from legacy_engine.archetype.rules import load_ruleset
    from legacy_engine.archetype.variants import load_variant_registry
    from legacy_engine.config import RULES_DIR, VARIANTS_REGISTRY_PATH
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.scryfall import ScryfallClient

    ruleset = load_ruleset(RULES_DIR)

    # Load the variant registry when the shipped file exists; gracefully None if absent
    # (gated-additive: missing registry → variant stays NULL, byte-identical to pre-variant).
    registry = None
    if VARIANTS_REGISTRY_PATH.exists():
        registry = load_variant_registry(VARIANTS_REGISTRY_PATH)

    con = store.connect()
    try:
        with ScryfallClient() as client:
            client.load_card_index()
            n = label_decks(con, ruleset, client.get_card, registry=registry)
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
    from legacy_engine.analytics.metashare import compute_metashare
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
            try:
                venue_list = resolve_venues(con, requested_keys)
            except ValueError as exc:
                raise click.ClickException(str(exc)) from exc

            definitions: list[str]
            if definition == "all":
                definitions = ["raw", "topcut", "wrw"]
            else:
                definitions = [definition]

            # Resolve a single window (venues mode uses one shared window).
            # When no explicit window flag is given, default to the current ban regime
            # rather than full corpus — venue comparison is inherently about the live
            # meta, and full-corpus data bleeds in obsolete regime shares (e.g. Tron
            # at 1% from eras before the ban list changed).  A plain (non-venues)
            # ``report meta`` keeps its existing full-corpus default (gated-additive:
            # the else-branch below is byte-identical to the pre-patch code).
            effective_regime = regime
            if venues is not None and regime is None and since is None and until is None and not all_time:
                effective_regime = "current"
            win = resolve_advisory_window(
                con, regime=effective_regime, since=since, until=until, all_time=all_time,
                thin_floor=0, adaptive_default=False,
            )
            _echo_window(win)

            for defn in definitions:
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
            for defn in definitions_leg:
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
    "--a",
    "archetype_a",
    default=None,
    help="Head-to-head mode: archetype A (use with --b).",
)
@click.option(
    "--b",
    "archetype_b",
    default=None,
    help="Head-to-head mode: archetype B (use with --a).",
)
@click.option(
    "--split-variant",
    "split_variant",
    default=None,
    help="Split this archetype's rows into decks.variant camps (e.g. 'Doomsday') — camp labels "
         "read '<ARCHETYPE> [<variant>]', with unlabeled decks kept visible as '<ARCHETYPE> "
         "[unlabeled]'. Camp rows are force-included regardless of --min-row-share. "
         "--a/--b accept camp labels for head-to-head mode.",
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
    archetype_a: str | None,
    archetype_b: str | None,
    split_variant: str | None,
    db: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Archetype matchup matrix with confidence intervals.

    Head-to-head mode: pass --a <archetype> and --b <archetype> to look up a single pair
    directly instead of printing the full matrix.
    """
    _setup_logging(verbose)
    from legacy_engine.advisory.window import build_advisory_inputs, resolve_advisory_window
    from legacy_engine.analytics.matchup import lookup_head_to_head
    from legacy_engine.ingestion import store

    # Validate head-to-head flag pair
    if (archetype_a is None) != (archetype_b is None):
        raise click.ClickException("--a and --b must be used together (both or neither).")

    head_to_head = archetype_a is not None and archetype_b is not None

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)
        if split_variant is not None:
            click.echo(
                f"// split-variant: {split_variant} (camps from decks.variant; "
                "unlabeled residue shown)"
            )
            try:
                from legacy_engine.archetype.discovered import load_discovered
                from legacy_engine.config import DISCOVERED_VARIANTS_PATH

                disc = load_discovered(DISCOVERED_VARIANTS_PATH)
                staged = next(
                    (
                        s for s in disc.splits
                        if s.parent == split_variant and s.status == "candidate"
                    ),
                    None,
                )
                if staged is not None:
                    click.echo(
                        f"// provenance: {split_variant} has a STAGED (unpromoted) candidate "
                        "split — variant labels may be speculative-provenance"
                    )
            except Exception:
                pass
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
            inputs = build_advisory_inputs(
                con, win, provenance=basis, min_row_share=min_row_share,
                split_variant=split_variant,
            )
            for line in inputs.audit:
                click.echo(line)
            matrix = inputs.matrix

            if head_to_head:
                cell = lookup_head_to_head(matrix, archetype_a, archetype_b)
                _print_head_to_head(matrix, archetype_a, archetype_b, cell)
            else:
                _print_matchup_matrix(matrix, split_variant=split_variant)
    finally:
        con.close()


def _print_matchup_matrix(matrix, *, split_variant: str | None = None) -> None:  # type: legacy_engine.analytics.matchup.MatchupMatrix
    """Render a matchup matrix as a labeled text table.

    ``split_variant`` (opt-in, default ``None``): when set, appends one audit-echo line per
    non-mirror cell touching a camp row (``f"{split_variant} ["`` label) naming its hierarchical
    ``prior_source`` (epic-stable-era-windows-shrinkage, Unit 3 AC "camp rows show prior
    labels") — the shrunk%|raw% grid cells themselves are unchanged, since the honesty carrier
    (triple-display) already covers the estimate; this only surfaces WHAT the shrunk number was
    anchored to. ``None`` is byte-identical to the pre-epic rendering (no lines added).
    """
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
    click.echo("Cells: shrunk%|raw% n=matches — the raw record always travels with the estimate; small n is pulled toward 50%.")
    click.echo(header)
    click.echo("-" * len(header))

    _camp_prefix = f"{split_variant} [" if split_variant is not None else None
    prior_lines: list[str] = []

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
                if cell.p_shrunk is not None and cell.p_raw is not None:
                    # Triple display (shrunk%|raw% n=) — shrinkage compresses small samples
                    # toward 50%, so the raw record must always travel with the estimate.
                    part = f"{cell.p_shrunk:.0%}|{cell.p_raw:.0%} n={cell.n}"
                else:
                    part = "n/a"
            row_parts.append(part.ljust(col_width))
            if (
                _camp_prefix is not None
                and cell is not None
                and not cell.is_mirror
                and row_arch.startswith(_camp_prefix)
                and cell.prior_source is not None
            ):
                prior_lines.append(f"// prior: {row_arch} vs {col_arch}: {cell.prior_source}")
        click.echo("  ".join(row_parts))

    if has_unclassified:
        click.echo(_UNCLASSIFIED_FOOTNOTE)

    for line in prior_lines:
        click.echo(line)


def _print_head_to_head(
    matrix: "MatchupMatrix",
    archetype_a: str,
    archetype_b: str,
    cell: "MatchupCell | None",
) -> None:
    """Render a single head-to-head matchup cell."""
    from legacy_engine.analytics.matchup import MatchupMatrix, DISPLAY_GATE_N  # noqa: F401
    from legacy_engine.models import MatchupCell  # noqa: F401

    basis_label = matrix.provenance if matrix.provenance else "all"
    click.echo(f"\n=== Head-to-Head [{basis_label}]: {archetype_a!r} vs {archetype_b!r} ===")
    click.echo(f"Caveat: {matrix.caveat}")

    if cell is None:
        if archetype_a not in matrix.archetypes or archetype_b not in matrix.archetypes:
            missing = [
                a for a in (archetype_a, archetype_b) if a not in matrix.archetypes
            ]
            click.echo(
                f"  (archetype(s) not in matrix — below row-inclusion threshold or no data: "
                f"{', '.join(missing)})"
            )
        else:
            click.echo("  (pair not found in matrix)")
        return

    click.echo(f"  {archetype_a!r} win-rate vs {archetype_b!r}:")
    click.echo(f"    n              = {cell.n}")
    click.echo(f"    wins           = {cell.wins}")
    click.echo(f"    tier           = {cell.tier}")
    if cell.prior_source is not None:
        click.echo(f"    prior          = {cell.prior_source}")

    if not cell.display:
        click.echo(
            f"    NOTE: n={cell.n} < {DISPLAY_GATE_N} (speculative) — "
            "rate present-and-honest but unreliable; treat as indicative only"
        )
    if cell.p_raw is not None:
        click.echo(f"    p_raw          = {cell.p_raw:.3f} ({cell.p_raw:.1%})")
    if cell.p_shrunk is not None:
        click.echo(f"    p_shrunk       = {cell.p_shrunk:.3f} ({cell.p_shrunk:.1%})")
    if cell.ci_low is not None and cell.ci_high is not None:
        click.echo(f"    95% CI         = [{cell.ci_low:.3f}, {cell.ci_high:.3f}]")

    # Also show the reverse direction
    rev = matrix.cells.get((archetype_b, archetype_a))
    if rev is not None and rev.p_shrunk is not None:
        rev_caveat = (
            f" [speculative — n={rev.n} < {DISPLAY_GATE_N}]" if not rev.display else ""
        )
        click.echo(
            f"  {archetype_b!r} win-rate vs {archetype_a!r}: "
            f"{rev.p_shrunk:.1%} (raw {rev.p_raw:.1%}, n={rev.n}){rev_caveat}"
        )


@report.command("affectedness")
@click.option(
    "--archetype",
    required=True,
    help="Archetype to explain (e.g. 'Dimir Reanimator').",
)
@click.option(
    "--provenance",
    type=click.Choice(["online", "paper"], case_sensitive=False),
    default=None,
    help="Filter to online or paper events (default: all).",
)
@click.option(
    "--threshold",
    type=float,
    default=0.25,
    show_default=True,
    help="Inclusion rate threshold above which a ban is considered materially affecting (0..1).",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def report_affectedness(
    archetype: str,
    provenance: str | None,
    threshold: float,
    db: str | None,
    verbose: bool,
) -> None:
    """Explain which bans drove an archetype's valid_since (ban-affectedness derivation).

    Shows, for each ban event, how many of the archetype's pre-ban decks ran any
    banned card — the inclusion rate that determined whether the ban materially
    affected the archetype's matchup history.

    Example: legacy report affectedness --archetype "Dimir Reanimator"
    """
    _setup_logging(verbose)
    from legacy_engine.analytics.affectedness import explain_valid_since
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)
        explanations = explain_valid_since(
            con, archetype, provenance=provenance, affect_threshold=threshold
        )
        _print_affectedness_explain(archetype, explanations, threshold=threshold)
    finally:
        con.close()


def _print_affectedness_explain(
    archetype: str,
    explanations: "list[AffectednessExplanation]",
    *,
    threshold: float,
) -> None:
    """Render the affectedness derivation as a labeled per-ban-event table."""
    from legacy_engine.analytics.affectedness import AffectednessExplanation  # noqa: F401

    click.echo(f"\n=== Affectedness Derivation: {archetype!r} (threshold={threshold:.0%}) ===")

    if not explanations:
        click.echo("  (no ban events in BAN_EVENTS — nothing to explain)")
        return

    # Determine valid_since: latest ban_date where affected=True
    affected_dates = [e.ban_date for e in explanations if e.affected]
    valid_since = max(affected_dates) if affected_dates else None
    click.echo(f"  Derived valid_since: {valid_since or 'None (full history — no affecting ban)'}")
    click.echo("")
    click.echo(
        f"  {'Ban date':<12}  {'Pre-ban decks':>13}  {'Run banned':>10}  "
        f"{'Rate':>6}  {'Affected?':<10}  Cards banned"
    )
    click.echo("  " + "-" * 90)

    for e in explanations:
        affected_str = "YES ***" if e.affected else "no"
        rate_str = f"{e.inclusion_rate:.1%}"
        cards_str = ", ".join(e.banned_cards)
        window_str = f"{e.prev_ban_date or 'open'} → {e.ban_date}"
        click.echo(
            f"  {e.ban_date:<12}  {e.pre_ban_decks:>13}  {e.running_decks:>10}  "
            f"{rate_str:>6}  {affected_str:<10}  {cards_str}"
        )
        if e.pre_ban_decks == 0:
            click.echo(f"    (no pre-ban deck data for window {window_str})")


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
    "--movers",
    type=int,
    default=0,
    show_default=True,
    help="Append a biggest-movers digest comparing the two most recent regimes (top N by |delta|). "
         "0 = off.",
)
@_verbose
def report_trends(
    definition: str,
    provenance: str,
    min_share: float,
    db: str | None,
    movers: int,
    verbose: bool,
) -> None:
    """Meta-share evolution across ban-list regimes (version-stamped)."""
    _setup_logging(verbose)
    from legacy_engine.analytics.trends import biggest_movers, compute_trends
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
            if movers > 0:
                top = biggest_movers(series, n=movers)
                _print_biggest_movers(top)
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


def _print_biggest_movers(movers: "list[BiggestMover]") -> None:
    """Render a biggest-movers digest as a compact labeled table."""
    from legacy_engine.analytics.trends import BiggestMover  # noqa: F401

    if not movers:
        click.echo("\n  (biggest-movers: fewer than 2 regimes — nothing to compare)")
        return

    # Derive the regime labels from the first entry (all share the same pair).
    prev_label = movers[0].prev_regime
    curr_label = movers[0].curr_regime
    click.echo(f"\n── Biggest Movers: {prev_label!r} → {curr_label!r} ──")
    click.echo(f"  {'Archetype':<30}  {'Prev':>7}  {'Curr':>7}  {'Delta':>7}")
    click.echo("  " + "-" * 58)

    for m in movers:
        prev_str = f"{m.prev_share:.1%}" if m.prev_share is not None else "new"
        curr_str = f"{m.curr_share:.1%}" if m.curr_share is not None else "gone"
        sign = "+" if m.delta > 0 else ""
        delta_str = f"{sign}{m.delta:.1%}"
        click.echo(f"  {m.archetype:<30}  {prev_str:>7}  {curr_str:>7}  {delta_str:>7}")


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


def _echo_slot_contrast(report) -> None:
    """Render one SlotContrastReport window as a table with honesty banners."""
    click.echo(
        f"\n// window: {report.window_label}  |  decisive "
        f"{report.archetype} vs {report.opponent} matches: {report.n_matches}"
    )
    if report.degraded:
        click.echo(f"// degraded: {report.note}")
        return

    def _cohort(p: float | None, n: int, ci) -> str:
        if not n:
            return "—  (n=0)"
        lo, hi = ci
        return f"{p * 100:5.1f}% (n={n:>3}) [{lo * 100:>2.0f}-{hi * 100:<2.0f}]"

    click.echo(
        f"{'Card':<26}  {'WITH card':<24}  {'WITHOUT card':<24}  {'diff':>6}  significance"
    )
    click.echo("-" * 96)
    for c in report.cells:
        diff_str = f"{c.diff * 100:+5.1f}" if c.diff is not None else "—"
        if c.p_value is None:
            sig = "—"
        elif c.significant:
            sig = f"yes (p={c.p_value:.2f})"
        else:
            sig = f"no  (p={c.p_value:.2f})"
        click.echo(
            f"{c.card:<26}  {_cohort(c.p_with, c.n_with, c.ci_with):<24}  "
            f"{_cohort(c.p_without, c.n_without, c.ci_without):<24}  {diff_str:>6}  {sig}"
        )
    if report.any_thin:
        click.echo("// thin: cohorts with n<30 are speculative — diffs indicative only, CIs wide.")


def _report_cards_contrast(
    *,
    archetype: str | None,
    opponent: str | None,
    board: str,
    card: str | None,
    since: str | None,
    until: str | None,
    db: str | None,
) -> None:
    """Matchup-conditioned sideboard-slot test (the `report cards --contrast` path)."""
    from legacy_engine.analytics.slot_test import card_matchup_contrast, pair_adaptive_since
    from legacy_engine.ingestion import store

    if not archetype or not opponent:
        raise click.ClickException(
            "--contrast requires both --archetype and --vs "
            "(the archetype to test, and the opponent matchup to test the slot against)."
        )

    cards = [card] if card else None
    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)
        click.echo(f"\n=== Sideboard-slot contrast: {archetype!r} vs {opponent!r} [board={board}] ===")
        click.echo(
            "// presence-correlational, NOT causal — owning a card != boarding it in; "
            "selection confounds apply."
        )
        if card is None:
            click.echo(
                "// scan: per-card p-values are uncorrected — treat a lone 'significant' "
                "with skepticism (multiple comparisons)."
            )

        if since is not None or until is not None:
            windows = [(since, until, f"custom ({since or 'start'} → {until or 'now'})")]
        else:
            adaptive_since = pair_adaptive_since(con, archetype, opponent)
            adaptive_label = (
                f"adaptive ban-aware (since {adaptive_since})"
                if adaptive_since
                else "adaptive ban-aware (full corpus — neither archetype ban-affected)"
            )
            windows = [
                (adaptive_since, None, adaptive_label),
                (None, None, "full-corpus (all-time)"),
            ]

        for win_since, win_until, label in windows:
            report = card_matchup_contrast(
                con, archetype, opponent, board=board, cards=cards,
                since=win_since, until=win_until, window_label=label,
            )
            _echo_slot_contrast(report)
    finally:
        con.close()


def _report_cards_conditioned(
    *,
    archetype: str | None,
    variant: str | None,
    board: str,
    min_tier: str,
    since: str | None,
    until: str | None,
    db: str | None,
) -> None:
    """Archetype/variant-conditioned card win-rate (the `report cards --conditioned` path).

    Restricts the win-rate denominator to ``archetype``'s (or ``archetype``+``variant``'s) own
    decks and prints BOTH the corpus-wide marginal lift and the conditioned lift per card, plus
    an honest-degrade sign-conflict line whenever the two disagree in sign — divergence-as-
    diagnostic, never auto-corrected (epic-subarchetype-resolution-card-winrate).
    """
    from legacy_engine.analytics.card_value import card_value_marginal, conflict_cards
    from legacy_engine.analytics.match_results import compute_card_winrates
    from legacy_engine.generation.consensus import card_frequencies
    from legacy_engine.ingestion import store

    if not archetype:
        raise click.ClickException("--conditioned requires --archetype.")

    _TIER_ORDER = {"speculative": 0, "evolving": 1, "established": 2}
    min_tier_rank = _TIER_ORDER[min_tier.lower()]

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)

        # Resolve the effective window ONCE so the card list and both win-rate slices share it
        # (mirrors the non-conditioned path above). Era-aware: this archetype's own stable_since
        # horizon (entity_era_window), not a global ban-regime window.
        if since is None and until is None:
            from legacy_engine.generation.consensus import entity_era_window
            effective_since, effective_until, window_label = entity_era_window(con, archetype)
            click.echo(f"// window: since {effective_since or 'full corpus'} ({window_label})")
        else:
            effective_since, effective_until = since, until

        r_marginal = compute_card_winrates(con, since=effective_since, until=effective_until)
        r_conditioned = compute_card_winrates(
            con, since=effective_since, until=effective_until,
            deck_archetype=archetype, deck_variant=variant,
        )

        card_freqs = card_frequencies(
            con, archetype, board=board, since=effective_since, until=effective_until
        )
        cards = [cf.name for cf in card_freqs]
        if not cards:
            click.echo(f"No cards found for archetype={archetype!r} board={board!r} in the given window.")
            return

        camp_label = f"{archetype} [{variant}]" if variant else archetype

        marginal_values = [card_value_marginal(r_marginal, c, board) for c in cards]
        conditioned_values = [card_value_marginal(r_conditioned, c, board) for c in cards]
        conditioned_by_card = {cv.card: cv for cv in conditioned_values}

        tier_label = "all" if min_tier == "speculative" else f">= {min_tier}"
        click.echo(
            f"\n=== Card Win-Rates [board={board}, conditioned={camp_label!r}, tier={tier_label}] ==="
        )
        click.echo("NOTE: presence-correlational — NOT causal. See registered 75, not game-by-game play.")
        window_label = (
            f"{effective_since or 'start'} → {effective_until or 'now'}"
            if (effective_since or effective_until)
            else "all dates"
        )
        click.echo(
            f"Window: {window_label}  |  decisive matches (corpus): {r_marginal.coverage.decisive_matched}  "
            f"|  decisive matches ({camp_label}): {r_conditioned.coverage.decisive_matched}"
        )
        click.echo(
            f"{'Card':<35}  {'n_marg':>6}  {'lift_marg':>9}  "
            f"{'n_cond':>6}  {'lift_cond':>9}  {'tier_cond':<12}"
        )
        click.echo("-" * 92)

        suppressed = 0
        printed = 0
        for mcv in sorted(marginal_values, key=lambda cv: cv.card):
            ccv = conditioned_by_card.get(mcv.card)
            if ccv is None:
                continue
            tier_rank = _TIER_ORDER[ccv.tier]
            if tier_rank < min_tier_rank:
                suppressed += 1
                continue
            click.echo(
                f"{mcv.card:<35}  {mcv.n:>6}  {mcv.lift:>+9.3f}  "
                f"{ccv.n:>6}  {ccv.lift:>+9.3f}  {ccv.tier:<12}"
            )
            printed += 1

        if suppressed > 0:
            click.echo(
                f"\n  {suppressed} row(s) below {min_tier!r} gate (conditioned tier) — suppressed "
                f"(use --min-tier speculative to show all). Data present; not fabricated."
            )
        if printed == 0 and suppressed == 0:
            click.echo("(no card data for the specified slice)")

        conflicts = conflict_cards(marginal_values, conditioned_values)
        for conflict_card, marg_lift, cond_lift in conflicts:
            click.echo(
                f"// sign conflict: {conflict_card} marginal {marg_lift:+.3f} vs "
                f"within-{camp_label} {cond_lift:+.3f} — archetype-specific keep/cut calls "
                f"must not use the marginal alone"
            )
    finally:
        con.close()


@report.command("cards")
@click.option("--archetype", default=None, help="Restrict to cards an archetype plays (via card_frequencies).")
@click.option("--vs", "opponent", default=None, help="Show per-matchup value vs this opponent; else shows marginal.")
@click.option("--board", default="main", show_default=True, help="Board to query: main or side.")
@click.option(
    "--conditioned",
    is_flag=True,
    default=False,
    help="Restrict the win-rate denominator to --archetype's (or --variant's) own decks; "
    "shows BOTH the corpus-wide marginal lift and the conditioned lift per card, plus a "
    "sign-conflict warning when they disagree (requires --archetype).",
)
@click.option(
    "--variant",
    default=None,
    help="With --conditioned: narrow further to this camp/variant label (decks.variant). "
    "Requires --conditioned.",
)
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
    "--contrast",
    is_flag=True,
    default=False,
    help="Sideboard-slot test: WITH-vs-WITHOUT card win-rate in a specific matchup "
    "(requires --archetype and --vs). Shows adaptive + full-corpus windows.",
)
@click.option(
    "--card",
    default=None,
    help="With --contrast: focus a single card (default: scan all cards the archetype runs on --board).",
)
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
    conditioned: bool,
    variant: str | None,
    min_tier: str,
    since: str | None,
    until: str | None,
    contrast: bool,
    card: str | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Per-card win-rate (presence-correlational — NOT causal).

    Shows how a card's decks perform relative to the archetype's baseline win-rate.
    Thin cells (below --min-tier) are suppressed with a note, never fabricated.

    With --contrast, instead shows the matchup-conditioned sideboard-slot test: for an
    --archetype vs --vs opponent, the WITH-card vs WITHOUT-card win-rate (on --board),
    with Wilson CIs and a Fisher's-exact significance test on the difference.

    With --conditioned, instead shows the archetype-scoped win-rate: --archetype's (or
    --variant camp's) own decks only, alongside the corpus-wide marginal, with an honest
    sign-conflict warning when the two disagree (a card can read as a "cut" in the pooled
    marginal while being a genuine "keep" within one archetype — see
    epic-subarchetype-resolution-card-winrate).
    """
    _setup_logging(verbose)

    if variant is not None and not conditioned:
        raise click.ClickException("--variant requires --conditioned.")
    if conditioned and archetype is None:
        raise click.ClickException("--conditioned requires --archetype.")
    if conditioned and opponent is not None:
        raise click.ClickException(
            "--conditioned does not support --vs yet (opponent-specific conditioned values are "
            "a tracked follow-up); drop one of the flags"
        )

    if conditioned:
        _report_cards_conditioned(
            archetype=archetype, variant=variant, board=board, min_tier=min_tier,
            since=since, until=until, db=db,
        )
        return

    if contrast:
        # This is the *sideboard*-slot test — default --board to "side" for the contrast path
        # unless the user explicitly passed --board (the shared option defaults to "main" for
        # the normal report-cards path, which we must not change).
        ctx = click.get_current_context()
        eff_board = board
        if ctx.get_parameter_source("board") == click.core.ParameterSource.DEFAULT:
            eff_board = "side"
        _report_cards_contrast(
            archetype=archetype, opponent=opponent, board=eff_board,
            card=card, since=since, until=until, db=db,
        )
        return

    from legacy_engine.analytics.card_value import card_value_marginal, card_values_vs
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
        # Era-aware when a single archetype scopes the report: that entity's own
        # stable_since horizon; the global (no --archetype) report keeps the
        # global ban-regime window (a cross-entity surface has no single era).
        if since is None and until is None:
            if archetype is not None:
                from legacy_engine.generation.consensus import entity_era_window
                effective_since, effective_until, window_label = entity_era_window(con, archetype)
                click.echo(f"// window: since {effective_since or 'full corpus'} ({window_label})")
            else:
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
    "--winrates",
    is_flag=True,
    default=False,
    help="Also compute each camp's decisive match win-rate (with-subgroup vs without-subgroup) — "
    "the W/L split that actually decides a keep/cut, not just the copy-count deltas.",
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
    winrates: bool,
    db: str | None,
    verbose: bool,
) -> None:
    """Subgroup-diff analysis — split an archetype on a signature card.

    Shows the avg-copies difference between decks with vs without the signature card,
    sorted by |delta|.  This is the validated discovery tool for identifying sub-archetype
    variants worth registering.

    With --winrates, also shows each camp's decisive match win-rate + match-n + tier (with a
    thin-sample note) — the W/L split that decides a keep/cut, which otherwise has to be
    computed by hand from the composition diff alone.

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
            with_winrates=winrates,
        )
    finally:
        con.close()

    _print_subgroup_report(split)


def _print_subgroup_report(split: "SubgroupSplit") -> None:
    """Render a SubgroupSplit as a labeled diff table."""
    from legacy_engine.analytics.subgroup import SubgroupSplit  # noqa: F401
    from legacy_engine.confidence import tier_for_sample

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

    if split.wins_with is not None:
        # with_winrates=True was requested (n_matches_with/without are set together).
        n_mw = split.n_matches_with or 0
        n_mwo = split.n_matches_without or 0
        wr_with = f"{split.wins_with / n_mw:.3f}" if n_mw else "n/a"
        wr_without = f"{split.wins_without / n_mwo:.3f}" if n_mwo else "n/a"
        tier_mw = tier_for_sample(n_mw)
        tier_mwo = tier_for_sample(n_mwo)
        click.echo(f"  with-subgroup win%:    {wr_with}  (matches n={n_mw})  [{tier_mw}]")
        click.echo(f"  without-subgroup win%: {wr_without}  (matches n={n_mwo})  [{tier_mwo}]")
        if tier_mw == "speculative" or tier_mwo == "speculative":
            click.echo(
                "  // ⚠ thin win-rate sample(s) — match-n below 30 (speculative tier); "
                "win% is present-and-honest, not hidden, but treat the magnitude as unreliable"
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
        # Deliberately NOT era-windowed: this is a cross-parent summary over the whole
        # registry — no single entity's era scopes it; the global ban-regime window is the
        # honest cross-entity basis (epic-stable-era-windows-consumption Unit 4 decision).
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


@report.command("prices")
@click.argument("name")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def report_prices(name: str, db: str | None, verbose: bool) -> None:
    """Show every paper printing and the cheapest USD price for NAME.

    Diagnostic: surfaces the full printing spread that exposes pricing gaps (e.g. the $33
    Secret Lair Dismember vs the $1.50 NPH copy) and confirms which printing the advisor
    would recommend.

    Example: legacy report prices "Dismember"
    """
    _setup_logging(verbose)
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.prices import price_quote, printing_prices
    from legacy_engine.ingestion.scryfall import ScryfallClient, normalize_name

    con = store.connect(db) if db else store.connect()
    try:
        # Echo price freshness from the prices metadata file.
        with ScryfallClient() as client:
            updated_at = client.prices_updated_at()
        _echo_price_freshness(updated_at)

        norm = normalize_name(name)
        q = price_quote(con, norm)
        all_printings = printing_prices(con, norm)

        click.echo(f"\n=== Prices: {norm} ===")
        if q.all_null:
            click.echo(f"  all_null=True — no paper USD price in card_prices (source: {q.source})")
            if q.stale:
                click.echo("  stale=True — price data older than threshold")
        else:
            pp = q.cheapest_printing
            set_str = f"{pp.set_code}/{pp.collector_number}" if pp else "?"
            promo_str = " [promo]" if pp and pp.promo else ""
            click.echo(
                f"  cheapest: ${q.cheapest_usd:.2f}  "
                f"({set_str}{promo_str})  "
                f"n_priced={q.n_priced_printings}  "
                f"source={q.source}"
            )
            if q.stale:
                click.echo("  stale=True — price data older than threshold")

        if all_printings:
            click.echo(f"\n  {'Set':<8}  {'#':<6}  {'USD':>7}  {'Foil':>7}  {'Promo'}")
            click.echo("  " + "-" * 42)
            for p in all_printings:
                usd_s = f"${p.usd:.2f}" if p.usd is not None else "null"
                foil_s = f"${p.usd_foil:.2f}" if p.usd_foil is not None else "null"
                promo_s = "yes" if p.promo else ""
                click.echo(
                    f"  {(p.set_code or ''):<8}  {(p.collector_number or ''):<6}  "
                    f"{usd_s:>7}  {foil_s:>7}  {promo_s}"
                )
        else:
            click.echo("  (no priced paper printings found in card_prices)")
    finally:
        con.close()


@report.command("new-cards")
@click.option("--limit", type=int, default=50, show_default=True,
              help="Maximum number of new cards to display.")
@_verbose
def report_new_cards(limit: int, verbose: bool) -> None:
    """Show cards added in the most recent diff-ingest run.

    Reads the persisted ingest diff written by `refresh cards` to list the
    actual new card names. For the "what's new to test this week" surface.

    Run `legacy refresh cards` first to populate the diff.

    Example: legacy report new-cards --limit 20
    """
    _setup_logging(verbose)

    from legacy_engine.ingestion import store

    diff = store.load_ingest_diff()
    if diff is None:
        click.echo(
            "// No diff recorded yet — run `legacy refresh cards` first.\n"
            "// The diff will be persisted automatically on the next refresh."
        )
        return

    date_str = (diff.scryfall_updated_at or "unknown")[:10]
    n_new = len(diff.new_names)
    click.echo(
        f"\n=== New Cards (bulk as of {date_str}, total in DB: {diff.total_after:,}) ==="
    )

    if n_new == 0:
        click.echo("// No new cards in the last diff (card universe was already current).")
        return

    click.echo(f"{n_new} new card(s) from the last `refresh cards` run:")
    for name in diff.new_names[:limit]:
        click.echo(f"  + {name}")
    if n_new > limit:
        click.echo(f"  … ({n_new - limit} more; use --limit to show more)")


@report.command("speculate")
@click.argument("card_name", required=False, default=None)
@click.option("--new", "all_new", is_flag=True, default=False,
              help="Forecast all cards in the last diff (requires a prior `refresh cards` run).")
@click.option("--k", type=int, default=5, show_default=True,
              help="Number of analogues to find.")
@click.option("--board", default="main", show_default=True,
              help="Board for card_value_marginal lookup.")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def report_speculate(
    card_name: str | None,
    all_new: bool,
    k: int,
    board: str,
    db: str | None,
    verbose: bool,
) -> None:
    """Pre-data speculation: forecast a new card before tournament data exists.

    Always labelled PRE-DATA FORECAST / speculative — borrowing an established
    neighbour's data does NOT upgrade the tier. The analogy itself is the unproven
    assumption.

    Examples:
      legacy report speculate "Some New Card"
      legacy report speculate --new          # forecast every card in the latest diff
    """
    _setup_logging(verbose)

    if card_name is None and not all_new:
        raise click.ClickException(
            "Provide a card name (e.g. `legacy report speculate \"Card Name\"`) "
            "or use --new to forecast all cards from the latest diff."
        )

    from legacy_engine.analytics.match_results import compute_card_winrates
    from legacy_engine.analytics.speculation import speculate_card
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.scryfall import ScryfallClient

    con = store.connect(db) if db else store.connect()
    try:
        # Load the card pool from DuckDB (all existing cards as the analogue pool).
        pool_rows = con.execute(
            "SELECT name, mana_cost, cmc, type_line, colors, produced_mana, "
            "oracle_text, layout, power, toughness FROM cards"
        ).fetchall()
    finally:
        con.close()

    from legacy_engine.models.card import Card

    def _row_to_card(row) -> Card:
        name, mana_cost, cmc, type_line, colors_str, produced_str, oracle_text, layout, power, toughness = row
        return Card(
            name=name or "",
            mana_cost=mana_cost,
            cmc=float(cmc or 0),
            type_line=type_line or "",
            colors=list(colors_str) if colors_str else [],
            produced_mana=list(produced_str) if produced_str else [],
            oracle_text=oracle_text or "",
            layout=layout or "normal",
            power=power,
            toughness=toughness,
        )

    pool = [_row_to_card(row) for row in pool_rows]

    # Compute card win-rates (for the borrowed prior — read-only).
    con2 = store.connect(db) if db else store.connect()
    try:
        try:
            card_winrates = compute_card_winrates(con2)
        except Exception:
            card_winrates = None
    finally:
        con2.close()

    # Determine the list of cards to forecast.
    if all_new:
        # --new mode: read the persisted ingest diff; fall back with a clear message.
        diff = store.load_ingest_diff()
        if diff is None or not diff.new_names:
            click.echo(
                "// --new: no persisted diff found — run `legacy refresh cards` first.\n"
                "// Once you run refresh cards, speculate --new will operate on the actual new-cards set."
            )
            return
        click.echo(
            f"// --new: using {len(diff.new_names)} card(s) from the last `refresh cards` diff."
        )
        target_names = list(diff.new_names)
    else:
        target_names = [card_name]  # type: ignore[list-item]

    # Resolve target Card objects — first from pool, then from Scryfall if needed.
    pool_by_name = {c.name: c for c in pool}

    for name in target_names:
        # Try to find the card in the existing pool first; fall back to Scryfall lookup.
        target = pool_by_name.get(name)
        if target is None:
            try:
                with ScryfallClient() as client:
                    target = client.get_card(name)
            except Exception:
                target = None
        if target is None:
            # Build a minimal stub so we can still compute an intrinsic score.
            target = Card(name=name)

        forecast = speculate_card(target, pool, card_winrates, k=k, board=board)
        _print_speculation(forecast)


def _print_speculation(forecast: "SpeculativeForecast") -> None:
    """Render a SpeculativeForecast as a labeled, human-readable text report."""
    from legacy_engine.analytics.speculation import SpeculativeForecast  # noqa: F401

    click.echo(f"\n{'=' * 70}")
    click.echo(f"  {forecast.label}")
    click.echo(f"{'=' * 70}")
    click.echo(f"  Card:       {forecast.card}")
    click.echo(f"  Forecast:   {forecast.forecast:.3f}  (rough fused score: 0=low, 1=high Legacy value estimate)")
    click.echo(f"  Confidence: {forecast.confidence.level} / {forecast.confidence.source}")
    click.echo("")

    # Intrinsic breakdown
    bd = forecast.intrinsic.breakdown
    click.echo(f"  Intrinsic score:  {forecast.intrinsic.score:.3f}")
    click.echo(f"    cmc_band:       {bd.cmc_band:+.3f}")
    click.echo(f"    interaction:    {bd.interaction:+.3f}")
    click.echo(f"    role_match:     {bd.role_match:+.3f}")
    click.echo(f"    stat_eff:       {bd.stat_efficiency:+.3f}")

    # Analogues
    if forecast.analogues:
        click.echo(f"\n  Analogues (k={len(forecast.analogues)}, card-type filter applied):")
        click.echo(f"  {'Name':<35}  {'Sim':>5}  {'Lift':>7}  {'Tier':<12}")
        click.echo("  " + "-" * 65)
        for a in forecast.analogues:
            lift_str = f"{a.borrowed_lift:+.3f}" if a.borrowed_lift is not None else "n/a"
            tier_str = a.borrowed_tier or "—"
            click.echo(f"  {a.card:<35}  {a.similarity:>5.3f}  {lift_str:>7}  {tier_str:<12}")
    else:
        click.echo("\n  Analogues: none (no cards in the same type bucket or empty pool)")

    # Borrowed prior
    if forecast.borrowed_prior is not None:
        click.echo(f"\n  Borrowed prior (gated analogues):  {forecast.borrowed_prior:+.3f}")
    else:
        click.echo("\n  Borrowed prior: none (no established/evolving analogues — intrinsic only)")

    click.echo("")


# ---------------------------------------------------------------------------
# Deck-source resolution helper
# ---------------------------------------------------------------------------

def _my_deck_opt(f):
    """Attach --my-deck NAME to a command (complement to --deck FILE)."""
    return click.option(
        "--my-deck",
        "my_deck",
        default=None,
        help="Name of a saved UserDeck (alternative to --deck FILE).",
    )(f)


def _resolve_deck_boards(
    deck: str | None,
    my_deck: str | None,
    command_label: str = "this command",
) -> tuple[dict[str, int], dict[str, int]]:
    """Resolve ``--deck FILE`` or ``--my-deck NAME`` into ``(mainboard, sideboard)``.

    Mutual exclusion:
    - Both supplied → ClickException
    - Neither supplied → ClickException
    - ``--deck FILE`` only → read and parse the file (byte-identical to old path)
    - ``--my-deck NAME`` only → look up UserDeck, extract current_cards

    The function is gated-additive: when ``my_deck`` is None the file path is
    exercised identically to before this feature shipped.
    """
    from pathlib import Path

    from legacy_engine.advisory.report import _parse_decklist

    if deck is not None and my_deck is not None:
        raise click.ClickException(
            "--deck and --my-deck are mutually exclusive: supply one, not both."
        )
    if deck is None and my_deck is None:
        raise click.ClickException(
            f"{command_label} requires either --deck FILE or --my-deck NAME."
        )

    if my_deck is not None:
        from legacy_engine.collection.decks import current_cards
        from legacy_engine.collection.persist import find_deck_by_name

        found = find_deck_by_name(my_deck)
        if found is None:
            raise click.ClickException(
                f"No deck named {my_deck!r} found in your collection. "
                "Use `deck list` to see saved decks."
            )
        main, side = current_cards(found)
        return main, side

    # --deck FILE path: byte-identical to the pre-feature baseline.
    deck_text = Path(deck).read_text()  # type: ignore[arg-type]
    return _parse_decklist(deck_text)


# ── advise: meta attack / advisory ──
@main.group()
def advise() -> None:
    """Meta attack / advisory — how to attack the field."""


def _parse_lift_spec(spec: str | None) -> dict[str, float]:
    """Parse `--*-lift` "opp=+0.11,opp2=-0.03" → {opponent: delta}. Opp names may contain spaces."""
    out: dict[str, float] = {}
    if not spec:
        return out
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise click.ClickException(f"--lift entry {part!r} must be 'opponent=delta' (e.g. 'Death & Taxes=+0.11').")
        opp, val = part.rsplit("=", 1)
        try:
            out[opp.strip()] = float(val)
        except ValueError:
            raise click.ClickException(f"--lift delta {val!r} for {opp.strip()!r} is not a number.")
    return out


def _apply_slot_lifts(con, archetype: str, slot_specs: tuple[str, ...], lifts: dict[str, float], board: str) -> list[str]:
    """Merge slot-test-measured diffs ("Card@Opponent") into `lifts` (user-supplied wins). Returns notes."""
    from legacy_engine.advisory.compare import slot_lift

    notes: list[str] = []
    for spec in slot_specs:
        if "@" not in spec:
            raise click.ClickException(f"--lift-slot entry {spec!r} must be 'Card@Opponent'.")
        card, opp = spec.rsplit("@", 1)
        card, opp = card.strip(), opp.strip()
        measured = slot_lift(con, archetype, card, opp, board=board)
        if measured is None:
            notes.append(f"// lift-slot: no computable diff for {card!r} vs {opp!r} — skipped.")
            continue
        if opp in lifts:
            notes.append(f"// lift-slot: {card!r} vs {opp!r} measured {measured:+.3f}, but --lift override {lifts[opp]:+.3f} kept.")
        else:
            lifts[opp] = measured
            notes.append(f"// lift-slot: {card!r} vs {opp!r} → measured lift {measured:+.3f}.")
    return notes


def _echo_comparison(result) -> None:
    """Render a ComparisonResult: EV summary + per-matchup table + break-even + honesty banners."""
    a, b = result.a_label, result.b_label
    click.echo(f"\n=== Configuration comparison vs field (source={result.field_source}) ===")
    click.echo("// lifts are presence-correlational assumptions (point overlay), NOT in the MC base.")
    click.echo("// transform = max-over-modes per matchup — the optimistic ceiling (assumes you reach the better mode post-board).")

    ac_lo, ac_hi = result.ev_a_base_ci
    bc_lo, bc_hi = result.ev_b_base_ci
    click.echo("\n// base field EV (no lifts) [95% MC CI]:")
    click.echo(f"//   A {a!r}: {result.ev_a_base*100:5.1f}%  [{ac_lo*100:4.1f}, {ac_hi*100:4.1f}]")
    click.echo(f"//   B {b!r}: {result.ev_b_base*100:5.1f}%  [{bc_lo*100:4.1f}, {bc_hi*100:4.1f}]")
    click.echo(f"//   P(A beats B), base: {result.p_a_beats_b_base:.2f}  ({result.n_draws} draws)")
    if any(r.wr_a_adj != r.wr_a_base or r.wr_b_adj != r.wr_b_base for r in result.rows):
        click.echo(f"// adjusted field EV (with lifts):  A {result.ev_a_adj*100:5.1f}%   B {result.ev_b_adj*100:5.1f}%")

    click.echo(f"\n{'Opponent':<20}{'share':>6}  {'A (mode)':<28}{'B (mode)':<28}{'contrib':>8}")
    click.echo("-" * 92)

    def _cell(wr: float, mode: str, imputed: bool, n: int) -> str:
        # * = imputed (no data); ~ = thin (0<n<30, present-but-unreliable)
        mark = "*" if imputed else ("~" if n < 30 else "")
        return f"{wr*100:5.1f}% ({mode}{mark})"

    for r in result.rows:
        click.echo(
            f"{r.opponent:<20}{r.share*100:>5.1f}%  "
            f"{_cell(r.wr_a_adj, r.chosen_mode_a, r.imputed_a, r.n_a):<28}"
            f"{_cell(r.wr_b_adj, r.chosen_mode_b, r.imputed_b, r.n_b):<28}"
            f"{r.contribution_diff*100:>+7.1f}"
        )
    click.echo("// cell marks: * = imputed (no matchup data); ~ = thin (n<30, present-but-unreliable).")

    click.echo()
    if result.breakeven_lift is None:
        if result.ev_a_base >= result.ev_b_adj:
            click.echo("// break-even: A is already at/ahead of B on base EV — no sideboard lift needed.")
        else:
            click.echo("// break-even: A trails B but no target matchups declared — pass --a-lift or --break-even-matchups.")
    elif not result.breakeven_feasible:
        click.echo(
            f"// break-even: A's hate package would need +{result.breakeven_lift*100:.0f} pts on each of "
            f"{result.breakeven_targets} to tie B — NOT achievable within [0,100%]."
        )
    else:
        click.echo(
            f"// break-even: A's hate package must add +{result.breakeven_lift*100:.0f} pts to EACH of "
            f"{result.breakeven_targets} to tie B's EV."
        )
    click.echo(f"// matchup-data coverage: A={result.coverage_a:.0%}, B={result.coverage_b:.0%}  (* = imputed cell)")
    for w in result.warnings:
        click.echo(f"// warning: {w}")


@advise.command("compare")
@click.option("--field", "field_file", type=click.Path(exists=True, dir_okay=False), default=None,
              help="Custom field file (<share> <archetype> lines); recommended for a meaningful comparison.")
@click.option("--a", "arch_a", default=None, help="Config A primary archetype (required).")
@click.option("--b", "arch_b", default=None, help="Config B primary archetype (required).")
@click.option("--a-transform", "a_transform", default=None, help="Add a transform mode to Config A (per-matchup max).")
@click.option("--b-transform", "b_transform", default=None, help="Add a transform mode to Config B (per-matchup max).")
@click.option("--a-lift", "a_lift", default=None, help="Config A SB lifts: 'opp=+0.11,opp2=-0.03'.")
@click.option("--b-lift", "b_lift", default=None, help="Config B SB lifts.")
@click.option("--a-lift-slot", "a_lift_slot", multiple=True, help="Pull a measured lift for Config A: 'Card@Opponent' (repeatable).")
@click.option("--b-lift-slot", "b_lift_slot", multiple=True, help="Pull a measured lift for Config B: 'Card@Opponent' (repeatable).")
@click.option("--break-even-matchups", "be_matchups", default=None, help="Comma-separated opponents the break-even lift spreads over (default: A's declared-lift matchups).")
@click.option("--board", default="side", show_default=True, help="Board for --*-lift-slot pulls.")
@click.option("--seed", type=int, default=None, help="RNG seed for deterministic MC.")
@click.option("--db", type=click.Path(exists=True, dir_okay=False), default=None, help="DuckDB path (defaults to project default).")
@_provenance_opt
@_window_opts
@_verbose
def advise_compare(
    field_file: str | None, arch_a: str | None, arch_b: str | None,
    a_transform: str | None, b_transform: str | None,
    a_lift: str | None, b_lift: str | None,
    a_lift_slot: tuple[str, ...], b_lift_slot: tuple[str, ...],
    be_matchups: str | None, board: str, seed: int | None, db: str | None,
    provenance: str | None, since: str | None, until: str | None, regime: str | None,
    all_time: bool, verbose: bool,
) -> None:
    """Compare two deck configurations (incl. transform-alternates) across the field.

    A "config" is one or more modes; its per-opponent win-rate is the max over modes. A plain deck
    with a hate sideboard is one mode + --a-lift; a transform-alternate is --a + --a-transform.
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.compare import ConfigMode, DeckConfig, compare_configs
    from legacy_engine.advisory.report import _load_field
    from legacy_engine.advisory.window import build_advisory_inputs, resolve_advisory_window
    from legacy_engine.ingestion import store

    if not arch_a or not arch_b:
        raise click.ClickException("advise compare requires both --a and --b (the two configs' primary archetypes).")

    field_text = Path(field_file).read_text() if field_file else None
    if provenance is not None:
        click.echo(f"// provenance: {provenance}")

    con = store.connect(db) if db else store.connect()
    try:
        win = resolve_advisory_window(con, regime=regime, since=since, until=until, all_time=all_time, provenance=provenance)
        _echo_window(win)
        inputs = build_advisory_inputs(con, win, provenance=provenance)
        for line in inputs.audit:
            click.echo(line)
        matrix = inputs.matrix
        field_provenance = None if field_text is not None else provenance
        field = _load_field(con, field_text=field_text, provenance=field_provenance, since=inputs.field_since, until=inputs.field_until)

        lifts_a = _parse_lift_spec(a_lift)
        lifts_b = _parse_lift_spec(b_lift)
        slot_notes = _apply_slot_lifts(con, arch_a, a_lift_slot, lifts_a, board)
        slot_notes += _apply_slot_lifts(con, arch_b, b_lift_slot, lifts_b, board)
        for note in slot_notes:
            click.echo(note)

        # Fail-fast: a declared lift opponent must be in the field.
        for opp in {*lifts_a, *lifts_b}:
            if opp not in field.shares:
                raise click.ClickException(f"lift opponent {opp!r} is not in the field — check spelling / --field.")

        config_a = DeckConfig(arch_a, [ConfigMode(arch_a, lifts_a)] + ([ConfigMode(a_transform)] if a_transform else []))
        config_b = DeckConfig(arch_b, [ConfigMode(arch_b, lifts_b)] + ([ConfigMode(b_transform)] if b_transform else []))
        be_targets = [t.strip() for t in be_matchups.split(",") if t.strip()] if be_matchups else None

        result = compare_configs(matrix, field, config_a, config_b, seed=seed, breakeven_targets=be_targets)
        _echo_comparison(result)
    finally:
        con.close()


@advise.command("positioning")
@click.option(
    "--deck",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a plain-text decklist file.",
)
@_my_deck_opt
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
    "--list-granular",
    "list_granular",
    is_flag=True,
    default=False,
    help=(
        "[EXPERIMENTAL] Show a list-granular S_granular score alongside archetype S. "
        "Nudges per-matchup win-rates by the deck's card composition vs the archetype baseline "
        "(presence-correlational heuristic — NOT causal precision). "
        "Caveat is always shown. Default OFF; archetype S is byte-identical when absent."
    ),
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_provenance_opt
@_window_opts
@_verbose
def advise_positioning(
    deck: str | None,
    my_deck: str | None,
    archetype: str | None,
    field_file: str | None,
    candidates_file: str | None,
    reserved: int,
    seed: int | None,
    list_granular: bool,
    db: str | None,
    provenance: str | None,
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
    from legacy_engine.advisory.report import _classify_deck, _load_field
    from legacy_engine.advisory.window import build_advisory_inputs, resolve_advisory_window
    from legacy_engine.ingestion import store

    mainboard, sideboard_cards = _resolve_deck_boards(deck, my_deck, "advise positioning")
    field_text = Path(field_file).read_text() if field_file else None

    if provenance is not None:
        click.echo(f"// provenance: {provenance}")

    con = store.connect(db) if db else store.connect()
    try:
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time, provenance=provenance,
        )
        _echo_window(win)
        inputs = build_advisory_inputs(con, win, provenance=provenance)
        for line in inputs.audit:
            click.echo(line)
        matrix = inputs.matrix
        # When --field is supplied, the custom field is used as-is; provenance only filtered
        # the matchup matrix above. When --field is absent, provenance narrows the global field.
        field_provenance = None if field_text is not None else provenance
        field = _load_field(con, field_text=field_text, provenance=field_provenance, since=inputs.field_since, until=inputs.field_until)

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
                # Label S as full-field when the deck would be restricted in the single-deck
                # view — keeps the ranking path consistent with advise positioning output.
                s_label = "S*" if d in ranking.coverage_caveated else "S"
                # Suppress P(best) when coverage ≈ 0 — the value is imputation noise that
                # otherwise reads as a spuriously confident ranking signal.
                if cov < _PBEST_SUPPRESS_COVERAGE:
                    pbest_str = "P(best)=n/a [cov≈0]"
                else:
                    pbest_str = f"P(best)={ranking.p_best[d]:.3f}"
                click.echo(
                    f"  {d:<35}  {s_label}={ranking.s_mean[d]:.3f}  "
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

            # ── List-granular overlay (OPT-IN via --list-granular) ───────────
            # Default OFF: this block is completely skipped when the flag is absent,
            # keeping the output byte-identical to the pre-flag baseline.
            if list_granular:
                _render_list_granular(
                    con, mainboard, matrix, field, resolved_archetype, seed=seed,
                    provenance=provenance, field_since=inputs.field_since, field_until=inputs.field_until,
                )
    finally:
        con.close()


def _render_list_granular(
    con,
    mainboard: dict[str, int],
    matrix,
    field,
    deck_archetype: str,
    *,
    seed: int | None,
    provenance: str | None,
    field_since: str | None,
    field_until: str | None,
) -> None:
    """Compute and render the list-granular S_granular overlay.

    Called ONLY when ``--list-granular`` is set.  The default ``advise positioning``
    path is completely unaffected (byte-identical) when this function is not called.

    Live-plumbing: resolves ``CardWinRates`` from the LIVE corpus using the SAME
    window the positioning path uses (``field_since``/``field_until``) so the card-
    lift signals are consistent with the matchup matrix.  Filters lands from
    ``mainboard`` before passing to ``positioning_score_granular`` (lands carry no
    matchup lift and would dilute the signal).
    """
    from legacy_engine.advisory.positioning import (
        GRANULAR_CAVEAT,
        filter_nonland_cards,
        positioning_score_granular,
    )
    from legacy_engine.analytics.match_results import compute_card_winrates
    from legacy_engine.ingestion.store import fetch_card

    # ── Resolve CardWinRates from the live corpus ───────────────────────────
    # Honor the same window as the positioning path (field_since/field_until);
    # pass provenance through for consistency with the matchup matrix.
    card_win_rates = compute_card_winrates(
        con,
        provenance=provenance,
        since=field_since,
        until=field_until,
    )

    # ── Filter lands out of mainboard ───────────────────────────────────────
    # Lands carry no meaningful matchup lift signal; including them would dilute
    # the composition signal by increasing the denominator without contributing lift.
    # Unknown cards (not in DB) are kept (conservative: unknown ≠ definitely land).
    def _is_land(name: str) -> bool:
        row = fetch_card(con, name)
        if row is None:
            return False
        return bool(row.get("is_land", False))

    nonland_main = filter_nonland_cards(mainboard, _is_land)

    # ── Compute granular positioning ─────────────────────────────────────────
    gr = positioning_score_granular(
        matrix, field, deck_archetype, nonland_main, card_win_rates,
        seed=seed,
    )

    # ── Render (caveat always shown — honesty contract) ──────────────────────
    # The audit line uses the `//` convention so it's clearly metadata, not a stat.
    click.echo("")
    click.echo(f"// {GRANULAR_CAVEAT}")
    click.echo(f"  S_granular (list-granular, experimental): {gr.s_granular:.3f}")
    click.echo(f"  S (archetype-level, baseline):            {gr.base.s_mean:.3f}")
    delta = gr.s_granular - gr.base.s_mean
    sign = "+" if delta >= 0 else ""
    click.echo(f"  delta (S_granular − S):                  {sign}{delta:.3f}")
    n_nonland = sum(nonland_main.values())
    n_total = sum(mainboard.values())
    n_lands = n_total - n_nonland
    click.echo(
        f"  Deck composition: {n_nonland} nonland cards used for lift signal"
        + (f" ({n_lands} land(s) excluded)" if n_lands > 0 else "")
    )


@advise.command("sideboard")
@click.option(
    "--deck",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a plain-text decklist file.",
)
@_my_deck_opt
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
    "--collection",
    "collection_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a plain-text collection file (<qty> <card name> lines). "
         "Enables owned/acquire annotations on each recommendation. "
         "When omitted, output is byte-identical to pre-collection behavior.",
)
@click.option(
    "--owned-only",
    is_flag=True,
    default=False,
    help="Only show cards the user already owns (requires --collection). "
         "Suppresses the acquire-list, prints count of suppressed cards.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@click.option(
    "--smart/--no-smart",
    "smart",
    default=False,
    help="Smart sideboard (epic-sideboard-core-and-hedge): stop padding the 15 with redundant "
         "copies — commit a dedicated core sized to the field (may return <15), surface the "
         "coverage curve + uncovered field. Off by default (byte-identical to the forced-15 model).",
)
@click.option(
    "--redundancy-strength",
    type=float,
    default=0.0,
    help="Absolute per-copy redundancy penalty strength (power-user override; 0 = none). "
         "With --smart, a field-scaled default is used unless this is set non-zero.",
)
@click.option(
    "--tau",
    type=float,
    default=0.0,
    help="Absolute natural-budget floor τ (power-user override; 0 = fill the budget). "
         "With --smart, a field-scaled default is used unless this is set non-zero.",
)
@_provenance_opt
@_window_opts
@_verbose
def advise_sideboard(
    deck: str | None,
    my_deck: str | None,
    archetype: str | None,
    field_file: str | None,
    reserved: int,
    solver: str,
    collection_file: str | None,
    owned_only: bool,
    db: str | None,
    smart: bool,
    redundancy_strength: float,
    tau: float,
    provenance: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Recommend a sideboard package for an expected field."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import _classify_deck, _load_field
    from legacy_engine.advisory.sideboard import recommend_sideboard
    from legacy_engine.advisory.window import resolve_advisory_window
    from legacy_engine.ingestion import store

    mainboard, _sideboard_cards = _resolve_deck_boards(deck, my_deck, "advise sideboard")
    field_text = Path(field_file).read_text() if field_file else None

    # Load collection view (gated: None when --collection not provided).
    cv = None
    if collection_file:
        from legacy_engine.advisory.collection import CollectionView
        cv = CollectionView.from_text(Path(collection_file).read_text())
        click.echo(f"// collection: {cv}")

    if owned_only and cv is None:
        raise click.ClickException("--owned-only requires --collection")

    if provenance is not None:
        click.echo(f"// provenance: {provenance}")

    con = store.connect(db) if db else store.connect()
    try:
        # Resolve window. Sideboard plans default to adaptive (per-opponent ban-aware);
        # uniform/full modes disable adaptive and use the resolved since/until instead.
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time, provenance=provenance,
        )
        _echo_window(win)

        # Determine whether to use adaptive per-opponent windows.
        use_adaptive = win.mode == "adaptive"
        plan_since = win.since
        plan_until = win.until

        # When --field is supplied, the custom field is used as-is; provenance only affects
        # the window's thinness check above. When --field is absent, provenance narrows the field.
        field_provenance = None if field_text is not None else provenance
        field = _load_field(con, field_text=field_text, provenance=field_provenance)

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
            collection=cv,
            smart=smart,
            redundancy_strength=redundancy_strength,
            tau=tau,
            hedge="expected" if smart else "off",
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

        # --- Output contract (epic-sideboard-core-and-hedge-output-contract) ---
        # Honest-degrade core+hedge surface: the natural dedicated budget, the marginal-coverage
        # curve (its flattening = the knee), and the uncovered-field tail. Printed only when the
        # core behavior is active; the forced-budget baseline (natural_budget_count is None)
        # renders byte-identically to before.
        if pkg.natural_budget_count is not None:
            click.echo(
                f"  // natural budget: {pkg.natural_budget_count}/{pkg.budget} dedicated "
                f"(remaining slots left flexible, not padded)"
            )
            if pkg.marginal_curve:
                curve_str = "  ".join(f"{n}:{w:.3f}" for n, w in pkg.marginal_curve)
                click.echo(f"  // coverage curve (cards:cumulative value): {curve_str}")
            if pkg.uncovered_tail:
                tail_str = ", ".join(f"{e} ({w:.3f})" for e, w in pkg.uncovered_tail)
                click.echo(f"  // uncovered field (top, by weight): {tail_str}")
            if pkg.insurance_cards:
                click.echo(f"  // insurance (hedge) slots: {', '.join(sorted(pkg.insurance_cards))}")

        # Render cards (with owned annotations when collection is wired).
        display_cards = pkg.cards
        suppressed_count = 0
        if owned_only and cv is not None:
            from legacy_engine.advisory.acquire import split_recommendation
            play_owned, acquire = split_recommendation(pkg.cards, cv)
            display_cards = play_owned
            suppressed_count = len(acquire)

        if display_cards:
            for card, copies in sorted(display_cards.items(), key=lambda kv: kv[1], reverse=True):
                # commit (dedicated core) vs insurance (hedge) label — only when the hedge ran.
                role = " [insurance]" if card in pkg.insurance_cards else ""
                if pkg.collection_aware and pkg.owned:
                    ann = pkg.owned.get(card)
                    if ann is not None:
                        status = "owned" if ann.owned else f"acquire {ann.to_acquire}"
                        click.echo(f"  {copies}x {card}  [{status}]{role}")
                    else:
                        click.echo(f"  {copies}x {card}{role}")
                else:
                    click.echo(f"  {copies}x {card}{role}")
        else:
            click.echo("  (no recommendations — no castable hosers for this deck's colors)")

        if owned_only and suppressed_count > 0:
            click.echo(f"  [--owned-only: {suppressed_count} acquire-card(s) suppressed]")

        # --- Coverage% diagnostic (feature-sb-field-weighted-scorer-output, Unit B5) ---
        # Locked decision (parent feature § "Design decisions"): coverage% is a DIAGNOSTIC —
        # the share of the field a card/board is meaningfully relevant against — never the
        # optimization objective (that's Σ field_share × Δequity, computed elsewhere). Always
        # rendered when cards were recommended; independent of whether impact data is present.
        if display_cards and pkg.card_coverage_pct:
            click.echo(
                "  // coverage diagnostic — NOT the optimization objective "
                "(field-share relevance, not a measured win-rate lift):"
            )
            for card, _copies in sorted(display_cards.items(), key=lambda kv: kv[1], reverse=True):
                cov = pkg.card_coverage_pct.get(card)
                if cov is not None:
                    click.echo(f"    // {card}: ~{cov:.0%} of field")
            click.echo(
                f"  // board coverage diagnostic: ~{pkg.board_coverage_pct:.0%} of field "
                "addressed by this board (union across cards, not additive)"
            )

        # --- Explainable per-card impact breakdown + field-share uncertainty (Unit B5) ---
        # Empty pkg.impact_annotations = no-impact-data path (opponent_linchpins was None) —
        # nothing rendered, never a fabricated breakdown. confidence/brittle reuse `advise
        # positioning`'s Dirichlet field-share machinery (honest-degrade: a thin/uncovered
        # matchup is labeled, never silently treated as solid).
        if display_cards and pkg.impact_annotations:
            click.echo("  // impact breakdown (auditable factors — see advisory/impact.py):")
            for card, _copies in sorted(display_cards.items(), key=lambda kv: kv[1], reverse=True):
                ann = pkg.impact_annotations.get(card)
                if ann is None:
                    continue
                b = ann.breakdown
                confidence_label = ann.confidence if ann.confidence is not None else "no-data"
                brittle_note = (
                    "  [BRITTLE — thin-sample matchup, don't over-commit a silver bullet]"
                    if ann.brittle
                    else ""
                )
                click.echo(
                    f"    // {card} vs {ann.reference_archetype} ({ann.reference_share:.1%} share): "
                    f"centrality={b.centrality:.2f} symmetry={b.symmetry:.2f} "
                    f"castability={b.castability:.2f} draw={b.draw_prob:.2f} "
                    f"→ impact={b.score():.3f}  [confidence={confidence_label}]{brittle_note}"
                )

        click.echo(f"  Note: {pkg.heuristic_note}")
        for w in pkg.warnings:
            click.echo(f"  [warn] {w}")

        # --- Considering pool (flex / meta-call alternatives on the bubble) ---
        if pkg.considering:
            click.echo("\nConsidering (flex / meta-call alternatives):")
            for cc in pkg.considering:
                promo_tag = "  [empirical]" if cc.promoted else ""
                click.echo(
                    f"  {cc.card}  [gain={cc.marginal_gain:.4f}]{promo_tag}"
                    f"  — {cc.label}"
                )

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

        # --- Slot-ROI + punt table (feature-sb-slot-roi-punt, Units D1+D2+D3) ---
        # DECISION SUPPORT ONLY: ranks field matchups by expected match-win per dedicated
        # slot (marginal equity gain × field share) and flags matchups where investment
        # doesn't pay — either because max realistic dedication still can't cross 50%, or
        # because the same slot buys more expected wins elsewhere. Does NOT change which
        # cards were picked above (see `_slot_roi_table`'s module docstring); a hard rule
        # never punts a speculative-tier (thin/absent-data) matchup — it is labeled
        # low-confidence instead.
        if pkg.slot_roi:
            click.echo(
                "\n  // slot-ROI (decision support — expected match-win per dedicated slot):"
            )
            for roi in pkg.slot_roi:
                confidence_label = roi.confidence if roi.confidence is not None else "no-data"
                punt_marker = f"  [PUNT — {roi.punt_reason}]" if roi.punt else ""
                click.echo(
                    f"    // vs {roi.opponent} ({roi.field_share:.1%} share): "
                    f"{roi.base_equity:.1%} → {roi.base_equity + roi.max_equity_gain:.1%} equity  "
                    f"ROI/slot={roi.roi_per_slot:.4f}  [confidence={confidence_label}]{punt_marker}"
                )
    finally:
        con.close()


@advise.command("backtest")
@click.option(
    "--archetype",
    required=True,
    help="Archetype to backtest: the scorer's recommendation vs top-finisher boards.",
)
@click.option(
    "--field",
    "field_file",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to a field file (<share> <archetype> lines) — the field to score "
         "the recommended board against.",
)
@click.option("--since", default=None, help="Window start (ISO date, inclusive).")
@click.option("--until", default=None, help="Window end (ISO date, exclusive).")
@click.option(
    "--field-scope/--no-field-scope",
    "field_scope",
    default=True,
    help="Restrict the top-finisher sample to tournaments whose own metagame overlaps "
         "--field's archetypes (excludes off-meta events, e.g. graveyard-heavy tech vs a "
         "Boulder field). On by default; --no-field-scope reproduces the prior global sample.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def advise_backtest(
    archetype: str,
    field_file: str,
    since: str | None,
    until: str | None,
    field_scope: bool,
    db: str | None,
    verbose: bool,
) -> None:
    """Backtest the scorer's recommended sideboard against what top-finishers actually ran.

    The empirical anchor for the sideboard scoring model: compares `recommend_sideboard`'s
    output for ARCHETYPE + FIELD against the sideboards top-finishing ARCHETYPE decks
    actually ran in the window. Never a pass/fail verdict — see the caveat line below.
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.backtest import (
        _FIELD_OVERLAP_MIN,
        _OBSERVED_THRESHOLD,
        backtest_board,
    )
    from legacy_engine.advisory.report import _load_field
    from legacy_engine.ingestion import store

    field_text = Path(field_file).read_text()

    con = store.connect(db) if db else store.connect()
    try:
        field = _load_field(con, field_text=field_text)
        result = backtest_board(con, archetype, field, since=since, until=until, field_scope=field_scope)

        click.echo(f"// backtest: {result.archetype}")
        click.echo(f"// window: since={since or 'earliest'} until={until or 'latest'}")
        if result.field_scope:
            click.echo(
                f"// field-scope: ON (candidate tournaments must be >= {_FIELD_OVERLAP_MIN:.0%} "
                f"archetypes present in --field) — {result.n_tournaments_excluded}/"
                f"{result.n_tournaments_considered} candidate tournaments excluded as off-field"
            )
        else:
            click.echo(
                "// field-scope: OFF (--no-field-scope) — comparing against the full "
                "global top-finisher sample, unfiltered by field composition"
            )
        click.echo(f"// top-finisher decks sampled: {result.n_winning_decks}")

        if result.confidence is None:
            if result.field_scope and result.n_tournaments_considered > 0:
                click.echo(
                    "// HONEST DEGRADE: field-scope excluded all "
                    f"{result.n_tournaments_considered} candidate tournament(s) as off-field — "
                    "no top-finisher decks remain to compare against. Try --no-field-scope or a "
                    "broader --field to diagnose."
                )
            else:
                click.echo(
                    "// HONEST DEGRADE: no top-finisher decks found for this archetype/window — "
                    "insufficient data, no comparison possible."
                )
        else:
            click.echo(f"// confidence: {result.confidence}")
            if result.confidence == "speculative":
                click.echo(
                    f"// HONEST DEGRADE: thin winner sample (n={result.n_winning_decks}) — "
                    "treat findings below as low-confidence."
                )

        def _render_group(title: str, cards: tuple[str, ...]) -> None:
            click.echo(f"\n{title} ({len(cards)}):")
            if not cards:
                click.echo("  (none)")
                return
            for card in cards:
                pct = result.observed_frequency.get(card, 0.0)
                click.echo(f"  {card:<32} observed {pct * 100:5.1f}%")

        click.echo(f"\nRecommended board ({len(result.recommended)} cards):")
        if not result.recommended:
            click.echo("  (none — scorer produced no recommendation for this archetype/field)")
        for card in result.recommended:
            pct = result.observed_frequency.get(card, 0.0)
            click.echo(f"  {card:<32} observed {pct * 100:5.1f}%")

        _render_group(
            f"Overlap — recommended AND commonly played (>= {_OBSERVED_THRESHOLD:.0%})",
            result.overlap,
        )
        _render_group(
            "Scorer-only — recommended but rarely/never played (candidate false positives)",
            result.scorer_only,
        )
        _render_group(
            "Winners-only — commonly played but not recommended (candidate blind spots)",
            result.winners_only,
        )

        n_rec = len(result.recommended)
        agreement_pct = (len(result.overlap) / n_rec * 100.0) if n_rec else 0.0
        click.echo(
            f"\n// agreement: {len(result.overlap)}/{n_rec} recommended cards "
            f"({agreement_pct:.0f}%) match observed top-finisher boards"
        )
        click.echo(
            "// divergence is a signal to investigate, not proof of error "
            "(winning boards are self-selected + metagame-lagged)"
        )
    finally:
        con.close()


@advise.command("sweep")
@click.option(
    "--field",
    "field_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a field file (<share> <archetype> lines). Default: the global field "
         "over the sweep window.",
)
@click.option("--since", default=None, help="Window start (ISO date, inclusive).")
@click.option("--until", default=None, help="Window end (ISO date, exclusive).")
@click.option(
    "--min-decks",
    type=int,
    default=20,
    show_default=True,
    help="Minimum in-window deck count for an archetype to be swept (smaller ones are "
         "listed as skipped, not silently dropped).",
)
@click.option(
    "--field-scope/--no-field-scope",
    "field_scope",
    default=True,
    help="Restrict each archetype's top-finisher sample to tournaments whose own metagame "
         "overlaps the field (same filter as `advise backtest`). On by default.",
)
@click.option(
    "--solver",
    type=click.Choice(["ilp", "greedy"]),
    default="ilp",
    show_default=True,
    help="Sideboard solver to backtest. `greedy` is the deterministic fallback and useful "
         "for solver-vs-solver copy-distribution comparison.",
)
@click.option(
    "--json",
    "json_path",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Also write the full machine-readable payload (per-archetype groups, frequencies, "
         "copy-count histograms, solver copies, clusters) to this path.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def advise_sweep(
    field_file: str | None,
    since: str | None,
    until: str | None,
    min_decks: int,
    field_scope: bool,
    solver: str,
    json_path: str | None,
    db: str | None,
    verbose: bool,
) -> None:
    """Backtest EVERY archetype's recommended board and mine divergences, ranked + clustered.

    Batch driver over `advise backtest`: for each archetype with enough in-window corpus,
    compare the scorer's recommendation against that archetype's top-finisher boards, then
    aggregate divergences across archetypes into root-cause clusters (by the vulnerability
    tag a card answers). A card that is winners-only across MANY archetypes is a systematic
    scorer gap; per-deck noise stays per-deck. Divergence is a diagnostic to investigate,
    never proof of error and never auto-calibration into scores.
    """
    _setup_logging(verbose)
    import json as json_mod
    from pathlib import Path

    from legacy_engine.advisory.backtest import _OBSERVED_THRESHOLD
    from legacy_engine.advisory.field import build_global_field
    from legacy_engine.advisory.report import _load_field
    from legacy_engine.advisory.sweep import (
        ArchetypeSweepEntry,
        run_sweep,
    )
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        # Window: explicit flags win; both-unset resolves to the current ban regime
        # (echoed below) — the sweep is a current-meta diagnostic by default, unlike the
        # deliberately unwindowed single-archetype backtest. Deliberately NOT era-windowed:
        # the sweep batches EVERY archetype against ONE shared field window; per-entity era
        # windows would give each backtest a different basis and break cross-archetype
        # comparability (epic-stable-era-windows-consumption Unit 4 decision).
        eff_since, eff_until = since, until
        window_label = "explicit"
        if eff_since is None and eff_until is None:
            from legacy_engine.generation.consensus import _latest_regime_window
            eff_since, eff_until = _latest_regime_window()
            window_label = "current regime (default)"

        if field_file is not None:
            field = _load_field(con, field_text=Path(field_file).read_text())
        else:
            field = build_global_field(con, since=eff_since, until=eff_until)

        click.echo("// sweep: archetype-sweep backtest (batch divergence mining)")
        click.echo(
            f"// window: since={eff_since or 'earliest'} until={eff_until or 'latest'} "
            f"[{window_label}]"
        )
        click.echo(
            f"// field: {field.field_source} ({len(field.shares)} archetypes) — "
            f"field-scope {'ON' if field_scope else 'OFF'}, solver={solver}, "
            f"min-decks={min_decks}"
        )

        def _progress(i: int, total: int, entry: ArchetypeSweepEntry) -> None:
            if entry.backtest is None:
                click.echo(
                    f"// [{i}/{total}] {entry.archetype}: SKIPPED — {entry.skipped_reason}"
                )
                return
            bt = entry.backtest
            tier = bt.confidence if bt.confidence is not None else "no winner sample"
            click.echo(
                f"// [{i}/{total}] {entry.archetype}: winners n={bt.n_winning_decks} "
                f"({tier}) — {len(bt.scorer_only)} scorer-only, "
                f"{len(bt.winners_only)} winners-only"
            )

        result = run_sweep(
            con, field,
            since=eff_since, until=eff_until,
            min_decks=min_decks, field_scope=field_scope, solver=solver,
            progress=_progress,
        )

        swept = [e for e in result.entries if e.backtest is not None]
        skipped = [e for e in result.entries if e.backtest is None]
        click.echo(
            f"// swept {len(swept)} archetypes ({len(skipped)} skipped); "
            f"{len(result.clusters)} divergence clusters"
        )
        for w in result.warnings:
            click.echo(f"// WARNING: {w}")

        def _render_clusters(direction: str, title: str) -> None:
            group = [c for c in result.clusters if c.direction == direction]
            click.echo(f"\n{title} ({len(group)} clusters):")
            if not group:
                click.echo("  (none)")
                return
            for rank, c in enumerate(group, start=1):
                tiers = ", ".join(f"{n} {t}" for t, n in sorted(c.tier_breakdown.items()))
                thin = "" if c.n_archetypes_nonspeculative > 0 else "  [THIN: speculative-tier support only]"
                click.echo(
                    f"  {rank}. {c.tag} — {c.n_archetypes} archetype(s) ({tiers}), "
                    f"Σ adoption {c.total_adoption * 100:.0f}%{thin}"
                )
                by_card: dict[str, list] = {}
                for m in c.members:
                    by_card.setdefault(m.card, []).append(m)
                for card, ms in sorted(
                    by_card.items(), key=lambda kv: -sum(m.adoption_pct for m in kv[1])
                ):
                    archs = ", ".join(
                        f"{m.archetype} {m.adoption_pct * 100:.0f}%" if m.adoption_pct
                        else m.archetype
                        for m in ms
                    )
                    click.echo(f"       {card:<28} {len(ms)} archetype(s): {archs}")

        _render_clusters(
            "winners_only",
            f"Winners-only clusters — commonly played (>= {_OBSERVED_THRESHOLD:.0%}) but "
            "not recommended (candidate blind spots)",
        )
        _render_clusters(
            "scorer_only",
            "Scorer-only clusters — recommended but rarely/never played "
            "(candidate false positives)",
        )

        substrate_candidates = [
            c for c in result.clusters if c.n_archetypes_nonspeculative > 0
        ][:6]
        click.echo("\nSubstrate-ready findings (top clusters with non-thin support):")
        if not substrate_candidates:
            click.echo("  (none — every cluster is speculative-tier only)")
        for c in substrate_candidates:
            cards_preview = ", ".join(sorted({m.card for m in c.members})[:5])
            click.echo(
                f"  - [{c.direction}] {c.tag}: {c.n_archetypes} archetype(s), "
                f"{c.n_archetypes_nonspeculative} non-speculative — e.g. {cards_preview}"
            )

        click.echo(
            "\n// divergence is a signal to investigate, not proof of error "
            "(winning boards are self-selected + metagame-lagged)"
        )

        if json_path is not None:
            payload = {
                "window": {"since": result.window[0], "until": result.window[1]},
                "field_source": result.field_source,
                "field_scope": result.field_scope,
                "solver": result.solver,
                "min_decks": result.min_decks,
                "observed_threshold": _OBSERVED_THRESHOLD,
                "archetypes": [
                    {
                        "archetype": e.archetype,
                        "n_decks_in_window": e.n_decks_in_window,
                        "skipped_reason": e.skipped_reason,
                        **(
                            {
                                "n_winning_decks": e.backtest.n_winning_decks,
                                "confidence": e.backtest.confidence,
                                "n_tournaments_considered": e.backtest.n_tournaments_considered,
                                "n_tournaments_excluded": e.backtest.n_tournaments_excluded,
                                "recommended_counts": e.backtest.recommended_counts,
                                "observed_frequency": e.backtest.observed_frequency,
                                "observed_copy_distribution": {
                                    card: {str(k): v for k, v in hist.items()}
                                    for card, hist in e.backtest.observed_copy_distribution.items()
                                },
                                "overlap": list(e.backtest.overlap),
                                "scorer_only": list(e.backtest.scorer_only),
                                "winners_only": list(e.backtest.winners_only),
                            }
                            if e.backtest is not None
                            else {}
                        ),
                    }
                    for e in result.entries
                ],
                "clusters": [
                    {
                        "tag": c.tag,
                        "direction": c.direction,
                        "n_archetypes": c.n_archetypes,
                        "n_archetypes_nonspeculative": c.n_archetypes_nonspeculative,
                        "total_adoption": c.total_adoption,
                        "tier_breakdown": c.tier_breakdown,
                        "members": [
                            {
                                "card": m.card,
                                "archetype": m.archetype,
                                "adoption_pct": m.adoption_pct,
                                "confidence": m.confidence,
                            }
                            for m in c.members
                        ],
                    }
                    for c in result.clusters
                ],
                "warnings": list(result.warnings),
            }
            Path(json_path).parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, "w") as fh:
                json_mod.dump(payload, fh, indent=2, sort_keys=True)
            click.echo(f"// json payload written: {json_path}")
    finally:
        con.close()


@advise.command("whattoplay")
@click.option(
    "--deck",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a plain-text decklist file.",
)
@_my_deck_opt
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
@_provenance_opt
@_window_opts
@_verbose
def advise_whattoplay(
    deck: str | None,
    my_deck: str | None,
    archetype: str | None,
    field_file: str | None,
    db: str | None,
    seed: int | None,
    provenance: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Field read and deck recommendation."""
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import _classify_deck, _load_field, _render_whattoplay
    from legacy_engine.advisory.whattoplay import proactivity_score, vulnerability_tags_for_deck
    from legacy_engine.advisory.window import build_advisory_inputs, resolve_advisory_window
    from legacy_engine.ingestion import store

    mainboard, sideboard_cards = _resolve_deck_boards(deck, my_deck, "advise whattoplay")
    field_text = Path(field_file).read_text() if field_file else None

    if provenance is not None:
        click.echo(f"// provenance: {provenance}")

    con = store.connect(db) if db else store.connect()
    try:
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time, provenance=provenance,
        )
        _echo_window(win)
        inputs = build_advisory_inputs(con, win, provenance=provenance)
        for line in inputs.audit:
            click.echo(line)
        field_provenance = None if field_text is not None else provenance
        field = _load_field(con, field_text=field_text, provenance=field_provenance, since=inputs.field_since, until=inputs.field_until)

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


@advise.command("field")
@click.option(
    "--field",
    "field_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a custom field file (<share> <archetype> lines). "
         "Absent → global corpus field (optionally filtered by --provenance/window opts).",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_provenance_opt
@_window_opts
@_verbose
def advise_field(
    field_file: str | None,
    db: str | None,
    provenance: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Field composition + vulnerability/hate-equity profile — no deck required.

    Prints the expected field (archetype shares) and the field's vulnerability
    profile (which vulnerability tags the field carries and what share each tag
    attacks), without requiring a player deck.  Useful for quickly understanding
    the field composition and its structural weaknesses before building a deck.

    Sources (in priority order):
      1. ``--field <file>``  — user-supplied archetype shares
      2. ``--provenance online|paper`` — corpus filtered to that venue
      3. No flags — full global corpus field

    Window opts (``--since``/``--until``/``--regime``/``--all-time``) narrow the
    global field time window.  When ``--field`` is supplied the window is ignored
    for the field itself (custom fields have no time axis) but still filters any
    downstream matchup data.
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.report import _load_field
    from legacy_engine.advisory.whattoplay import field_vulnerability_tags, hate_equity
    from legacy_engine.advisory.window import resolve_advisory_window
    from legacy_engine.ingestion import store

    field_text = Path(field_file).read_text() if field_file else None

    if provenance is not None:
        click.echo(f"// provenance: {provenance}")

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con, provenance=provenance)
        win = resolve_advisory_window(
            con,
            regime=regime,
            since=since,
            until=until,
            all_time=all_time,
            provenance=provenance,
            thin_floor=0,
            adaptive_default=False,
        )
        _echo_window(win)

        # When --field is supplied, the custom field is used as-is; provenance/window
        # filter only applies to the global field builder.
        field_provenance = None if field_text is not None else provenance
        field = _load_field(
            con,
            field_text=field_text,
            provenance=field_provenance,
            since=win.since,
            until=win.until,
        )

        # Warn on field warnings (thin-data banners, normalization, etc.)
        for w in field.warnings:
            click.echo(f"// field warning: {w}")

        # Compute per-archetype vulnerability tags + hate-equity coverage
        archetype_tags = field_vulnerability_tags(con, field)
        field_vuln_profile = hate_equity(field, archetype_tags)

        # Render field composition
        click.echo(f"\n=== Field Read (field_source={field.field_source}) ===")
        click.echo(f"Field composition ({len(field.shares)} archetypes):")
        for archetype, share in sorted(field.shares.items(), key=lambda kv: kv[1], reverse=True):
            tags = archetype_tags.get(archetype, frozenset())
            tag_str = f"  [{', '.join(sorted(tags))}]" if tags else ""
            click.echo(f"  {archetype:<30}  {share:>6.1%}{tag_str}")

        # Render field vulnerability profile (hate-equity)
        if field_vuln_profile:
            click.echo("\nField vulnerability profile (hate-equity):")
            click.echo(
                "  (share of the field that carries each vulnerability tag — "
                "what a hate card targeting that tag would attack)"
            )
            for tag, eq in sorted(
                field_vuln_profile.items(), key=lambda kv: kv[1], reverse=True
            ):
                click.echo(f"  {tag:<28}  field share attacked: {eq:>6.1%}")
        else:
            click.echo("\nField vulnerability profile: (no tagged archetypes found)")

    finally:
        con.close()


@advise.command("report")
@click.option(
    "--deck",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a plain-text decklist file.",
)
@_my_deck_opt
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
@_provenance_opt
@_window_opts
@_verbose
def advise_report(
    deck: str | None,
    my_deck: str | None,
    archetype: str | None,
    field_file: str | None,
    venues: str | None,
    reserved: int,
    seed: int | None,
    db: str | None,
    provenance: str | None,
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

    # --provenance and --venues are mutually exclusive: venues already provides per-venue splits.
    if provenance is not None and venues is not None:
        raise click.ClickException(
            "--provenance and --venues are mutually exclusive: --venues provides per-venue "
            "splits already. Use --provenance for a single-provenance global field, or "
            "--venues for side-by-side venue comparison."
        )

    mainboard, sideboard_cards = _resolve_deck_boards(deck, my_deck, "advise report")
    field_text = Path(field_file).read_text() if field_file else None

    if provenance is not None:
        click.echo(f"// provenance: {provenance}")

    con = store.connect(db) if db else store.connect()
    try:
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time, provenance=provenance,
        )
        _echo_window(win)
        inputs = build_advisory_inputs(con, win, provenance=provenance)
        for line in inputs.audit:
            click.echo(line)

        # ── venues comparison mode ────────────────────────────────────────────
        if venues is not None:
            from legacy_engine.analytics.venue import resolve_venues

            requested_keys = [k.strip() for k in venues.split(",") if k.strip()]
            try:
                venue_list = resolve_venues(con, requested_keys)
            except ValueError as exc:
                raise click.ClickException(str(exc)) from exc

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
        # When --field is supplied, the custom field is used as-is; provenance only filtered
        # the matchup matrix. When --field is absent, provenance narrows the global field.
        field_provenance = None if field_text is not None else provenance
        field = _load_field(con, field_text=field_text, provenance=field_provenance, since=inputs.field_since, until=inputs.field_until)
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


@advise.command("refresh")
@click.option(
    "--deck",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a plain-text decklist file (consensus shell or user list).",
)
@_my_deck_opt
@click.option(
    "--archetype",
    default=None,
    help="Archetype name; if omitted the deck is classified automatically.",
)
@click.option(
    "--venues",
    default=None,
    help="Comma-separated venue keys (e.g. online,paper). Defaults to online and paper.",
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
    help="Maximum greedy maindeck swap rounds.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_provenance_opt
@_window_opts
@_verbose
def advise_refresh(
    deck: str | None,
    my_deck: str | None,
    archetype: str | None,
    venues: str | None,
    lock_threshold: float,
    max_swaps: int,
    db: str | None,
    provenance: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Full deck-tuning refresh: per-venue maindeck + sideboard + plain-speak primer.

    Pulls current data and emits a ready-to-play tuning package for each requested
    venue (default: online and paper).  Each package includes:

      1. Recommended maindeck (field-tuned, current-regime-aware).
      2. Recommended sideboard (15, field-tuned).
      3. A concise plain-speak primer explaining how the sideboard attacks each
         meaningful opponent — including the exact OUT/IN swaps and WHY.

    Ban-regime-correct by default (adaptive per-opponent ban-aware windows).
    Loudly labels thin/no-data matchups — never fabricates numbers.

    Example:
      legacy-engine advise refresh --deck shell.txt --archetype "Dimir Tempo"
      legacy-engine advise refresh --deck shell.txt --venues online,paper
    """
    _setup_logging(verbose)

    from legacy_engine.advisory.refresh import run_refresh, render_refresh_result
    from legacy_engine.advisory.report import _classify_deck
    from legacy_engine.advisory.window import resolve_advisory_window
    from legacy_engine.analytics.venue import resolve_venues
    from legacy_engine.ingestion import store

    # --provenance and --venues are mutually exclusive: venues already embeds provenance.
    if provenance is not None and venues is not None:
        raise click.ClickException(
            "--provenance and --venues are mutually exclusive for advise refresh: "
            "use --venues to select specific venues (which carry their own provenance), "
            "or --provenance to restrict to a single provenance venue."
        )

    maindeck, sideboard_in = _resolve_deck_boards(deck, my_deck, "advise refresh")

    if provenance is not None:
        click.echo(f"// provenance: {provenance}")

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)

        # Resolve window (default: adaptive — ban-regime-correct per-opponent).
        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time, provenance=provenance,
        )
        _echo_window(win)

        # Resolve archetype.
        resolved_archetype = archetype
        if resolved_archetype is None:
            result = _classify_deck(con, maindeck, sideboard_in)
            resolved_archetype = result.archetype
            click.echo(f"// Classified archetype: {resolved_archetype} (kind={result.kind})")

        # Resolve venues. When --provenance is given (without --venues), restrict to that
        # single provenance venue. When --venues is given, use those keys directly.
        # Default (both None): use the standard online + paper set.
        if provenance is not None:
            venue_keys = [provenance]
        elif venues is not None:
            venue_keys = [k.strip() for k in venues.split(",")]
        else:
            venue_keys = None
        venue_list = resolve_venues(con, venue_keys)

        # Determine the window to pass (None = adaptive within tune_deck/recommend_sideboard).
        # When the caller gave an explicit window, forward it; otherwise let adaptive activate.
        use_since = win.since if win.mode != "adaptive" else None
        use_until = win.until if win.mode != "adaptive" else None

        refresh = run_refresh(
            con,
            maindeck,
            sideboard_in,
            archetype=resolved_archetype,
            venues=venue_list,
            since=use_since,
            until=use_until,
            lock_threshold=lock_threshold,
            max_swaps=max_swaps,
        )

        click.echo(render_refresh_result(refresh))

        if refresh.warnings:
            for w in refresh.warnings:
                click.echo(f"// [warn] {w}", err=True)
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
        # Deliberately NOT era-windowed: player strength is not an archetype entity —
        # per-entity eras don't apply; the current ban regime is the right recency basis
        # (epic-stable-era-windows-consumption Unit 4 decision).
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


@advise.command("acquire")
@click.option(
    "--collection",
    "collection_file",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to a plain-text collection file (<qty> <card name> lines). Required.",
)
@click.option(
    "--archetype",
    default=None,
    help="Target archetype for consensus-based candidate universe.",
)
@click.option(
    "--deck",
    "deck_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a plain-text decklist to use as the target board (alternative to --archetype).",
)
@click.option(
    "--field",
    "field_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a custom field file (<share> <archetype> lines).",
)
@click.option(
    "--budget",
    type=float,
    default=None,
    help="Optional USD budget cap; takes buys in impact-per-dollar order until spent.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_provenance_opt
@_window_opts
@_verbose
def advise_acquire(
    collection_file: str,
    archetype: str | None,
    deck_file: str | None,
    field_file: str | None,
    budget: float | None,
    db: str | None,
    provenance: str | None,
    since: str | None,
    until: str | None,
    regime: str | None,
    all_time: bool,
    verbose: bool,
) -> None:
    """Generate a ranked, priced buy list for a target field/board.

    Outputs a buy list ranked by impact (field_relevance × archetype_relevance),
    flags redundant/over-quantity owns and overpriced printings, and shows how each
    buy slots into the board.

    Example:
      legacy-engine advise acquire --collection binder.txt --archetype "Dimir Tempo"
      legacy-engine advise acquire --collection binder.txt --deck mylist.txt --budget 50
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.advisory.acquire import acquire_plan
    from legacy_engine.advisory.collection import CollectionView
    from legacy_engine.advisory.report import _load_field, _parse_decklist
    from legacy_engine.advisory.window import resolve_advisory_window
    from legacy_engine.ingestion import store

    if archetype is None and deck_file is None:
        raise click.ClickException("One of --archetype or --deck is required.")

    cv = CollectionView.from_text(Path(collection_file).read_text())
    click.echo(f"// collection: {cv}")

    deck: dict[str, int] | None = None
    if deck_file:
        deck_text = Path(deck_file).read_text()
        main, side = _parse_decklist(deck_text)
        deck = {**main, **side}

    field_text = Path(field_file).read_text() if field_file else None

    if provenance is not None:
        click.echo(f"// provenance: {provenance}")

    # Resolve price source (soft dep — absent → unpriced ranking).
    price_fn = None
    con = store.connect(db) if db else store.connect()
    try:
        # Try to build a price_fn from the loaded card_prices table.
        try:
            from legacy_engine.ingestion.prices import price_quote as _pq
            def price_fn(name: str):  # type: ignore[misc]
                try:
                    return _pq(con, name)
                except Exception:
                    return None
        except Exception:
            pass

        win = resolve_advisory_window(
            con, regime=regime, since=since, until=until, all_time=all_time, provenance=provenance,
        )
        _echo_window(win)

        # When --field is supplied, the custom field is used as-is; provenance only affects
        # the window thinness check. When --field is absent, provenance narrows the global field.
        field_provenance = None if field_text is not None else provenance
        field = _load_field(con, field_text=field_text, provenance=field_provenance)

        plan = acquire_plan(
            con,
            field,
            archetype=archetype,
            deck=deck,
            collection=cv,
            price_fn=price_fn,
            since=win.since,
            until=win.until,
        )

        click.echo(
            f"\n=== Acquisition Plan (field_source={plan.field_source}, "
            f"impact_basis={plan.impact_basis}) ==="
        )

        if not plan.buy_list:
            click.echo("  (nothing to acquire — you already own everything recommended!)")
        else:
            header = f"  {'copies':>6}  {'card':<40}  {'impact':>7}  {'price':>7}  slots-into"
            click.echo(header)
            click.echo("  " + "-" * (len(header) - 2))
            for item in plan.buy_list:
                price_str = f"${item.price:.2f}" if item.price is not None else "n/a"
                click.echo(
                    f"  {item.acquire_copies:>6}x  {item.card:<40}  "
                    f"{item.impact:>7.4f}  {price_str:>7}  {item.slots_into}"
                )
                if item.replaces:
                    click.echo(f"            replaces: {item.replaces}")

        if plan.total_cost is not None:
            click.echo(f"\n  Total estimated cost: ${plan.total_cost:.2f}")
        elif plan.buy_list:
            click.echo("\n  Total cost: unavailable (no price source or some cards unpriced)")

        # Budget filter.
        if budget is not None and plan.buy_list:
            priced_buys = [b for b in plan.buy_list if b.price is not None and b.price > 0]
            if priced_buys:
                # Sort by impact-per-dollar for budget fill.
                by_eff = sorted(
                    priced_buys,
                    key=lambda b: -(b.impact / b.price if b.price else 0),
                )
                remaining = budget
                chosen = []
                for item in by_eff:
                    cost = item.price * item.acquire_copies  # type: ignore[operator]
                    if cost <= remaining:
                        chosen.append(item)
                        remaining -= cost
                click.echo(
                    f"\n  [--budget ${budget:.2f}] {len(chosen)} buys fit "
                    f"(${budget - remaining:.2f} spent, ${remaining:.2f} left):"
                )
                for item in chosen:
                    click.echo(f"    {item.acquire_copies}x {item.card}  ${item.price:.2f}")
            else:
                click.echo(f"\n  [--budget] no priced buys to filter")

        # Flags section.
        if plan.flags:
            click.echo("\n  === Collection Flags ===")
            for flag in plan.flags:
                click.echo(f"  [{flag.kind}] {flag.card}: {flag.detail}")

        # Warnings.
        for w in plan.warnings:
            click.echo(f"  [warn] {w}")

        click.echo(f"\n  {plan.heuristic_note}")
        from legacy_engine.advisory.sideboard import _VALUE_DISCLAIMER
        click.echo(f"  [disclaimer] {_VALUE_DISCLAIMER}")

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
    "--variant",
    default=None,
    help="Scope the pool to decks with this variant tag (e.g. 'Bauble'). Combines with --players as an AND-filter. Requires labeler with registry.",
)
@click.option(
    "--players",
    default=None,
    help="Comma-separated player handles/ids to restrict the deck pool to (explicit player filter). Combines with --variant as an AND-filter.",
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
            from legacy_engine.generation.consensus import entity_era_window

            # Use the same (era-aware) window as the consensus query.
            eff_since = since
            eff_until = until
            if eff_since is None and eff_until is None:
                eff_since, eff_until, window_label = entity_era_window(con, archetype)
                click.echo(f"// window: since {eff_since or 'full corpus'} ({window_label})")

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
    default=None,
    help="Path to a plain-text decklist file (consensus shell or user list).",
)
@_my_deck_opt
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
    "--collection",
    "collection_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a plain-text collection file (<qty> <card name> lines). "
         "Enables owned/acquire annotations on each recommendation. "
         "When omitted, output is byte-identical to pre-collection behavior.",
)
@click.option(
    "--owned-only",
    is_flag=True,
    default=False,
    help="Only show cards the user already owns (requires --collection). "
         "Suppresses the acquire-list, prints count of suppressed cards.",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def generate_tune(
    deck: str | None,
    my_deck: str | None,
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
    collection_file: str | None,
    owned_only: bool,
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

    from legacy_engine.advisory.report import _classify_deck, _load_field
    from legacy_engine.analytics.players.identity import load_alias_map
    from legacy_engine.generation.tuning import tune_deck
    from legacy_engine.ingestion import store

    maindeck, starting_side = _resolve_deck_boards(deck, my_deck, "generate tune")
    field_text = Path(field_file).read_text() if field_file else None

    # Load collection view (gated: None when --collection not provided).
    cv = None
    if collection_file:
        from legacy_engine.advisory.collection import CollectionView
        cv = CollectionView.from_text(Path(collection_file).read_text())
        click.echo(f"// collection: {cv}")

    if owned_only and cv is None:
        raise click.ClickException("--owned-only requires --collection")

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
            from legacy_engine.generation.consensus import entity_era_window

            eff_since_s = since
            eff_until_s = until
            if eff_since_s is None and eff_until_s is None:
                eff_since_s, eff_until_s, window_label_s = entity_era_window(con, resolved_archetype)
                click.echo(f"// window: since {eff_since_s or 'full corpus'} ({window_label_s})")

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
            collection=cv,
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
    # Echo window divergence — list window is current-regime; matchup math window depends
    # on whether the caller gave an explicit --since/--until:
    #   • No explicit window → recommend_sideboard uses adaptive per-opponent ban-aware pooling
    #     (tuned.plan_window_label = "adaptive (per-opponent ban-aware)")
    #   • Explicit --since/--until → recommend_sideboard uses the caller-supplied uniform window
    #     (tuned.plan_window_label = "" — adaptive suppressed by explicit window)
    _matchup_window_label = tuned.plan_window_label or "current-regime (uniform, explicit window)"
    click.echo(
        f"// NOTE: tuning uses two windows: consensus/card-frequency list = "
        f"current-regime (uniform); matchup math = {_matchup_window_label}. "
        "This divergence is intentional — the list reflects what is played NOW; "
        "matchup depth may borrow prior-regime data. Both are labeled here."
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

    # ── Collection-aware annotation (only when --collection supplied) ─────────
    if tuned.collection_aware and tuned.owned:
        from legacy_engine.advisory.acquire import split_recommendation
        all_cards = {**tuned.maindeck, **tuned.sideboard}
        if owned_only and cv is not None:
            play_owned, acquire = split_recommendation(all_cards, cv)
            click.echo(f"\n// [owned-only] Showing {len(play_owned)} owned cards; "
                       f"{len(acquire)} acquire-card(s) suppressed")
        else:
            to_acquire = {c: ann for c, ann in tuned.owned.items() if not ann.owned}
            already_own = {c: ann for c, ann in tuned.owned.items() if ann.owned}
            if to_acquire:
                click.echo(f"\n// [collection] Acquire ({len(to_acquire)} cards):")
                for card, ann in sorted(to_acquire.items(), key=lambda kv: -kv[1].to_acquire):
                    click.echo(f"//   need {ann.to_acquire}x {card} (own {ann.owned_copies})")
            if already_own:
                click.echo(f"// [collection] Already owned: {len(already_own)} cards")

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

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)

        resolved_archetype = archetype
        if resolved_archetype is None:
            result = _classify_deck(con, main_counts, side_counts)
            resolved_archetype = result.archetype
            click.echo(f"// Classified archetype: {resolved_archetype} (kind={result.kind})")

        # Resolve the effective window in the CLI layer so the orchestrator always receives
        # explicit dates (never the (None, None) that would re-trigger a default-window lookup).
        # Resolved AFTER resolved_archetype is known so the default branch can use THIS
        # archetype's own era-aware horizon (entity_era_window).
        #   --all-time     → full corpus: (None, None) — but we pass all_time=True to the builder
        #   --since/--until → explicit window (passed through as-is)
        #   neither flag   → this archetype's stable_since horizon, same SSOT as generate consensus
        if all_time:
            effective_since: str | None = None
            effective_until: str | None = None
        elif since is not None or until is not None:
            effective_since = since
            effective_until = until
        else:
            from legacy_engine.generation.consensus import entity_era_window
            effective_since, effective_until, window_label = entity_era_window(con, resolved_archetype)
            click.echo(f"// window: since {effective_since or 'full corpus'} ({window_label})")

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
                # The CLI has ALWAYS already resolved the effective window by this point (via
                # --all-time, explicit --since/--until, or the era-aware entity_era_window
                # default) — apply_default_window=False so build_deck_doctor_report never
                # re-resolves internally. This matters now that the era-aware default can
                # itself legitimately produce (None, None) for an undisturbed entity (full
                # corpus): with apply_default_window=`not all_time` that (None, None) would
                # have been silently re-interpreted as "resolve internally" and overwritten
                # with the ban-only regime window, defeating the undisturbed-widens-to-
                # full-corpus behavior specifically for this command.
                apply_default_window=False,
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
    default=None,
    help="Path to a plain-text decklist file.",
)
@click.option(
    "--my-deck",
    "my_deck",
    default=None,
    help="Name of a saved UserDeck (alternative to --deck FILE).",
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
    deck_file: str | None,
    my_deck: str | None,
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

    from legacy_engine.generation.export import format_decklist

    maindeck, sideboard = _resolve_deck_boards(deck_file, my_deck, "export deck")

    output = format_decklist(maindeck, sideboard, fmt=fmt)

    if out:
        Path(out).write_text(output)
        click.echo(f"Written to {out}")
    else:
        click.echo(output)


# ── collection: personal card inventory ──
@main.group()
def collection() -> None:
    """Manage your personal card inventory (binder)."""


@collection.command("import")
@click.option(
    "--file",
    "deck_file",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to a plain-text decklist file listing owned cards.",
)
@click.option(
    "--merge/--replace",
    default=True,
    show_default=True,
    help="Merge with existing inventory (default) or replace it entirely.",
)
@_verbose
def collection_import(deck_file: str, merge: bool, verbose: bool) -> None:
    """Import owned cards from a plain-text decklist into the inventory.

    The file uses the standard ``<count> <name>`` decklist format.  Both the
    main and sideboard sections are treated as owned cards.

    Example: legacy-engine collection import --file binder.txt
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.collection.inventory import import_inventory, merge_inventory, replace_inventory
    from legacy_engine.collection.persist import load_inventory, save_inventory

    text = Path(deck_file).read_text()
    try:
        incoming = import_inventory(text)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    existing = load_inventory()
    if merge:
        updated = merge_inventory(existing, incoming)
        action = "Merged"
    else:
        updated = replace_inventory(existing, incoming)
        action = "Replaced"

    save_inventory(updated)
    total = sum(e.count for e in updated.entries)
    click.echo(f"{action} inventory: {len(updated.entries)} entries, {total} total cards")


@collection.command("show")
@click.option("--free-only", is_flag=True, default=False, help="Show only cards free in the binder (not allocated).")
@click.option("--card", "card_name", default=None, help="Filter to a specific card name.")
@_verbose
def collection_show(free_only: bool, card_name: str | None, verbose: bool) -> None:
    """Show your card inventory: owned, allocated across decks, and free.

    Example: legacy-engine collection show
    Example: legacy-engine collection show --free-only
    Example: legacy-engine collection show --card "Brainstorm"
    """
    _setup_logging(verbose)
    from legacy_engine.collection.allocation import free_binder
    from legacy_engine.collection.inventory import owned_counts_map
    from legacy_engine.collection.persist import list_user_decks, load_inventory
    from legacy_engine.collection.decks import current_cards

    inv = load_inventory()
    if not inv.entries:
        click.echo("(inventory is empty — use `collection import` to add cards)")
        return

    owned = owned_counts_map(inv)

    # Compute allocated: sum across all current deck versions.
    decks = list_user_decks()
    allocated: dict[str, int] = {}
    for deck in decks:
        main, side = current_cards(deck)
        for name, cnt in {**main, **side}.items():
            allocated[name] = allocated.get(name, 0) + cnt

    free = free_binder(owned, allocated)

    click.echo(f"\n=== Inventory ({inv.owner}) ===")
    click.echo(f"{'Card':<40}  {'Owned':>5}  {'Alloc':>5}  {'Free':>5}")
    click.echo("-" * 60)

    entries = sorted(owned.items(), key=lambda kv: kv[0])
    shown = 0
    for name, owned_cnt in entries:
        alloc_cnt = allocated.get(name, 0)
        free_cnt = free.get(name, 0)
        if card_name and card_name.lower() not in name.lower():
            continue
        if free_only and free_cnt == 0:
            continue
        click.echo(f"{name:<40}  {owned_cnt:>5}  {alloc_cnt:>5}  {free_cnt:>5}")
        shown += 1

    if shown == 0:
        click.echo("(no cards match the filter)")


@collection.command("status")
@_verbose
def collection_status(verbose: bool) -> None:
    """Show buildability and contention summary across all decks.

    Reports cards that are over-committed (claimed by more decks than owned).

    Example: legacy-engine collection status
    """
    _setup_logging(verbose)
    from legacy_engine.collection.allocation import buildability, contention
    from legacy_engine.collection.decks import current_cards
    from legacy_engine.collection.inventory import owned_counts_map
    from legacy_engine.collection.persist import list_user_decks, load_inventory

    inv = load_inventory()
    owned = owned_counts_map(inv)
    decks = list_user_decks()

    if not decks:
        click.echo("(no decks saved — use `deck save` to register a deck)")
        return

    click.echo(f"\n=== Collection Status ({len(decks)} deck(s)) ===")

    # Per-deck buildability.
    click.echo("\n  Buildability:")
    per_deck_cards: dict[str, dict[str, int]] = {}
    for deck in decks:
        main, side = current_cards(deck)
        combined = {**main}
        for name, cnt in side.items():
            combined[name] = combined.get(name, 0) + cnt
        per_deck_cards[deck.name] = combined
        report = buildability(main, side, owned, deck_name=deck.name)
        status_str = "OK" if report.buildable else f"MISSING {len(report.missing)} card(s)"
        click.echo(f"    {deck.name:<35}  {status_str}")
        if not report.buildable:
            for card_name, shortfall in sorted(report.missing.items()):
                click.echo(f"      − {card_name}: need {shortfall} more")

    # Contention: cards over-committed across decks.
    conflicts = contention(per_deck_cards, owned)
    if conflicts:
        click.echo("\n  Contention (cards claimed by more decks than owned):")
        for entry in conflicts:
            click.echo(
                f"    {entry.name}: owned={entry.owned}, claimed={entry.total_claimed}, "
                f"shortfall={entry.shortfall}  [{', '.join(entry.decks_claiming)}]"
            )
    else:
        click.echo("\n  No contention — all decks can coexist with your collection.")


@collection.command("rebuild")
@_verbose
def collection_rebuild(verbose: bool) -> None:
    """Drop and reload the collection DuckDB tables from raw JSON files.

    Safe to run repeatedly — raw JSON is the source of truth.

    Example: legacy-engine collection rebuild
    """
    _setup_logging(verbose)
    from legacy_engine.collection import store as cstore
    from legacy_engine.ingestion import store

    con = store.connect()
    try:
        cstore.init_schema(con)
        cstore.rebuild_collection(con)
    finally:
        con.close()
    click.echo("Collection DuckDB tables rebuilt from data/collection/")


# ── deck: personal deck management ──
@main.group()
def deck() -> None:
    """Manage your personal decks (named, versioned 75s)."""


@deck.command("save")
@click.option("--name", "deck_name", required=True, help="Deck name (e.g. 'my Dimir Tempo').")
@click.option(
    "--deck",
    "deck_file",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to a plain-text decklist file.",
)
@click.option("--note", default="", help="Changelog note for this version.")
@click.option("--label", default="", help="Short human label for this version (e.g. 'post-Frog-ban').")
@click.option("--archetype-hint", default=None, help="Optional archetype label (engine archetype still inferred).")
@click.option(
    "--deck-id",
    default=None,
    help="Existing deck id to append a new version to (omit to create a new deck).",
)
@_verbose
def deck_save(
    deck_name: str,
    deck_file: str,
    note: str,
    label: str,
    archetype_hint: str | None,
    deck_id: str | None,
    verbose: bool,
) -> None:
    """Save a decklist as a named deck (or append a new version).

    If ``--deck-id`` is omitted, a new deck is created.  To append a new
    version to an existing deck, pass its id (visible via ``deck list``).

    Example: legacy-engine deck save --name "my Dimir Tempo" --deck list.txt
    Example: legacy-engine deck save --name "my Dimir Tempo" --deck list2.txt --deck-id <id>
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.collection.decks import save_deck_from_file
    from legacy_engine.collection.persist import find_deck_by_name, save_user_deck

    text = Path(deck_file).read_text()

    # If no deck_id given but a deck with this name exists, auto-append a version.
    resolved_id = deck_id
    if resolved_id is None:
        existing = find_deck_by_name(deck_name)
        if existing is not None:
            resolved_id = existing.id
            click.echo(f"// Appending new version to existing deck '{deck_name}' (id={existing.id})")

    try:
        saved = save_deck_from_file(
            text,
            deck_name,
            deck_id=resolved_id,
            note=note,
            label=label,
            archetype_hint=archetype_hint,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    save_user_deck(saved)
    ver = saved.versions[-1]
    main_count = sum(c.count for c in ver.cards if c.board == "main")
    side_count = sum(c.count for c in ver.cards if c.board == "side")
    click.echo(
        f"Saved '{saved.name}' (id={saved.id}) "
        f"v{ver.version}: {main_count} main / {side_count} side"
    )


@deck.command("load")
@click.option("--name", "deck_name", required=True, help="Deck name.")
@click.option("--version", "version_num", type=int, default=None, help="Version number (default: current).")
@click.option("--out", type=click.Path(dir_okay=False), default=None, help="Write to file instead of stdout.")
@_verbose
def deck_load(
    deck_name: str,
    version_num: int | None,
    out: str | None,
    verbose: bool,
) -> None:
    """Print a saved deck as a plain-text decklist.

    Example: legacy-engine deck load --name "my Dimir Tempo"
    Example: legacy-engine deck load --name "my Dimir Tempo" --version 1
    """
    _setup_logging(verbose)
    from pathlib import Path

    from legacy_engine.collection.decks import export_deck_text
    from legacy_engine.collection.persist import find_deck_by_name

    deck = find_deck_by_name(deck_name)
    if deck is None:
        raise click.ClickException(f"No deck named {deck_name!r}. Use `deck list` to see available decks.")

    try:
        text = export_deck_text(deck, version_num)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if out:
        Path(out).write_text(text)
        click.echo(f"Written to {out}")
    else:
        click.echo(text)


@deck.command("list")
@_verbose
def deck_list(verbose: bool) -> None:
    """List all saved decks with their current version and archetype hint.

    Example: legacy-engine deck list
    """
    _setup_logging(verbose)
    from legacy_engine.collection.decks import current_version
    from legacy_engine.collection.persist import list_user_decks

    decks = list_user_decks()
    if not decks:
        click.echo("(no decks saved — use `deck save` to register a deck)")
        return

    click.echo(f"\n=== My Decks ({len(decks)}) ===")
    click.echo(f"  {'Name':<35}  {'v':>3}  {'Cards':>5}  {'Archetype'}")
    click.echo("  " + "-" * 65)
    for d in decks:
        ver = current_version(d)
        ver_num = ver.version if ver else 0
        card_count = sum(c.count for c in ver.cards) if ver else 0
        arch = d.archetype_hint or "(none)"
        click.echo(f"  {d.name:<35}  v{ver_num:>2}  {card_count:>5}  {arch}")
        click.echo(f"    id={d.id}")


@deck.command("show")
@click.option("--name", "deck_name", required=True, help="Deck name.")
@click.option("--version", "version_num", type=int, default=None, help="Version number (default: current).")
@_verbose
def deck_show(deck_name: str, version_num: int | None, verbose: bool) -> None:
    """Show the 75 for a deck version plus its version history.

    Example: legacy-engine deck show --name "my Dimir Tempo"
    """
    _setup_logging(verbose)
    from legacy_engine.collection.decks import current_version, get_version_by_number
    from legacy_engine.collection.persist import find_deck_by_name

    deck = find_deck_by_name(deck_name)
    if deck is None:
        raise click.ClickException(f"No deck named {deck_name!r}.")

    if version_num is not None:
        ver = get_version_by_number(deck, version_num)
        if ver is None:
            raise click.ClickException(f"Version {version_num} not found in deck {deck_name!r}.")
    else:
        ver = current_version(deck)
        if ver is None:
            raise click.ClickException(f"Deck {deck_name!r} has no versions.")

    click.echo(f"\n=== {deck.name} — v{ver.version} ===")
    if ver.label:
        click.echo(f"  Label: {ver.label}")
    if ver.note:
        click.echo(f"  Note: {ver.note}")
    click.echo(f"  Created: {ver.created}")
    click.echo(f"  id: {deck.id}")

    main_cards = [(c.name, c.count) for c in ver.cards if c.board == "main"]
    side_cards = [(c.name, c.count) for c in ver.cards if c.board == "side"]

    if main_cards:
        click.echo(f"\n  Mainboard ({sum(c for _, c in main_cards)}):")
        for name, cnt in sorted(main_cards, key=lambda kv: (-kv[1], kv[0])):
            click.echo(f"    {cnt:>2}  {name}")
    if side_cards:
        click.echo(f"\n  Sideboard ({sum(c for _, c in side_cards)}):")
        for name, cnt in sorted(side_cards, key=lambda kv: (-kv[1], kv[0])):
            click.echo(f"    {cnt:>2}  {name}")

    click.echo(f"\n  Version history ({len(deck.versions)}):")
    for v in deck.versions:
        marker = " ←current" if v.id == deck.current_version_id else ""
        click.echo(f"    v{v.version}  {v.created}  {v.label or ''}  {v.note or ''}{marker}")


@deck.command("versions")
@click.option("--name", "deck_name", required=True, help="Deck name.")
@_verbose
def deck_versions(deck_name: str, verbose: bool) -> None:
    """Show the full version log for a deck (evolution over time).

    Example: legacy-engine deck versions --name "my Dimir Tempo"
    """
    _setup_logging(verbose)
    from legacy_engine.collection.persist import find_deck_by_name

    deck = find_deck_by_name(deck_name)
    if deck is None:
        raise click.ClickException(f"No deck named {deck_name!r}.")

    click.echo(f"\n=== Version log: {deck.name} ===")
    click.echo(f"  id={deck.id}  owner={deck.owner}  created={deck.created}")
    click.echo("")
    for v in deck.versions:
        marker = " ← current" if v.id == deck.current_version_id else ""
        main_cnt = sum(c.count for c in v.cards if c.board == "main")
        side_cnt = sum(c.count for c in v.cards if c.board == "side")
        click.echo(
            f"  v{v.version}  {v.created}  "
            f"main={main_cnt} side={side_cnt}"
            f"{('  ' + v.label) if v.label else ''}"
            f"{('  — ' + v.note) if v.note else ''}"
            f"{marker}"
        )


@deck.command("buildable")
@click.option("--name", "deck_name", required=True, help="Deck name.")
@_verbose
def deck_buildable(deck_name: str, verbose: bool) -> None:
    """Check whether you can build a deck from your current inventory.

    Lists missing cards and the shortfall count for each.

    Example: legacy-engine deck buildable --name "my Dimir Tempo"
    """
    _setup_logging(verbose)
    from legacy_engine.collection.allocation import buildability
    from legacy_engine.collection.decks import current_cards
    from legacy_engine.collection.inventory import owned_counts_map
    from legacy_engine.collection.persist import find_deck_by_name, load_inventory

    deck = find_deck_by_name(deck_name)
    if deck is None:
        raise click.ClickException(f"No deck named {deck_name!r}.")

    main, side = current_cards(deck)
    if not main:
        raise click.ClickException(f"Deck {deck_name!r} has no cards.")

    inv = load_inventory()
    owned = owned_counts_map(inv)
    report = buildability(main, side, owned, deck_name=deck_name)

    if report.buildable:
        click.echo(f"OK — you can build '{deck_name}' from your collection.")
    else:
        click.echo(f"MISSING — you cannot build '{deck_name}' without {len(report.missing)} more card(s):")
        for card, shortfall in sorted(report.missing.items()):
            click.echo(f"  − {card}: need {shortfall} more")


# ── discover: data-driven subarchetype discovery ──
@main.group()
def discover() -> None:
    """Discover, stage, apply, and promote data-driven subarchetype splits."""


@discover.command("run")
@click.option("--archetype", required=True, help="Parent archetype to discover within (e.g. 'Doomsday').")
@click.option(
    "--since", default=None,
    help="Window start (YYYY-MM-DD, inclusive; overrides the era-aware default). "
         "Default: this archetype's era-aware stable window (see --all-pool).",
)
@click.option(
    "--all-pool", is_flag=True, default=False,
    help="Ignore the era-aware default and cluster the full unwindowed corpus "
         "(the pre-epic behavior). Ignored when --since is given explicitly.",
)
@click.option(
    "--reducer",
    type=click.Choice(["svd", "umap"], case_sensitive=False),
    default="svd",
    show_default=True,
    help="Dimensionality reduction before HDBSCAN (svd is deterministic; umap needs the "
         "'discovery' extra installed).",
)
@click.option("--seed", type=int, default=0, show_default=True, help="RNG seed (reduction + bootstrap).")
@click.option(
    "--n-boot", type=int, default=50, show_default=True,
    help="Bootstrap resamples for the Gate-A stability estimate.",
)
@click.option(
    "--min-samples", type=int, default=10, show_default=True,
    help="HDBSCAN min_samples (density conservatism; decoupled from the camp-size floor — "
         "larger values push more decks to noise).",
)
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@click.option(
    "--discovered-path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Staging registry to write (defaults to data/variants/discovered.json).",
)
@_verbose
def discover_run(
    archetype: str,
    since: str | None,
    all_pool: bool,
    reducer: str,
    seed: int,
    n_boot: int,
    min_samples: int,
    db: str | None,
    discovered_path: str | None,
    verbose: bool,
) -> None:
    """Discover candidate subarchetype camps within a parent archetype.

    Clusters the parent's flex-band mainboard compositions (HDBSCAN on a reduced TF-IDF
    embedding), validates the split through both gates (bootstrap stability; both-camp
    sample tier + signature divergence), and stages a PASSing split as a candidate in the
    staging registry.  A FAILing split is still fully reported — never silently dropped —
    it just isn't staged.

    Defaults the clustering pool to this archetype's era-aware stable window
    (`entity_era_window`) rather than the full corpus — pass `--since` to override, or
    `--all-pool` to explicitly restore the pre-epic unwindowed pool.

    Example: legacy-engine discover run --archetype "Doomsday"
    """
    _setup_logging(verbose)
    from functools import partial

    from legacy_engine.analytics.discovery import discover_subarchetypes, reduce_dims
    from legacy_engine.archetype.discovered import (
        load_discovered,
        record_from_split,
        save_discovered,
        stage_split,
    )
    from legacy_engine.config import DISCOVERED_VARIANTS_PATH
    from legacy_engine.ingestion import store

    reducer = reducer.lower()
    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con)

        if since is not None:
            effective_since = since
            current_since = since
        elif all_pool:
            # Full-corpus pool, but %current stays anchored to the entity's ERA since —
            # that's the diagnostic value of --all-pool: cluster everything, then see how
            # current each camp is relative to the live era (design decision, Unit 2).
            from legacy_engine.generation.consensus import entity_era_window

            effective_since = None
            current_since, _until, window_label = entity_era_window(con, archetype)
            click.echo(
                f"// pool window: full corpus (--all-pool); % current vs "
                f"{current_since or 'full corpus'} ({window_label})"
            )
        else:
            from legacy_engine.generation.consensus import entity_era_window

            effective_since, _until, window_label = entity_era_window(con, archetype)
            current_since = effective_since
            if effective_since is None:
                click.echo(f"// pool window: full corpus ({window_label})")
            else:
                click.echo(f"// pool window: since {effective_since} ({window_label})")

        pool_n = con.execute(
            """
            SELECT count(*) FROM decks d JOIN tournaments t ON t.id = d.tournament_id
            WHERE d.archetype = ? AND (? IS NULL OR t.date >= ?)
            """,
            [archetype, effective_since, effective_since],
        ).fetchone()[0]
        click.echo(f"// pool: {pool_n} decks")
        if pool_n == 0:
            click.echo(
                "// ⚠ the resolved pool window excludes every deck of this archetype — "
                "widen with --since or --all-pool (the FAIL below reflects an empty pool, "
                "not unstructured decks)"
            )

        split = discover_subarchetypes(
            con,
            archetype,
            since=effective_since,
            current_since=current_since,
            reducer=partial(reduce_dims, method=reducer),
            seed=seed,
            n_boot=n_boot,
            min_samples=min_samples,
        )
    finally:
        con.close()

    _print_discovery_report(
        split, since=effective_since, reducer=reducer, seed=seed, n_boot=n_boot,
        min_samples=min_samples,
    )

    if not split.passed:
        click.echo(
            "// not staged: split failed validation — the report above is the complete, "
            "honest result"
        )
        return

    staging_path = discovered_path or str(DISCOVERED_VARIANTS_PATH)
    from datetime import date

    record = record_from_split(
        split,
        generated_from=f"discover run @ {date.today().isoformat()}",
        params={
            "since": effective_since,
            "reducer": reducer,
            "seed": seed,
            "n_boot": n_boot,
        },
    )
    reg = load_discovered(staging_path)
    new_reg, replaced = stage_split(reg, record)
    save_discovered(new_reg, staging_path)
    if replaced is not None:
        camp_names = ", ".join(c.name for c in replaced.camps)
        click.echo(
            f"// replaced prior staged candidate for {archetype!r} "
            f"(was: generated_from={replaced.generated_from!r}, camps={camp_names})"
        )
    click.echo(f"// staged candidate split for {archetype!r} -> {staging_path}")
    click.echo("// next: `discover list` to inspect, `discover promote` to curate a camp")


def _print_discovery_report(
    split: "DiscoveredSplit",
    *,
    since: str | None,
    reducer: str,
    seed: int,
    n_boot: int,
    min_samples: int = 10,
) -> None:
    """Render a DiscoveredSplit with full `// ` audit provenance (PASS or FAIL alike)."""

    click.echo(f"\n=== Subarchetype Discovery: {split.parent!r} ===")
    click.echo(f"// window: {since or 'full corpus'}{' ..' if since else ''}")
    click.echo(f"// params: reducer={reducer} seed={seed} n_boot={n_boot} min_samples={min_samples}")
    sil = f"{split.silhouette:.3f}" if split.silhouette is not None else "n/a"
    click.echo(f"// stability: {split.stability:.3f}  silhouette (diagnostic only): {sil}")
    click.echo(f"// noise decks (outlier brews, no camp): {split.n_noise}")

    for camp in split.camps:
        top = ", ".join(
            f"{name} ({delta:+.2f})"
            for name, delta in camp.signature_cards[:5]
            if delta > 0
        )
        temporal = _format_camp_temporal(camp.median_date, camp.pct_current)
        click.echo(
            f"  camp {camp.name}: n={camp.n} [{camp.tier}]  signature: {top or '(none)'}{temporal}"
        )

    if split.temporal_mixing:
        click.echo(f"// ⚠ temporal mixing: {split.temporal_note}")

    for reason in split.reasons:
        click.echo(f"// {reason}")
    click.echo(f"// verdict: {'PASS' if split.passed else 'FAIL'}")


def _format_camp_temporal(median_date: str | None, pct_current: float | None) -> str:
    """Render a camp's Gate C diagnostics as a trailing report fragment, or "" when absent.

    ``median <YYYY-MM-DD> · <NN>% current`` — the `% current` clause is omitted when
    ``pct_current`` is ``None`` (honest: we don't know, don't fabricate a number). The whole
    fragment is omitted when ``median_date`` itself is ``None`` (no dated decks in the camp).
    """
    if median_date is None:
        return ""
    if pct_current is None:
        return f"  median {median_date}"
    return f"  median {median_date} · {pct_current:.0%} current"


@discover.command("list")
@click.option(
    "--discovered-path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Staging registry to read (defaults to data/variants/discovered.json).",
)
@_verbose
def discover_list(discovered_path: str | None, verbose: bool) -> None:
    """List staged candidate splits (and their promotion status)."""
    _setup_logging(verbose)
    from legacy_engine.archetype.discovered import load_discovered
    from legacy_engine.config import DISCOVERED_VARIANTS_PATH

    path = discovered_path or str(DISCOVERED_VARIANTS_PATH)
    try:
        reg = load_discovered(path)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"// staging registry: {path}")
    if not reg.splits:
        click.echo("(no staged candidate splits — run `discover run --archetype X`)")
        return

    for split in reg.splits:
        click.echo(
            f"\n{split.parent}  [status: {split.status}]  stability={split.stability:.3f}"
        )
        click.echo(f"// generated: {split.generated_from}  params: {split.params}")
        if split.temporal_mixing:
            click.echo(f"// ⚠ temporal mixing: {split.temporal_note}")
        for camp in split.camps:
            sig = ", ".join(camp.signature_cards[:3]) or "(none)"
            temporal = _format_camp_temporal(camp.median_date, camp.pct_current)
            click.echo(f"  - {camp.name}: n={camp.n} [{camp.tier}]  signature: {sig}{temporal}")


@discover.command("promote")
@click.option("--archetype", required=True, help="Parent archetype of the staged split.")
@click.option("--variant", required=True, help="Staged camp name to promote (see `discover list`).")
@click.option(
    "--discovered-path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Staging registry to read/update (defaults to data/variants/discovered.json).",
)
@click.option(
    "--registry-path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Curated variant registry to append to (defaults to the shipped legacy.json).",
)
@_verbose
def discover_promote(
    archetype: str,
    variant: str,
    discovered_path: str | None,
    registry_path: str | None,
    verbose: bool,
) -> None:
    """Promote a staged camp into the curated variant registry.

    Appends a ``VariantRule`` (InMainboard on the camp's top signature card) to the curated
    registry and sets the complement camp as the parent's default tag.  Fails loudly on
    unknown parent/camp or an already-promoted split — promotion is a deliberate, one-way
    human decision, never automatic.

    Example: legacy-engine discover promote --archetype "Doomsday" --variant "Murktide Regent"
    """
    _setup_logging(verbose)
    from legacy_engine.archetype.discovered import promote_split
    from legacy_engine.config import DISCOVERED_VARIANTS_PATH, VARIANTS_REGISTRY_PATH

    disc_path = discovered_path or str(DISCOVERED_VARIANTS_PATH)
    reg_path = registry_path or str(VARIANTS_REGISTRY_PATH)
    try:
        rule = promote_split(archetype, variant, disc_path, reg_path)
    except (ValueError, FileNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc

    cond = rule.conditions[0]
    click.echo(f"// promoted {archetype!r}/{variant!r} -> {reg_path}")
    click.echo(f"  rule: {cond.type} {cond.cards}")
    click.echo("// staged split marked status=promoted; re-run `label` to apply variant tags")


@discover.command("apply")
@click.option("--archetype", required=True, help="Parent archetype with a staged candidate split.")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@click.option(
    "--discovered-path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Staging registry to read (defaults to data/variants/discovered.json).",
)
@_verbose
def discover_apply(
    archetype: str,
    db: str | None,
    discovered_path: str | None,
    verbose: bool,
) -> None:
    """Apply a staged (unpromoted) candidate split's camps directly onto decks.variant.

    A labeled-speculative analytics overlay: resolves the SAME transient variant rules
    `discover promote` would install (top signature card per camp; a complement default in the
    2-camp case) against every deck currently labeled --archetype, and writes matching decks'
    decks.variant. Non-matching decks are left untouched — they surface honestly as
    '<ARCHETYPE> [unlabeled]' via `report matchups --split-variant`. Does NOT touch the curated
    registry and does NOT promote the staged record — it stays status: candidate.

    Example: legacy-engine discover apply --archetype "Doomsday"
    """
    _setup_logging(verbose)
    from legacy_engine.archetype.discovered import apply_split, load_discovered
    from legacy_engine.config import DISCOVERED_VARIANTS_PATH
    from legacy_engine.ingestion import store

    disc_path = discovered_path or str(DISCOVERED_VARIANTS_PATH)

    con = store.connect(db) if db else store.connect()
    try:
        try:
            disc = load_discovered(disc_path)
            split = next((s for s in disc.splits if s.parent == archetype), None)
            camp_names = ", ".join(c.name for c in split.camps) if split is not None else None
            n_labeled = apply_split(con, archetype, discovered_path=disc_path)
        except (ValueError, FileNotFoundError) as exc:
            raise click.ClickException(str(exc)) from exc
    finally:
        con.close()

    if camp_names:
        click.echo(f"// camps: {camp_names}")
    click.echo(f"// {n_labeled} deck(s) labeled from staged candidate for {archetype!r}")
    click.echo(
        "// STAGED CANDIDATE labels applied to decks.variant — speculative provenance; "
        "not promoted to the curated registry"
    )


# ── eras: stable-era detection, persistence, attribution, drift alarm ──
@main.group()
def eras() -> None:
    """Detect, persist, and explain per-entity stable eras (stable_since) and B&R drift."""


@eras.command("run")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_provenance_opt
@click.option(
    "--alpha", type=float, default=0.05, show_default=True,
    help="Benjamini-Hochberg FDR alpha for the fleet-wide era-boundary screen.",
)
@_verbose
def eras_run(db: str | None, provenance: str | None, alpha: float, verbose: bool) -> None:
    """Run the offline era-detection pass: series -> detectors -> ensemble -> attribution ->
    drift alarm -> persisted store (`entity_eras`). Sibling of `label`/`discover run` — a
    full-corpus recompute every call, never incremental.

    Example: legacy-engine eras run
    """
    _setup_logging(verbose)
    from legacy_engine.analytics.eras.run import run_eras
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        _echo_data_freshness(con, provenance=provenance)
        result = run_eras(con, provenance=provenance, alpha=alpha)
    finally:
        con.close()

    click.echo(f"// eras run: {result.n_entities} entities analyzed (alpha={alpha})")
    if result.n_entities == 0:
        click.echo("(no qualifying entities — corpus too thin, unlabeled, or empty)")
        return

    for entity in sorted(result.summaries):
        s = result.summaries[entity]
        since = s.stable_since or "full history"
        tag = " [inherited from parent]" if s.inherited_from_parent else ""
        click.echo(
            f"  {entity}: stable since {since}{tag}  "
            f"({s.n_accepted}/{s.n_boundaries} boundaries accepted)"
        )

    if result.alarms:
        for entity in sorted(result.alarms):
            click.echo(f"// ⚠ {entity}: {result.alarms[entity].note}")
    else:
        click.echo("// no drift alarms")


@eras.command("list")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def eras_list(db: str | None, verbose: bool) -> None:
    """List every persisted entity's stable_since, trigger, and confidence tier.

    Example: legacy-engine eras list
    """
    _setup_logging(verbose)
    from legacy_engine.analytics.eras.store import read_entity_eras
    from legacy_engine.confidence import tier_for_sample
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        rows = read_entity_eras(con)
    finally:
        con.close()

    if not rows:
        click.echo("(no era data — run `eras run` first)")
        return

    click.echo(f"// {len(rows)} entities")
    for entity in sorted(rows):
        r = rows[entity]
        since = r.stable_since or "full history"
        trigger = "(full history — no boundary)"
        if r.stable_since is not None:
            triggering = next((b for b in r.boundaries if b.date == r.stable_since), None)
            if triggering is not None and triggering.attribution is not None:
                trigger = triggering.attribution.detail
            else:
                trigger = "(boundary detail unavailable)"
        tier = tier_for_sample(r.post_boundary_decks)
        tag = " [inherited from parent]" if r.inherited_from_parent else ""
        alarm_tag = "  ⚠ alarm" if r.alarm_fired else ""
        click.echo(
            f"{entity}: stable since {since}{tag}  trigger: {trigger}  "
            f"[{tier}, n={r.post_boundary_decks}]{alarm_tag}"
        )


@eras.command("explain")
@click.argument("entity")
@click.option(
    "--db",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to the DuckDB database file (defaults to project default).",
)
@_verbose
def eras_explain(entity: str, db: str | None, verbose: bool) -> None:
    """Walk one entity's full boundary derivation — signals, magnitude, p-value, BH verdict,
    floor, and attribution. The `explain_valid_since` analog for detected eras.

    Example: legacy-engine eras explain "Tron"
    """
    _setup_logging(verbose)
    from legacy_engine.analytics.eras.store import read_entity_eras
    from legacy_engine.ingestion import store

    con = store.connect(db) if db else store.connect()
    try:
        rows = read_entity_eras(con)
    finally:
        con.close()

    if entity not in rows:
        raise click.ClickException(
            f"unknown entity {entity!r} — run `eras run` first, or check `eras list`"
        )

    r = rows[entity]
    click.echo(f"=== {entity} — era derivation ===")
    inherited_note = "  [inherited from parent]" if r.inherited_from_parent else ""
    click.echo(f"// parent: {r.parent}{inherited_note}")
    click.echo(f"// stable since: {r.stable_since or 'full history'}")
    click.echo(
        f"// run: provenance={r.run_provenance or 'combined'} alpha={r.run_alpha} at {r.run_at}"
    )

    if not r.boundaries:
        click.echo("(no candidate boundaries detected)")
    for b in r.boundaries:
        if b.bh_accepted and not b.floor_rejected:
            verdict = "ACCEPTED"
        elif b.bh_accepted:
            verdict = "FLOOR-REJECTED"
        else:
            verdict = "BH-REJECTED"
        click.echo(f"\n  {b.date}  [{verdict}]  p={b.pvalue:.4f}")
        if b.attribution is not None:
            click.echo(f"    attribution: {b.attribution.detail}")
        for sig in b.signals:
            trigger_note = f"  (trigger: {sig.trigger_card})" if sig.trigger_card else ""
            click.echo(
                f"    signal {sig.signal}: magnitude={sig.magnitude:.4f} "
                f"p={sig.pvalue:.4f}{trigger_note}"
            )
            click.echo(f"      evidence: {sig.evidence}")

    if r.alarm_fired:
        click.echo(f"\n// ⚠ {r.alarm_note}")


@eras.command("confirm")
@click.argument("event_date")
@click.argument("card")
@click.argument("reason")
@click.option(
    "--events-path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Curated ban-events JSON to append to (defaults to the shipped events.json).",
)
@_verbose
def eras_confirm(event_date: str, card: str, reason: str, events_path: str | None, verbose: bool) -> None:
    """Register a human-confirmed B&R event — the drift-alarm confirmation loop's write path.

    Appends (DATE, CARD, REASON) to the curated ban-events JSON. Every BAN_EVENTS consumer
    (`banlist_as_of`/`current_banlist`, `analytics.trends.regime_windows`,
    `analytics.affectedness`) heals on its NEXT import of `ingestion.banlist` — BAN_EVENTS is
    bound once at import, so a long-running process must be restarted (or the module reloaded)
    to see the update; a fresh CLI invocation always does.

    Example: legacy-engine eras confirm 2026-06-29 "Candelabra of Tawnos" "Tron 4x growth engine"
    """
    _setup_logging(verbose)
    from datetime import date as _date

    from legacy_engine.config import BAN_EVENTS_PATH
    from legacy_engine.ingestion.banlist import append_ban_event

    try:
        parsed_date = _date.fromisoformat(event_date)
    except ValueError as exc:
        raise click.ClickException(
            f"invalid DATE {event_date!r} (expected YYYY-MM-DD)"
        ) from exc

    path = events_path or str(BAN_EVENTS_PATH)
    try:
        updated = append_ban_event(parsed_date, card, reason, path=path)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"// registered: {card} banned {parsed_date.isoformat()} — {reason}")
    click.echo(f"// events file: {path} ({len(updated)} total events)")

    prior_dates = [d for d, _c, _r in updated if d < parsed_date]
    since_label = max(prior_dates).isoformat() if prior_dates else "baseline"
    click.echo(
        f"// regime healed: [{since_label} .. {parsed_date.isoformat()}) closes; "
        f"new regime opens at {parsed_date.isoformat()}"
    )
    click.echo("// re-run `eras run` (and any windowed report) to pick up the healed regime")


if __name__ == "__main__":
    main()
