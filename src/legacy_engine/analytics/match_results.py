"""Match-outcome extraction: rounds → archetype win/loss aggregates.

Joins the DuckDB ``rounds`` table to archetype labels via ``decks``, parses
aggregate match-score strings (``"2-1"`` = one match win for player1), and
accumulates directed matchup tallies and per-archetype marginal records.

This is the shared data-prep foundation that both ``metashare`` (win-rate-
weighted §3c) and ``matchup-matrix`` depend on.  Emits raw ``{wins, losses,
n}`` aggregates only — Wilson CIs, shrinkage, and matchup stats are owned by
downstream consumers.
"""

from __future__ import annotations

from collections.abc import Collection
from collections import Counter
from dataclasses import dataclass, field

import duckdb


# ---------------------------------------------------------------------------
# Unit 1: Result-string parser
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatchOutcome:
    """A parsed match score from player1's perspective.

    ``p1_games`` / ``p2_games`` are the game counts from the aggregate score
    string (e.g. ``"2-1"`` → ``p1_games=2, p2_games=1``).  ``winner`` is
    ``"p1"`` or ``"p2"`` when one side has strictly more games, ``None`` on a
    tie (draw).
    """

    p1_games: int
    p2_games: int
    winner: str | None  # "p1" | "p2" | None (draw / no decisive winner)


def parse_match_result(result: str | None) -> MatchOutcome | None:
    """Parse an aggregate match-score string into a match-level outcome.

    Accepts ``"2-1"``, ``"2-0"``, ``"1-2"``, ``"0-2"``, and draw forms
    ``"1-1"`` / ``"1-1-1"`` (3rd token = draws, ignored for winner
    determination).  Returns the ``MatchOutcome`` with
    ``winner="p1"|"p2"`` when one side has strictly more games,
    ``winner=None`` on a tie.

    Returns ``None`` (NOT a draw) when the string is absent, empty, a bye /
    forfeit, or otherwise unparseable — the caller routes ``None`` to the
    dropped-rows coverage count.  Never raises; one bad row must not crash the
    aggregation.
    """
    if not result or not result.strip():
        return None
    parts = result.strip().split("-")
    if len(parts) < 2:
        return None
    try:
        p1 = int(parts[0])
        p2 = int(parts[1])
    except (ValueError, IndexError):
        return None
    if p1 > p2:
        winner = "p1"
    elif p2 > p1:
        winner = "p2"
    else:
        winner = None
    return MatchOutcome(p1_games=p1, p2_games=p2, winner=winner)


# ---------------------------------------------------------------------------
# Unit 2: Player-name normalizer
# ---------------------------------------------------------------------------


def normalize_player(name: str | None) -> str:
    """Normalize a player handle for the rounds↔decks join: strip + casefold.

    Mirrors the SQL join key ``lower(trim(player))`` exactly so the Python
    and SQL sides never diverge.  Returns ``""`` for ``None``/blank.
    """
    return (name or "").strip().lower()


# ---------------------------------------------------------------------------
# Unit 3: Aggregate record types
# ---------------------------------------------------------------------------


@dataclass
class MatchupTally:
    """Directed cell: archetype_a's record vs archetype_b.

    ``n`` = wins + losses (decisive non-mirror matches only).
    Mirror matches are tracked separately in ``MatchCoverage.mirror_matches``
    and are not written to directed cells.
    """

    archetype_a: str
    archetype_b: str
    wins: int = 0
    losses: int = 0

    @property
    def n(self) -> int:
        """Total decisive matches (wins + losses)."""
        return self.wins + self.losses


@dataclass
class ArchetypeRecord:
    """Per-archetype marginal record across all opponents.

    This is the win-rate-weighted meta-share input (§3c).  Mirror matches
    contribute ``+1 win`` and ``+1 loss`` to keep the marginal win-rate honest
    (a mirror is one archetype-win and one archetype-loss simultaneously).
    ``n`` = wins + losses.
    """

    archetype: str
    wins: int = 0
    losses: int = 0

    @property
    def n(self) -> int:
        """Total matches contributing to win-rate (wins + losses)."""
        return self.wins + self.losses


