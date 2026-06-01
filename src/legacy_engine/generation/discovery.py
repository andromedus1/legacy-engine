"""Card-adjacency model for deck-generation mode 3 (gap discovery) — candidate nomination.

This module answers the *nomination* half of card-level discovery: given a shell ``D``
(an archetype + a maindeck), which cards that ``D`` does **not** already run are plausible
swap-in candidates? It deliberately lives OUTSIDE ``tuning.py`` — tuning stays the proven
in-pool swap engine; discovery composes alongside it and the sibling ``discovery-tuning``
feature adds the evidence (cross-archetype value transfer) + honesty (confidence gating).

A card ``X`` is an adjacency candidate for ``D`` when ALL hold (brief §1.2):
  1. ``X`` is not already in ``D`` (discovery, not re-suggestion);
  2. color-legal: ``X.colors ⊆ C(D)`` (colorless always legal);
  3. role-relevant: ``_card_roles(X)`` shares ≥1 role with the shell's flexible slots;
  4. CMC-band: ``X.cmc`` within the flex-slot curve band (median flex CMC ± 1).
Survivors are ranked by **decklist co-occurrence lift** (PMI of ``X`` against the
archetype's locked core over the windowed corpus) — the auditable, bounded analogue of
card2vec. Never-paired cards (PMI undefined) are excluded, not imputed.

The candidate universe is itself co-occurrence-derived (cards appearing in decks that run
the archetype core), so PMI is well-defined for every member and the scan stays bounded.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median

import duckdb

from legacy_engine.advisory.field import FieldDistribution, build_global_field
from legacy_engine.advisory.whattoplay import _card_roles
from legacy_engine.analytics.card_value import CardValue, card_values_vs
from legacy_engine.analytics.match_results import CardWinRates, compute_card_winrates
from legacy_engine.generation.consensus import _latest_regime_window, card_frequencies
from legacy_engine.ingestion.store import load_card
from legacy_engine.models.card import Card

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_LOCK_THRESHOLD: float = 0.65   # ≥65% inclusion → locked core (matches tuning)
_DEFAULT_COOCCUR_FLOOR: int = 5         # min decks running candidate-AND-core before PMI
_CMC_BAND: float = 1.0                  # ± window around the median flex CMC


# ---------------------------------------------------------------------------
# Unit 2 — the candidate record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AdjacencyCandidate:
    """One nominated swap-in candidate for a shell, with its adjacency audit trail.

    ``pmi`` is ``log[ P(X, core) / (P(X) · P(core)) ]`` over the windowed corpus — how
    much more often ``X`` is paired with this archetype's core than chance. ``matched_roles``
    is the (non-empty) intersection of the card's roles with the shell's wanted roles.
    ``in_sideboard`` flags a candidate already in the deck's *sideboard* — still a valid
    discovery for the 60.
    """

    name: str
    card: Card
    roles: frozenset[str]
    matched_roles: frozenset[str]
    cmc: float
    pmi: float
    decks_running: int      # P(X) numerator: window decks running X
    cooccur_decks: int      # decks running X AND core (≥ floor)
    in_sideboard: bool


# ---------------------------------------------------------------------------
# Unit 3 — the shell profile (what the deck "wants")
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ShellProfile:
    """The adjacency demand a shell expresses through its flexible slots."""

    core: frozenset[str]            # locked-core card names (inclusion ≥ lock_threshold)
    wanted_roles: frozenset[str]    # union of _card_roles over flex non-land cards
    cmc_lo: float                   # median flex non-land CMC − band
    cmc_hi: float                   # median flex non-land CMC + band
    color_identity: frozenset[str]  # union of card.colors over all of D


def _shell_profile(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    maindeck: dict[str, int],
    *,
    lock_threshold: float = _DEFAULT_LOCK_THRESHOLD,
    since: str | None = None,
    until: str | None = None,
) -> ShellProfile:
    """Derive the locked core, wanted-role set, CMC band, and color identity for ``D``.

    Core comes from the archetype's consensus inclusion (≥ ``lock_threshold``), matching
    what ``tuning.partition_flex`` locks. "Flex" is every maindeck card NOT in that core;
    the wanted-role set is the union of ``_card_roles`` over the flex *non-land* cards, and
    the CMC band straddles the median flex non-land CMC by ``_CMC_BAND``. Color identity is
    the union of every maindeck card's colors. An all-locked deck yields empty ``wanted_roles``
    (nothing swappable → no candidates surface).
    """
    if since is None and until is None:
        since, until = _latest_regime_window()

    freqs = card_frequencies(con, archetype, board="main", since=since, until=until)
    core = frozenset(cf.name for cf in freqs if cf.inclusion_pct >= lock_threshold)

    wanted: set[str] = set()
    flex_cmcs: list[float] = []
    colors: set[str] = set()

    for name in maindeck:
        card = load_card(con, name)
        if card is None:
            continue
        colors.update(card.colors)
        if name in core:
            continue
        # flex card
        if card.is_land:
            continue
        wanted.update(_card_roles(card))
        flex_cmcs.append(card.cmc)

    if flex_cmcs:
        mid = median(flex_cmcs)
        cmc_lo, cmc_hi = mid - _CMC_BAND, mid + _CMC_BAND
    else:
        # No flex non-land cards: band is empty (lo > hi) so nothing passes the CMC gate.
        cmc_lo, cmc_hi = 1.0, -1.0

    return ShellProfile(
        core=core,
        wanted_roles=frozenset(wanted),
        cmc_lo=cmc_lo,
        cmc_hi=cmc_hi,
        color_identity=frozenset(colors),
    )


# ---------------------------------------------------------------------------
# Unit 4 (trickiest) — co-occurrence counts over the windowed corpus
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _CooccurCounts:
    total_decks: int                       # in-window decks (the universe denominator)
    core_decks: int                        # decks running ≥k core cards → P(core)
    per_card: dict[str, tuple[int, int]]   # name -> (decks_running_X, decks_running_X_and_core)


def _cooccurrence(
    con: duckdb.DuckDBPyConnection,
    core: frozenset[str],
    *,
    k: int,
    since: str | None,
    until: str | None,
    cooccur_floor: int = _DEFAULT_COOCCUR_FLOOR,
) -> _CooccurCounts:
    """Count, over in-window maindecks, how often each card pairs with the archetype core.

    A deck "runs the core" when it runs ≥ ``k`` distinct cards from ``core``. The candidate
    universe is every card appearing in a core-running deck (so co-occurrence ≥ 1 by
    construction); cards with fewer than ``cooccur_floor`` core-co-occurrences are dropped
    (thin → excluded, not imputed). Returns raw counts only — PMI is computed in Python.
    """
    if not core:
        return _CooccurCounts(total_decks=0, core_decks=0, per_card={})

    core_list = sorted(core)
    placeholders = ",".join("?" for _ in core_list)

    # Window filter mirrors card_frequencies (date-bounded, main board).
    rows = con.execute(
        f"""
        WITH deck_pool AS (
            SELECT d.tournament_id, d.deck_idx
            FROM decks d
            JOIN tournaments t ON t.id = d.tournament_id
            WHERE (? IS NULL OR t.date >= ?)
              AND (? IS NULL OR t.date < ?)
        ),
        deck_main AS (
            SELECT dp.tournament_id, dp.deck_idx, dc.name
            FROM deck_pool dp
            JOIN deck_cards dc
              ON dc.tournament_id = dp.tournament_id
             AND dc.deck_idx      = dp.deck_idx
            WHERE dc.board = 'main'
        ),
        core_hits AS (
            SELECT tournament_id, deck_idx,
                   count(DISTINCT CASE WHEN name IN ({placeholders}) THEN name END) AS n_core
            FROM deck_main
            GROUP BY tournament_id, deck_idx
        ),
        is_core AS (
            SELECT tournament_id, deck_idx, (n_core >= ?) AS runs_core
            FROM core_hits
        ),
        card_decks AS (
            SELECT dm.name,
                   count(DISTINCT (dm.tournament_id, dm.deck_idx)) AS decks_running,
                   count(DISTINCT CASE WHEN ic.runs_core
                                       THEN (dm.tournament_id, dm.deck_idx) END) AS decks_with_core
            FROM deck_main dm
            JOIN is_core ic
              ON ic.tournament_id = dm.tournament_id
             AND ic.deck_idx      = dm.deck_idx
            GROUP BY dm.name
        )
        SELECT name, decks_running, decks_with_core
        FROM card_decks
        WHERE decks_with_core >= ?
        """,
        [since, since, until, until, *core_list, k, cooccur_floor],
    ).fetchall()

    total_row = con.execute(
        """
        SELECT count(*)
        FROM decks d
        JOIN tournaments t ON t.id = d.tournament_id
        WHERE (? IS NULL OR t.date >= ?)
          AND (? IS NULL OR t.date < ?)
        """,
        [since, since, until, until],
    ).fetchone()
    total_decks = int(total_row[0]) if total_row else 0

    core_row = con.execute(
        f"""
        WITH deck_pool AS (
            SELECT d.tournament_id, d.deck_idx
            FROM decks d
            JOIN tournaments t ON t.id = d.tournament_id
            WHERE (? IS NULL OR t.date >= ?)
              AND (? IS NULL OR t.date < ?)
        ),
        core_hits AS (
            SELECT dp.tournament_id, dp.deck_idx,
                   count(DISTINCT CASE WHEN dc.name IN ({placeholders}) THEN dc.name END) AS n_core
            FROM deck_pool dp
            JOIN deck_cards dc
              ON dc.tournament_id = dp.tournament_id
             AND dc.deck_idx      = dp.deck_idx
            WHERE dc.board = 'main'
            GROUP BY dp.tournament_id, dp.deck_idx
        )
        SELECT count(*) FROM core_hits WHERE n_core >= ?
        """,
        [since, since, until, until, *core_list, k],
    ).fetchone()
    core_decks = int(core_row[0]) if core_row else 0

    per_card = {name: (int(run), int(with_core)) for name, run, with_core in rows}
    return _CooccurCounts(total_decks=total_decks, core_decks=core_decks, per_card=per_card)


# ---------------------------------------------------------------------------
# Unit 5 — public entry: nominate + gate + rank
# ---------------------------------------------------------------------------

def _core_overlap_k(core_size: int) -> int:
    """A deck "runs the core" when it has ≥ this many of the core cards."""
    return max(3, math.ceil(0.6 * core_size))


def adjacency_candidates(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    maindeck: dict[str, int],
    sideboard: dict[str, int] | None = None,
    *,
    lock_threshold: float = _DEFAULT_LOCK_THRESHOLD,
    cooccur_floor: int = _DEFAULT_COOCCUR_FLOOR,
    limit: int | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[AdjacencyCandidate]:
    """Nominate + rank cards adjacent to deck ``D`` that ``D`` does not already run.

    Pipeline: build the shell profile → count co-occurrence over the window → for each
    universe card apply the four gates (∉ D, color-legal, role-relevant, CMC-band), compute
    PMI, keep if defined → rank by PMI DESC (tie-break cooccur DESC then name). Returns at
    most ``limit`` candidates (all when ``None``). Window defaults to the latest ban regime.
    """
    if since is None and until is None:
        since, until = _latest_regime_window()

    sideboard = sideboard or {}
    profile = _shell_profile(
        con, archetype, maindeck,
        lock_threshold=lock_threshold, since=since, until=until,
    )

    if not profile.core or not profile.wanted_roles:
        return []

    k = _core_overlap_k(len(profile.core))
    counts = _cooccurrence(
        con, profile.core, k=k, since=since, until=until, cooccur_floor=cooccur_floor,
    )
    if counts.total_decks == 0 or counts.core_decks == 0:
        return []

    p_core = counts.core_decks / counts.total_decks
    candidates: list[AdjacencyCandidate] = []

    for name, (decks_running, cooccur_decks) in counts.per_card.items():
        if name in maindeck:
            continue  # gate 1: discovery, not re-suggestion
        card = load_card(con, name)
        if card is None:
            continue
        # gate 2: color-legal (colorless always legal)
        if not set(card.colors) <= profile.color_identity:
            continue
        # gate 3: role-relevant
        roles = _card_roles(card)
        matched = roles & profile.wanted_roles
        if not matched:
            continue
        # gate 4: CMC band
        if not (profile.cmc_lo <= card.cmc <= profile.cmc_hi):
            continue
        # PMI = log[ P(X,core) / (P(X) · P(core)) ]; all counts > 0 here.
        p_x = decks_running / counts.total_decks
        p_x_core = cooccur_decks / counts.total_decks
        denom = p_x * p_core
        if denom <= 0 or p_x_core <= 0:
            continue  # PMI undefined — exclude, don't impute
        pmi = math.log(p_x_core / denom)

        candidates.append(
            AdjacencyCandidate(
                name=name,
                card=card,
                roles=frozenset(roles),
                matched_roles=frozenset(matched),
                cmc=card.cmc,
                pmi=pmi,
                decks_running=decks_running,
                cooccur_decks=cooccur_decks,
                in_sideboard=name in sideboard,
            )
        )

    candidates.sort(key=lambda c: (-c.pmi, -c.cooccur_decks, c.name))
    if limit is not None:
        candidates = candidates[:limit]
    return candidates


# ===========================================================================
# Discovery tuning (epic-gap-discovery-discovery-tuning) — value transfer +
# confidence-gated exploratory suggestion surface, composed atop the adjacency
# model above. Kept OUT of tuning.py; tuning stays the proven-swap engine.
# ===========================================================================

# Roles where cross-archetype value transfer is honest (answers / disruption /
# generic card-advantage — value is largely pilot/shell-independent). Curated like
# advisory.sideboard.HOSER_CATALOG. Synergy/engine roles (threat, ritual, storm, tutor,
# graveyard_recursion, stax, fast_mana) are NON-transferable: pooled lift is meaningless
# out of deck context, so those candidates require in-shell evidence (unavailable in v1).
TRANSFERABLE_ROLES: frozenset[str] = frozenset(
    {"counter", "removal", "protection", "card_advantage", "discard"}
)

_DISCOVERY_DISCLAIMER: str = (
    "Discovery suggestions are PRESENCE-CORRELATIONAL and TRANSFERRED from cross-field "
    "data (how the card performs vs these threats in OTHER decks), NOT causal and NOT "
    "goldfish-validated in this shell. Treat as candidates to test, not swaps to make."
)


@dataclass(frozen=True)
class DiscoverySuggestion:
    """One exploratory swap-in suggestion: an adjacent card with transferred field value."""

    name: str
    matched_roles: frozenset[str]
    transferred_value: float            # Σ field.shares[M]·lift over gate-clearing opponents
    per_opponent: dict[str, CardValue]  # opponent → the gate-clearing CardValue (audit trail)
    n_total: int                        # Σ cv.n over kept opponents
    pmi: float                          # carried from the AdjacencyCandidate
    cmc: float
    in_sideboard: bool


@dataclass(frozen=True)
class DiscoveryResult:
    """Capped, ranked discovery suggestions plus the honest accounting of what was omitted."""

    suggestions: list[DiscoverySuggestion]  # capped, sorted transferred_value DESC
    n_considered: int                       # adjacency candidates examined
    omitted_below_gate: int                 # transferable cands with no established lift>0 cell
    omitted_synergy: list[str]              # synergy-role cands (need in-shell/goldfish validation)
    capped_out: int                         # surfaced-eligible candidates beyond the cap
    gate: tuple[str, ...]
    disclaimer: str


def _transfer_from_values(
    values: dict[str, CardValue],
    field: FieldDistribution,
    *,
    gate: tuple[str, ...],
) -> tuple[float, dict[str, CardValue]]:
    """PURE: field-weighted positive transferred lift over gate-clearing established cells.

    Keeps opponent ``M`` iff ``cv.tier in gate`` AND ``cv.lift > 0`` AND ``M in field.shares``;
    its contribution is ``field.shares[M] · cv.lift``. Returns ``(total, kept_values)``. No DB,
    no MC — testable with hand-built ``CardValue``s. ``lift`` is already the two-level-EB-shrunk
    estimate (regresses to ~0 as n→0), so no further shrinkage is applied here.
    """
    total = 0.0
    kept: dict[str, CardValue] = {}
    for opponent, cv in values.items():
        if cv.tier not in gate or cv.lift <= 0.0:
            continue
        share = field.shares.get(opponent)
        if not share:
            continue
        total += share * cv.lift
        kept[opponent] = cv
    return total, kept


def discover_candidates(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    maindeck: dict[str, int],
    sideboard: dict[str, int] | None = None,
    field: FieldDistribution | None = None,
    *,
    rates: CardWinRates | None = None,
    cap: int = 5,
    gate: tuple[str, ...] = ("established",),
    lock_threshold: float = _DEFAULT_LOCK_THRESHOLD,
    cooccur_floor: int = _DEFAULT_COOCCUR_FLOOR,
    adjacency_limit: int | None = None,
    since: str | None = None,
    until: str | None = None,
) -> DiscoveryResult:
    """Nominate (adjacency) → role-split → transfer/gate → assemble the suggestion list.

    Transferable-role candidates are scored by field-weighted cross-archetype lift, gated at the
    ``gate`` tier (default established, n≥100). Synergy/engine-role candidates are nominated but
    have no honest transfer (and no in-shell-conditioned value source in v1), so they are omitted
    and reported in ``omitted_synergy`` — the future goldfish pillar is their validation path.
    Never enters the tuner's greedy objective. Capped at ``cap``; the capped-out / below-gate /
    synergy counts are all reported (no silent caps).
    """
    if since is None and until is None:
        since, until = _latest_regime_window()
    if field is None:
        field = build_global_field(con)
    if rates is None:
        rates = compute_card_winrates(con, since=since, until=until)

    cands = adjacency_candidates(
        con, archetype, maindeck, sideboard,
        lock_threshold=lock_threshold, cooccur_floor=cooccur_floor,
        limit=adjacency_limit, since=since, until=until,
    )

    eligible: list[DiscoverySuggestion] = []
    omitted_below_gate = 0
    omitted_synergy: list[str] = []

    for cand in cands:
        if not (cand.matched_roles & TRANSFERABLE_ROLES):
            omitted_synergy.append(cand.name)  # synergy/engine — no honest transfer in v1
            continue
        # Value the candidate vs each field opponent (rates is precomputed → dict lookups).
        # card_values_vs is keyed by card NAME, so unwrap to build an opponent→CardValue map.
        values: dict[str, CardValue] = {
            opponent: card_values_vs(rates, [cand.name], "main", opponent)[cand.name]
            for opponent in field.shares
        }
        total, kept = _transfer_from_values(values, field, gate=gate)
        if total <= 0.0 or not kept:
            omitted_below_gate += 1
            continue
        eligible.append(
            DiscoverySuggestion(
                name=cand.name,
                matched_roles=cand.matched_roles,
                transferred_value=total,
                per_opponent=kept,
                n_total=sum(cv.n for cv in kept.values()),
                pmi=cand.pmi,
                cmc=cand.cmc,
                in_sideboard=cand.in_sideboard,
            )
        )

    eligible.sort(key=lambda s: (-s.transferred_value, -s.n_total, s.name))
    capped_out = max(0, len(eligible) - cap)
    return DiscoveryResult(
        suggestions=eligible[:cap],
        n_considered=len(cands),
        omitted_below_gate=omitted_below_gate,
        omitted_synergy=sorted(omitted_synergy),
        capped_out=capped_out,
        gate=gate,
        disclaimer=_DISCOVERY_DISCLAIMER,
    )
