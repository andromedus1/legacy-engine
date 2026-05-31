"""Scryfall ingestion — oracle bulk download + whole-pool name index + on-demand Card resolution.

Ported and extended from edh-engine's ScryfallClient. The key Legacy adaptation: index the WHOLE
oracle pool (a Legacy decklist can reference any legal card) and resolve to a typed ``Card`` on
demand, rather than pre-resolving a meta-scoped subset.
"""

from __future__ import annotations

import json
import logging
import time
import unicodedata
from pathlib import Path

import httpx

from legacy_engine.config import (
    SCRYFALL_API_BASE,
    SCRYFALL_API_DELAY,
    SCRYFALL_BULK_TYPE,
    SCRYFALL_DIR,
    USER_AGENT,
)
from legacy_engine.models.card import Card

logger = logging.getLogger(__name__)

BULK_DATA_URL = f"{SCRYFALL_API_BASE}/bulk-data"
COLLECTION_URL = f"{SCRYFALL_API_BASE}/cards/collection"
ORACLE_CARDS_PATH = SCRYFALL_DIR / "oracle_cards.json"
METADATA_PATH = SCRYFALL_DIR / "metadata.json"


def normalize_name(name: str) -> str:
    """Normalize a card name — fix curly apostrophes, apply NFC Unicode normalization, and trim.

    NFC normalization ensures accented characters (e.g. "û" in "Khazad-dûm", "Æ") resolve
    consistently regardless of whether the decklist source encoded them in NFC or NFD form.
    Curly-apostrophe replacement runs before normalization so smart-quote variants collapse too.
    """
    return unicodedata.normalize("NFC", name.replace("’", "'").replace("‘", "'")).strip()


class ScryfallClient:
    """Client for Scryfall — bulk download, whole-pool index, and on-demand Card lookup."""

    def __init__(self) -> None:
        self.client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60.0)
        self._card_index: dict[str, dict] | None = None

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "ScryfallClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ── bulk download ──
    def download_bulk_data(self, force: bool = False) -> Path:
        """Download the oracle_cards bulk file (skips if cached copy is current)."""
        SCRYFALL_DIR.mkdir(parents=True, exist_ok=True)

        if not force and ORACLE_CARDS_PATH.exists() and METADATA_PATH.exists():
            cached = json.loads(METADATA_PATH.read_text())
            remote = self._fetch_bulk_metadata()
            if cached.get("updated_at") == remote.get("updated_at"):
                logger.info("Scryfall bulk is up to date, skipping download")
                return ORACLE_CARDS_PATH

        meta = self._fetch_bulk_metadata()
        logger.info("Downloading Scryfall %s bulk from %s", SCRYFALL_BULK_TYPE, meta["download_uri"])
        resp = self.client.get(meta["download_uri"], follow_redirects=True)
        resp.raise_for_status()
        cards = resp.json()

        ORACLE_CARDS_PATH.write_text(json.dumps(cards))
        METADATA_PATH.write_text(
            json.dumps(
                {"updated_at": meta.get("updated_at"), "card_count": len(cards), "bulk_type": SCRYFALL_BULK_TYPE},
                indent=2,
            )
        )
        logger.info("Downloaded %d cards", len(cards))
        self._card_index = None  # invalidate
        return ORACLE_CARDS_PATH

    def _fetch_bulk_metadata(self) -> dict:
        resp = self.client.get(BULK_DATA_URL)
        resp.raise_for_status()
        for item in resp.json().get("data", []):
            if item.get("type") == SCRYFALL_BULK_TYPE:
                return item
        raise RuntimeError(f"Scryfall bulk type not found: {SCRYFALL_BULK_TYPE}")

    # ── index + resolution ──
    def load_card_index(self) -> dict[str, dict]:
        """Load the bulk file into a name-indexed dict over the WHOLE pool (cached).

        Indexes by full name and by each face of split/DFC/adventure cards (``A // B``).
        """
        if self._card_index is not None:
            return self._card_index
        if not ORACLE_CARDS_PATH.exists():
            raise FileNotFoundError("Scryfall bulk not found. Run `legacy seed cards` first.")

        cards = json.loads(ORACLE_CARDS_PATH.read_text())
        index: dict[str, dict] = {}
        for card in cards:
            name = card.get("name", "")
            if not name:
                continue
            # Primary key is always normalized so accented names resolve regardless of NFC/NFD
            # encoding in the source decklist.
            index[normalize_name(name)] = card
            # Split/adventure/aftermath cards: index each face from the combined name ("A // B").
            if " // " in name:
                for face in name.split(" // "):
                    index.setdefault(normalize_name(face), card)
            # DFC / meld / modal cards carry a card_faces list — index each face's name too.
            for face in card.get("card_faces", []) or []:
                fname = face.get("name", "")
                if fname:
                    index.setdefault(normalize_name(fname), card)
        self._card_index = index
        logger.info("Indexed %d card names (whole oracle pool)", len(index))
        return index

    def get_card(self, name: str) -> Card | None:
        """Resolve a card name to a typed Card, or None if unknown."""
        raw = self.load_card_index().get(normalize_name(name))
        return Card.from_scryfall(raw) if raw is not None else None

    def _batch_lookup(self, card_names: list[str]) -> dict[str, dict]:
        """Batch-resolve names via POST /cards/collection (75 per request)."""
        results: dict[str, dict] = {}
        for i in range(0, len(card_names), 75):
            batch = card_names[i : i + 75]
            resp = self.client.post(
                COLLECTION_URL, json={"identifiers": [{"name": n} for n in batch]}
            )
            resp.raise_for_status()
            data = resp.json()
            for card in data.get("data", []):
                results[card["name"]] = card
            if data.get("not_found"):
                logger.warning("Batch %d: %d names not found", i // 75, len(data["not_found"]))
            time.sleep(SCRYFALL_API_DELAY)
        return results
