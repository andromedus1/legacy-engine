"""Models for the fbettega tournament cache (a CacheItem).

PascalCase Scryfall/Badaro-style keys map to snake_case Python via field aliases; the
LegacyEngineModel base sets ``populate_by_name=True`` so both forms work and unmodeled keys are
dropped. Provenance (online/paper) and source are derived at parse time, not present in the JSON.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from legacy_engine.models.base import LegacyEngineModel


def _none_to_empty(v: object) -> object:
    """Coerce an explicit JSON ``null`` to ``""`` for string fields.

    A field default only applies when the key is *absent*; the fbettega cache frequently emits an
    explicit ``null`` (e.g. a bye's ``Player2``, or missing ``Result``/``Player``), which would
    otherwise fail string validation and crash ingestion. Treat null as the empty default — a bye
    becomes an empty opponent, which the match-results join already drops from win-rate.
    """
    return "" if v is None else v


class CardCount(LegacyEngineModel):
    count: int = Field(default=1, alias="Count")
    name: str = Field(default="", alias="CardName")

    _coerce = field_validator("name", mode="before")(_none_to_empty)


class RoundMatch(LegacyEngineModel):
    player1: str = Field(default="", alias="Player1")
    player2: str = Field(default="", alias="Player2")  # "" = bye / no opponent
    result: str = Field(default="", alias="Result")

    _coerce = field_validator("player1", "player2", "result", mode="before")(_none_to_empty)


class Standing(LegacyEngineModel):
    rank: int = Field(default=0, alias="Rank")
    player: str = Field(default="", alias="Player")
    points: int = Field(default=0, alias="Points")
    wins: int = Field(default=0, alias="Wins")
    losses: int = Field(default=0, alias="Losses")
    draws: int = Field(default=0, alias="Draws")

    _coerce = field_validator("player", mode="before")(_none_to_empty)


class Deck(LegacyEngineModel):
    player: str = Field(default="", alias="Player")
    result: str = Field(default="", alias="Result")
    anchor_uri: str | None = Field(default=None, alias="AnchorUri")
    mainboard: list[CardCount] = Field(default_factory=list, alias="Mainboard")
    sideboard: list[CardCount] = Field(default_factory=list, alias="Sideboard")

    _coerce = field_validator("player", "result", mode="before")(_none_to_empty)


class TournamentResult(LegacyEngineModel):
    name: str = Field(default="", alias="Name")
    date: str | None = Field(default=None, alias="Date")
    uri: str | None = Field(default=None, alias="Uri")
    format: str = Field(default="", alias="Formats")
    source: str = ""  # derived: MTGO / MTGmelee / Topdeck / ...
    provenance: str = ""  # derived: "online" | "paper" | "unknown"
    decks: list[Deck] = Field(default_factory=list)
    rounds: list[RoundMatch] = Field(default_factory=list)
    standings: list[Standing] = Field(default_factory=list)
