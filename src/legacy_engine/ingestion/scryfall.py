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
import urllib.parse
import gzip
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from legacy_engine.ingestion.prices import PrintingPrice

from legacy_engine.config import (
    SCRYFALL_API_BASE,
    SCRYFALL_ALL_CARDS_BULK_TYPE,
    SCRYFALL_ALL_CARDS_META_PATH,
    SCRYFALL_ALL_CARDS_PATH,
    SCRYFALL_API_DELAY,
    SCRYFALL_BULK_TYPE,
    SCRYFALL_DIR,
    SCRYFALL_PRICES_BULK_TYPE,
    SCRYFALL_PRICES_META_PATH,
    SCRYFALL_PRICES_PATH,
    USER_AGENT,
)
from legacy_engine.models.card import Card, PrintedCardAlias

logger = logging.getLogger(__name__)

BULK_DATA_URL = f"{SCRYFALL_API_BASE}/bulk-data"
COLLECTION_URL = f"{SCRYFALL_API_BASE}/cards/collection"
ORACLE_CARDS_PATH = SCRYFALL_DIR / "oracle_cards.json"
METADATA_PATH = SCRYFALL_DIR / "metadata.json"


_SCRYFALL_ALLOWED_HOSTS = frozenset({"scryfall.com", "api.scryfall.com", "c2.scryfall.com"})
_SCRYFALL_ALLOWED_SUFFIXES = (".scryfall.com", ".scryfall.io")


def _validate_scryfall_uri(uri: str) -> None:
    """Raise ``ValueError`` if *uri* does not point at a Scryfall-owned host.

    Scryfall's bulk ``download_uri`` values point at their CDN
    (*.scryfall.com / *.scryfall.io).  Validating the host before following
    redirects closes an SSRF-on-redirect vector where a tampered or replayed
    metadata response could redirect us to an internal address.
    """
    parsed = urllib.parse.urlparse(uri)
    host = parsed.hostname or ""
    if host in _SCRYFALL_ALLOWED_HOSTS:
        return
    if any(host.endswith(suffix) for suffix in _SCRYFALL_ALLOWED_SUFFIXES):
        return
    raise ValueError(
        f"Scryfall download_uri host {host!r} is not in the allowlist "
        f"({_SCRYFALL_ALLOWED_HOSTS | set(_SCRYFALL_ALLOWED_SUFFIXES)})"
    )


def normalize_name(name: str) -> str:
    """Normalize a card name — fix curly apostrophes, apply NFC Unicode normalization, and trim.

    NFC normalization ensures accented characters (e.g. "û" in "Khazad-dûm", "Æ") resolve
    consistently regardless of whether the decklist source encoded them in NFC or NFD form.
    Curly-apostrophe replacement runs before normalization so smart-quote variants collapse too.
    """
    return unicodedata.normalize("NFC", name.replace("’", "'").replace("‘", "'")).strip()


