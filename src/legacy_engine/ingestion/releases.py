"""Release-aware ingestion — scan Scryfall /sets for upcoming and recently-released sets.

Pure advisory: the release scan informs *when* to trigger a bulk re-pull; the
authoritative "what's new" signal is the table-vs-table diff in store.load_cards_diff,
not set metadata. No legality filtering is applied per set — the per-card BanListSnapshot
path decides legality downstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from legacy_engine.models.base import LegacyEngineModel

if TYPE_CHECKING:
    from legacy_engine.ingestion.scryfall import ScryfallClient

class SetRelease(LegacyEngineModel):
    """A Scryfall set record with the fields relevant to release tracking.

    Subclasses LegacyEngineModel: extra="ignore" drops unmodeled Scryfall fields.
    ``released_at`` is None for unscheduled/preview sets with no release date yet.
    """

    code: str
    name: str
    released_at: date | None = None
    set_type: str = ""
    card_count: int = 0


@dataclass(frozen=True)
class ReleaseScan:
    """Result of a Scryfall /sets scan.

    ``upcoming``: sets with released_at in (today, today+horizon_days].
    ``recently_released``: sets with released_at in [today-lookback_days, today].
    ``scanned_at``: the date the scan ran.

    Advisory only: does NOT gate ingestion. The diff is the authoritative new-card signal.
    """

    upcoming: list[SetRelease]
    recently_released: list[SetRelease]
    scanned_at: date


def fetch_sets(client: "ScryfallClient") -> list[SetRelease]:
    """Fetch the Scryfall /sets list and return typed SetRelease objects.

    Makes one GET to {SCRYFALL_API_BASE}/sets; drops unmodeled fields via LegacyEngineModel.
    Returns all sets including those without a release date (released_at=None).
    """
    from legacy_engine.config import SCRYFALL_API_BASE

    resp = client.client.get(f"{SCRYFALL_API_BASE}/sets")
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return [SetRelease.model_validate(raw) for raw in data]


def upcoming_and_recent(
    sets: list[SetRelease],
    *,
    today: date,
    horizon_days: int = 30,
    lookback_days: int = 14,
) -> ReleaseScan:
    """Split a list of SetRelease objects into upcoming and recently-released.

    Pure function — no network, no DB. Deterministic given the same inputs.

    ``upcoming``: released_at in (today, today + horizon_days] (exclusive lower, inclusive upper).
    ``recently_released``: released_at in [today - lookback_days, today] (both inclusive).
    Sets with released_at=None are excluded from both (no release date → unknown timing).
    No per-set legality filtering — supplemental products may carry Legacy-legal cards.

    Args:
        sets: Scryfall set list.
        today: The reference date (injected for testability; callers pass date.today()).
        horizon_days: How far into the future to consider a set "upcoming".
        lookback_days: How far back to consider a set "recently released".
    """
    from datetime import timedelta

    horizon = today + timedelta(days=horizon_days)
    lookback = today - timedelta(days=lookback_days)

    upcoming: list[SetRelease] = []
    recently_released: list[SetRelease] = []

    for s in sets:
        if s.released_at is None:
            continue
        if today < s.released_at <= horizon:
            upcoming.append(s)
        elif lookback <= s.released_at <= today:
            recently_released.append(s)

    # Sort for determinism: upcoming by date ascending, recent by date descending (newest first)
    upcoming.sort(key=lambda s: s.released_at)  # type: ignore[arg-type]
    recently_released.sort(key=lambda s: s.released_at, reverse=True)  # type: ignore[arg-type]

    return ReleaseScan(
        upcoming=upcoming,
        recently_released=recently_released,
        scanned_at=today,
    )
