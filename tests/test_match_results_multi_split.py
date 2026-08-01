"""Tests for ``compute_match_results(split_variants=...)`` (feature-multi-split-matrix Unit 1).

Covers the multi-parent relabel seam and the ``camp_parent`` provenance map: singleton
equivalence with the single-archetype ``split_variant`` path, simultaneous two-parent relabeling,
the explicit camp->parent map (never prefix parsing), the both-params ``ValueError``, and the
``split_variants=None`` identity path.

House style: module-level raw dicts -> ``parse_cache_item`` -> ``store.load_tournament`` into
``:memory:``; labels pinned via direct SQL ``UPDATE``; ``TestX`` classes; deterministic.  The
two-parent corpus defined here is also the parity fixture imported by
``test_matchup_multi_split.py``.
"""

from __future__ import annotations

import pytest

from legacy_engine.analytics import compute_match_results
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item

# ---------------------------------------------------------------------------
# Shared two-parent corpus (also the Unit 2 parity fixture)
#
#   Split parents: "Doomsday" (camps Murktide / Turbo / unlabeled residue) and
#                  "Painter"  (camps Grindstone / Welder / unlabeled residue)
#   Plain archetypes: "Control", "Delver", "Elves" (Elves is fringe — below the 0.02 floor)
#
#   Pairings deliberately cover: camp vs plain, camp vs OTHER parent's camp (cross-parent),
#   camp vs SIBLING camp (same-parent cross-camp — a parent-level mirror), camp mirrors,
#   plain mirrors, and plain vs plain.  Two tournaments on different dates so the
#   ``since``/``until`` window has something to bite on.
# ---------------------------------------------------------------------------

PARENTS = ("Doomsday", "Painter")

# player -> (archetype, variant)
_ROSTER: dict[str, tuple[str, str | None]] = {
    "d1": ("Doomsday", "Murktide"),
    "d2": ("Doomsday", "Murktide"),
    "d3": ("Doomsday", "Turbo"),
    "d4": ("Doomsday", None),
    "p1": ("Painter", "Grindstone"),
    "p2": ("Painter", "Grindstone"),
    "p3": ("Painter", "Welder"),
    "p4": ("Painter", None),
    "c1": ("Control", None),
    "c2": ("Control", None),
    "v1": ("Delver", None),
    "e1": ("Elves", None),
}

_MAIN = [{"Count": 4, "CardName": "Brainstorm"}, {"Count": 4, "CardName": "Ponder"}]

# (player1, player2, result, repeat)
_ROUNDS_EARLY: list[tuple[str, str, str, int]] = [
    ("d1", "c1", "2-1", 20), ("c1", "d1", "2-0", 6),
    ("d3", "c1", "2-1", 12), ("c1", "d3", "2-0", 9),
    ("d4", "c1", "2-0", 5), ("c1", "d4", "2-1", 4),
    ("d1", "p1", "2-0", 11), ("p1", "d1", "2-1", 7),
    ("d1", "p3", "2-1", 4), ("d3", "p1", "2-0", 6),
    ("d3", "p4", "2-1", 3), ("d4", "p3", "2-0", 2), ("p4", "d4", "2-1", 3),
    ("d1", "d3", "2-1", 5), ("d3", "d4", "2-0", 3), ("d1", "d4", "2-1", 2),
    ("p1", "p3", "2-0", 4), ("p3", "p4", "2-1", 2),
    ("d1", "d2", "2-1", 6), ("p1", "p2", "2-0", 5), ("c1", "c2", "2-1", 4),
    ("p1", "c1", "2-1", 9), ("c1", "p1", "2-0", 6),
    ("p3", "v1", "2-1", 7), ("v1", "p3", "2-0", 5), ("p4", "v1", "2-1", 3),
    ("d1", "v1", "2-0", 8), ("v1", "d1", "2-1", 6), ("d3", "v1", "2-1", 4),
    ("c1", "v1", "2-1", 10), ("v1", "c1", "2-0", 8),
    ("e1", "v1", "2-1", 1),
]

_ROUNDS_LATE: list[tuple[str, str, str, int]] = [
    ("d1", "c1", "2-1", 7), ("c1", "d1", "2-0", 9),
    ("d3", "p3", "2-0", 5), ("p3", "d3", "2-1", 4),
    ("d4", "p1", "2-1", 3),
    ("d1", "d3", "2-0", 4), ("p1", "p4", "2-1", 3),
    ("d1", "d2", "2-0", 5),
    ("p3", "c1", "2-1", 6), ("c1", "p3", "2-0", 4),
    ("v1", "d1", "2-1", 5), ("d1", "v1", "2-0", 6),
    ("c1", "v1", "2-1", 7), ("v1", "c1", "2-0", 6),
    ("p1", "v1", "2-1", 4),
    ("e1", "c1", "2-1", 1),
]

