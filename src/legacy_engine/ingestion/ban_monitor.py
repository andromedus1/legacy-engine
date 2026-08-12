"""Strict WotC Legacy B&R announcement extraction.

Parsing is pure and deliberately fail-loud: page or phrasing drift is an
unavailable signal, never an implicit "no changes" result.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from html.parser import HTMLParser
from typing import Literal

from legacy_engine.models.base import LegacyEngineModel


class WotcLegacyAction(LegacyEngineModel):
    card: str
    action: Literal["banned", "unbanned", "restricted", "unrestricted"]


class WotcAnnouncement(LegacyEngineModel):
    source_url: str
    effective_date: date
    legacy_actions: tuple[WotcLegacyAction, ...]
    legacy_no_changes: bool
    next_announcement: date | None = None


class _TextExtractor(HTMLParser):
    _BLOCKS = frozenset({
        "article", "br", "div", "h1", "h2", "h3", "h4", "li", "p", "section",
    })

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        lines = (" ".join(part.split()) for part in "".join(self.parts).splitlines())
        return "\n".join(line for line in lines if line)


_FORMATS = (
    "Standard", "Pioneer", "Modern", "Legacy", "Vintage", "Pauper",
    "Historic", "Explorer", "Brawl", "Commander",
)
_ACTION_RE = re.compile(
    r"(?P<card>[^.\n]+?)\s+is\s+(?P<action>banned|unbanned|restricted|unrestricted)\.",
    re.IGNORECASE,
)
_EFFECTIVE_RE = re.compile(
    r"Changes effective as of (?P<date>[A-Z][a-z]+ \d{1,2}, \d{4})\.?",
    re.IGNORECASE,
)
_NEXT_RE = re.compile(
    r"Next announcement:\s*(?P<date>[A-Z][a-z]+ \d{1,2}, \d{4})\.?,?",
    re.IGNORECASE,
)


def _parse_month_date(value: str) -> date:
    from datetime import datetime

    try:
        return datetime.strptime(value, "%B %d, %Y").date()
    except ValueError as exc:
        raise ValueError(f"invalid WotC announcement date {value!r}") from exc


def _legacy_section(text: str) -> str:
    lines = text.splitlines()
    indexes = [index for index, line in enumerate(lines) if line.strip() == "Legacy"]
    if len(indexes) != 1:
        raise ValueError(f"expected exactly one Legacy section, found {len(indexes)}")
    start = indexes[0] + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].strip() in _FORMATS:
            end = index
            break
    section = "\n".join(lines[start:end]).strip()
    if not section:
        raise ValueError("WotC Legacy section is empty")
    return section


def parse_wotc_legacy_announcement(html: str, *, source_url: str) -> WotcAnnouncement:
    """Extract the effective date, Legacy actions/no-change, and next date."""
    parser = _TextExtractor()
    parser.feed(html)
    text = parser.text()
    effective_matches = _EFFECTIVE_RE.findall(text)
    if len(effective_matches) != 1:
        raise ValueError(
            f"expected exactly one WotC effective date, found {len(effective_matches)}"
        )
    section = _legacy_section(text)
    actions = tuple(
        WotcLegacyAction(card=match.group("card").strip(), action=match.group("action").lower())
        for match in _ACTION_RE.finditer(section)
    )
    no_changes = bool(re.search(r"\bno changes\b", section, re.IGNORECASE))
    if bool(actions) == no_changes:
        raise ValueError(
            "WotC Legacy section must contain actions or explicit no changes, but not both"
        )
    next_matches = _NEXT_RE.findall(text)
    if len(next_matches) > 1:
        raise ValueError(f"expected at most one next-announcement date, found {len(next_matches)}")
    return WotcAnnouncement(
        source_url=source_url,
        effective_date=_parse_month_date(effective_matches[0]),
        legacy_actions=actions,
        legacy_no_changes=no_changes,
        next_announcement=_parse_month_date(next_matches[0]) if next_matches else None,
    )


def announcement_candidate_urls(expected: date, *, radius_days: int = 3) -> tuple[str, ...]:
    """Return deterministic WotC slug candidates around a scheduled date."""
    if radius_days < 0 or radius_days > 7:
        raise ValueError("WotC announcement radius_days must be between 0 and 7")
    base = "https://magic.wizards.com/en/news/announcements/banned-and-restricted"
    dates = [expected]
    for offset in range(1, radius_days + 1):
        dates.extend((expected - timedelta(days=offset), expected + timedelta(days=offset)))
    return tuple(
        f"{base}-{day.strftime('%B').lower()}-{day.day}-{day.year}" for day in dates
    )
