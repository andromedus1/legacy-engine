"""Tests for the multi-split pooling kernel + uniform builder (feature-multi-split-matrix Unit 2).

The headline is **the parity test**: every camp cell of a ``MultiSplitMatrix`` must equal
``build_matrix(split_variant=parent)``'s cell field-for-field, and every unsplit-subject cell must
equal the plain ``build_matrix``'s — otherwise the one-pass build is not a pure batching win and
the architecture is wrong.  Alongside it: pure-kernel tests for ``_pool_opponent_tallies`` /
``_multi_hierarchy_inputs`` (hand-built ``MatchResults``, no DB), the deliberate
``(camp, own_parent)`` absence, singleton degeneracy, and the ``ranking_view()`` contract.

Hermetic only — the shared two-parent corpus comes from ``test_match_results_multi_split``.
"""

from __future__ import annotations

import pytest

from legacy_engine.advisory.field import build_custom_field
from legacy_engine.advisory.positioning import rank_decks
from legacy_engine.analytics.match_results import (
    ArchetypeRecord,
    MatchCoverage,
    MatchResults,
    MatchupTally,
    compute_match_results,
)
from legacy_engine.analytics.matchup import (
    MatchupMatrix,
    MultiSplitMatrix,
    _multi_hierarchy_inputs,
    _multi_split_inclusion,
    _pool_opponent_tallies,
    beta_binomial_shrink,
    build_matrix,
    build_multi_split_matrix,
)

from test_match_results_multi_split import (  # noqa: E402  (sibling test module, sys.path via rootdir)
    EARLY_DATE,
    LATE_DATE,
    PARENTS,
    two_parent_con,
)

# Every field a MatchupCell carries — parity is asserted over ALL of them, not a subset.
_CELL_FIELDS = (
    "archetype_a", "archetype_b", "wins", "n", "p_raw", "p_shrunk",
    "ci_low", "ci_high", "tier", "is_mirror", "display", "prior_mean", "prior_source",
)

# (min_row_share, since, until) — full corpus, post-window, and pre-window at two floors.
_WINDOWS = [
    (0.02, None, None),
    (0.02, LATE_DATE, None),
    (0.02, None, LATE_DATE),
    (0.0, None, None),
    (0.0, LATE_DATE, None),
    (0.0, EARLY_DATE, LATE_DATE),
]


def _fields(cell) -> dict:
    return {f: getattr(cell, f) for f in _CELL_FIELDS}


def _assert_cell_parity(got, want, context: str) -> None:
    assert _fields(got) == _fields(want), f"cell parity broken for {context}"


# ---------------------------------------------------------------------------
# Pure kernel — _pool_opponent_tallies (hand-built MatchResults, no DB)
# ---------------------------------------------------------------------------


def _hand_mr(
    tallies: dict[tuple[str, str], tuple[int, int]],
    records: dict[str, tuple[int, int]] | None = None,
    camp_parent: dict[str, str] | None = None,
    mirror_n: dict[str, int] | None = None,
    decisive: int = 0,
    mirror: int = 0,
) -> MatchResults:
    """Build a ``MatchResults`` directly from ``(wins, losses)`` literals — no DB, no scan."""
    return MatchResults(
        matchups={
            (a, b): MatchupTally(archetype_a=a, archetype_b=b, wins=w, losses=losses)
            for (a, b), (w, losses) in tallies.items()
        },
        archetypes={
            label: ArchetypeRecord(archetype=label, wins=w, losses=losses)
            for label, (w, losses) in (records or {}).items()
        },
        coverage=MatchCoverage(decisive_matched=decisive, mirror_matches=mirror),
        provenance=None,
        mirror_n=dict(mirror_n or {}),
        camp_parent=dict(camp_parent or {}),
    )


