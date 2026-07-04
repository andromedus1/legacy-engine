"""Archetype-sweep backtest — batch divergence mining for the sideboard advisor.

Runs ``backtest_board`` for EVERY archetype with enough in-window corpus against one shared
field, then aggregates the per-archetype divergences (scorer_only false-positive candidates,
winners_only blind-spot candidates) into ranked, root-cause-clustered findings. One
archetype's dogfooding found FoN/Consign/Defense Grid in a day; the sweep mines the whole
failure surface systematically.

ETHOS GUARDS (read before extending):

- Divergence stays a DIAGNOSTIC — a flag to investigate, never auto-calibration into the
  scorer (the pure-mechanics guardrail; see divergence-as-diagnostic-surface pattern). This
  module reads the scorer's output through ``backtest_board`` exactly as any caller would
  and never feeds anything back.
- Confidence-tier gating per archetype: thin winner samples are LABELED, not silently mined.
  Cluster ranking counts archetypes at "evolving"-or-better tiers first; clusters supported
  only by speculative-tier archetypes sink and carry ``n_archetypes_nonspeculative == 0`` as
  the explicit thin-signal marker. No invented down-weights — label-and-rank, never blend.
- Clustering is mechanical: a divergent card maps to the vulnerability tags it answers
  (hoser-catalog ``attacks`` when curated, else the same oracle-text derivation the
  promoted-candidates path uses). A card whose attribution is genuinely unknown lands in the
  first-class ``unclassified`` cluster — whose size is itself a diagnostic (catalog/tag gap).
  Note: ``_derive_attacks_for_promoted``'s conservative ``{combo}`` fallback fires exactly
  when NO derivation rule matched, so an exact-fallback result is treated as unclassified
  here rather than fabricating "combo" cluster membership.

Objective-search-split shape: ``run_sweep`` does the DB-heavy per-archetype loop and builds
a plain ``attacks_lookup`` mapping once; ``cluster_divergences`` / ``rank_clusters`` are pure
functions over hand-buildable inputs — unit-testable with no DB.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

import duckdb

from legacy_engine.advisory.backtest import BoardBacktest, backtest_board
from legacy_engine.advisory.field import FieldDistribution

log = logging.getLogger(__name__)

# Archetype labels that mean "unlabeled", excluded from enumeration alongside NULL.
_EXCLUDED_ARCHETYPE_LABELS: frozenset[str] = frozenset({"Unknown"})

# Confidence tiers that count toward a cluster's non-speculative archetype support.
_NONSPECULATIVE_TIERS: frozenset[str] = frozenset({"evolving", "established"})

# Cluster key for cards with no mechanical tag attribution.
UNCLASSIFIED_TAG = "unclassified"


@dataclass(frozen=True)
class ArchetypeSweepEntry:
    """One archetype's slot in the sweep — a backtest result or an honest skip."""

    archetype: str
    n_decks_in_window: int
    backtest: BoardBacktest | None      # None ⇔ skipped (see skipped_reason)
    skipped_reason: str | None


@dataclass(frozen=True)
class ClusterMember:
    """One (card, archetype) divergence observation inside a cluster."""

    card: str
    archetype: str
    adoption_pct: float                 # observed inclusion% (0.0 for scorer_only cards)
    confidence: str | None              # the archetype's winner-sample tier


@dataclass(frozen=True)
class DivergenceCluster:
    """All same-direction divergences sharing one answer-tag root cause."""

    tag: str                            # vulnerability tag, or UNCLASSIFIED_TAG
    direction: str                      # "scorer_only" | "winners_only"
    members: tuple[ClusterMember, ...]  # sorted by (card, archetype)
    n_archetypes: int                   # distinct archetypes represented
    n_archetypes_nonspeculative: int    # of those, tier evolving-or-better (0 = thin-only)
    total_adoption: float               # Σ adoption_pct over members
    tier_breakdown: dict[str, int]      # tier label → n distinct archetypes


@dataclass(frozen=True)
class SweepResult:
    """Full sweep output: per-archetype entries + ranked divergence clusters."""

    window: tuple[str | None, str | None]
    field_source: str
    field_scope: bool
    solver: str
    min_decks: int
    entries: tuple[ArchetypeSweepEntry, ...]
    clusters: tuple[DivergenceCluster, ...]   # ranked (see rank_clusters)
    warnings: tuple[str, ...]


