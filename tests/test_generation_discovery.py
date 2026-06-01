"""Tests for generation.discovery — the card-adjacency nomination model (epic-gap-discovery).

House style (mirrors test_generation_consensus): module-level raw dicts → ``parse_cache_item``
→ ``store.load_tournament`` into ``:memory:``; labels pinned via SQL UPDATE; cards seeded via
``store.load_cards``; a fixed explicit window so tests don't depend on the live ban regime.

Corpus design (deterministic) — one "Delver" tournament, 41 decks, dated 2026-03-15:

    Locked core (inclusion ≥ 0.65): Brainstorm, Force of Will, Ponder
    Candidate templates (each a core-running deck + one extra card):
      10× + Daze            (U, cmc1, counter)        → passes every gate
       6× + Flusterstorm    (U, cmc1, counter)        → passes; lives in D's sideboard
       5× + Pyroblast       (R, cmc1, counter)        → color gate excludes
       5× + Curiosity Test  (U, cmc1, no role)        → role gate excludes
       5× + Cryptic Command (U, cmc4, counter)        → CMC-band gate excludes
       6× + Spell Pierce    (U, cmc1, counter)        → already in D → gate 1 excludes
       4× {Brainstorm, Ponder}  (only 2 core → NOT core-runners; no extra candidate)

    k = max(3, ceil(0.6·3)) = 3 → a core-runner must run all three core cards.
    cooccur_floor = 5. total_decks = 41, core_decks = 37.
"""

from __future__ import annotations

import math

import pytest

from legacy_engine.generation.discovery import (
    AdjacencyCandidate,
    _cooccurrence,
    _shell_profile,
    adjacency_candidates,
)
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from legacy_engine.models.card import Card

_SINCE = "2026-01-01"
_UNTIL = "2026-12-31"
_DATE = "2026-03-15"

_CORE = ["Brainstorm", "Force of Will", "Ponder"]

# Card dimension: colors / cmc / oracle_text drive _card_roles + the gates.
_CARDS = [
    Card(name="Brainstorm", type_line="Instant", cmc=1.0, colors=["U"],
         oracle_text="Draw three cards, then put two cards from your hand on top of your library."),
    Card(name="Force of Will", type_line="Instant", cmc=5.0, colors=["U"],
         oracle_text="Counter target spell."),
    Card(name="Ponder", type_line="Sorcery", cmc=1.0, colors=["U"],
         oracle_text="Look at the top three cards of your library, then draw a card."),
    Card(name="Daze", type_line="Instant", cmc=1.0, colors=["U"],
         oracle_text="Counter target spell unless its controller pays {1}."),
    Card(name="Flusterstorm", type_line="Instant", cmc=1.0, colors=["U"],
         oracle_text="Counter target instant or sorcery spell unless its controller pays {1}."),
    Card(name="Pyroblast", type_line="Instant", cmc=1.0, colors=["R"],
         oracle_text="Choose one — Counter target spell if it's blue; or destroy target permanent if it's blue."),
    Card(name="Curiosity Test", type_line="Enchantment", cmc=1.0, colors=["U"], oracle_text=""),
    Card(name="Cryptic Command", type_line="Instant", cmc=4.0, colors=["U"],
         oracle_text="Choose two — Counter target spell; or return target permanent; or tap all creatures; or draw a card."),
    Card(name="Spell Pierce", type_line="Instant", cmc=1.0, colors=["U"],
         oracle_text="Counter target noncreature spell unless its controller pays {2}."),
]

# (extra-card name, how many core-running decks carry it). None → a non-core deck.
_TEMPLATES = [
    ("Daze", 10),
    ("Flusterstorm", 6),
    ("Pyroblast", 5),
    ("Curiosity Test", 5),
    ("Cryptic Command", 5),
    ("Spell Pierce", 6),
]
_NONCORE_DECKS = 4  # run only {Brainstorm, Ponder} — 2 core < k


def _deck_raw(player: str, mainboard_names: list[str]) -> dict:
    return {
        "Player": player,
        "Result": "1st Place",
        "Mainboard": [{"Count": 4, "CardName": n} for n in mainboard_names],
        "Sideboard": [],
    }


def _build_corpus():
    """Build the in-memory corpus described in the module docstring. Returns the connection."""
    con = store.connect(":memory:")
    store.load_cards(con, _CARDS)

    decks: list[dict] = []
    idx = 0
    for extra, n in _TEMPLATES:
        for _ in range(n):
            decks.append(_deck_raw(f"p{idx}", [*_CORE, extra]))
            idx += 1
    for _ in range(_NONCORE_DECKS):
        decks.append(_deck_raw(f"p{idx}", ["Brainstorm", "Ponder"]))
        idx += 1

    raw = {
        "Tournament": {"Name": "Delver Corpus", "Date": _DATE,
                       "Uri": "https://example.test/delver-corpus", "Formats": "Legacy"},
        "Decks": decks,
        "Rounds": [],
        "Standings": [],
    }
    tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
    con.execute("UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ?", [tid])
    return con