EARLY_DATE = "2026-01-15"
LATE_DATE = "2026-05-20"


def _deck(player: str) -> dict:
    return {"Player": player, "Result": "1st Place", "Mainboard": _MAIN, "Sideboard": []}


def _expand(spec: list[tuple[str, str, str, int]]) -> list[dict]:
    rounds: list[dict] = []
    for player1, player2, result, repeat in spec:
        rounds.extend(
            {"Player1": player1, "Player2": player2, "Result": result} for _ in range(repeat)
        )
    return rounds


def _raw(name: str, date: str, spec: list[tuple[str, str, str, int]]) -> dict:
    return {
        "Tournament": {
            "Name": name,
            "Date": date,
            "Uri": f"https://example.test/{name}",
            "Formats": "Legacy",
        },
        "Decks": [_deck(p) for p in _ROSTER],
        "Rounds": _expand(spec),
        "Standings": [],
    }


def _pin_labels(con, tid: str) -> None:
    for player, (archetype, variant) in _ROSTER.items():
        con.execute(
            "UPDATE decks SET archetype=?, variant=? WHERE tournament_id=? AND player=?",
            [archetype, variant, tid, player],
        )


def build_two_parent_corpus(con) -> None:
    """Load the shared two-parent corpus (two tournaments, distinct dates) into ``con``."""
    for name, date, spec in (
        ("multi-split-early", EARLY_DATE, _ROUNDS_EARLY),
        ("multi-split-late", LATE_DATE, _ROUNDS_LATE),
    ):
        tid = store.load_tournament(con, parse_cache_item(_raw(name, date, spec), "MTGO"))
        _pin_labels(con, tid)


def two_parent_con():
    """Hermetic in-memory connection preloaded with the shared two-parent corpus."""
    con = store.connect(":memory:")
    build_two_parent_corpus(con)
    return con


# ---------------------------------------------------------------------------
# Prefix-trap corpus: "Painter" and "Blue Painter" coexist as distinct archetypes.
# ---------------------------------------------------------------------------

_PREFIX_ROSTER: dict[str, tuple[str, str | None]] = {
    "a1": ("Painter", "Grindstone"),
    "a2": ("Painter", "Welder"),
    "b1": ("Blue Painter", "Grindstone"),
    "b2": ("Blue Painter", None),
    "c1": ("Control", None),
}

_PREFIX_ROUNDS: list[tuple[str, str, str, int]] = [
    ("a1", "c1", "2-1", 6), ("a2", "c1", "2-0", 4),
    ("b1", "c1", "2-1", 5), ("b2", "c1", "2-0", 3),
    ("a1", "b1", "2-1", 4), ("b2", "a2", "2-0", 2),
]


def _prefix_con():
    con = store.connect(":memory:")
    raw = {
        "Tournament": {
            "Name": "prefix-trap",
            "Date": EARLY_DATE,
            "Uri": "https://example.test/prefix-trap",
            "Formats": "Legacy",
        },
        "Decks": [_deck(p) for p in _PREFIX_ROSTER],
        "Rounds": _expand(_PREFIX_ROUNDS),
        "Standings": [],
    }
    tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
    for player, (archetype, variant) in _PREFIX_ROSTER.items():
        con.execute(
            "UPDATE decks SET archetype=?, variant=? WHERE tournament_id=? AND player=?",
            [archetype, variant, tid, player],
        )
    return con


# ---------------------------------------------------------------------------
# Identity path (the byte-identical-default gate)
# ---------------------------------------------------------------------------


class TestSplitVariantsIdentity:
    def test_none_is_identity(self):
        con = two_parent_con()
        baseline = compute_match_results(con)
        res = compute_match_results(con, split_variants=None)
        assert res.matchups == baseline.matchups
        assert res.archetypes == baseline.archetypes
        assert res.coverage == baseline.coverage
        assert res.mirror_n == baseline.mirror_n
        assert res.camp_parent == {}
        con.close()

    def test_empty_collection_is_identity(self):
        con = two_parent_con()
        baseline = compute_match_results(con)
        res = compute_match_results(con, split_variants=[])
        assert res.matchups == baseline.matchups
        assert res.archetypes == baseline.archetypes
        assert res.coverage == baseline.coverage
        assert res.mirror_n == baseline.mirror_n
        assert res.camp_parent == {}
        con.close()

    def test_no_camp_labels_leak_into_default_path(self):
        con = two_parent_con()
        res = compute_match_results(con)
        assert not any("[" in a for a in res.archetypes)
        assert res.archetypes.keys() == {"Doomsday", "Painter", "Control", "Delver", "Elves"}
        con.close()


