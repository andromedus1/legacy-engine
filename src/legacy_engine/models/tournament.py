"""Models for the fbettega tournament cache (a CacheItem).

PascalCase Scryfall/Badaro-style keys map to snake_case Python via field aliases; the
LegacyEngineModel base sets ``populate_by_name=True`` so both forms work and unmodeled keys are
dropped. Provenance (online/paper) and source are derived at parse time, not present in the JSON.
"""

from __future__ import annotations

from pydantic import Field

from legacy_engine.models.base import LegacyEngineModel


class CardCount(LegacyEngineModel):
    count: int = Field(default=1, alias="Count")
    name: str = Field(default="", alias="CardName")


class RoundMatch(LegacyEngineModel):
    player1: str = Field(default="", alias="Player1")
    player2: str = Field(default="", alias="Player2")
    result: str = Field(default="", alias="Result")


class Standing(LegacyEngineModel):
    rank: int = Field(default=0, alias="Rank")
    player: str = Field(default="", alias="Player")
    points: int = Field(default=0, alias="Points")
    wins: int = Field(default=0, alias="Wins")
    losses: int = Field(default=0, alias="Losses")
    draws: int = Field(default=0, alias="Draws")


class Deck(LegacyEngineModel):
    player: str = Field(default="", alias="Player")
    result: str = Field(default="", alias="Result")
    anchor_uri: str | None = Field(default=None, alias="AnchorUri")
    mainboard: list[CardCount] = Field(default_factory=list, alias="Mainboard")
    sideboard: list[CardCount] = Field(default_factory=list, alias="Sideboard")


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
