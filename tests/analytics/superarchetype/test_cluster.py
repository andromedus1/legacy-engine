"""Unit tests for the pure superarchetype clustering core (no DuckDB anywhere in this module)."""

from __future__ import annotations

import numpy as np
import pytest

from legacy_engine.analytics.superarchetype.cluster import (
    ArchetypeDeck,
    _linkage_from,
    au_pvalues,
    build_compositions,
    cluster_archetypes,
    comembership_stability,
    jaccard_dissimilarity,
    select_supported_clusters,
    weighted_jaccard_matrix,
)


class TestBuildCompositions:
    def test_core_threshold_is_inclusive(self, make_deck):
        # Exactly 50% inclusion is core; below it is not.
        decks = [
            make_deck("A", ["x", "half", "low"], idx=0),
            make_deck("A", ["x", "half"], idx=1),
            make_deck("A", ["x"], idx=2),
            make_deck("A", ["x"], idx=3),
        ]
        compositions, _staples = build_compositions(decks, definer_min_decks=1, definer_min_core=1)
        assert compositions["A"].core == frozenset({"x", "half"})

    def test_definer_floors_are_inclusive(self, make_pool):
        eight = tuple(f"c{i}" for i in range(8))
        decks = make_pool("Exactly", eight, n=30) + make_pool("OneShort", eight, n=29)
        compositions, _ = build_compositions(decks)
        assert compositions["Exactly"].is_definer is True
        assert compositions["OneShort"].is_definer is False

    def test_seven_core_cards_is_not_a_definer(self, make_pool):
        decks = make_pool("Thin", tuple(f"c{i}" for i in range(7)), n=100)
        compositions, _ = build_compositions(decks)
        assert compositions["Thin"].is_definer is False

    def test_staples_are_derived_from_definers_and_hard_removed(
        self, two_family_corpus, staples
    ):
        compositions, derived_staples = build_compositions(two_family_corpus)
        assert derived_staples == staples
        for comp in compositions.values():
            assert not (comp.stripped_core & set(staples))

    def test_empty_input(self):
        assert build_compositions([]) == ({}, ())

    def test_tier_rides_along(self, make_pool):
        decks = make_pool("Big", tuple(f"c{i}" for i in range(9)), n=120)
        compositions, _ = build_compositions(decks)
        assert compositions["Big"].tier == "established"


class TestDistance:
    def test_jaccard_basics(self):
        assert jaccard_dissimilarity(frozenset("ab"), frozenset("ab")) == 0.0
        assert jaccard_dissimilarity(frozenset("ab"), frozenset("cd")) == 1.0
        assert jaccard_dissimilarity(frozenset("abc"), frozenset("abd")) == pytest.approx(0.5)

    def test_empty_union_is_maximally_dissimilar_not_nan(self):
        assert jaccard_dissimilarity(frozenset(), frozenset()) == 1.0

    def test_weighted_matrix_with_unit_weights_is_set_jaccard(self):
        M = np.array([[1.0, 1.0, 0.0], [1.0, 0.0, 1.0]])
        D = weighted_jaccard_matrix(M, np.ones(3))
        assert D[0, 1] == pytest.approx(1.0 - 1 / 3)
        assert D[0, 0] == 0.0

    def test_weighting_a_shared_card_up_pulls_rows_together(self):
        M = np.array([[1.0, 1.0, 0.0], [1.0, 0.0, 1.0]])
        heavy = weighted_jaccard_matrix(M, np.array([10.0, 1.0, 1.0]))
        assert heavy[0, 1] < weighted_jaccard_matrix(M, np.ones(3))[0, 1]

    def test_zero_weight_everywhere_degrades_to_maximally_dissimilar(self):
        M = np.array([[1.0, 1.0], [1.0, 1.0]])
        assert weighted_jaccard_matrix(M, np.zeros(2))[0, 1] == 1.0