class TestPoolOpponentTallies:
    def test_camp_opponents_sum_into_their_parent_column(self):
        mr = _hand_mr(
            {
                ("Delver", "Q [a]"): (3, 1),
                ("Delver", "Q [b]"): (2, 2),
                ("Delver", "Control"): (5, 5),
            },
            camp_parent={"Q [a]": "Q", "Q [b]": "Q"},
        )
        pooled = _pool_opponent_tallies(mr, mr.camp_parent)
        assert pooled[("Delver", "Q")] == (5, 8)

    def test_unsplit_opponent_passes_through_unchanged(self):
        mr = _hand_mr({("Delver", "Control"): (5, 5)}, camp_parent={})
        assert _pool_opponent_tallies(mr, mr.camp_parent) == {("Delver", "Control"): (5, 10)}

    def test_own_parent_pairs_are_excluded(self):
        """A camp vs its SIBLING camp pools to the camp's own parent — no such cell exists in a
        per-parent split matrix either, so it is dropped (decision 2)."""
        mr = _hand_mr(
            {
                ("P [a]", "P [b]"): (4, 1),
                ("P [b]", "P [a]"): (1, 4),
                ("P [a]", "Control"): (6, 2),
            },
            camp_parent={"P [a]": "P", "P [b]": "P"},
        )
        pooled = _pool_opponent_tallies(mr, mr.camp_parent)
        assert ("P [a]", "P") not in pooled
        assert ("P [b]", "P") not in pooled
        assert pooled == {("P [a]", "Control"): (6, 8)}

    def test_cross_parent_camps_pool_on_the_opponent_side_only(self):
        mr = _hand_mr(
            {
                ("P [a]", "Q [x]"): (3, 2),
                ("P [a]", "Q [y]"): (1, 4),
                ("P [b]", "Q [x]"): (2, 0),
            },
            camp_parent={"P [a]": "P", "P [b]": "P", "Q [x]": "Q", "Q [y]": "Q"},
        )
        pooled = _pool_opponent_tallies(mr, mr.camp_parent)
        assert pooled == {("P [a]", "Q"): (4, 10), ("P [b]", "Q"): (2, 2)}

    def test_empty_camp_parent_is_the_identity_pooling(self):
        mr = _hand_mr({("A", "B"): (3, 1), ("B", "A"): (1, 3)})
        assert _pool_opponent_tallies(mr, {}) == {("A", "B"): (3, 4), ("B", "A"): (1, 4)}


# ---------------------------------------------------------------------------
# Pure kernel — _multi_hierarchy_inputs
# ---------------------------------------------------------------------------


class TestMultiHierarchyInputs:
    def _two_parent_hand_mr(self) -> MatchResults:
        return _hand_mr(
            tallies={},
            records={
                "P [a]": (10, 6), "P [b]": (4, 8),
                "Q [x]": (7, 3), "Q [y]": (2, 5),
                "Control": (9, 9),
            },
            camp_parent={"P [a]": "P", "P [b]": "P", "Q [x]": "Q", "Q [y]": "Q"},
        )

    def test_parent_marginal_is_the_camp_sum(self):
        mr = self._two_parent_hand_mr()
        marginals, _lco, _camp_of = _multi_hierarchy_inputs(
            mr, ["P [a]", "P [b]", "Q [x]", "Q [y]", "Control"], ["Control"], mr.camp_parent, {},
        )
        assert marginals["P"] == beta_binomial_shrink(14, 28)
        assert marginals["Q"] == beta_binomial_shrink(9, 17)
        assert marginals["Control"] == beta_binomial_shrink(9, 18)

    def test_camp_of_maps_subjects_to_parent_or_self(self):
        mr = self._two_parent_hand_mr()
        _m, _lco, camp_of = _multi_hierarchy_inputs(
            mr, ["P [a]", "Q [x]", "Control"], ["Control"], mr.camp_parent, {},
        )
        assert camp_of == {"P [a]": "P", "Q [x]": "Q", "Control": "Control"}

    def test_lco_is_pooled_parent_minus_the_camp_itself(self):
        mr = self._two_parent_hand_mr()
        pooled = {("P [a]", "Control"): (10, 16), ("P [b]", "Control"): (4, 12)}
        _m, lco, _c = _multi_hierarchy_inputs(
            mr, ["P [a]", "P [b]", "Control"], ["Control"], mr.camp_parent, pooled,
        )
        assert lco[("P [a]", "Control")] == (4, 12)
        assert lco[("P [b]", "Control")] == (10, 16)

    def test_unobserved_opponent_still_gets_a_zero_lco_reference(self):
        """A camp that never played an included opponent keeps the parent-cell prior source with
        a (0, 0) reference — matching ``_camp_hierarchy_inputs``'s behavior exactly."""
        mr = self._two_parent_hand_mr()
        _m, lco, _c = _multi_hierarchy_inputs(
            mr, ["P [a]", "P [b]"], ["Control"], mr.camp_parent, {},
        )
        assert lco[("P [a]", "Control")] == (0, 0)

    def test_own_parent_column_has_no_reference_cell(self):
        mr = self._two_parent_hand_mr()
        _m, lco, _c = _multi_hierarchy_inputs(
            mr, ["P [a]", "P [b]"], ["P", "Control"], mr.camp_parent, {},
        )
        assert ("P [a]", "P") not in lco
        assert ("P [a]", "Control") in lco

    def test_negative_lco_asserts_on_a_non_partition_input(self):
        """Synthetic corruption: a sibling carrying negative pooled counts makes the parent total
        smaller than one camp's own, which can only mean the camps are not a partition of the
        parent.  That must crash loudly, never be clamped."""
        mr = self._two_parent_hand_mr()
        corrupted = {("P [a]", "Control"): (10, 16), ("P [b]", "Control"): (-12, -20)}
        with pytest.raises(AssertionError, match="not a partition"):
            _multi_hierarchy_inputs(
                mr, ["P [a]", "P [b]"], ["Control"], mr.camp_parent, corrupted,
            )


