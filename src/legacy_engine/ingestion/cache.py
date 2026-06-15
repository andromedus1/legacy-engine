"""Parse a fbettega CacheItem JSON object into typed tournament models.

The CacheItem is nested: ``{Tournament: {Date, Name, Uri, Formats}, Decks: [...], Rounds: [...],
Standings: [...]}``. Provenance (online vs paper) is derived from the source directory + Uri host,
not stored in the JSON. MTGO Leagues legitimately have empty Rounds/Standings and a "5-0"-style deck
Result — that is normal, never an error.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path

from legacy_engine.config import CACHE_DIR, FBETTEGA_CACHE_REPO
from legacy_engine.models.tournament import Deck, RoundMatch, Standing, TournamentResult

logger = logging.getLogger(__name__)

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
    """Parse one CacheItem JSON object into a TournamentResult, deriving source + provenance.

    Resilience NFR: a single malformed deck is dropped (logged) rather than aborting the whole
    event — the community cache is fragile / single-maintainer, so one bad row must not lose an
    otherwise-valid tournament.
    """
    tournament = raw.get("Tournament", {}) or {}
    uri = tournament.get("Uri")
    name = tournament.get("Name", "")
    decks: list[Deck] = []
    for i, d in enumerate(raw.get("Decks", []) or []):
        try:
            decks.append(Deck.model_validate(d))
        except Exception as exc:  # noqa: BLE001 — tolerate one bad deck, keep the event
            logger.warning("Skipping malformed deck %d in event %r (%s): %s", i, name, source, exc)
    return TournamentResult(
        name=name,
        date=tournament.get("Date"),
        uri=uri,
        format=_coerce_format(tournament.get("Formats")),
        source=source,
        provenance=derive_provenance(source, uri),
        decks=decks,
        rounds=parse_rounds(raw.get("Rounds", []) or []),
        standings=[Standing.model_validate(s) for s in raw.get("Standings", []) or []],
    )


def _coerce_format(value) -> str:
    """Formats is a bare string in real files but typed as a list in the model — normalize.

    When a list contains "Legacy" (e.g. ``["Modern", "Legacy"]``), return "Legacy" so the event
    is not skipped by Legacy discovery. Otherwise return the first element (or "" if empty).
    A bare string is returned as-is (or "" for falsy).
    """
    if isinstance(value, list):
        if "Legacy" in value:
            return "Legacy"
        return value[0] if value else ""
    return value or ""


# ── Mirror + discovery + ingest ──

def mirror_cache(
    repo: str = FBETTEGA_CACHE_REPO,
    dest: Path = CACHE_DIR,
    runner: Callable = subprocess.run,
) -> Path:
    """Mirror the fbettega cache repo locally: clone if absent, else pull. Returns the dest path.

    The git call is injected (``runner``) so tests can assert clone-vs-pull without invoking git.
    """
    dest = Path(dest)
    if (dest / ".git").exists():
        logger.info("Updating cache mirror at %s", dest)
        runner(["git", "-C", str(dest), "pull", "--ff-only"], check=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Cloning cache mirror %s -> %s", repo, dest)
        runner(["git", "clone", "--depth", "1", repo, str(dest)], check=True)
    return dest


def discover_legacy_events(cache_dir: Path = CACHE_DIR) -> list[tuple[Path, str]]:
    """Find Legacy tournament JSON files under ``Tournaments/<Source>/<Y>/<M>/<D>/``.

    Returns (path, source) pairs, where source is the directory under ``Tournaments/`` (e.g. "MTGO").
    Files whose ``Tournament.Formats`` is not "Legacy", and non-JSON files, are skipped.
    """
    root = Path(cache_dir) / "Tournaments"
    if not root.exists():
        return []
    events: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*.json")):
        try:
            raw = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Skipping unreadable cache file: %s", path)
            continue
        fmt = _coerce_format((raw.get("Tournament", {}) or {}).get("Formats"))
        if fmt != "Legacy":
            continue
        source = path.relative_to(root).parts[0]  # <Source> directory
        events.append((path, source))
    return events


def ingest_cache(con, cache_dir: Path = CACHE_DIR) -> int:
    """Parse + load every discovered Legacy event into the DuckDB store. Returns the count loaded.

    Resilience NFR: one bad event (unreadable JSON, parse failure, or load failure) is logged and
    skipped — the batch continues. Returns the count of events successfully loaded.
    """
    from legacy_engine.ingestion import store

    count = 0
    skipped = 0
    for path, source in discover_legacy_events(cache_dir):
        try:
            raw = json.loads(path.read_text())
            store.load_tournament(con, parse_cache_item(raw, source))
            count += 1
        except Exception as exc:  # noqa: BLE001 — tolerate one bad event, keep the batch
            skipped += 1
            logger.warning("Skipping bad event %s: %s", path, exc)
    if skipped:
        logger.warning("Ingest complete: %d events loaded, %d skipped", count, skipped)
    return count
