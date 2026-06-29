"""Matchup-conditioned sideboard-slot test.

Answers: *does owning card X (on a board) change an archetype's win-rate vs a specific
opponent?* Splits an archetype's decisive matches vs one opponent into two cohorts —
decks that OWN a candidate card on ``board`` vs decks that do NOT — and compares the
cohort win-rates with Wilson/Jeffreys CIs and a Fisher's-exact significance test on the
difference.

**PRESENCE-CORRELATIONAL, NOT CAUSAL.** Owning a card in the registered 75 is not the same
as boarding it in for the match (the corpus has no game-level / sideboarding-action data),
and the decks that choose to run a card may differ systematically (selection confound).
Read the diff as suggestive, gated by CI + significance + sample tier — never as proof.
This is the statistic that, without its significance test, nearly let a noisy −8.2pt point
estimate (Null Rod vs Blue Artifacts, p≈0.33) read as a real finding.

Reuses ``match_results``' cardinality-safe dedup CTE (so the rounds↔decks join never fans
out on duplicate ``(tournament, player)`` deck rows) and ``matchup.wilson_or_jeffreys_ci``.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
from scipy.stats import fisher_exact

from legacy_engine.analytics.match_results import _DUP_UNIQ_CTE, parse_match_result
from legacy_engine.analytics.matchup import wilson_or_jeffreys_ci
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class SlotContrastCell:
    """One candidate card's with-vs-without win-rate contrast in a single matchup."""

    card: str
    board: str                              # "main" | "side"
    opponent: str
    w_with: int                             # hero wins / decisive matches, deck OWNS card on board
    n_with: int
    w_without: int
    n_without: int
    p_with: float | None                    # w_with / n_with (None when n_with == 0)
    p_without: float | None
    ci_with: tuple[float, float] | None     # Wilson/Jeffreys 95% CI (None when n == 0)
    ci_without: tuple[float, float] | None
    diff: float | None                      # p_with − p_without (None if either cohort empty)
    p_value: float | None                   # Fisher's exact, two-sided (None if either cohort empty)
    significant: bool                       # p_value is not None and p_value < alpha
    tier_with: ConfidenceLevel
    tier_without: ConfidenceLevel


@dataclass
class SlotContrastReport:
    """All candidate cards' contrasts for one (archetype, opponent, board, window)."""

    archetype: str
    opponent: str
    board: str
    window_label: str
    n_matches: int                          # total decisive archetype-vs-opponent matches in window
    cells: list[SlotContrastCell]           # sorted by abs(diff) desc; None-diff last; tie-break name
    degraded: bool                          # True when no decisive matches resolved
    note: str | None                        # named-reason banner when degraded

    @property
    def any_thin(self) -> bool:
        """True if any cohort in any cell is below the speculative floor (n < 30)."""
        return any(
            c.tier_with == "speculative" or c.tier_without == "speculative" for c in self.cells
        )


# ---------------------------------------------------------------------------
# Match resolution query (reuses match_results' dedup guards verbatim)
# ---------------------------------------------------------------------------

_RESOLVE_SQL = f"""
WITH
{_DUP_UNIQ_CTE}
SELECT r.tournament_id,
       lower(trim(r.player1)) AS p1,
       lower(trim(r.player2)) AS p2,
       r.result,
       d1.archetype AS a1,
       d2.archetype AS a2,
       (du1.norm IS NOT NULL) AS amb1,
       (du2.norm IS NOT NULL) AS amb2
FROM rounds r
JOIN tournaments t ON t.id = r.tournament_id
LEFT JOIN uniq_decks d1 ON d1.tournament_id = r.tournament_id AND d1.norm = lower(trim(r.player1))
LEFT JOIN uniq_decks d2 ON d2.tournament_id = r.tournament_id AND d2.norm = lower(trim(r.player2))
LEFT JOIN dup du1 ON du1.tournament_id = r.tournament_id AND du1.norm = lower(trim(r.player1))
LEFT JOIN dup du2 ON du2.tournament_id = r.tournament_id AND du2.norm = lower(trim(r.player2))
WHERE (? IS NULL OR t.provenance = ?)
  AND (? IS NULL OR t.date >= ?)
  AND (? IS NULL OR t.date <  ?)   -- half-open [since, until): aligns with compute_match_results'
                                   -- _JOIN_SQL, NOT compute_card_winrates' inclusive upper bound.
  AND ((d1.archetype = ? AND d2.archetype = ?) OR (d1.archetype = ? AND d2.archetype = ?))
"""


def pair_adaptive_since(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    opponent: str,
    *,
    provenance: str | None = None,
) -> str | None:
    """The adaptive ban-aware window start for an (archetype, opponent) pair.

    Mirrors ``matchup.build_adaptive_matrix``: the later of the two archetypes'
    ``valid_since`` horizons (``None`` = full corpus when neither was ban-affected).
    """
    from legacy_engine.analytics.affectedness import archetype_valid_since

    vs = archetype_valid_since(con, [archetype, opponent], provenance=provenance)
    dates = [d for d in (vs.get(archetype), vs.get(opponent)) if d]
    return max(dates) if dates else None


