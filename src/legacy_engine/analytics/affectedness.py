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

from datetime import date

import duckdb

from legacy_engine.ingestion.banlist import BAN_EVENTS

_DEFAULT_AFFECT_THRESHOLD: float = 0.25  # banned-card inclusion in pre-ban decks → "affected"


def _cards_by_ban_date() -> list[tuple[date, list[str]]]:
    """Group ``BAN_EVENTS`` into ``[(date, [cards])]`` ordered by date."""
    grouped: dict[date, list[str]] = {}
    for event_date, card, _reason in BAN_EVENTS:
        grouped.setdefault(event_date, []).append(card)
    return [(d, grouped[d]) for d in sorted(grouped)]


def archetype_valid_since(
    con: duckdb.DuckDBPyConnection,
    archetypes: list[str],
    *,
    provenance: str | None = None,
    affect_threshold: float = _DEFAULT_AFFECT_THRESHOLD,
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
    for d, cards in _cards_by_ban_date():
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