# ---------------------------------------------------------------------------
# Inclusion: subjects/opponents reproduce the plain + per-parent row sets exactly
# ---------------------------------------------------------------------------


class TestInclusion:
    @pytest.mark.parametrize(("min_row_share", "since", "until"), _WINDOWS)
    def test_opponent_axis_is_the_plain_matrix_row_set(self, min_row_share, since, until):
        con = two_parent_con()
        msm = build_multi_split_matrix(
            con, parents=PARENTS, min_row_share=min_row_share, since=since, until=until,
        )
        plain = build_matrix(con, min_row_share=min_row_share, since=since, until=until)
        assert msm.opponents == plain.archetypes
        con.close()

    @pytest.mark.parametrize(("min_row_share", "since", "until"), _WINDOWS)
    def test_subject_axis_is_camps_plus_unsplit_rows(self, min_row_share, since, until):
        con = two_parent_con()
        msm = build_multi_split_matrix(
            con, parents=PARENTS, min_row_share=min_row_share, since=since, until=until,
        )
        plain = build_matrix(con, min_row_share=min_row_share, since=since, until=until)
        camps = {s for s in msm.subjects if s in msm.camp_parent}
        assert camps  # both parents split
        assert set(msm.subjects) - camps == set(plain.archetypes) - set(msm.parents)
        con.close()

    def test_camps_are_force_included_below_the_floor(self):
        """Painter [unlabeled] is a fringe camp — force-included as a subject even though its
        parent-level share is what clears the floor."""
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS, min_row_share=0.02)
        assert "Painter [unlabeled]" in msm.subjects
        assert "Doomsday [unlabeled]" in msm.subjects
        con.close()

    def test_fringe_unsplit_archetype_still_respects_the_floor(self):
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS, min_row_share=0.02)
        assert "Elves" not in msm.subjects
        assert "Elves" not in msm.opponents
        msm_open = build_multi_split_matrix(con, parents=PARENTS, min_row_share=0.0)
        assert "Elves" in msm_open.subjects
        con.close()

    def test_inclusion_reconstructs_parents_from_camp_sums(self):
        """``_multi_split_inclusion`` reads a camp-granularity scan but must yield the SAME
        parent-level opponent set the plain scan would — reconstructed records, invariant
        denominator."""
        con = two_parent_con()
        maximal = compute_match_results(con, split_variants=PARENTS)
        subjects, opponents, parents = _multi_split_inclusion(maximal, 0.02)
        plain = build_matrix(con)
        assert opponents == plain.archetypes
        assert parents == sorted(PARENTS)
        assert set(subjects) & set(maximal.camp_parent) == set(maximal.camp_parent)
        con.close()


# ---------------------------------------------------------------------------
# THE PARITY TEST
# ---------------------------------------------------------------------------