def enumerate_archetypes(
    con: duckdb.DuckDBPyConnection,
    *,
    since: str | None,
    until: str | None,
    min_decks: int,
) -> list[tuple[str, int, bool]]:
    """All labeled archetypes with in-window deck counts: ``[(archetype, n, qualifies)]``.

    ``qualifies`` is ``n >= min_decks``. NULL-archetype decks and the
    ``_EXCLUDED_ARCHETYPE_LABELS`` sentinels ("Unknown") are excluded entirely — an
    unlabeled deck is not an archetype to sweep. Sorted by count DESC then name ASC
    (deterministic). Never raises — a query failure degrades to an empty list.
    """
    try:
        placeholders = ", ".join(["?"] * len(_EXCLUDED_ARCHETYPE_LABELS))
        rows = con.execute(
            f"""
            SELECT d.archetype, count(*) AS n
            FROM decks d
            JOIN tournaments t ON t.id = d.tournament_id
            WHERE d.archetype IS NOT NULL
              AND d.archetype NOT IN ({placeholders})
              AND (? IS NULL OR t.date >= ?)
              AND (? IS NULL OR t.date < ?)
            GROUP BY d.archetype
            ORDER BY n DESC, d.archetype ASC
            """,
            [*sorted(_EXCLUDED_ARCHETYPE_LABELS), since, since, until, until],
        ).fetchall()
    except Exception as exc:
        log.debug("enumerate_archetypes: query failed: %s", exc)
        return []
    return [(a, int(n), int(n) >= min_decks) for a, n in rows]


def _attacks_lookup_for(
    con: duckdb.DuckDBPyConnection,
    card_names: "set[str]",
) -> Callable[[str], frozenset[str]]:
    """Build the card → answer-tags lookup for clustering, resolved once for all names.

    Catalog ``attacks`` wins for curated cards; otherwise the promoted-candidates oracle
    derivation runs on the card's DB row. Unknown cards — and exact-``{combo}``-fallback
    derivations (which mean "no rule matched", see module docstring) — resolve to the empty
    frozenset, which ``cluster_divergences`` buckets as ``unclassified``.
    """
    from legacy_engine.advisory.sideboard import (
        _FALLBACK_ATTACKS,
        _derive_attacks_for_promoted,
        HOSER_CATALOG,
    )

    resolved: dict[str, frozenset[str]] = {}
    to_derive: list[str] = []
    for name in card_names:
        hoser = HOSER_CATALOG.get(name)
        if hoser is not None:
            resolved[name] = hoser.attacks
        else:
            to_derive.append(name)

    if to_derive:
        try:
            placeholders = ", ".join(["?"] * len(to_derive))
            rows = con.execute(
                f"SELECT name, oracle_text, type_line FROM cards WHERE name IN ({placeholders})",
                to_derive,
            ).fetchall()
        except Exception as exc:
            log.debug("_attacks_lookup_for: cards query failed: %s", exc)
            rows = []
        by_name = {name: (oracle or "", type_line or "") for name, oracle, type_line in rows}
        for name in to_derive:
            oracle_text, type_line = by_name.get(name, ("", ""))
            if not oracle_text:
                resolved[name] = frozenset()   # not in DB / no text → unclassified, not fabricated
                continue
            derived = _derive_attacks_for_promoted(name, oracle_text, type_line)
            resolved[name] = frozenset() if derived == _FALLBACK_ATTACKS else derived

    def lookup(name: str) -> frozenset[str]:
        return resolved.get(name, frozenset())

    return lookup


def cluster_divergences(
    entries: "tuple[ArchetypeSweepEntry, ...] | list[ArchetypeSweepEntry]",
    attacks_lookup: Callable[[str], frozenset[str]],
) -> tuple[DivergenceCluster, ...]:
    """PURE: group every divergent (card, archetype) observation by direction × answer-tag.

    A card contributes to EVERY tag it attacks (per-tag membership) — that is what lets a
    creature-interaction cluster emerge from Fatal Push + Snuff Out + Sheoldred's Edict even
    though their full tag sets differ. Directions never merge. Entries whose backtest is
    absent or has ``confidence is None`` (no winner sample — nothing observed to diverge
    from) contribute nothing. Output is deterministic: members sorted by (card, archetype),
    clusters sorted by (direction, tag); ranking is ``rank_clusters``' job.
    """
    buckets: dict[tuple[str, str], list[ClusterMember]] = {}
    for entry in entries:
        bt = entry.backtest
        if bt is None or bt.confidence is None:
            continue
        for direction, cards in (("scorer_only", bt.scorer_only), ("winners_only", bt.winners_only)):
            for card in cards:
                tags = attacks_lookup(card) or frozenset({UNCLASSIFIED_TAG})
                member = ClusterMember(
                    card=card,
                    archetype=entry.archetype,
                    adoption_pct=bt.observed_frequency.get(card, 0.0),
                    confidence=bt.confidence,
                )
                for tag in tags:
                    buckets.setdefault((direction, tag), []).append(member)

    clusters: list[DivergenceCluster] = []
    for (direction, tag), members in sorted(buckets.items()):
        members_sorted = tuple(sorted(members, key=lambda m: (m.card, m.archetype)))
        arch_tiers: dict[str, str | None] = {m.archetype: m.confidence for m in members_sorted}
        tier_breakdown: dict[str, int] = {}
        for tier in arch_tiers.values():
            label = tier if tier is not None else "none"
            tier_breakdown[label] = tier_breakdown.get(label, 0) + 1
        clusters.append(
            DivergenceCluster(
                tag=tag,
                direction=direction,
                members=members_sorted,
                n_archetypes=len(arch_tiers),
                n_archetypes_nonspeculative=sum(
                    1 for t in arch_tiers.values() if t in _NONSPECULATIVE_TIERS
                ),
                total_adoption=sum(m.adoption_pct for m in members_sorted),
                tier_breakdown=tier_breakdown,
            )
        )
    return tuple(clusters)


