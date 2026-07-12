"""Entity series builder — per-(archetype|camp) density-adaptive bucketed history.

Generalizes ``analytics/affectedness.py``'s "one batched scan, then pure Python" shape to a
richer per-entity time series: every corpus week gets a deck count, a field-share denominator,
a marginal win/loss record (rounds-derived), and flex-band card-inclusion counts. Downstream
change-point detectors (``detect.py``/``bocpd.py``) consume these series without ever touching
DuckDB (objective-search-split — see ``docs/briefs/change-point-detection.md`` §6, §1).

**Entities**: every ``decks.archetype`` with >= ``min_entity_decks`` corpus decks (excluding the
``"Unknown"`` and ``"Conflict(...)"`` classifier-junk labels — real decks, just not a detectable
entity) is a *parent* entity. Every ``(archetype, variant)`` pair with >= ``min_camp_decks`` decks
is additionally a *camp* entity, labeled ``f"{archetype} [{variant}]"`` (the matchup camp-label
convention from ``analytics/match_results.py::effective_label``), with ``parent`` set to the
underlying archetype. A camp does not require its own archetype to also clear the parent floor.

**Buckets** are ISO-Monday-aligned weeks (matching DuckDB's ``date_trunc('week', ...)``
convention), grouped ``bucket_weeks`` at a time (1/2/4, density-adaptive — brief §6) as
*consecutive entries of the corpus's active-week list* (weeks where NO tournament happened
anywhere are dropped from that list, never zero-padded — brief's "weeks where the whole corpus
has no tournaments may be skipped consistently"), anchored so the first group starts at the
corpus's first active week. A week where THIS entity had zero decks but the corpus was active
elsewhere still appears with ``decks=0`` (brief: "so downstream series are evenly spaced").

**Flex band**: reuses ``discovery.build_feature_matrix``'s 10%/95% inclusion-rate thresholds
(the ubiquitous chassis and rare tail carry no era signal any more than they carry split signal)
but, unlike discovery's mainboard-only scope, counts a card from *either* board — a card moving
between main and sideboard is itself a signal this module needs to see.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

import duckdb

from legacy_engine.analytics.match_results import parse_match_result

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Flex-band inclusion-rate thresholds — identical cutoffs to
# analytics/discovery.py::build_feature_matrix (flex_lo/flex_hi): below 10% is the rare tail,
# above 95% is the ubiquitous chassis, neither carries split/era signal.
_FLEX_LO: float = 0.10
_FLEX_HI: float = 0.95

# Density-adaptive bucket width (brief §6 small-sample playbook): median weekly deck count over
# the corpus's active weeks decides how many ISO weeks each bucket pools.
_WEEKLY_DENSITY_FLOOR: int = 10   # median >= this -> 1-week buckets
_BIWEEKLY_DENSITY_FLOOR: int = 5  # median >= this (below the weekly floor) -> 2-week buckets
                                  # below both -> 4-week buckets

# Classifier-junk labels: real decks, but never their own detectable entity (epic decision).
_EXCLUDED_ENTITY_LABELS = frozenset({"Unknown"})


def _is_entity_label(archetype: str) -> bool:
    """True when ``archetype`` is eligible to be (or seed) a detectable entity."""
    return archetype not in _EXCLUDED_ENTITY_LABELS and not archetype.startswith("Conflict(")


def _week_start(d: date) -> date:
    """Monday-aligned ISO week start (matches DuckDB's ``date_trunc('week', ...)``)."""
    return d - timedelta(days=d.isoweekday() - 1)


def _bucket_weeks_for(median_weekly: float) -> int:
    """Density-adaptive bucket width from an entity's median weekly deck count."""
    if median_weekly >= _WEEKLY_DENSITY_FLOOR:
        return 1
    if median_weekly >= _BIWEEKLY_DENSITY_FLOOR:
        return 2
    return 4


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Bucket:
    """One chronological time slice of an entity's series.

    ``card_incl`` is sparse: only flex-band cards actually run by >=1 entity deck in this bucket
    appear (an absent key means zero decks ran that card this bucket, not "unknown").
    """

    start: str                    # ISO date, bucket start (Monday)
    complete: bool                # False for the leading/trailing partial bucket
    decks: int                    # entity decks in bucket
    field_decks: int              # all labeled decks in bucket (share denominator)
    wins: int                     # entity match wins in bucket (marginal, rounds-derived)
    losses: int
    card_incl: dict[str, int]     # flex-band card -> count of entity decks running it


@dataclass(frozen=True)
class EntitySeries:
    """A single entity's (parent archetype, or camp) chronological bucketed history."""

    entity: str                   # "Doomsday" or "Dimir Tempo [Barrowgoyf]"
    parent: str                   # == entity for parents
    bucket_weeks: int             # 1 | 2 | 4 (density-adaptive)
    flex_cards: tuple[str, ...]   # entity flex band (10-95% inclusion over its whole pool)
    buckets: tuple[Bucket, ...]   # chronological


# ---------------------------------------------------------------------------
# Batched scans (objective-search-split: one query per table, no per-entity loop)
# ---------------------------------------------------------------------------

_DECKS_SQL = """
SELECT dk.tournament_id, dk.deck_idx, dk.archetype, dk.variant, CAST(t.date AS DATE) AS d
FROM decks dk
JOIN tournaments t ON t.id = dk.tournament_id
WHERE dk.archetype IS NOT NULL
  AND (? IS NULL OR t.provenance = ?)
"""

_DECK_CARDS_SQL = """
SELECT dc.tournament_id, dc.deck_idx, dc.name
FROM deck_cards dc
JOIN decks dk ON dk.tournament_id = dc.tournament_id AND dk.deck_idx = dc.deck_idx
JOIN tournaments t ON t.id = dk.tournament_id
WHERE dk.archetype IS NOT NULL
  AND (? IS NULL OR t.provenance = ?)
"""

# Rounds joined to archetype/variant labels via the cardinality-safe dup/uniq_decks guard —
# the same idiom as analytics/match_results.py's _DUP_UNIQ_CTE, reproduced here (not imported:
# match_results' shared CTE is a private module constant, and this query's output shape — both
# sides' archetype AND variant, no directed matchup cells — is distinct enough to not warrant a
# cross-module private import).
_ROUNDS_SQL = """
WITH
dup AS (
    SELECT tournament_id, lower(trim(player)) AS norm
    FROM decks
    GROUP BY tournament_id, lower(trim(player))
    HAVING count(*) > 1
),
uniq_decks AS (
    SELECT tournament_id, lower(trim(player)) AS norm,
           ANY_VALUE(archetype) AS archetype, ANY_VALUE(variant) AS variant
    FROM decks
    GROUP BY tournament_id, lower(trim(player))
)
SELECT CAST(t.date AS DATE) AS d, r.player1, r.player2, r.result,
       d1.archetype AS arch1, d1.variant AS var1,
       d2.archetype AS arch2, d2.variant AS var2,
       (du1.norm IS NOT NULL) AS amb1,
       (du2.norm IS NOT NULL) AS amb2
FROM rounds r
JOIN tournaments t ON t.id = r.tournament_id
LEFT JOIN uniq_decks d1 ON d1.tournament_id = r.tournament_id
                       AND d1.norm = lower(trim(r.player1))
LEFT JOIN uniq_decks d2 ON d2.tournament_id = r.tournament_id
                       AND d2.norm = lower(trim(r.player2))
LEFT JOIN dup du1 ON du1.tournament_id = r.tournament_id
                 AND du1.norm = lower(trim(r.player1))
LEFT JOIN dup du2 ON du2.tournament_id = r.tournament_id
                 AND du2.norm = lower(trim(r.player2))
WHERE (? IS NULL OR t.provenance = ?)
"""


def build_entity_series(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None = None,
    min_entity_decks: int = 100,
    min_camp_decks: int = 30,
    force_bucket_weeks: int | None = None,
) -> dict[str, EntitySeries]:
    """Build every qualifying entity's bucketed series from three batched DuckDB scans.

    ``force_bucket_weeks`` overrides the density-adaptive bucket width for every entity —
    the drift alarm uses ``force_bucket_weeks=1`` because it is a RECENCY instrument: a 4-week
    entity's density-adaptive bucketing can leave a whole ban cliff inside the incomplete
    trailing bucket, invisible to any complete-bucket tail check (the Candelabra/Tron case).

    ``min_entity_decks`` (default 100, the established-tier floor) gates parent archetypes;
    ``min_camp_decks`` (default 30, the evolving-tier floor) gates camp entities — both exposed
    as keywords purely so tests can shrink the fixtures needed to exercise the floor logic; the
    architecture's own operating point is 100/30.

    Three passes, each a single query (objective-search-split — no per-entity queries):
      1. ``decks`` x ``tournaments`` — population, per-entity totals, weekly field/entity counts.
      2. ``deck_cards`` — flex-band pool inclusion + weekly flex-band inclusion counts.
      3. ``rounds`` (dup-safe join to ``decks``) — weekly marginal win/loss counts.

    Returns ``{}`` when the corpus has no labeled decks at all, or no entity clears either floor.
    """
    deck_rows = con.execute(_DECKS_SQL, [provenance, provenance]).fetchall()
    if not deck_rows:
        return {}

    # ---- Pass 1: population + entity eligibility -----------------------------
    deck_week: dict[tuple[str, int], date] = {}
    deck_archetype: dict[tuple[str, int], str] = {}
    deck_variant: dict[tuple[str, int], str | None] = {}
    field_by_week: Counter[date] = Counter()
    archetype_totals: Counter[str] = Counter()
    camp_totals: Counter[tuple[str, str]] = Counter()
    corpus_min_date: date | None = None
    corpus_max_date: date | None = None

    for tournament_id, deck_idx, archetype, variant, d in deck_rows:
        key = (tournament_id, deck_idx)
        wk = _week_start(d)
        deck_week[key] = wk
        deck_archetype[key] = archetype
        deck_variant[key] = variant
        field_by_week[wk] += 1
        archetype_totals[archetype] += 1
        if variant:
            camp_totals[(archetype, variant)] += 1
        if corpus_min_date is None or d < corpus_min_date:
            corpus_min_date = d
        if corpus_max_date is None or d > corpus_max_date:
            corpus_max_date = d

    canonical_weeks = sorted(field_by_week)

    parent_entities: set[str] = {
        a for a, cnt in archetype_totals.items()
        if cnt >= min_entity_decks and _is_entity_label(a)
    }
    camp_entities: dict[tuple[str, str], str] = {
        (a, v): f"{a} [{v}]"
        for (a, v), cnt in camp_totals.items()
        if cnt >= min_camp_decks and _is_entity_label(a)
    }

    if not parent_entities and not camp_entities:
        return {}

    entity_parent: dict[str, str] = {a: a for a in parent_entities}
    entity_pool_size: dict[str, int] = {a: archetype_totals[a] for a in parent_entities}
    for (a, v), label in camp_entities.items():
        entity_parent[label] = a
        entity_pool_size[label] = camp_totals[(a, v)]

    def _entities_for(archetype: str, variant: str | None) -> list[str]:
        """Every entity name a (archetype, variant) pair contributes to (parent, then camp)."""
        out = []
        if archetype in parent_entities:
            out.append(archetype)
        if variant and (archetype, variant) in camp_entities:
            out.append(camp_entities[(archetype, variant)])
        return out

    # deck key -> entity names it belongs to (a deck may feed BOTH its parent and its camp)
    deck_entities: dict[tuple[str, int], list[str]] = {}
    for key in deck_week:
        ents = _entities_for(deck_archetype[key], deck_variant[key])
        if ents:
            deck_entities[key] = ents

    # ---- Pass 1 continued: weekly deck counts per entity ---------------------
    entity_week_decks: dict[str, Counter[date]] = defaultdict(Counter)
    for key, ents in deck_entities.items():
        wk = deck_week[key]
        for e in ents:
            entity_week_decks[e][wk] += 1

    # ---- Pass 2: deck_cards -> pool inclusion + weekly flex inclusion --------
    card_rows = con.execute(_DECK_CARDS_SQL, [provenance, provenance]).fetchall()
    deck_cardset: dict[tuple[str, int], set[str]] = defaultdict(set)
    for tournament_id, deck_idx, name in card_rows:
        key = (tournament_id, deck_idx)
        if key in deck_entities:  # bound memory to decks feeding a qualifying entity
            deck_cardset[key].add(name)

    entity_pool_inclusion: dict[str, Counter[str]] = defaultdict(Counter)
    for key, cardset in deck_cardset.items():
        for e in deck_entities[key]:
            for card in cardset:
                entity_pool_inclusion[e][card] += 1

    entity_flex_cards: dict[str, tuple[str, ...]] = {}
    for e, pool_size in entity_pool_size.items():
        counts = entity_pool_inclusion.get(e, Counter())
        entity_flex_cards[e] = tuple(sorted(
            card for card, cnt in counts.items()
            if pool_size and _FLEX_LO <= (cnt / pool_size) <= _FLEX_HI
        ))

    entity_week_card_incl: dict[str, dict[date, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    for key, cardset in deck_cardset.items():
        wk = deck_week[key]
        for e in deck_entities[key]:
            flex_set = entity_flex_cards.get(e)
            if not flex_set:
                continue
            for card in cardset.intersection(flex_set):
                entity_week_card_incl[e][wk][card] += 1

    # ---- Pass 3: rounds -> weekly marginal win/loss per entity ----------------
    entity_week_wins: dict[str, Counter[date]] = defaultdict(Counter)
    entity_week_losses: dict[str, Counter[date]] = defaultdict(Counter)

    round_rows = con.execute(_ROUNDS_SQL, [provenance, provenance]).fetchall()
    for d, _p1, p2, match_result, arch1, var1, arch2, var2, amb1, amb2 in round_rows:
        if not (p2 and str(p2).strip()):
            continue  # bye: no real opponent
        if amb1 or amb2:
            continue  # ambiguous within-tournament player-name collision
        if arch1 is None or arch2 is None:
            continue  # at least one side unlabeled — cannot attribute safely
        outcome = parse_match_result(match_result)
        if outcome is None or outcome.winner is None:
            continue  # unparseable, bye/forfeit string, or a draw

        wk = _week_start(d)
        if outcome.winner == "p1":
            w_arch, w_var, l_arch, l_var = arch1, var1, arch2, var2
        else:
            w_arch, w_var, l_arch, l_var = arch2, var2, arch1, var1

        w_ents = set(_entities_for(w_arch, w_var))
        l_ents = set(_entities_for(l_arch, l_var))

        # A round can be simultaneously a mirror at one granularity (both decks are the same
        # PARENT archetype) and a decisive cross-camp match at another (different camps within
        # that archetype) — each affected entity is scored independently: present on both sides
        # (mirror, at THAT entity's granularity) credits +1 win AND +1 loss (match_results.py's
        # ArchetypeRecord mirror precedent); present on one side only credits that side.
        for e in w_ents | l_ents:
            in_w = e in w_ents
            in_l = e in l_ents
            if in_w and in_l:
                entity_week_wins[e][wk] += 1
                entity_week_losses[e][wk] += 1
            elif in_w:
                entity_week_wins[e][wk] += 1
            elif in_l:
                entity_week_losses[e][wk] += 1

    # ---- Assemble EntitySeries per entity -------------------------------------
    series_by_entity: dict[str, EntitySeries] = {}
    for entity in sorted(entity_parent):
        weekly_counts = [entity_week_decks[entity].get(w, 0) for w in canonical_weeks]
        median_weekly = statistics.median(weekly_counts) if weekly_counts else 0.0
        bucket_weeks = force_bucket_weeks or _bucket_weeks_for(median_weekly)

        chunks = [
            canonical_weeks[i:i + bucket_weeks]
            for i in range(0, len(canonical_weeks), bucket_weeks)
        ]

        buckets: list[Bucket] = []
        for chunk in chunks:
            start = chunk[0]
            chunk_end = chunk[-1] + timedelta(weeks=1)

            decks = sum(entity_week_decks[entity].get(w, 0) for w in chunk)
            field_decks = sum(field_by_week.get(w, 0) for w in chunk)
            wins = sum(entity_week_wins[entity].get(w, 0) for w in chunk)
            losses = sum(entity_week_losses[entity].get(w, 0) for w in chunk)

            card_incl: dict[str, int] = {}
            for w in chunk:
                week_counts = entity_week_card_incl.get(entity, {}).get(w)
                if not week_counts:
                    continue
                for card, cnt in week_counts.items():
                    card_incl[card] = card_incl.get(card, 0) + cnt

            leading_incomplete = corpus_min_date is not None and corpus_min_date > start
            trailing_incomplete = (
                corpus_max_date is not None
                and corpus_max_date < chunk_end - timedelta(days=1)
            )

            buckets.append(Bucket(
                start=start.isoformat(),
                complete=not (leading_incomplete or trailing_incomplete),
                decks=decks,
                field_decks=field_decks,
                wins=wins,
                losses=losses,
                card_incl=card_incl,
            ))

        series_by_entity[entity] = EntitySeries(
            entity=entity,
            parent=entity_parent[entity],
            bucket_weeks=bucket_weeks,
            flex_cards=entity_flex_cards.get(entity, ()),
            buckets=tuple(buckets),
        )

    return series_by_entity
