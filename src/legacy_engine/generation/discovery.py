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

from legacy_engine.advisory.whattoplay import _card_roles
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
