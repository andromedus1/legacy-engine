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
    """

    matchups: dict[tuple[str, str], MatchupTally]  # keyed (archetype_a, archetype_b)
    archetypes: dict[str, ArchetypeRecord]
    coverage: MatchCoverage
    provenance: str | None  # "online" | "paper" | None
    mirror_n: dict[str, int] = field(default_factory=dict)  # per-archetype mirror count


# ---------------------------------------------------------------------------
# Unit 4: Join query + accumulator
# ---------------------------------------------------------------------------

_JOIN_SQL = """
WITH
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
-- return one arbitrary archetype — but those rows are flagged by the dup CTE
-- and dropped before the archetype is ever used.
uniq_decks AS (
    SELECT tournament_id, lower(trim(player)) AS norm,
           ANY_VALUE(archetype) AS archetype
    FROM decks
    GROUP BY tournament_id, lower(trim(player))
)
SELECT t.provenance, r.player1, r.player2, r.result,
       d1.archetype AS arch1, d2.archetype AS arch2,
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


def compute_match_results(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None = None
) -> MatchResults:
    """Join rounds→archetype labels, parse results, accumulate directed + marginal tallies.

    ``provenance`` filters to ``"online"``/``"paper"`` tournaments; ``None`` =
    all.  Only rounds-bearing events contribute (Leagues have no rounds), so
    this aggregate's n is the matchup-n population — strictly separate from
    the metashare deck-count n.

    Mirror matches (``arch1 == arch2``) are **not** written to directed
    ``matchups`` cells; their count is carried in
    ``coverage.mirror_matches``.  Each mirror match credits the matching
    archetype with ``+1 win`` and ``+1 loss`` in ``archetypes`` so its
    marginal win-rate remains honest.
    """
    cov = MatchCoverage()
    matchups: dict[tuple[str, str], MatchupTally] = {}
    archetypes: dict[str, ArchetypeRecord] = {}
    mirror_n: dict[str, int] = {}

    rows = con.execute(_JOIN_SQL, [provenance, provenance]).fetchall()

    for _prov, _p1, p2, result, arch1, arch2, amb1, amb2 in rows:
        cov.total_pairings += 1

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
    )