class TestAuPvalues:
    def test_clean_blocks_are_strongly_supported(self):
        # Two disjoint card blocks: each block's pair is a real branch.
        M = np.array([
            [1, 1, 1, 1, 0, 0, 0, 0],
            [1, 1, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 1],
            [0, 0, 0, 0, 1, 1, 1, 0],
        ], dtype=float)
        support = au_pvalues(M, ["a", "b", "c", "d"], seed=0, n_boot=40)
        by_members = {b.members: b for b in support.values()}
        assert by_members[("a", "b")].au > 0.95
        assert by_members[("c", "d")].au > 0.95

    def test_is_deterministic_for_a_fixed_seed(self):
        M = np.array([
            [1, 1, 1, 0, 0, 0],
            [1, 1, 0, 1, 0, 0],
            [0, 0, 0, 1, 1, 1],
        ], dtype=float)
        first = au_pvalues(M, ["a", "b", "c"], seed=7, n_boot=25)
        second = au_pvalues(M, ["a", "b", "c"], seed=7, n_boot=25)
        assert {k: (v.au, v.bp) for k, v in first.items()} == {
            k: (v.au, v.bp) for k, v in second.items()
        }

    def test_a_different_seed_is_allowed_to_differ_but_stays_in_range(self):
        M = np.array([
            [1, 1, 1, 0, 0, 0],
            [1, 1, 0, 1, 0, 0],
            [0, 0, 0, 1, 1, 1],
        ], dtype=float)
        for branch in au_pvalues(M, ["a", "b", "c"], seed=11, n_boot=25).values():
            assert 0.0 <= branch.au <= 1.0
            assert 0.0 <= branch.bp_at_unit_scale <= 1.0

    def test_degenerate_shapes_return_empty(self):
        assert au_pvalues(np.zeros((1, 4)), ["a"], n_boot=5) == {}
        assert au_pvalues(np.zeros((3, 0)), ["a", "b", "c"], n_boot=5) == {}


class TestSelectSupportedClusters:
    def _tree(self, M, labels, *, seed=0, n_boot=40):
        D = weighted_jaccard_matrix(M, np.ones(M.shape[1]))
        return _linkage_from(D), au_pvalues(M, labels, seed=seed, n_boot=n_boot)

    def test_partitions_every_label_exactly_once(self):
        M = np.array([
            [1, 1, 1, 0, 0, 0, 0, 0],
            [1, 1, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 0],
            [0, 0, 0, 0, 1, 1, 0, 1],
        ], dtype=float)
        labels = ["a", "b", "c", "d"]
        Z, support = self._tree(M, labels)
        clusters, singletons, _reasons = select_supported_clusters(Z, labels, support)
        placed = [x for group in clusters for x in group] + singletons
        assert sorted(placed) == labels

    def test_never_returns_the_trivial_root(self):
        M = np.array([
            [1, 1, 1, 0],
            [1, 1, 0, 1],
            [1, 1, 1, 1],
        ], dtype=float)
        labels = ["a", "b", "c"]
        Z, support = self._tree(M, labels)
        clusters, _singletons, _reasons = select_supported_clusters(
            Z, labels, support, au_min=-1.0, min_bp=-1.0
        )
        assert all(len(group) < len(labels) for group in clusters)

    def test_unsupported_tree_degrades_to_named_singletons(self):
        M = np.array([
            [1, 1, 1, 0, 0, 0],
            [0, 0, 1, 1, 1, 0],
            [0, 0, 0, 1, 1, 1],
        ], dtype=float)
        labels = ["a", "b", "c"]
        Z, support = self._tree(M, labels)
        clusters, singletons, reasons = select_supported_clusters(
            Z, labels, support, au_min=1.1, min_bp=0.0
        )
        assert clusters == []
        assert singletons == labels
        assert any("no branch cleared the AU cut" in r for r in reasons)

    def test_records_the_no_multiplicity_correction_caveat(self):
        M = np.array([[1, 1, 0], [1, 0, 1]], dtype=float)
        labels = ["a", "b"]
        Z, support = self._tree(M, labels)
        _clusters, _singletons, reasons = select_supported_clusters(Z, labels, support)
        assert any("multiplicity correction" in r for r in reasons)

    def test_bp_floor_can_veto_a_high_au_branch(self):
        M = np.array([
            [1, 1, 1, 0, 0, 0, 0, 0],
            [1, 1, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 1, 1, 1, 1, 1],
        ], dtype=float)
        labels = ["a", "b", "c"]
        Z, support = self._tree(M, labels)
        permissive, _s, _r = select_supported_clusters(Z, labels, support, min_bp=0.0)
        vetoed, singletons, _r2 = select_supported_clusters(Z, labels, support, min_bp=1.01)
        assert permissive != [] and vetoed == []
        assert singletons == labels