def rank_clusters(
    clusters: "tuple[DivergenceCluster, ...] | list[DivergenceCluster]",
) -> tuple[DivergenceCluster, ...]:
    """PURE: rank clusters most-systematic-first, honestly tier-gated.

    Sort key: non-speculative archetype support first (thin-only clusters sink), then total
    adoption, then raw archetype count, then (direction, tag) for a deterministic tail.
    """
    return tuple(
        sorted(
            clusters,
            key=lambda c: (
                -c.n_archetypes_nonspeculative,
                -c.total_adoption,
                -c.n_archetypes,
                c.direction,
                c.tag,
            ),
        )
    )


def run_sweep(
    con: duckdb.DuckDBPyConnection,
    field: FieldDistribution,
    *,
    since: str | None = None,
    until: str | None = None,
    min_decks: int = 20,
    field_scope: bool = True,
    solver: str = "ilp",
    progress: "Callable[[int, int, ArchetypeSweepEntry], None] | None" = None,
) -> SweepResult:
    """Backtest every qualifying archetype against ``field`` and cluster the divergences.

    ``since``/``until`` are passed to ``backtest_board`` unchanged (both ``None`` = full
    corpus, matching that module's documented convention — the CLI resolves its
    current-regime default explicitly and echoes it). ``progress``, when given, is called
    after each archetype (qualifying or skipped) with ``(index_1based, total, entry)``.

    Honest-degrade: a per-archetype failure becomes a skipped entry + warning, never a
    crash; an empty corpus yields empty entries/clusters.
    """
    enumerated = enumerate_archetypes(con, since=since, until=until, min_decks=min_decks)
    warnings: list[str] = []
    entries: list[ArchetypeSweepEntry] = []
    total = len(enumerated)

    for i, (archetype, n_decks, qualifies) in enumerate(enumerated, start=1):
        if not qualifies:
            entry = ArchetypeSweepEntry(
                archetype=archetype,
                n_decks_in_window=n_decks,
                backtest=None,
                skipped_reason=f"below --min-decks ({n_decks} < {min_decks})",
            )
        else:
            try:
                bt = backtest_board(
                    con, archetype, field,
                    since=since, until=until,
                    field_scope=field_scope, solver=solver,
                )
                entry = ArchetypeSweepEntry(
                    archetype=archetype,
                    n_decks_in_window=n_decks,
                    backtest=bt,
                    skipped_reason=None,
                )
            except Exception as exc:  # backtest_board never raises by contract; belt+braces
                log.debug("run_sweep: backtest failed for %r: %s", archetype, exc)
                warnings.append(f"{archetype}: backtest failed ({exc})")
                entry = ArchetypeSweepEntry(
                    archetype=archetype,
                    n_decks_in_window=n_decks,
                    backtest=None,
                    skipped_reason=f"backtest failed ({exc})",
                )
        entries.append(entry)
        if progress is not None:
            progress(i, total, entry)

    divergent_cards: set[str] = set()
    for entry in entries:
        if entry.backtest is not None and entry.backtest.confidence is not None:
            divergent_cards.update(entry.backtest.scorer_only)
            divergent_cards.update(entry.backtest.winners_only)

    attacks_lookup = _attacks_lookup_for(con, divergent_cards)
    clusters = rank_clusters(cluster_divergences(entries, attacks_lookup))

    return SweepResult(
        window=(since, until),
        field_source=field.field_source,
        field_scope=field_scope,
        solver=solver,
        min_decks=min_decks,
        entries=tuple(entries),
        clusters=clusters,
        warnings=tuple(warnings),
    )