@dataclass
class MatchCoverage:
    """How much of the rounds data resolved — surfaced, never silent.

    Every counter is incremented exactly once per pairing row so that
    ``total_pairings == decisive_matched + unmatched + dropped_byes_draws
    + mirror_matches + ambiguous_player_names``.
    """

    total_pairings: int = 0
    decisive_matched: int = 0        # both players resolved + decisive non-mirror winner
    unmatched: int = 0               # ≥1 player did not resolve to a labeled deck
    dropped_byes_draws: int = 0      # parsed to None or winner is None
    mirror_matches: int = 0          # both resolved archetypes equal
    ambiguous_player_names: int = 0  # pairing excluded: a player's normalized name is
                                     # non-unique within its tournament (dup-CTE hit)

    @property
    def match_rate(self) -> float:
        """Fraction of pairings that resolved to a decisive matched outcome."""
        return self.decisive_matched / self.total_pairings if self.total_pairings else 0.0


@dataclass
class MatchResults:
    """On-demand match-outcome aggregate consumed by ``metashare`` and ``matchup-matrix``.

    ``matchups`` is keyed by ``(archetype_a, archetype_b)`` — both directed
    pairs are materialised for every non-mirror decisive match so the matrix
    is symmetric.  Mirror matches are not written here; their count lives in
    ``coverage.mirror_matches``.

    ``archetypes`` is keyed by archetype label string.  Mirror matches
    contribute ``+1 win`` and ``+1 loss`` to the matching archetype's marginal
    so win-rate-weighted meta-share remains honest.

    ``mirror_n`` tracks per-archetype mirror-match counts so the matchup-matrix
    can render honest mirror cells (n only, p=0.5 fixed).  Additive field —
    existing consumers that do not read it are unaffected.

    ``provenance`` records the filter that was applied: ``"online"``,
    ``"paper"``, or ``None`` (all sources).

    ``camp_parent`` (feature-multi-split-matrix, additive): maps every relabeled camp
    label back to the parent archetype it was split from (``"Doomsday [Murktide]" ->
    "Doomsday"``). Populated whenever ``split_variant``/``split_variants`` relabels at
    least one deck — including the single-archetype ``split_variant`` path, so a
    single-split caller gets the same provenance for free. Empty when neither is set.
    No existing consumer reads it.
    """

    matchups: dict[tuple[str, str], MatchupTally]  # keyed (archetype_a, archetype_b)
    archetypes: dict[str, ArchetypeRecord]
    coverage: MatchCoverage
    provenance: str | None  # "online" | "paper" | None
    mirror_n: dict[str, int] = field(default_factory=dict)  # per-archetype mirror count
    camp_parent: dict[str, str] = field(default_factory=dict)  # camp label -> parent archetype
    matchup_event_counts: dict[tuple[str, str], dict[str, int]] = field(default_factory=dict)
    matchup_month_counts: dict[tuple[str, str], dict[str, int]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Per-card win-rate record types (Unit 1 of epic-deck-generation-per-card-value)
# ---------------------------------------------------------------------------


@dataclass
class CardMatchupRecord:
    """Directed per-(card, board, opponent-archetype) win/loss cell.

    ``n`` = wins + losses (decisive non-mirror matches only; excludes
    byes/draws/mirrors/ambiguous/unmatched in the same way
    ``compute_match_results`` does).  Board is ``"main"`` or ``"side"``.
    """

    card: str
    board: str
    opponent: str
    wins: int = 0
    losses: int = 0

    @property
    def n(self) -> int:
        """Total decisive matches (wins + losses) for this cell."""
        return self.wins + self.losses


@dataclass
class CardMarginalRecord:
    """Per-(card, board) win/loss aggregate across ALL opponent archetypes.

    This is the denser prior used by the two-level empirical-Bayes shrinkage
    in ``card_value.py``.  Mirrors and byes/draws/ambiguous are excluded
    identically to ``CardMatchupRecord`` — the marginal is strictly the
    sum over all ``CardMatchupRecord`` cells for the same (card, board).
    """

    card: str
    board: str
    wins: int = 0
    losses: int = 0

    @property
    def n(self) -> int:
        """Total decisive matches (wins + losses) for this card."""
        return self.wins + self.losses


@dataclass
class CardWinRates:
    """Raw per-card win-rate aggregates (presence-correlational, not causal).

    ``matchup``: directed per-(card, board, opponent) cells.
    ``marginal``: per-(card, board) aggregate across all opponents — the
    empirical-Bayes prior for the two-level shrinkage.
    ``baseline_winrate``: global decisive win-rate across all cards/matches
    (≈ 0.5 by construction since every match credits one win + one loss
    globally; stored explicitly as the grand prior for the marginal shrink).
    ``coverage``: the same resolution counters as ``compute_match_results``
    for the same corpus + window, so callers can audit parity.
    ``provenance``: the filter applied (``"online"``/``"paper"``/``None``).
    """

    matchup: dict[tuple[str, str, str], CardMatchupRecord]  # (card, board, opponent)
    marginal: dict[tuple[str, str], CardMarginalRecord]     # (card, board)
    baseline_winrate: float
    coverage: MatchCoverage
    provenance: str | None


# ---------------------------------------------------------------------------
# Variant label-split (epic-subarchetype-resolution-matchup-cells)
# ---------------------------------------------------------------------------


def effective_label(
    archetype: str | None, variant: str | None, split_variant: str | None
) -> str | None:
    """Return the row/cell label for a deck, applying an optional single-archetype label-split.

    ``split_variant`` is the ONE archetype (if any) whose ``decks.variant`` camps should be
    resolved separately.  When ``archetype == split_variant`` this returns the camp label
    ``f"{archetype} [{variant or 'unlabeled'}]"`` — a ``NULL`` variant becomes the visible
    ``"unlabeled"`` residue camp rather than disappearing.  In every other case (``split_variant``
    is ``None``, or ``archetype`` doesn't match it, or ``archetype`` is ``None``) this returns
    ``archetype`` unchanged — the identity path that keeps the no-flag output byte-identical.
    """
    if archetype is None or split_variant is None or archetype != split_variant:
        return archetype
    return f"{archetype} [{variant or 'unlabeled'}]"


def _split_set_label(
    archetype: str | None, variant: str | None, split_set: frozenset[str]
) -> str | None:
    """Generalization of ``effective_label`` to a SET of split parents (feature-multi-split-matrix).

    Same ``f"{archetype} [{variant or 'unlabeled'}]"`` convention, but the relabel test is
    membership in ``split_set`` rather than equality to one archetype. With a singleton
    ``split_set`` this is byte-identical to ``effective_label(archetype, variant, next(iter(split_set)))``
    (the singleton-equivalence acceptance criterion); with ``split_set == frozenset()`` this is
    the literal identity path — ``archetype`` is returned unchanged, matching ``effective_label``'s
    own ``split_variant=None`` identity branch. ``effective_label`` itself is untouched; this is a
    private, additive helper used only by ``compute_match_results``.
    """
    if archetype is None or archetype not in split_set:
        return archetype
    return f"{archetype} [{variant or 'unlabeled'}]"


# ---------------------------------------------------------------------------
# Unit 4: Join query + accumulator
# ---------------------------------------------------------------------------

# Shared CTE fragment — used by both _JOIN_SQL and _CARD_WINRATES_SQL so there is
# exactly ONE copy of the dup/uniq_decks guard logic (SSOT; no parser divergence).
_DUP_UNIQ_CTE = """\
-- dup: normalized player names that occur more than once within a tournament.
-- A LEFT JOIN hit (du1.norm IS NOT NULL) means the pairing is ambiguous —
-- we cannot safely attribute a single deck to that player.
dup AS (
    SELECT tournament_id, lower(trim(player)) AS norm
    FROM decks
    GROUP BY tournament_id, lower(trim(player))
    HAVING count(*) > 1
),
-- uniq_decks: one row per (tournament_id, normalized-player), collapsing any
-- duplicate deck rows so the rounds LEFT JOIN stays cardinality-safe.  For
-- unique players this is identical to the raw decks row; for duplicates we
-- return one arbitrary archetype/variant — but those rows are flagged by the
-- dup CTE and dropped before either is ever used.
uniq_decks AS (
    SELECT tournament_id, lower(trim(player)) AS norm,
           ANY_VALUE(archetype) AS archetype,
           ANY_VALUE(variant) AS variant
    FROM decks
    GROUP BY tournament_id, lower(trim(player))
)\
"""

_JOIN_SQL = f"""
WITH
{_DUP_UNIQ_CTE}
SELECT t.provenance, t.id, CAST(t.date AS VARCHAR), r.player1, r.player2, r.result,
       d1.archetype AS arch1, d2.archetype AS arch2,
       d1.variant AS var1, d2.variant AS var2,
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
  AND (? IS NULL OR t.date >= ?)
  AND (? IS NULL OR t.date <  ?)
"""


def compute_match_results(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None = None,
    since: str | None = None, until: str | None = None,
    split_variant: str | None = None,
    split_variants: Collection[str] | None = None,
) -> MatchResults:
    """Join rounds→archetype labels, parse results, accumulate directed + marginal tallies.

    ``provenance`` filters to ``"online"``/``"paper"`` tournaments; ``None`` =
    all.  ``since``/``until`` window by ``tournaments.date`` over a half-open
    ``[since, until)`` interval (matching ``regime_windows`` / ``card_frequencies``;
    note the sibling ``compute_card_winrates`` uses an inclusive upper bound — a
    pre-existing minor discrepancy, intentionally not reconciled here).  Both
    ``None`` (the default) = full corpus, byte-identical to the un-windowed query.
    Only rounds-bearing events contribute (Leagues have no rounds), so this
    aggregate's n is the matchup-n population — strictly separate from the
    metashare deck-count n.

    ``split_variant`` (opt-in): when set to an archetype name, any deck whose
    ``archetype`` equals it is relabeled to its ``decks.variant`` camp via
    ``effective_label`` — on BOTH sides of every pairing — before any tallying
    happens, so mirror/marginal/directed-cell logic below operates on camp labels
    as if they were ordinary archetypes.  ``None`` (the default) leaves every label
    unchanged (byte-identical to the pre-split behavior).

    ``split_variants`` (opt-in, feature-multi-split-matrix): the multi-parent
    generalization of ``split_variant`` — every archetype in the collection is
    relabeled to its camp on both sides of a pairing, in ONE scan (all staged parents
    camp-labeled simultaneously). Passing BOTH ``split_variant`` and ``split_variants``
    raises ``ValueError``. Internally both normalize to one ``split_set``: a singleton
    ``split_variant="Doomsday"`` and ``split_variants=["Doomsday"]`` produce identical
    ``matchups``/``archetypes``/``coverage``/``mirror_n``/``camp_parent`` output. Neither
    given (the default) is the literal identity relabel path.

    Mirror matches (``arch1 == arch2``) are **not** written to directed
    ``matchups`` cells; their count is carried in
    ``coverage.mirror_matches``.  Each mirror match credits the matching
    archetype with ``+1 win`` and ``+1 loss`` in ``archetypes`` so its
    marginal win-rate remains honest.
    """
    if split_variant is not None and split_variants is not None:
        raise ValueError("pass split_variant or split_variants, not both")
    split_set = frozenset((split_variant,)) if split_variant else frozenset(split_variants or ())

    cov = MatchCoverage()
    matchups: dict[tuple[str, str], MatchupTally] = {}
    archetypes: dict[str, ArchetypeRecord] = {}
    mirror_n: dict[str, int] = {}
    camp_parent: dict[str, str] = {}
    matchup_event_counts: dict[tuple[str, str], Counter[str]] = {}
    matchup_month_counts: dict[tuple[str, str], Counter[str]] = {}

    rows = con.execute(
        _JOIN_SQL, [provenance, provenance, since, since, until, until]
    ).fetchall()

    for _prov, event_id, event_date, _p1, p2, result, arch1, arch2, var1, var2, amb1, amb2 in rows:
        cov.total_pairings += 1
        orig1, orig2 = arch1, arch2
        arch1 = _split_set_label(arch1, var1, split_set)
        arch2 = _split_set_label(arch2, var2, split_set)
        if orig1 is not None and orig1 in split_set:
            camp_parent[arch1] = orig1
        if orig2 is not None and orig2 in split_set:
            camp_parent[arch2] = orig2

        # ── #7 Blank-opponent bye: not a real pairing ───────────────────────
        # A bye row has an empty/None player2; classifying it here prevents the
        # blank player2 from falling through to unmatched (arch2 would be NULL).
        if not (p2 and str(p2).strip()):
            cov.dropped_byes_draws += 1
            continue

        # ── #1 Ambiguous normalized name: cannot safely attribute a deck ────
        # When a player's normalized name (lower(trim(...))) is non-unique
        # within the tournament the LEFT JOIN to decks can produce multiple
        # rows (cardinality explosion).  The dup-CTE flags these; we surface
        # them in ambiguous_player_names rather than silently inflating n's or
        # mislabeling the pairing as unmatched.
        if amb1 or amb2:
            cov.ambiguous_player_names += 1
            continue

        # ── Unmatched: at least one player has no labeled deck ──────────────
        if arch1 is None or arch2 is None:
            cov.unmatched += 1
            continue

        # ── Parse result; drop byes, forfeits, draws ────────────────────────
        outcome = parse_match_result(result)
        if outcome is None or outcome.winner is None:
            cov.dropped_byes_draws += 1
            continue

        # ── Mirror match: same archetype on both sides ──────────────────────
        if arch1 == arch2:
            cov.mirror_matches += 1
            mirror_n[arch1] = mirror_n.get(arch1, 0) + 1
            # Marginal: a mirror is +1 win AND +1 loss for that archetype
            rec = archetypes.setdefault(arch1, ArchetypeRecord(archetype=arch1))
            rec.wins += 1
            rec.losses += 1
            continue

        # ── Decisive non-mirror match ───────────────────────────────────────
        if outcome.winner == "p1":
            winner_arch, loser_arch = arch1, arch2
        else:
            winner_arch, loser_arch = arch2, arch1

        # Directed matchup cells — both directions materialised for symmetry
        w_key = (winner_arch, loser_arch)
        l_key = (loser_arch, winner_arch)
        if w_key not in matchups:
            matchups[w_key] = MatchupTally(archetype_a=winner_arch, archetype_b=loser_arch)
        if l_key not in matchups:
            matchups[l_key] = MatchupTally(archetype_a=loser_arch, archetype_b=winner_arch)
        matchups[w_key].wins += 1
        matchups[l_key].losses += 1
        month = event_date[:7]
        for key in (w_key, l_key):
            matchup_event_counts.setdefault(key, Counter())[str(event_id)] += 1
            matchup_month_counts.setdefault(key, Counter())[month] += 1

        # Per-archetype marginals
        w_rec = archetypes.setdefault(winner_arch, ArchetypeRecord(archetype=winner_arch))
        l_rec = archetypes.setdefault(loser_arch, ArchetypeRecord(archetype=loser_arch))
        w_rec.wins += 1
        l_rec.losses += 1

        cov.decisive_matched += 1

    return MatchResults(
        matchups=matchups,
        archetypes=archetypes,
        coverage=cov,
        provenance=provenance,
        mirror_n=mirror_n,
        camp_parent=camp_parent,
        matchup_event_counts={k: dict(v) for k, v in matchup_event_counts.items()},
        matchup_month_counts={k: dict(v) for k, v in matchup_month_counts.items()},
    )


# ---------------------------------------------------------------------------
# Per-card win-rate query + accumulator
# (Unit 1 of epic-deck-generation-per-card-value)
# ---------------------------------------------------------------------------

# Reuses _DUP_UNIQ_CTE verbatim (SSOT).  Returns one row per pairing with the
# same cardinality-safe guards as _JOIN_SQL; adds tournament_id + normalized
# player names so the Python accumulator can attribute cards without re-joining.
_CARD_WINRATES_SQL = f"""
WITH
{_DUP_UNIQ_CTE}
SELECT
    r.tournament_id,
    lower(trim(r.player1)) AS p1_norm,
    lower(trim(r.player2)) AS p2_norm,
    r.result,
    d1.archetype AS arch1,
    d2.archetype AS arch2,
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
  AND (? IS NULL OR t.date >= ?)
  AND (? IS NULL OR t.date <= ?)
"""

# Board normalization: cache stores "Mainboard"/"Sideboard" but deck_cards stores
# "main"/"side" (store.py inserts as "main"/"side" already — this map is a safety net
# in case a data source produces the verbose form).
_BOARD_NORM = {"mainboard": "main", "sideboard": "side", "main": "main", "side": "side"}


def compute_card_winrates(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None = None,
    since: str | None = None,
    until: str | None = None,
    deck_archetype: str | None = None,
    deck_variant: str | None = None,
) -> CardWinRates:
    """Compute per-card win-rate aggregates (presence-correlational, not causal).

    **Design (option 2 from epic-deck-generation-per-card-value):** two queries —
    (a) the cardinality-safe dup/uniq_decks rounds join (shared CTE, zero parser
    divergence) to get resolved decisive non-mirror matches; (b) a deck_cards→decks
    map restricted to players appearing in those resolved matches.  Attribution is a
    Python loop: each match credits a win to each card in the winner's deck vs the
    loser's archetype, and a loss to each card in the loser's deck vs the winner's.

    **Invariant**: a card in a deck contributes exactly 1 to a (card, board, opponent)
    cell's ``n`` per resolved match — no fan-out double-count.  Verified by the
    no-fan-out invariant test in test_card_winrates.py.

    ``since``/``until`` window by ``tournaments.date`` (ISO string comparison, same
    collation that DuckDB uses for VARCHAR date columns in this schema).

    ``provenance`` filters to ``"online"``/``"paper"``; ``None`` = all.

    ``deck_archetype``/``deck_variant`` (opt-in, epic-subarchetype-resolution-card-winrate):
    restrict the deck→cards map (query b) to decks whose ``archetype`` (and, when given,
    ``variant``) match — the attribution loop itself is UNCHANGED.  A resolved match still
    requires both sides to resolve to a labeled deck as before; only the *cards* attributed
    are scoped to the requested archetype/camp, so a card's win-rate reflects that archetype's
    own decks rather than every archetype that plays it.  Both ``None`` (the default) is
    byte-identical to the pre-conditioning query (no filter applied).
    """
    cov = MatchCoverage()
    matchup: dict[tuple[str, str, str], CardMatchupRecord] = {}
    marginal: dict[tuple[str, str], CardMarginalRecord] = {}

    # ── Step 1: Resolve decisive matches (reusing _DUP_UNIQ_CTE guards) ──────
    rows = con.execute(
        _CARD_WINRATES_SQL,
        [provenance, provenance, since, since, until, until],
    ).fetchall()

    # Collect resolved (tournament_id, winner_norm, loser_norm, winner_arch, loser_arch)
    resolved: list[tuple[str, str, str, str, str]] = []

    for tid, p1_norm, p2_norm, result, arch1, arch2, amb1, amb2 in rows:
        cov.total_pairings += 1

        # ── Blank-opponent bye ───────────────────────────────────────────────
        if not (p2_norm and p2_norm.strip()):
            cov.dropped_byes_draws += 1
            continue

        # ── Ambiguous normalized name ────────────────────────────────────────
        if amb1 or amb2:
            cov.ambiguous_player_names += 1
            continue

        # ── Unmatched: at least one player has no labeled deck ───────────────
        if arch1 is None or arch2 is None:
            cov.unmatched += 1
            continue

        # ── Parse result; drop byes/forfeits/draws ───────────────────────────
        outcome = parse_match_result(result)
        if outcome is None or outcome.winner is None:
            cov.dropped_byes_draws += 1
            continue

        # ── Mirror match ─────────────────────────────────────────────────────
        if arch1 == arch2:
            cov.mirror_matches += 1
            continue

        # ── Decisive non-mirror ──────────────────────────────────────────────
        if outcome.winner == "p1":
            winner_norm, loser_norm = p1_norm, p2_norm
            winner_arch, loser_arch = arch1, arch2
        else:
            winner_norm, loser_norm = p2_norm, p1_norm
            winner_arch, loser_arch = arch2, arch1

        resolved.append((tid, winner_norm, loser_norm, winner_arch, loser_arch))
        cov.decisive_matched += 1

    if not resolved:
        return CardWinRates(
            matchup=matchup,
            marginal=marginal,
            baseline_winrate=0.5,
            coverage=cov,
            provenance=provenance,
        )

    # ── Step 2: Build deck_cards map restricted to resolved players ───────────
    # Key: (tournament_id, norm_player) → list of (board, card_name)
    # Restricting to resolved players bounds memory: we only load cards for decks
    # that appear in at least one resolved match.
    resolved_players: set[tuple[str, str]] = set()
    for tid, w_norm, l_norm, _wa, _la in resolved:
        resolved_players.add((tid, w_norm))
        resolved_players.add((tid, l_norm))

    # Fetch deck_cards joined to decks for all relevant (tournament_id, norm) pairs.
    # board values from deck_cards are already "main"/"side" (see store.py), but we
    # normalise defensively via _BOARD_NORM.
    #
    # deck_archetype/deck_variant (opt-in): restrict this map to decks matching the
    # requested archetype/camp.  Decks that don't match simply contribute no rows, so
    # the Step 3 attribution loop below sees empty card lists for them — the loop
    # itself never changes.  Both None (the default) leaves the WHERE a no-op via the
    # "? IS NULL OR ..." guard, byte-identical to the unconditioned query.
    deck_cards_rows = con.execute(
        """
        SELECT dc.tournament_id,
               lower(trim(d.player)) AS norm,
               dc.board,
               dc.name
        FROM deck_cards dc
        JOIN decks d ON d.tournament_id = dc.tournament_id
                    AND d.deck_idx = dc.deck_idx
        WHERE (? IS NULL OR d.archetype = ?)
          AND (? IS NULL OR d.variant = ?)
        """,
        [deck_archetype, deck_archetype, deck_variant, deck_variant],
    ).fetchall()

    # deck_map[(tournament_id, norm)] = list of (board, card_name)
    # Multiple rows for the same card (different count) are still one card presence.
    deck_map: dict[tuple[str, str], list[tuple[str, str]]] = {}
    seen_card: dict[tuple[str, str, str, str], None] = {}  # dedup within a deck

    for dc_tid, dc_norm, dc_board, dc_name in deck_cards_rows:
        key = (dc_tid, dc_norm)
        if key not in resolved_players:
            continue  # skip players not in any resolved match (memory bound)
        board = _BOARD_NORM.get(dc_board.lower() if dc_board else "", dc_board or "main")
        dedup_key = (dc_tid, dc_norm, dc_board, dc_name)
        if dedup_key in seen_card:
            continue  # same card appears in multiple deck_cards rows (different count rows)
        seen_card[dedup_key] = None
        deck_map.setdefault(key, []).append((board, dc_name))

    # ── Step 3: Attribute wins/losses per resolved match ─────────────────────
    for tid, winner_norm, loser_norm, winner_arch, loser_arch in resolved:
        winner_cards = deck_map.get((tid, winner_norm), [])
        loser_cards = deck_map.get((tid, loser_norm), [])

        # Winner's cards vs loser's archetype
        for board, card in winner_cards:
            mkey = (card, board, loser_arch)
            if mkey not in matchup:
                matchup[mkey] = CardMatchupRecord(card=card, board=board, opponent=loser_arch)
            matchup[mkey].wins += 1

            mgkey = (card, board)
            if mgkey not in marginal:
                marginal[mgkey] = CardMarginalRecord(card=card, board=board)
            marginal[mgkey].wins += 1

        # Loser's cards vs winner's archetype
        for board, card in loser_cards:
            mkey = (card, board, winner_arch)
            if mkey not in matchup:
                matchup[mkey] = CardMatchupRecord(card=card, board=board, opponent=winner_arch)
            matchup[mkey].losses += 1

            mgkey = (card, board)
            if mgkey not in marginal:
                marginal[mgkey] = CardMarginalRecord(card=card, board=board)
            marginal[mgkey].losses += 1

    # baseline_winrate is the MATCH-level grand prior: every decisive match is one
    # win and one loss at the match level, so the symmetric prior is exactly 0.5.
    # This is what the marginal card-value shrinks toward (a card with no signal
    # regresses to "an even match"). Note this is the match-level prior, NOT the
    # card-attribution win-rate (which would only equal 0.5 if winner and loser
    # decks always had identical card counts).
    baseline_winrate = 0.5

    return CardWinRates(
        matchup=matchup,
        marginal=marginal,
        baseline_winrate=baseline_winrate,
        coverage=cov,
        provenance=provenance,
    )