# ---------------------------------------------------------------------------
# Singleton equivalence: split_variants=["X"] == split_variant="X"
# ---------------------------------------------------------------------------


class TestSingletonEquivalence:
    @pytest.mark.parametrize("parent", PARENTS)
    def test_singleton_matches_single_split_field_for_field(self, parent):
        con = two_parent_con()
        single = compute_match_results(con, split_variant=parent)
        multi = compute_match_results(con, split_variants=[parent])
        assert multi.matchups == single.matchups
        assert multi.archetypes == single.archetypes
        assert multi.coverage == single.coverage
        assert multi.mirror_n == single.mirror_n
        # camp_parent is populated for the single-split path too (additive provenance)
        assert multi.camp_parent == single.camp_parent
        con.close()

    def test_singleton_camp_parent_contents(self):
        con = two_parent_con()
        res = compute_match_results(con, split_variants=["Doomsday"])
        assert res.camp_parent == {
            "Doomsday [Murktide]": "Doomsday",
            "Doomsday [Turbo]": "Doomsday",
            "Doomsday [unlabeled]": "Doomsday",
        }
        con.close()

    def test_singleton_windowed_equivalence(self):
        con = two_parent_con()
        single = compute_match_results(con, split_variant="Painter", since=LATE_DATE)
        multi = compute_match_results(con, split_variants=("Painter",), since=LATE_DATE)
        assert multi.matchups == single.matchups
        assert multi.archetypes == single.archetypes
        assert multi.coverage == single.coverage
        con.close()


# ---------------------------------------------------------------------------
# Two-parent simultaneous relabel
# ---------------------------------------------------------------------------


class TestTwoParentScan:
    def test_both_parents_camp_labeled_simultaneously(self):
        con = two_parent_con()
        res = compute_match_results(con, split_variants=PARENTS)
        assert "Doomsday" not in res.archetypes
        assert "Painter" not in res.archetypes
        assert {
            "Doomsday [Murktide]", "Doomsday [Turbo]", "Doomsday [unlabeled]",
            "Painter [Grindstone]", "Painter [Welder]", "Painter [unlabeled]",
            "Control", "Delver", "Elves",
        } == res.archetypes.keys()
        con.close()

    def test_cross_parent_camp_pairing_is_a_directed_camp_cell(self):
        """A Doomsday camp vs a Painter camp tallies at camp granularity on BOTH sides."""
        con = two_parent_con()
        res = compute_match_results(con, split_variants=PARENTS)
        cell = res.matchups[("Doomsday [Murktide]", "Painter [Grindstone]")]
        assert (cell.wins, cell.losses) == (11, 7)
        back = res.matchups[("Painter [Grindstone]", "Doomsday [Murktide]")]
        assert (back.wins, back.losses) == (7, 11)
        con.close()

    def test_same_camp_pairing_is_a_camp_level_mirror(self):
        """d1 and d2 are both Doomsday/Murktide — same effective label, so a mirror."""
        con = two_parent_con()
        res = compute_match_results(con, split_variants=PARENTS)
        assert res.mirror_n["Doomsday [Murktide]"] == 11  # 6 early + 5 late
        assert res.mirror_n["Painter [Grindstone]"] == 5
        con.close()

    def test_sibling_camp_pairing_is_decisive_not_mirror(self):
        """Two DIFFERENT camps of the same parent are distinct labels: directed, not a mirror."""
        con = two_parent_con()
        res = compute_match_results(con, split_variants=PARENTS)
        cell = res.matchups[("Doomsday [Murktide]", "Doomsday [Turbo]")]
        assert (cell.wins, cell.losses) == (9, 0)  # 5 early + 4 late
        # The SAME pairing is a parent-level mirror in the unsplit scan.
        unsplit = compute_match_results(con)
        assert unsplit.mirror_n["Doomsday"] >= 9
        con.close()

    def test_decisive_plus_mirror_is_relabel_invariant(self):
        """The row-inclusion denominator basis is invariant under relabeling — a cross-camp
        pairing merely moves from the mirror counter to the decisive counter."""
        con = two_parent_con()
        plain = compute_match_results(con).coverage
        split = compute_match_results(con, split_variants=PARENTS).coverage
        assert plain.total_pairings == split.total_pairings
        assert (plain.decisive_matched + plain.mirror_matches) == (
            split.decisive_matched + split.mirror_matches
        )
        assert split.decisive_matched > plain.decisive_matched  # cross-camp pairings moved
        con.close()

    def test_parent_marginal_reconstructs_from_camp_sums(self):
        """Summing wins and losses separately across camp siblings reproduces the unsplit
        parent's marginal exactly — the property the pooling kernel rests on."""
        con = two_parent_con()
        plain = compute_match_results(con)
        split = compute_match_results(con, split_variants=PARENTS)
        for parent in PARENTS:
            camps = [c for c, p in split.camp_parent.items() if p == parent]
            assert sum(split.archetypes[c].wins for c in camps) == plain.archetypes[parent].wins
            assert sum(split.archetypes[c].losses for c in camps) == plain.archetypes[parent].losses
        con.close()

    def test_unsplit_archetype_records_untouched(self):
        con = two_parent_con()
        plain = compute_match_results(con)
        split = compute_match_results(con, split_variants=PARENTS)
        for label in ("Control", "Delver", "Elves"):
            assert split.archetypes[label] == plain.archetypes[label]
            assert split.mirror_n.get(label, 0) == plain.mirror_n.get(label, 0)
        con.close()

    def test_absent_parent_is_a_no_op(self):
        con = two_parent_con()
        with_ghost = compute_match_results(con, split_variants=[*PARENTS, "NoSuchArchetype"])
        without = compute_match_results(con, split_variants=PARENTS)
        assert with_ghost.archetypes == without.archetypes
        assert with_ghost.camp_parent == without.camp_parent
        con.close()