class TestUniformParity:
    """One multi-split build must reproduce, cell-for-cell, what N per-parent builds produce."""

    @pytest.mark.parametrize(("min_row_share", "since", "until"), _WINDOWS)
    def test_camp_rows_equal_the_per_parent_split_build(self, min_row_share, since, until):
        con = two_parent_con()
        msm = build_multi_split_matrix(
            con, parents=PARENTS, min_row_share=min_row_share, since=since, until=until,
        )
        checked = 0
        for parent in PARENTS:
            per = build_matrix(
                con, split_variant=parent, min_row_share=min_row_share,
                since=since, until=until,
            )
            camps = [s for s in msm.subjects if msm.camp_parent.get(s) == parent]
            assert camps, f"no camps observed for {parent}"
            # The shared key set: the per-parent build's rows minus its camp columns is exactly
            # the multi build's opponent axis minus the parent's own (absent) column.
            assert set(per.archetypes) - set(camps) == set(msm.opponents) - {parent}
            for camp in camps:
                for opponent in msm.opponents:
                    if opponent == parent:
                        continue  # own-parent column: absent by design, covered separately
                    _assert_cell_parity(
                        msm.cells[(camp, opponent)], per.cells[(camp, opponent)],
                        f"{camp!r} vs {opponent!r} (split_variant={parent!r})",
                    )
                    checked += 1
                _assert_cell_parity(
                    msm.cells[(camp, camp)], per.cells[(camp, camp)], f"mirror {camp!r}",
                )
                checked += 1
        assert checked >= 20
        con.close()

    @pytest.mark.parametrize(("min_row_share", "since", "until"), _WINDOWS)
    def test_unsplit_rows_equal_the_plain_build(self, min_row_share, since, until):
        con = two_parent_con()
        msm = build_multi_split_matrix(
            con, parents=PARENTS, min_row_share=min_row_share, since=since, until=until,
        )
        plain = build_matrix(con, min_row_share=min_row_share, since=since, until=until)
        unsplit = [s for s in msm.subjects if s not in msm.camp_parent]
        assert unsplit
        for subject in unsplit:
            for opponent in msm.opponents:
                if opponent == subject:
                    continue
                _assert_cell_parity(
                    msm.cells[(subject, opponent)], plain.cells[(subject, opponent)],
                    f"{subject!r} vs {opponent!r} (plain)",
                )
            _assert_cell_parity(
                msm.cells[(subject, subject)], plain.cells[(subject, subject)],
                f"mirror {subject!r} (plain)",
            )
        con.close()

    def test_camp_prior_source_is_the_leave_camp_out_chain(self):
        """Parity is not vacuous: camp cells really do carry the hierarchical LCO prior, unsplit
        cells the marginal one."""
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS)
        assert msm.cells[("Doomsday [Murktide]", "Control")].prior_source == (
            "parent cell (leave-camp-out)"
        )
        assert msm.cells[("Doomsday [Murktide]", "Painter")].prior_source == (
            "parent cell (leave-camp-out)"
        )
        assert msm.cells[("Control", "Doomsday")].prior_source == "marginal"
        con.close()

    def test_pooled_camp_column_sums_the_opponents_camps(self):
        """The pooling itself, end-to-end: a camp's record vs a split parent is the sum of its
        records against that parent's camps."""
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS)
        per = build_matrix(con, split_variant="Doomsday")
        pooled_cell = msm.cells[("Doomsday [Murktide]", "Painter")]
        assert (pooled_cell.wins, pooled_cell.n) == (
            per.cells[("Doomsday [Murktide]", "Painter")].wins,
            per.cells[("Doomsday [Murktide]", "Painter")].n,
        )
        assert pooled_cell.n > 0
        con.close()


# ---------------------------------------------------------------------------
# (camp, own_parent) absence
# ---------------------------------------------------------------------------


class TestOwnParentColumnAbsent:
    @pytest.mark.parametrize(("min_row_share", "since", "until"), _WINDOWS)
    def test_no_camp_has_a_cell_against_its_own_parent(self, min_row_share, since, until):
        con = two_parent_con()
        msm = build_multi_split_matrix(
            con, parents=PARENTS, min_row_share=min_row_share, since=since, until=until,
        )
        for camp, parent in msm.camp_parent.items():
            assert (camp, parent) not in msm.cells
        con.close()

    def test_every_other_ordered_pair_is_present(self):
        """Rectangular apart from the documented hole: every (subject, opponent) pair exists
        unless the opponent is the subject's own parent."""
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS)
        for subject in msm.subjects:
            own_parent = msm.camp_parent.get(subject)
            for opponent in msm.opponents:
                if opponent == own_parent:
                    continue
                assert (subject, opponent) in msm.cells, f"missing {(subject, opponent)}"
            assert (subject, subject) in msm.cells
        con.close()

    def test_camp_labels_never_appear_on_the_opponent_axis(self):
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS)
        assert not any("[" in o for o in msm.opponents)
        con.close()


