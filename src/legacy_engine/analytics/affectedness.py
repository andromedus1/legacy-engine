"""Ban-affectedness classifier for adaptive regime-aware advisory (epic-regime-aware-advisory, v2).

Each archetype gets a ``valid_since`` — the date of the most recent ban that *materially* affected it
(it ran a banned card in ≥ ``affect_threshold`` of its pre-ban decks). Cells between unaffected
archetypes keep full history; cells touching an affected archetype truncate to post-ban data. The
signal is data-derived from ``BAN_EVENTS`` × per-archetype deck inclusion — validated bimodal on the
real corpus (Entomb ≈100% of Dimir Reanimator / ≈0% elsewhere; Undercity Informer ≈99.9% of Oops!).

Lives in ``analytics`` (data classification over the corpus, no advice), so the matrix builder can
consume it without an ``analytics → advisory`` back-edge. Limitation (documented at the epic):
inclusion catches DIRECT ban hits, not indirect field-driven rebuilds. Conservative — a too-thin
pre-ban sample leaves an archetype unaffected (keeps full history).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb

from legacy_engine.ingestion.banlist import BAN_EVENTS

_DEFAULT_AFFECT_THRESHOLD: float = 0.25  # banned-card inclusion in pre-ban decks → "affected"


def _cards_by_ban_date(
    ban_events: tuple[tuple[date, str, str], ...] | None = None,
) -> list[tuple[date, list[str]]]:
    """Group a ban ledger into ``[(date, [cards])]`` ordered by date."""
    grouped: dict[date, list[str]] = {}
    for event_date, card, _reason in BAN_EVENTS if ban_events is None else ban_events:
        grouped.setdefault(event_date, []).append(card)
    return [(d, grouped[d]) for d in sorted(grouped)]


def archetype_valid_since(
    con: duckdb.DuckDBPyConnection,
    archetypes: list[str],
    *,
    provenance: str | None = None,
    affect_threshold: float = _DEFAULT_AFFECT_THRESHOLD,
    ban_events: tuple[tuple[date, str, str], ...] | None = None,
) -> dict[str, str | None]:
    """Map each archetype to the ISO date of the latest ban that materially affected it (else None).

    "Affected at ban date ``d``" = the archetype ran ANY card banned at ``d`` in ≥ ``affect_threshold``
    of its decks (either board) during the pre-ban regime ``[prev_d, d)``. ``valid_since`` is the
    latest such ``d``; ``None`` if the archetype was never affected (keep full history). One batched
    query per ban date.
    """
    valid: dict[str, str | None] = {a: None for a in archetypes}
    if not archetypes:
        return valid

    arch_ph = ",".join("?" for _ in archetypes)
    prev_d: date | None = None
    for d, cards in _cards_by_ban_date(ban_events):
        since = prev_d.isoformat() if prev_d else None
        until = d.isoformat()
        card_ph = ",".join("?" for _ in cards)
        rows = con.execute(
            f"""
            WITH pool AS (
                SELECT dk.archetype, dk.tournament_id, dk.deck_idx
                FROM decks dk
                JOIN tournaments t ON t.id = dk.tournament_id
                WHERE dk.archetype IN ({arch_ph})
                  AND (? IS NULL OR t.provenance = ?)
                  AND (? IS NULL OR t.date >= ?)
                  AND t.date < ?
            )
            SELECT p.archetype,
                   count(DISTINCT (p.tournament_id, p.deck_idx)) AS decks,
                   count(DISTINCT CASE WHEN dc.name IN ({card_ph})
                                       THEN (p.tournament_id, p.deck_idx) END) AS run_decks
            FROM pool p
            LEFT JOIN deck_cards dc
              ON dc.tournament_id = p.tournament_id AND dc.deck_idx = p.deck_idx
            GROUP BY p.archetype
            """,
            [*archetypes, provenance, provenance, since, since, until, *cards],
        ).fetchall()

        for archetype, decks, run_decks in rows:
            if decks and (run_decks / decks) >= affect_threshold:
                valid[archetype] = until  # later d overwrites earlier → latest affecting ban
        prev_d = d

    return valid


# ---------------------------------------------------------------------------
# Affectedness explanation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AffectednessExplanation:
    """One ban event's contribution to an archetype's ``valid_since`` determination.

    ``ban_date`` is the date the ban took effect (ISO YYYY-MM-DD).
    ``banned_cards`` are the cards banned on that date.
    ``pre_ban_decks`` is the total decks in the pre-ban window (the denominator).
    ``running_decks`` is how many ran ANY of the banned cards (the numerator).
    ``inclusion_rate`` is ``running_decks / pre_ban_decks`` (0 when no pre-ban data).
    ``affected`` is True when ``inclusion_rate >= affect_threshold``.
    ``prev_ban_date`` is the lower bound of the pre-ban window (None = open start).
    """

    ban_date: str                # ISO YYYY-MM-DD
    banned_cards: tuple[str, ...]
    prev_ban_date: str | None    # lower bound of the pre-ban window
    pre_ban_decks: int
    running_decks: int
    inclusion_rate: float
    affected: bool


def explain_valid_since(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    *,
    provenance: str | None = None,
    affect_threshold: float = _DEFAULT_AFFECT_THRESHOLD,
) -> list[AffectednessExplanation]:
    """Return a per-ban-event breakdown of how ``valid_since`` was derived for ``archetype``.

    For each ban date in ``BAN_EVENTS``, shows the pre-ban inclusion rate of the banned
    cards in this archetype's decks and whether the ban was deemed materially affecting.
    The ``valid_since`` date will be the latest ``ban_date`` where ``affected=True``.

    Results are ordered chronologically (earliest ban first) so a human can read the
    derivation sequentially.
    """
    explanations: list[AffectednessExplanation] = []
    prev_d: date | None = None

    for d, cards in _cards_by_ban_date():
        since = prev_d.isoformat() if prev_d else None
        until = d.isoformat()
        card_ph = ",".join("?" for _ in cards)

        row = con.execute(
            f"""
            WITH pool AS (
                SELECT dk.tournament_id, dk.deck_idx
                FROM decks dk
                JOIN tournaments t ON t.id = dk.tournament_id
                WHERE dk.archetype = ?
                  AND (? IS NULL OR t.provenance = ?)
                  AND (? IS NULL OR t.date >= ?)
                  AND t.date < ?
            )
            SELECT
                count(DISTINCT (pool.tournament_id, pool.deck_idx)) AS decks,
                count(DISTINCT CASE WHEN dc.name IN ({card_ph})
                                    THEN (pool.tournament_id, pool.deck_idx) END) AS run_decks
            FROM pool
            LEFT JOIN deck_cards dc
              ON dc.tournament_id = pool.tournament_id AND dc.deck_idx = pool.deck_idx
            """,
            [archetype, provenance, provenance, since, since, until, *cards],
        ).fetchone()

        pre_ban_decks = int(row[0]) if row else 0
        running_decks = int(row[1]) if row else 0
        inclusion_rate = (running_decks / pre_ban_decks) if pre_ban_decks > 0 else 0.0
        affected = pre_ban_decks > 0 and inclusion_rate >= affect_threshold

        explanations.append(
            AffectednessExplanation(
                ban_date=until,
                banned_cards=tuple(cards),
                prev_ban_date=since,
                pre_ban_decks=pre_ban_decks,
                running_decks=running_decks,
                inclusion_rate=inclusion_rate,
                affected=affected,
            )
        )
        prev_d = d

    return explanations