class TestComembershipStability:
    def test_clean_separation_is_stable(self):
        M = np.array([
            [1, 1, 1, 0, 0, 0],
            [1, 1, 1, 0, 0, 0],
            [0, 0, 0, 1, 1, 1],
            [0, 0, 0, 1, 1, 1],
        ], dtype=float)
        assert comembership_stability(M, [0, 0, 1, 1], seed=0, n_boot=25) > 0.9

    def test_degenerate_inputs_return_one(self):
        M = np.array([[1.0, 0.0]])
        assert comembership_stability(M, [0], seed=0, n_boot=10) == 1.0
        assert comembership_stability(M, [0], seed=0, n_boot=0) == 1.0


class TestClusterArchetypes:
    def test_recovers_the_planted_families(self, two_family_corpus, family_of, staples):
        solution = cluster_archetypes(two_family_corpus, seed=0, n_boot=40)
        assert solution.staples == staples
        assert len(solution.definers) == 8

        home = {
            member.archetype: cluster.key
            for cluster in solution.clusters
            for member in cluster.members
        }
        for label, family in family_of.items():
            siblings = [o for o, f in family_of.items() if f == family and o != label]
            for sibling in siblings:
                assert home[label] == home[sibling], f"{label} and {sibling} split apart"
        # No cluster spans two planted families.
        for cluster in solution.clusters:
            assert len({family_of[m.archetype] for m in cluster.members}) == 1

    def test_is_deterministic(self, two_family_corpus):
        first = cluster_archetypes(two_family_corpus, seed=3, n_boot=25)
        second = cluster_archetypes(two_family_corpus, seed=3, n_boot=25)
        assert first == second

    def test_no_definers_degrades_with_a_named_reason(self, make_pool):
        solution = cluster_archetypes(make_pool("Brew", ("a", "b", "c"), n=4), n_boot=5)
        assert solution.clusters == ()
        assert solution.degraded is True
        assert any("no definer archetypes" in r for r in solution.reasons)
        assert all("no definer archetypes" in reason for _a, reason in solution.unassigned)

    def test_every_definer_stripped_empty_degrades_with_a_named_reason(self, make_pool):
        shared = tuple(f"c{i}" for i in range(10))
        decks = make_pool("A", shared, n=40) + make_pool("B", shared, n=40)
        solution = cluster_archetypes(decks, n_boot=5)
        assert solution.clusters == ()
        assert solution.degraded is True
        assert any("removed every definer's core" in r for r in solution.reasons)

    def test_long_tail_is_assigned_not_dropped(self, two_family_corpus, families):
        tail = [
            ArchetypeDeck(
                archetype="Tiny Combo Brew",
                key=("tail", i),
                cards=frozenset(families["combo"][:5] + ("Brainstorm",)),
            )
            for i in range(4)
        ]
        solution = cluster_archetypes(two_family_corpus + tail, seed=0, n_boot=25)
        placed = {
            member.archetype: (cluster, member)
            for cluster in solution.clusters
            for member in cluster.members
        }
        assert "Tiny Combo Brew" in placed
        cluster, member = placed["Tiny Combo Brew"]
        assert member.provenance == "assigned"
        assert "Show and Tell" in {m.archetype for m in cluster.members}

    def test_below_assignee_floor_is_unassigned_with_a_named_reason(self, two_family_corpus):
        tail = [
            ArchetypeDeck(archetype="Two Card Brew", key=("tail", i), cards=frozenset({"q", "z"}))
            for i in range(3)
        ]
        solution = cluster_archetypes(two_family_corpus + tail, seed=0, n_boot=25)
        reasons = dict(solution.unassigned)
        assert "Two Card Brew" in reasons
        assert "below assignee core floor" in reasons["Two Card Brew"]

    def test_an_archetype_sharing_nothing_is_unassigned_not_forced(self, two_family_corpus):
        tail = [
            ArchetypeDeck(
                archetype="Alien Brew",
                key=("tail", i),
                cards=frozenset(f"alien-{j}" for j in range(6)),
            )
            for i in range(4)
        ]
        solution = cluster_archetypes(two_family_corpus + tail, seed=0, n_boot=25)
        reasons = dict(solution.unassigned)
        assert "Alien Brew" in reasons
        assert "shares no stripped-core card" in reasons["Alien Brew"]

    def test_reports_stability_and_cophenetic_as_diagnostics(self, two_family_corpus):
        solution = cluster_archetypes(two_family_corpus, seed=0, n_boot=25)
        assert 0.0 <= solution.stability <= 1.0
        assert -1.0 <= solution.cophenetic <= 1.0
        assert any("co-membership stability" in r for r in solution.reasons)
        assert any("cophenetic correlation" in r for r in solution.reasons)
