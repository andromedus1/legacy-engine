"""Parse a fbettega CacheItem JSON object into typed tournament models.

The CacheItem is nested: ``{Tournament: {Date, Name, Uri, Formats}, Decks: [...], Rounds: [...],
Standings: [...]}``. Provenance (online vs paper) is derived from the source directory + Uri host,
not stored in the JSON. MTGO Leagues legitimately have empty Rounds/Standings and a "5-0"-style deck
Result — that is normal, never an error.
"""

from __future__ import annotations

from legacy_engine.models.tournament import Deck, RoundMatch, Standing, TournamentResult

_ONLINE_SOURCES = {"mtgo", "manatraders", "manatrader"}
_PAPER_SOURCES = {"mtgmelee", "melee", "topdeck", "cardsrealm"}
_ONLINE_HOSTS = ("mtgo.com", "manatraders.com")
_PAPER_HOSTS = ("melee.gg", "topdeck.gg", "cardsrealm.com")


def derive_provenance(source: str, uri: str | None) -> str:
    """Classify an event as online (MTGO) or paper (Melee/Topdeck/...) from source dir + Uri host."""
    s = (source or "").lower()
    if s in _ONLINE_SOURCES:
        return "online"
    if s in _PAPER_SOURCES:
        return "paper"
    host = (uri or "").lower()
    if any(h in host for h in _ONLINE_HOSTS):
        return "online"
    if any(h in host for h in _PAPER_HOSTS):
        return "paper"
    return "unknown"


def parse_rounds(raw_rounds: list) -> list[RoundMatch]:
    """Flatten the Rounds structure into a flat list of matches.

    Handles both shapes: a flat list of match dicts, or a list of round objects each wrapping a
    ``Matches`` list.
    """
    matches: list[RoundMatch] = []
    for entry in raw_rounds or []:
        if isinstance(entry, dict) and "Matches" in entry:
            for m in entry.get("Matches") or []:
                matches.append(RoundMatch.model_validate(m))
        else:
            matches.append(RoundMatch.model_validate(entry))
    return matches


def parse_cache_item(raw: dict, source: str) -> TournamentResult:
    """Parse one CacheItem JSON object into a TournamentResult, deriving source + provenance."""
    tournament = raw.get("Tournament", {}) or {}
    uri = tournament.get("Uri")
    return TournamentResult(
        name=tournament.get("Name", ""),
        date=tournament.get("Date"),
        uri=uri,
        format=_coerce_format(tournament.get("Formats")),
        source=source,
        provenance=derive_provenance(source, uri),
        decks=[Deck.model_validate(d) for d in raw.get("Decks", []) or []],
        rounds=parse_rounds(raw.get("Rounds", []) or []),
        standings=[Standing.model_validate(s) for s in raw.get("Standings", []) or []],
    )


def _coerce_format(value) -> str:
    """Formats is a bare string in real files but typed as a list in the model — normalize."""
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""
