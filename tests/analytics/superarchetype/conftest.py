"""Shared fixtures for the superarchetype clustering tests.

House style: factory fixtures returning ``_make_X(**kwargs)`` closures (pytest-factory-fixtures),
``TestX`` classes in the consuming modules, fully deterministic. The pure core is exercised entirely
on hand-built ``ArchetypeDeck`` lists — no DuckDB, no default DB, no wall clock.

The corpus fixture is built with EIGHT definers in four two-member families on purpose: the staple
threshold is a fraction of the definer count, so with fewer definers a family's own package would
itself clear 30% and be stripped as a "staple". Eight definers puts a two-member family at 25%,
safely under the cut, while the shared band sits at 100%.
"""

from __future__ import annotations

import pytest

from legacy_engine.analytics.superarchetype.cluster import ArchetypeDeck

_STAPLES = ("Brainstorm", "Force of Will", "Ponder", "Wasteland", "Underground Sea")

_FAMILIES: dict[str, tuple[str, ...]] = {
    "combo": ("Show and Tell", "Omniscience", "Emrakul", "Atraxa", "Ancient Tomb", "Lotus Petal"),
    "fair": ("Swords to Plowshares", "Stoneforge Mystic", "Batterskull", "Flooded Strand",
             "Plains", "Thalia"),
    "graveyard": ("Cabal Therapy", "Narcomoeba", "Bridge from Below", "Cephalid Coliseum",
                  "Ichorid", "Prized Amalgam"),
    "lands": ("Life from the Loam", "Dark Depths", "Thespian's Stage", "Exploration",
              "Mox Diamond", "Bojuka Bog"),
}

# (label, family, unique package card) — the pair inside each family differs by exactly one card.
_DEFINERS: tuple[tuple[str, str, str], ...] = (
    ("Show and Tell", "combo", "Sneak Attack"),
    ("Aluren", "combo", "Acererak the Archlich"),
    ("Azorius Stoneblade", "fair", "Sword of Fire and Ice"),
    ("Death & Taxes", "fair", "Kaldra Compleat"),
    ("Dredge", "graveyard", "Creeping Chill"),
    ("Oops! All Spells", "graveyard", "Balustrade Spy"),
    ("Lands", "lands", "Sphere of Resistance"),
    ("Cradle Control", "lands", "Gaea's Cradle"),
)

# Weak cross-family links so no two cross-family distances are exactly equal. Without them every
# cross-family pair sits at Jaccard 1.0, average linkage's tie-breaking is identical in every
# bootstrap replicate, and spurious upper-tree nodes score BP = 1.0 — an artifact of a perfectly
# symmetric fixture that no real corpus produces. Each card lands in exactly 2 of 8 definers (25%),
# safely under the 30% staple cut, and the links form a chain rather than a rival family.
_GENERIC_POOL = (
    "Chalice of the Void", "Karakas", "Pithing Needle", "Grafdigger's Cage",
    "Endurance", "Mindbreak Trap", "Surgical Extraction", "Boseiju, Who Endures",
)


@pytest.fixture
def make_deck():
    def _make(archetype: str, cards, idx: int = 0, tournament: str = "t1") -> ArchetypeDeck:
        return ArchetypeDeck(archetype=archetype, key=(tournament, idx), cards=frozenset(cards))
    return _make


@pytest.fixture
def make_pool(make_deck):
    """``_make(archetype, cards, n)`` -> n identical decks under one archetype label."""
    def _make(archetype: str, cards, n: int = 40, tournament: str | None = None):
        tag = tournament or f"t-{archetype}"
        return [make_deck(archetype, cards, idx=i, tournament=tag) for i in range(n)]
    return _make


@pytest.fixture
def two_family_corpus(make_pool):
    """Eight definers in four clean two-member families, all sharing one staple band."""
    decks: list[ArchetypeDeck] = []
    for i, (label, family, unique) in enumerate(_DEFINERS):
        generics = (_GENERIC_POOL[i], _GENERIC_POOL[(i + 3) % len(_GENERIC_POOL)])
        decks.extend(make_pool(label, _STAPLES + _FAMILIES[family] + (unique,) + generics, 40))
    return decks


@pytest.fixture
def family_of():
    return {label: family for label, family, _unique in _DEFINERS}


@pytest.fixture
def staples():
    return tuple(sorted(_STAPLES))


@pytest.fixture
def families():
    return _FAMILIES