# ---------------------------------------------------------------------------
# Degenerate / no-op paths
# ---------------------------------------------------------------------------


class TestDegenerateParents:
    def test_singleton_parents_equals_the_single_split_build(self):
        con = two_parent_con()
        for parent in PARENTS:
            msm = build_multi_split_matrix(con, parents=[parent])
            per = build_matrix(con, split_variant=parent)
            camps = [s for s in msm.subjects if msm.camp_parent.get(s) == parent]
            assert camps
            for camp in camps:
                for opponent in msm.opponents:
                    if opponent == parent:
                        continue
                    _assert_cell_parity(
                        msm.cells[(camp, opponent)], per.cells[(camp, opponent)],
                        f"singleton {camp!r} vs {opponent!r}",
                    )
            assert msm.parents == [parent]
        con.close()

    def test_no_parents_is_the_plain_rectangular_matrix(self):
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=[])
        plain = build_matrix(con)
        assert msm.subjects == plain.archetypes
        assert msm.opponents == plain.archetypes
        assert msm.parents == []
        assert msm.camp_parent == {}
        assert msm.cells.keys() == plain.cells.keys()
        for key, cell in plain.cells.items():
            _assert_cell_parity(msm.cells[key], cell, f"no-parents {key}")
        con.close()

    def test_parent_absent_from_the_corpus_is_dropped_gracefully(self):
        con = two_parent_con()
        with_ghost = build_multi_split_matrix(con, parents=[*PARENTS, "NoSuchArchetype"])
        without = build_multi_split_matrix(con, parents=PARENTS)
        assert with_ghost.parents == without.parents == list(sorted(PARENTS))
        assert with_ghost.subjects == without.subjects
        assert with_ghost.cells.keys() == without.cells.keys()
        con.close()

    def test_parent_absent_from_the_window_is_dropped_gracefully(self):
        """A window with no matches at all still builds an (empty) matrix rather than raising."""
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS, until="2020-01-01")
        assert msm.subjects == []
        assert msm.opponents == []
        assert msm.parents == []
        assert msm.cells == {}
        con.close()


# ---------------------------------------------------------------------------
# MultiSplitMatrix metadata + ranking_view
# ---------------------------------------------------------------------------


class TestMultiSplitMatrixMetadata:
    def test_total_matches_is_camp_granularity(self):
        """Documented divergence from the plain matrix: cross-camp pairings count as decisive
        here and as mirrors there; only the sum is invariant."""
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS)
        plain = build_matrix(con)
        assert msm.total_matches > plain.total_matches
        con.close()

    def test_provenance_and_caveat_travel(self):
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS, provenance="online")
        assert msm.provenance == "online"
        assert "n<30" in msm.caveat
        con.close()


class TestRankingView:
    def test_view_shares_the_cell_dict_and_spans_both_axes(self):
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS)
        view = msm.ranking_view()
        assert isinstance(view, MatchupMatrix)
        assert not isinstance(view, MultiSplitMatrix)
        assert view.cells is msm.cells
        assert view.archetypes == sorted(set(msm.subjects) | set(msm.opponents))
        # Deliberately NOT square — the parent columns have no camp rows' own-parent cell.
        assert any(
            (a, b) not in view.cells
            for a in view.archetypes for b in view.archetypes if a != b
        )
        con.close()

    def test_rank_decks_consumes_the_view(self):
        """Cross-camp P(best) in ONE shared-field MC — the whole point of the feature."""
        con = two_parent_con()
        msm = build_multi_split_matrix(con, parents=PARENTS)
        con.close()
        field = build_custom_field(
            {"Doomsday": 0.4, "Painter": 0.3, "Control": 0.2, "Delver": 0.1},
            counts={"Doomsday": 120, "Painter": 90, "Control": 60, "Delver": 30},
        )
        candidates = list(msm.subjects)
        ranking = rank_decks(msm.ranking_view(), field, candidates, n_draws=200, seed=7)
        assert set(ranking.decks) == set(candidates)
        assert sum(ranking.p_best.values()) == pytest.approx(1.0, abs=1e-6)
        # Deterministic under a fixed seed.
        again = rank_decks(msm.ranking_view(), field, candidates, n_draws=200, seed=7)
        assert again.decks == ranking.decks
        assert again.p_best == ranking.p_best