def normalize_alias_key(name: str) -> str:
    """Build an exact-comparison key for localized aliases, never a fuzzy-search key."""
    normalized = name.replace("’", "'").replace("‘", "'").casefold()
    decomposed = unicodedata.normalize("NFKD", normalized)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(without_marks.split())


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
        _validate_scryfall_uri(meta["download_uri"])
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

    def _fetch_all_cards_metadata(self) -> dict:
        resp = self.client.get(BULK_DATA_URL)
        resp.raise_for_status()
        for item in resp.json().get("data", []):
            if item.get("type") == SCRYFALL_ALL_CARDS_BULK_TYPE:
                return item
        raise RuntimeError(f"Scryfall bulk type not found: {SCRYFALL_ALL_CARDS_BULK_TYPE}")

    def download_all_cards_bulk(self, *, force: bool = False) -> Path:
        """Stream the every-printing/every-language bulk into the local raw mirror."""
        SCRYFALL_DIR.mkdir(parents=True, exist_ok=True)
        if not force and SCRYFALL_ALL_CARDS_PATH.exists() and SCRYFALL_ALL_CARDS_META_PATH.exists():
            return SCRYFALL_ALL_CARDS_PATH

        meta = self._fetch_all_cards_metadata()
        _validate_scryfall_uri(meta["download_uri"])
        tmp_path = SCRYFALL_ALL_CARDS_PATH.with_suffix(".gz.tmp")
        try:
            with self.client.stream("GET", meta["download_uri"], follow_redirects=True) as resp:
                resp.raise_for_status()
                encoding = (resp.headers.get("content-encoding") or "").lower()
                with tmp_path.open("wb") as fh:
                    if "gzip" in encoding or meta["download_uri"].endswith(".gz"):
                        # Preserve transport gzip bytes. httpx.iter_bytes() decodes content
                        # encodings, which would leave a plain JSON body at our .json.gz path.
                        for chunk in resp.iter_raw(chunk_size=64 * 1024):
                            fh.write(chunk)
                    else:
                        with gzip.GzipFile(fileobj=fh, mode="wb") as zipped:
                            for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                                zipped.write(chunk)
            # Consume the full stream before replacing last-good raw data; corruption after the
            # first valid row must not become the persisted mirror.
            for _alias in self.iter_printed_aliases(tmp_path):
                pass
            tmp_path.replace(SCRYFALL_ALL_CARDS_PATH)
            SCRYFALL_ALL_CARDS_META_PATH.write_text(json.dumps({
                "updated_at": meta.get("updated_at"),
                "bulk_type": SCRYFALL_ALL_CARDS_BULK_TYPE,
            }, indent=2))
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
        return SCRYFALL_ALL_CARDS_PATH

    def iter_printed_aliases(self, path: Path | None = None) -> Iterator[PrintedCardAlias]:
        """Stream localized printed names from all-cards JSON array or JSONL gzip."""
        src = path or SCRYFALL_ALL_CARDS_PATH
        if not src.exists():
            raise FileNotFoundError(f"Scryfall all-cards bulk not found at {src}")
        with gzip.open(src, "rt", encoding="utf-8") as fh:
            first = fh.read(1)
            fh.seek(0)
            if first == "[":
                import ijson
                rows = ijson.items(fh, "item")
            else:
                rows = (json.loads(line) for line in fh if line.strip())
            for raw in rows:
                language = str(raw.get("lang") or "")
                scryfall_id = str(raw.get("id") or "")
                printed = raw.get("printed_name")
                canonical = raw.get("name")
                if printed and canonical and printed != canonical:
                    yield PrintedCardAlias(
                        printed_name=printed,
                        normalized_alias=normalize_alias_key(printed),
                        canonical_name=canonical,
                        language=language,
                        scryfall_id=scryfall_id,
                    )
                for face in raw.get("card_faces") or []:
                    face_printed = face.get("printed_name")
                    face_canonical = face.get("name")
                    if face_printed and face_canonical and face_printed != face_canonical:
                        yield PrintedCardAlias(
                            printed_name=face_printed,
                            normalized_alias=normalize_alias_key(face_printed),
                            canonical_name=face_canonical,
                            language=language,
                            scryfall_id=scryfall_id,
                        )

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

    # ── prices bulk (default_cards: one object per printing) ──
    def download_prices_bulk(self, force: bool = False) -> Path:
        """Download the default_cards bulk file into data/scryfall/default_cards.json.

        Skips the download when the locally mirrored file is already at the same
        ``updated_at`` as the remote bulk (same skip-if-current mechanism as
        ``download_bulk_data`` for oracle_cards).

        NOTE: default_cards is ~547 MB.  This is a deliberate one-time fetch; re-running
        is a no-op until Scryfall publishes a new bulk.  The table is rebuildable from the
        mirrored file, so deleting the DuckDB loses no data.
        """
        SCRYFALL_DIR.mkdir(parents=True, exist_ok=True)

        if not force and SCRYFALL_PRICES_PATH.exists() and SCRYFALL_PRICES_META_PATH.exists():
            cached = json.loads(SCRYFALL_PRICES_META_PATH.read_text())
            remote = self._fetch_prices_metadata()
            if cached.get("updated_at") == remote.get("updated_at"):
                logger.info("Scryfall prices bulk is up to date, skipping download")
                return SCRYFALL_PRICES_PATH

        meta = self._fetch_prices_metadata()
        _validate_scryfall_uri(meta["download_uri"])
        logger.info(
            "Downloading Scryfall %s bulk from %s",
            SCRYFALL_PRICES_BULK_TYPE,
            meta["download_uri"],
        )
        # Stream into a temp file first, then rename atomically so a partial download
        # never leaves a corrupt mirror.
        tmp_path = SCRYFALL_PRICES_PATH.with_suffix(".json.tmp")
        with self.client.stream("GET", meta["download_uri"], follow_redirects=True) as resp:
            resp.raise_for_status()
            with tmp_path.open("wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                    fh.write(chunk)

        tmp_path.rename(SCRYFALL_PRICES_PATH)
        SCRYFALL_PRICES_META_PATH.write_text(
            json.dumps(
                {
                    "updated_at": meta.get("updated_at"),
                    "bulk_type": SCRYFALL_PRICES_BULK_TYPE,
                },
                indent=2,
            )
        )
        logger.info("Downloaded prices bulk (updated_at=%s)", meta.get("updated_at"))
        return SCRYFALL_PRICES_PATH

    def _fetch_prices_metadata(self) -> dict:
        resp = self.client.get(BULK_DATA_URL)
        resp.raise_for_status()
        for item in resp.json().get("data", []):
            if item.get("type") == SCRYFALL_PRICES_BULK_TYPE:
                return item
        raise RuntimeError(f"Scryfall bulk type not found: {SCRYFALL_PRICES_BULK_TYPE}")

    def iter_price_rows(self, path: Path | None = None) -> "Iterator[PrintingPrice]":
        """Stream the mirrored default_cards.json and yield one ``PrintingPrice`` per printing.

        Filters to paper-legal, gameplay-layout printings only (excludes MTGO-only cards,
        tokens, art-series, etc.).  All price fields are kept as-is from Scryfall (None where
        Scryfall has no price).

        The iterator holds only the current card object in memory at a time — suitable for
        the ~547 MB default_cards bulk.

        Args:
            path: Override the mirrored file path (for tests).
        """
        from legacy_engine.ingestion.prices import _raw_to_printing_price  # prices.py imports nothing from scryfall

        import json as _json

        src = path or SCRYFALL_PRICES_PATH
        if not src.exists():
            raise FileNotFoundError(
                f"Prices bulk not found at {src}. Run `legacy seed prices` first."
            )

        # Inject price_date from the metadata file so each PrintingPrice row carries staleness info.
        price_date = self.prices_updated_at()

        # Stream-parse with ijson when available; fall back to a full json.load for
        # environments/tests where ijson is not installed.
        try:
            import ijson  # type: ignore[import]
            use_ijson = True
        except ImportError:
            use_ijson = False

        def _with_date(raw: dict) -> dict:
            if price_date is not None:
                raw = dict(raw)  # don't mutate the original
                raw["_price_date"] = price_date
            return raw

        if use_ijson:
            with src.open("rb") as fh:
                for raw in ijson.items(fh, "item"):
                    pp = _raw_to_printing_price(_with_date(raw))
                    if pp is not None:
                        yield pp
        else:
            data = _json.loads(src.read_text())
            for raw in data:
                pp = _raw_to_printing_price(_with_date(raw))
                if pp is not None:
                    yield pp

    def prices_updated_at(self) -> str | None:
        """Return the ``updated_at`` timestamp from the prices metadata file, or None."""
        if not SCRYFALL_PRICES_META_PATH.exists():
            return None
        try:
            return json.loads(SCRYFALL_PRICES_META_PATH.read_text()).get("updated_at")
        except Exception:
            return None

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
