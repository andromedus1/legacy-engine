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
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Literal

import duckdb
from pydantic import model_validator

from legacy_engine.ingestion.banlist import BAN_EVENTS
from legacy_engine.models.base import LegacyEngineModel

_DEFAULT_AFFECT_THRESHOLD: float = 0.25  # banned-card inclusion in pre-ban decks → "affected"

ExposureBoundaryProvenance = Literal[
    "released-at", "corpus-first-seen", "first-material-adoption"
]


class ExposureBoundaryAuthority(LegacyEngineModel):
    """Outcome-free contamination boundary for one materially affected entity/card.

    The two clean bounds deliberately repeat the half-open contamination endpoints.  That makes
    the excluded span inspectable without asking a downstream consumer to infer it from a scalar
    ``valid_since`` date.
    """

    entity: str
    cards: tuple[str, ...]
    ban_date: date
    clean_pre_exposure_end: date
    contaminated_start: date
    contaminated_end: date
    clean_post_ban_start: date
    provenance: ExposureBoundaryProvenance
    materiality_scope: Literal["same-date-card-union"] = "same-date-card-union"
    material_decks: int
    pre_ban_decks: int
    ban_event_inclusion_rate: float

    @model_validator(mode="after")
    def _coherent_boundary(self) -> "ExposureBoundaryAuthority":
        if not (
            self.clean_pre_exposure_end
            == self.contaminated_start
            < self.contaminated_end
            == self.clean_post_ban_start
            == self.ban_date
        ):
            raise ValueError("exposure authority requires one exact half-open contamination gap")
        if self.pre_ban_decks <= 0 or not (0 <= self.material_decks <= self.pre_ban_decks):
            raise ValueError("exposure authority material counts must fit the pre-ban denominator")
        if not 0.0 <= self.ban_event_inclusion_rate <= 1.0:
            raise ValueError("ban-event inclusion rate must be between zero and one")
        return self


def exposure_boundary_authorities(
    con: duckdb.DuckDBPyConnection,
    entities: Sequence[str],
    *,
    provenance: str | None = None,
    affect_threshold: float = _DEFAULT_AFFECT_THRESHOLD,
    ban_events: Sequence[tuple[date, str, str]] | None = None,
    released_at_by_card: Mapping[str, date] | None = None,
) -> dict[str, tuple[ExposureBoundaryAuthority, ...]]:
    """Return exact localized-ban gaps for materially affected parent entities.

    Materiality intentionally reuses :func:`archetype_valid_since`'s denominator and ANY-card
    rule.  An authoritative release date wins when supplied; otherwise the first corpus deck for
    that entity/card is the deterministic, outcome-free fallback.  Unaffected entities retain an
    empty tuple rather than acquiring a global ban boundary.
    """

    result: dict[str, list[ExposureBoundaryAuthority]] = {entity: [] for entity in entities}
    if not entities:
        return {entity: () for entity in entities}
    entity_ph = ",".join("?" for _ in entities)
    previous: date | None = None
    grouped = _cards_by_ban_date(tuple(ban_events) if ban_events is not None else None)
    release_dates = released_at_by_card or {}
    for ban_date, cards in grouped:
        card_ph = ",".join("?" for _ in cards)
        since = previous.isoformat() if previous is not None else None
        material_rows = con.execute(
            f"""
            WITH pool AS (
                SELECT d.archetype, d.tournament_id, d.deck_idx
                FROM decks d
                JOIN tournaments t ON t.id = d.tournament_id
                WHERE d.archetype IN ({entity_ph})
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
            [*entities, provenance, provenance, since, since, ban_date.isoformat(), *cards],
        ).fetchall()
        affected = {
            str(entity): (int(decks), int(run_decks))
            for entity, decks, run_decks in material_rows
            if decks and run_decks / decks >= affect_threshold
        }
        if not affected:
            previous = ban_date
            continue
        affected_names = sorted(affected)
        affected_ph = ",".join("?" for _ in affected_names)
        first_rows = con.execute(
            f"""
            SELECT d.archetype, dc.name,
                   min(cast(substr(t.date, 1, 10) AS DATE)) AS first_seen,
                   count(DISTINCT CASE WHEN (? IS NULL OR t.date >= ?)
                                       THEN (d.tournament_id, d.deck_idx) END) AS card_decks
            FROM decks d
            JOIN tournaments t ON t.id = d.tournament_id
            JOIN deck_cards dc
              ON dc.tournament_id = d.tournament_id AND dc.deck_idx = d.deck_idx
            WHERE d.archetype IN ({affected_ph})
              AND dc.name IN ({card_ph})
              AND (? IS NULL OR t.provenance = ?)
              AND t.date < ?
            GROUP BY d.archetype, dc.name
            """,
            [since, since, *affected_names, *cards, provenance, provenance, ban_date.isoformat()],
        ).fetchall()
        observations: dict[str, list[tuple[str, date, int, date | None]]] = {}
        for entity, card, first_seen, card_decks in first_rows:
            card = str(card)
            release_date = release_dates.get(card)
            if release_date is not None and release_date >= ban_date:
                raise ValueError(
                    f"release date for {card} must precede its {ban_date.isoformat()} ban"
                )
            observations.setdefault(str(entity), []).append(
                (card, first_seen, int(card_decks), release_date)
            )
        for entity, seen in observations.items():
            # Materiality is defined for the same-date card union, so its contamination authority
            # is also one event-cohort gap.  This avoids letting a tiny individual card silently
            # widen a union-qualified entity while preserving every contributing card name.
            exposure_start = min(release or first for _card, first, _n, release in seen)
            if exposure_start >= ban_date:
                continue
            decks, run_decks = affected[entity]
            result[entity].append(
                ExposureBoundaryAuthority(
                    entity=entity,
                    cards=tuple(sorted(card for card, _first, _n, _release in seen)),
                    ban_date=ban_date,
                    clean_pre_exposure_end=exposure_start,
                    contaminated_start=exposure_start,
                    contaminated_end=ban_date,
                    clean_post_ban_start=ban_date,
                    provenance=(
                        "released-at"
                        if all(release is not None for _card, _first, _n, release in seen)
                        else "corpus-first-seen"
                    ),
                    material_decks=run_decks,
                    pre_ban_decks=decks,
                    ban_event_inclusion_rate=run_decks / decks,
                )
            )
        previous = ban_date
    return {
        entity: tuple(
            sorted(rows, key=lambda row: (row.contaminated_start, row.ban_date, row.cards))
        )
        for entity, rows in result.items()
    }


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