# ---------------------------------------------------------------------------
# camp_parent provenance: explicit map, never prefix parsing
# ---------------------------------------------------------------------------


class TestCampParentMap:
    def test_two_parent_map_contents(self):
        con = two_parent_con()
        res = compute_match_results(con, split_variants=PARENTS)
        assert res.camp_parent == {
            "Doomsday [Murktide]": "Doomsday",
            "Doomsday [Turbo]": "Doomsday",
            "Doomsday [unlabeled]": "Doomsday",
            "Painter [Grindstone]": "Painter",
            "Painter [Welder]": "Painter",
            "Painter [unlabeled]": "Painter",
        }
        con.close()

    def test_every_camp_label_is_mapped(self):
        con = two_parent_con()
        res = compute_match_results(con, split_variants=PARENTS)
        assert {a for a in res.archetypes if "[" in a} == res.camp_parent.keys()
        con.close()

    def test_sibling_archetypes_sharing_a_word_map_to_their_own_parent(self):
        """``Painter`` and ``Blue Painter`` coexist in the staged registry — the map is recorded
        at relabel time by the labeler, so each camp resolves to the archetype it came from."""
        con = _prefix_con()
        res = compute_match_results(con, split_variants=["Painter", "Blue Painter"])
        assert res.camp_parent == {
            "Painter [Grindstone]": "Painter",
            "Painter [Welder]": "Painter",
            "Blue Painter [Grindstone]": "Blue Painter",
            "Blue Painter [unlabeled]": "Blue Painter",
        }
        con.close()

    def test_splitting_one_sibling_leaves_the_other_whole(self):
        con = _prefix_con()
        res = compute_match_results(con, split_variants=["Painter"])
        assert "Blue Painter" in res.archetypes
        assert not any(a.startswith("Blue Painter [") for a in res.archetypes)
        assert set(res.camp_parent.values()) == {"Painter"}
        con.close()


# ---------------------------------------------------------------------------
# Fail-fast on conflicting params
# ---------------------------------------------------------------------------


class TestConflictingParams:
    def test_both_params_raises(self):
        con = two_parent_con()
        with pytest.raises(ValueError, match="not both"):
            compute_match_results(con, split_variant="Doomsday", split_variants=["Painter"])
        con.close()

    def test_both_params_raises_even_when_equal(self):
        con = two_parent_con()
        with pytest.raises(ValueError, match="not both"):
            compute_match_results(con, split_variant="Doomsday", split_variants=["Doomsday"])
        con.close()