def card_matchup_contrast(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    opponent: str,
    *,
    board: str = "side",
    cards: list[str] | None = None,
    since: str | None = None,
    until: str | None = None,
    provenance: str | None = None,
    alpha: float = 0.05,
    window_label: str = "",
) -> SlotContrastReport:
    """Contrast each candidate card's with-vs-without win-rate for ``archetype`` vs ``opponent``.

    ``cards=None`` tests every card the archetype runs on ``board`` (the "what in my SB helps
    vs Y?" scan); pass a list to focus. Matches are resolved with the same guards as
    ``compute_match_results`` (drop byes/draws/mirrors/ambiguous/unmatched); ownership is keyed
    by ``(tournament_id, normalized_player)`` — the grain matches are resolved to — so no
    ``deck_idx`` plumbing and no fan-out on duplicate deck rows.
    """
    # --- 1. Resolve decisive archetype-vs-opponent matches → (tid, hero_norm, won) ----------
    rows = con.execute(
        _RESOLVE_SQL,
        [provenance, provenance, since, since, until, until,
         archetype, opponent, opponent, archetype],
    ).fetchall()

    matches: list[tuple[tuple[str, str], bool]] = []  # ((tid, hero_norm), hero_won)
    for tid, p1, p2, result, a1, a2, amb1, amb2 in rows:
        if not (p2 and p2.strip()) or amb1 or amb2 or a1 is None or a2 is None or a1 == a2:
            continue
        outcome = parse_match_result(result)
        if outcome is None or outcome.winner is None:
            continue
        if a1 == archetype and a2 == opponent:
            matches.append(((tid, p1), outcome.winner == "p1"))
        elif a2 == archetype and a1 == opponent:
            matches.append(((tid, p2), outcome.winner == "p2"))

    if not matches:
        return SlotContrastReport(
            archetype=archetype, opponent=opponent, board=board,
            window_label=window_label, n_matches=0, cells=[], degraded=True,
            note=f"No decisive {archetype!r} vs {opponent!r} matches in this window.",
        )

    # --- 2. Ownership: card → set of (tid, norm) for archetype decks holding it on board -----
    own_rows = con.execute(
        """
        SELECT dc.name, dc.tournament_id, lower(trim(d.player))
        FROM deck_cards dc
        JOIN decks d ON d.tournament_id = dc.tournament_id AND d.deck_idx = dc.deck_idx
        WHERE d.archetype = ? AND dc.board = ?
        """,
        [archetype, board],
    ).fetchall()

    owners: dict[str, set[tuple[str, str]]] = {}
    for name, tid, norm in own_rows:
        owners.setdefault(name, set()).add((tid, norm))

    candidates = cards if cards is not None else sorted(owners.keys())

    # --- 3. Bucket each match per candidate card and compute stats --------------------------
    cells: list[SlotContrastCell] = []
    for card in candidates:
        owned = owners.get(card, set())
        w_with = n_with = w_without = n_without = 0
        for hero, won in matches:
            if hero in owned:
                n_with += 1
                w_with += int(won)
            else:
                n_without += 1
                w_without += int(won)

        p_with = (w_with / n_with) if n_with else None
        p_without = (w_without / n_without) if n_without else None
        ci_with = wilson_or_jeffreys_ci(w_with, n_with, alpha=alpha) if n_with else None
        ci_without = wilson_or_jeffreys_ci(w_without, n_without, alpha=alpha) if n_without else None

        diff = (p_with - p_without) if (p_with is not None and p_without is not None) else None
        if n_with and n_without:
            # 2x2: [[with_wins, with_losses], [without_wins, without_losses]]
            _odds, pval = fisher_exact(
                [[w_with, n_with - w_with], [w_without, n_without - w_without]]
            )
            p_value = float(pval)  # coerce numpy float → native (no numpy leaking into the API)
        else:
            p_value = None
        significant = bool(p_value is not None and p_value < alpha)

        cells.append(SlotContrastCell(
            card=card, board=board, opponent=opponent,
            w_with=w_with, n_with=n_with, w_without=w_without, n_without=n_without,
            p_with=p_with, p_without=p_without, ci_with=ci_with, ci_without=ci_without,
            diff=diff, p_value=p_value, significant=significant,
            tier_with=tier_for_sample(n_with), tier_without=tier_for_sample(n_without),
        ))

    # Sort for decision-usefulness, not raw effect size: cells whose SMALLER cohort clears the
    # evolving floor (n>=30) come first (the trustworthy diffs), then thinner cells, then cells
    # with no computable diff. Within each band, largest |diff| first. This keeps every cell
    # visible (honest-degrade) but stops n=1/n=2 noise from burying the real signal at the top.
    def _rank(c: SlotContrastCell) -> tuple:
        if c.diff is None:
            return (2, 0.0, c.card)
        robust = min(c.n_with, c.n_without) >= 30
        return (0 if robust else 1, -abs(c.diff), c.card)

    cells.sort(key=_rank)

    return SlotContrastReport(
        archetype=archetype, opponent=opponent, board=board,
        window_label=window_label, n_matches=len(matches), cells=cells,
        degraded=False, note=None,
    )