class TestShellProfile:
    def test_core_wanted_roles_band_and_colors(self):
        con = _build_corpus()
        maindeck = {"Brainstorm": 4, "Force of Will": 4, "Ponder": 4, "Spell Pierce": 2}
        prof = _shell_profile(con, "Delver", maindeck, since=_SINCE, until=_UNTIL)

        assert prof.core == frozenset(_CORE)
        # only flex non-land card is Spell Pierce (counter)
        assert prof.wanted_roles == frozenset({"counter"})
        # band straddles median flex CMC (Spell Pierce = 1) by ±1
        assert prof.cmc_lo == pytest.approx(0.0)
        assert prof.cmc_hi == pytest.approx(2.0)
        # color identity = union over all maindeck cards
        assert prof.color_identity == frozenset({"U"})
        con.close()

    def test_all_locked_yields_empty_wanted_roles(self):
        con = _build_corpus()
        maindeck = {"Brainstorm": 4, "Force of Will": 4, "Ponder": 4}  # all core
        prof = _shell_profile(con, "Delver", maindeck, since=_SINCE, until=_UNTIL)
        assert prof.wanted_roles == frozenset()
        assert prof.cmc_lo > prof.cmc_hi  # empty band → nothing passes the CMC gate
        con.close()


class TestCooccurrence:
    def test_counts_core_and_floor_exclusion(self):
        con = _build_corpus()
        counts = _cooccurrence(con, frozenset(_CORE), k=3, since=_SINCE, until=_UNTIL, cooccur_floor=5)

        assert counts.total_decks == 41
        assert counts.core_decks == 37
        # Daze: 10 core-running decks carry it
        assert counts.per_card["Daze"] == (10, 10)
        assert counts.per_card["Flusterstorm"] == (6, 6)
        # Pyroblast appears in exactly 5 core decks → at the floor, retained
        assert counts.per_card["Pyroblast"] == (5, 5)
        con.close()

    def test_below_floor_excluded(self):
        con = _build_corpus()
        counts = _cooccurrence(con, frozenset(_CORE), k=3, since=_SINCE, until=_UNTIL, cooccur_floor=7)
        # floor raised to 7: Daze (10) survives; Flusterstorm/Pyroblast (≤6) drop out
        assert "Daze" in counts.per_card
        assert "Flusterstorm" not in counts.per_card
        assert "Pyroblast" not in counts.per_card
        con.close()

    def test_empty_core_returns_empty(self):
        con = _build_corpus()
        counts = _cooccurrence(con, frozenset(), k=3, since=_SINCE, until=_UNTIL)
        assert counts.total_decks == 0 and counts.core_decks == 0 and counts.per_card == {}
        con.close()


class TestAdjacencyCandidates:
    def _run(self, con):
        maindeck = {"Brainstorm": 4, "Force of Will": 4, "Ponder": 4, "Spell Pierce": 2}
        sideboard = {"Flusterstorm": 2}
        return adjacency_candidates(con, "Delver", maindeck, sideboard, since=_SINCE, until=_UNTIL)

    def test_only_gated_candidates_surface_in_pmi_order(self):
        con = _build_corpus()
        result = self._run(con)
        names = [c.name for c in result]
        # Daze + Flusterstorm pass every gate; both co-occur only with core so PMI ties,
        # tie-break is cooccur_decks DESC → Daze (10) before Flusterstorm (6).
        assert names == ["Daze", "Flusterstorm"]
        con.close()

    def test_gates_exclude_the_right_cards(self):
        con = _build_corpus()
        names = {c.name for c in self._run(con)}
        assert "Pyroblast" not in names         # off-color
        assert "Curiosity Test" not in names    # no matching role
        assert "Cryptic Command" not in names   # off-curve (cmc 4 ∉ [0,2])
        assert "Spell Pierce" not in names       # already in maindeck (gate 1)
        assert names.isdisjoint(set(_CORE))      # core cards are in the deck
        con.close()

    def test_candidate_metadata_and_sideboard_flag(self):
        con = _build_corpus()
        by_name = {c.name: c for c in self._run(con)}
        daze = by_name["Daze"]
        assert isinstance(daze, AdjacencyCandidate)
        assert daze.matched_roles == frozenset({"counter"})
        assert 0.0 <= daze.cmc <= 2.0
        assert daze.in_sideboard is False
        assert by_name["Flusterstorm"].in_sideboard is True   # lives in D's sideboard
        assert daze.pmi == pytest.approx(math.log(41 / 37))    # P(X,core)=P(X), P(core)=37/41
        con.close()

    def test_limit_caps_results(self):
        con = _build_corpus()
        maindeck = {"Brainstorm": 4, "Force of Will": 4, "Ponder": 4, "Spell Pierce": 2}
        result = adjacency_candidates(con, "Delver", maindeck, {"Flusterstorm": 2},
                                      limit=1, since=_SINCE, until=_UNTIL)
        assert [c.name for c in result] == ["Daze"]
        con.close()

    def test_deterministic_across_calls(self):
        con = _build_corpus()
        a = [c.name for c in self._run(con)]
        b = [c.name for c in self._run(con)]
        assert a == b
        con.close()
