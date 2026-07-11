"""Tests for analytics/discovery.py — subarchetype discovery engine.

Units 1-2 (this story, ``-repr``): the DB-free flex-band feature matrix builder
(``build_feature_matrix``) and the injectable reducer (``reduce_dims``). Units 3-4 (clustering,
validation, naming, DB wrapper) land in the ``-cluster`` story's tests, appended to this file.

All Unit 1-2 tests are pure — hand-built ``DeckVector`` lists, no DB (objective-search-split).
"""

from __future__ import annotations

import numpy as np
import pytest

from legacy_engine.analytics.discovery import (
    Camp,
    DeckVector,
    build_feature_matrix,
    cluster_and_validate,
    discover_subarchetypes,
    reduce_dims,
)
from legacy_engine.confidence import tier_for_sample


# ---------------------------------------------------------------------------
# Unit 1 — build_feature_matrix
# ---------------------------------------------------------------------------

class TestBuildFeatureMatrix:
    def _decks(self) -> list[DeckVector]:
        """20 decks: 1 ubiquitous core card, 1 rare tail card, 2 flex-band cards.

        - "Core Land": in every deck (100% inclusion) -> ubiquitous, dropped.
        - "Rare Tech": in exactly 1 deck (5% inclusion) -> rare tail, dropped.
        - "Flex A": in 10 of 20 decks (50% inclusion) -> flex band, kept.
        - "Flex B": in 12 of 20 decks (60% inclusion) -> flex band, kept.
        """
        decks = []
        for i in range(20):
            counts = {"Core Land": 4}
            if i < 10:
                counts["Flex A"] = 3
            if i < 12:
                counts["Flex B"] = 2
            if i == 0:
                counts["Rare Tech"] = 1
            decks.append(DeckVector(key=("t1", i), counts=counts))
        return decks

    def test_flex_band_columns_only(self):
        fm = build_feature_matrix(self._decks())
        assert fm.cards == ["Flex A", "Flex B"]

    def test_rows_in_sorted_key_order(self):
        decks = self._decks()
        # Shuffle input order — build_feature_matrix must sort internally.
        shuffled = list(reversed(decks))
        fm = build_feature_matrix(shuffled)
        assert fm.keys == sorted(d.key for d in decks)

    def test_l2_row_norms_approx_one(self):
        fm = build_feature_matrix(self._decks())
        norms = np.linalg.norm(fm.X, axis=1)
        # Rows with at least one non-zero flex-band cell L2-normalize to 1.0.
        nonzero_rows = np.any(fm.X != 0, axis=1)
        assert np.allclose(norms[nonzero_rows], 1.0)

    def test_matrix_shape(self):
        fm = build_feature_matrix(self._decks())
        assert fm.X.shape == (20, 2)

    def test_default_thresholds_drop_ubiquitous_and_rare(self):
        fm = build_feature_matrix(self._decks())
        assert "Core Land" not in fm.cards
        assert "Rare Tech" not in fm.cards

    def test_fewer_than_two_flex_cards_degrades_to_empty(self):
        """A parent with <2 cards in the flex band returns an empty FeatureMatrix."""
        decks = [
            DeckVector(key=("t1", i), counts={"Core Land": 4})
            for i in range(20)
        ]
        fm = build_feature_matrix(decks)
        assert fm.cards == []
        assert fm.keys == []
        assert fm.X.shape == (0, 0)

    def test_empty_deck_list(self):
        fm = build_feature_matrix([])
        assert fm.keys == []
        assert fm.cards == []
        assert fm.X.shape == (0, 0)

    def test_custom_flex_thresholds(self):
        """Narrowing flex_hi excludes a card at 60% inclusion, keeping the other two."""
        decks = []
        for i in range(20):
            counts = {"Core Land": 4}
            if i < 10:
                counts["Flex A"] = 3     # 50% inclusion
            if i < 12:
                counts["Flex B"] = 2     # 60% inclusion -- excluded by flex_hi=0.55
            if i < 9:
                counts["Flex C"] = 1     # 45% inclusion
            decks.append(DeckVector(key=("t1", i), counts=counts))
        fm = build_feature_matrix(decks, flex_lo=0.10, flex_hi=0.55)
        assert fm.cards == ["Flex A", "Flex C"]

    def test_single_deck_pool_all_cards_ubiquitous(self):
        """A pool of 1 deck: every present card has inclusion 1.0 -> ubiquitous, empty result."""
        decks = [DeckVector(key=("t1", 0), counts={"A": 4, "B": 2})]
        fm = build_feature_matrix(decks)
        assert fm.cards == []


# ---------------------------------------------------------------------------
# Unit 2 — reduce_dims
# ---------------------------------------------------------------------------

class TestReduceDims:
    def _wide_matrix(self, n_rows=30, n_features=20, seed=0) -> np.ndarray:
        rng = np.random.default_rng(seed)
        return rng.random((n_rows, n_features))

    def test_svd_shape(self):
        X = self._wide_matrix(n_rows=30, n_features=20)
        Xred = reduce_dims(X, method="svd", n_components=10, seed=0)
        assert Xred.shape == (30, 10)

    def test_svd_reduces_to_n_components_when_below_n_features(self):
        """n_features (30) > n_components (25) -> SVD path runs, output has 25 dims.

        (The `min(n_components, n_features-1)` cap in the spec is a defensive no-op here: the
        pass-through branch already guarantees n_features > n_components whenever this branch
        runs, so n_features-1 >= n_components always holds and the min collapses to
        n_components.)
        """
        X = self._wide_matrix(n_rows=30, n_features=30)
        Xred = reduce_dims(X, method="svd", n_components=25, seed=0)
        assert Xred.shape == (30, 25)

    def test_svd_deterministic_across_runs(self):
        X = self._wide_matrix(n_rows=30, n_features=20)
        a = reduce_dims(X, method="svd", n_components=10, seed=0)
        b = reduce_dims(X, method="svd", n_components=10, seed=0)
        assert np.allclose(a, b)

    def test_pass_through_when_n_features_at_or_below_n_components(self):
        X = self._wide_matrix(n_rows=10, n_features=4)
        Xred = reduce_dims(X, method="svd", n_components=10, seed=0)
        assert Xred.shape == (10, 4)
        assert np.array_equal(Xred, X)

    def test_pass_through_exact_equal(self):
        X = self._wide_matrix(n_rows=10, n_features=10)
        Xred = reduce_dims(X, method="svd", n_components=10, seed=0)
        assert np.array_equal(Xred, X)

    def test_unknown_method_raises(self):
        X = self._wide_matrix(n_rows=10, n_features=20)
        with pytest.raises(ValueError, match="unknown method"):
            reduce_dims(X, method="bogus", n_components=10, seed=0)

    def test_umap_smoke(self):
        """UMAP path is a smoke test only — skipped if umap-learn isn't installed."""
        pytest.importorskip("umap")
        X = self._wide_matrix(n_rows=40, n_features=20)
        Xred = reduce_dims(X, method="umap", n_components=5, seed=0)
        assert Xred.shape == (40, 5)

    def test_umap_lazy_import_not_required_for_svd(self, monkeypatch):
        """The svd path must not import umap at all (confines the optional dep)."""
        import builtins

        real_import = builtins.__import__

        def _blocking_import(name, *args, **kwargs):
            if name == "umap":
                raise AssertionError("svd path must not import umap")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _blocking_import)
        X = self._wide_matrix(n_rows=30, n_features=20)
        reduce_dims(X, method="svd", n_components=10, seed=0)


# ---------------------------------------------------------------------------
# Unit 3 — cluster_and_validate (the trickiest unit) + _gate_b_domain
#
# Four acceptance scenarios (per the parent feature's Implementation Units):
#   (a) two well-separated hand-built camps (n>=30 each) -> passed=True, 2 camps, correct names.
#   (b) one homogeneous blob -> 1 cluster, passed=False, reason "single cluster".
#   (c) a 300/12 split -> passed=False, reason "camp below evolving floor".
#   (d) deterministic across runs.
#
# Scenario (c) is tested directly against `_gate_b_domain` rather than through the full
# cluster_and_validate/HDBSCAN pipeline: HDBSCAN's own `min_cluster_size` floor
# (`max(30, round(0.10*n))`, see Unit 3 notes) makes it structurally impossible for HDBSCAN to
# ever *form* a non-noise cluster smaller than 30 members — so the only way to exercise "a
# formed camp that is below the evolving floor" is to hand-build Camp objects and drive the
# domain gate directly. This mirrors the objective-search-split idiom of testing an internal
# pure piece (like `_greedy_tune`) in isolation.
# ---------------------------------------------------------------------------

def _two_camp_decks(n_a: int = 35, n_b: int = 35) -> list[DeckVector]:
    """Two well-separated camps sharing a ubiquitous core, split on two flex-card pairs.

    Mirrors the brief's worked Doomsday example (bimodal signature cards, not just presence):
    camp A runs "Card A1"/"Card A2" at ~4/~3 copies and never runs the B cards, camp B is the
    mirror image. Small jitter (±1 copy) keeps rows non-identical without touching separation.
    """
    decks: list[DeckVector] = []
    idx = 0
    for i in range(n_a):
        wobble = i % 2  # deterministic, no RNG needed for a fixture this clean
        decks.append(DeckVector(
            key=("t1", idx),
            counts={"Core Land": 4, "Card A1": 4 - wobble, "Card A2": 3 + wobble},
        ))
        idx += 1
    for i in range(n_b):
        wobble = i % 2
        decks.append(DeckVector(
            key=("t1", idx),
            counts={"Core Land": 4, "Card B1": 4 - wobble, "Card B2": 3 + wobble},
        ))
        idx += 1
    return decks


def _blob_decks(n: int = 70) -> list[DeckVector]:
    """A single homogeneous parent — every deck plays the identical flex-band composition.

    ``flex_hi=1.0`` is required at matrix-build time since these two cards are ubiquitous
    (100% inclusion) by construction — there is deliberately no split signal anywhere.
    """
    return [
        DeckVector(key=("t1", i), counts={"Core Land": 4, "Flex A": 3, "Flex B": 2})
        for i in range(n)
    ]


class TestClusterAndValidateCleanSplit:
    """Scenario (a): two well-separated camps -> passed=True, 2 camps, correct names."""

    def test_passes_both_gates(self):
        decks = _two_camp_decks()
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=30)
        assert split.passed is True
        assert len(split.camps) == 2
        assert split.n_noise == 0

    def test_camp_names_are_card_and_non_card(self):
        decks = _two_camp_decks()
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=30)
        names = sorted(c.name for c in split.camps)
        assert len(names) == 2
        card_name = next(n for n in names if not n.startswith("non-"))
        assert f"non-{card_name}" in names

    def test_camp_sizes_and_tiers(self):
        decks = _two_camp_decks()
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=30)
        sizes = sorted(c.n for c in split.camps)
        assert sizes == [35, 35]
        assert all(c.tier == "evolving" for c in split.camps)

    def test_stability_high_and_gate_reasons_present(self):
        decks = _two_camp_decks()
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=30)
        assert split.stability >= 0.90
        assert any("gate A stability" in r for r in split.reasons)
        assert any("gate B" in r and "PASS" in r for r in split.reasons)

    def test_double_dipping_guard_note_always_present(self):
        """The reasons list always documents the validation guard, pass or fail."""
        decks = _two_camp_decks()
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=30)
        assert any("double-dipping" in r for r in split.reasons)


class TestClusterAndValidateBlob:
    """Scenario (b): one homogeneous blob -> FAIL with an honest no-structure reason.

    With ``allow_single_cluster`` off (the sklearn default — the root-cluster bias it
    introduces swallowed a validated real-world split), a homogeneous blob resolves to
    either one dense cluster or all-noise depending on density; both are k<2 outcomes
    and both must FAIL with a named "no separable structure" family reason.
    """

    def test_homogeneous_blob_fails_honestly(self):
        decks = _blob_decks()
        fm = build_feature_matrix(decks, flex_hi=1.0)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20)
        assert split.passed is False
        assert len(split.camps) <= 1  # k<2: one dense cluster or none (all noise)
        assert any(
            ("single cluster" in r) or ("no separable structure" in r) for r in split.reasons
        )

    def test_no_flex_band_also_fails_honestly(self):
        """A parent with <2 flex cards degrades before clustering is even attempted."""
        decks = [
            DeckVector(key=("t1", i), counts={"Core Land": 4})
            for i in range(40)
        ]
        fm = build_feature_matrix(decks)  # default thresholds -> Core Land is ubiquitous, dropped
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20)
        assert split.passed is False
        assert split.camps == []
        assert any("no separable structure" in r for r in split.reasons)


class TestGateBDomainDirect:
    """Scenario (c): a 300/12 split -> passed=False, reason 'camp below evolving floor'.

    Tested directly against `_gate_b_domain` — see the module docstring above for why.
    """

    def _camp(self, name: str, n: int, sig: list[tuple[str, float]]) -> Camp:
        return Camp(name=name, member_keys=[], signature_cards=sig, n=n, tier=tier_for_sample(n))

    def test_below_floor_camp_fails_with_named_reason(self):
        from legacy_engine.analytics.discovery import _gate_b_domain

        big = self._camp("Big", 300, [("Tamiyo, Inquisitive Student", 2.72), ("Wasteland", 2.15)])
        small = self._camp("Small", 12, [("Tamiyo, Inquisitive Student", -2.72), ("Wasteland", -2.15)])

        ok, reasons = _gate_b_domain([big, small])
        assert ok is False
        assert any("below evolving floor" in r and "Small" in r for r in reasons)

    def test_both_camps_above_floor_with_divergence_passes(self):
        from legacy_engine.analytics.discovery import _gate_b_domain

        a = self._camp("A", 50, [("Card X", 1.0), ("Card Y", 0.9)])
        b = self._camp("B", 40, [("Card X", -1.0), ("Card Y", -0.9)])
        ok, reasons = _gate_b_domain([a, b])
        assert ok is True
        assert all("FAIL" not in r for r in reasons)

    def test_insufficient_signature_divergence_fails(self):
        """Both camps clear the tier floor but neither shows >=2 cards at |delta|>=0.75."""
        from legacy_engine.analytics.discovery import _gate_b_domain

        a = self._camp("A", 50, [("Card X", 0.3)])
        b = self._camp("B", 40, [("Card X", -0.3)])
        ok, reasons = _gate_b_domain([a, b])
        assert ok is False
        assert any("flex card(s)" in r for r in reasons)

    def test_fewer_than_two_camps_fails(self):
        from legacy_engine.analytics.discovery import _gate_b_domain

        ok, reasons = _gate_b_domain([self._camp("Only", 50, [("X", 1.0)])])
        assert ok is False
        assert any("fewer than 2 camps" in r for r in reasons)


class TestClusterAndValidateDeterminism:
    """Scenario (d): deterministic across runs given the same seed."""

    def test_repeated_calls_identical(self):
        decks = _two_camp_decks()
        fm = build_feature_matrix(decks)
        split1 = cluster_and_validate(fm, decks, seed=0, n_boot=20)
        split2 = cluster_and_validate(fm, decks, seed=0, n_boot=20)

        assert split1.passed == split2.passed
        assert split1.stability == split2.stability
        assert split1.n_noise == split2.n_noise
        assert [c.name for c in split1.camps] == [c.name for c in split2.camps]
        assert [c.n for c in split1.camps] == [c.n for c in split2.camps]

    def test_different_seed_still_finds_the_same_structure(self):
        """Determinism is about reproducibility, not brittleness to seed choice — a genuinely
        well-separated split should pass under any seed, even if bootstrap details differ."""
        decks = _two_camp_decks()
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=7, n_boot=20)
        assert split.passed is True
        assert len(split.camps) == 2


# ---------------------------------------------------------------------------
# Unit 4 — discover_subarchetypes (DB wrapper, hermetic in-memory DuckDB)
# ---------------------------------------------------------------------------

class TestDiscoverSubarchetypesDB:
    """Hermetic: in-memory DuckDB seeded with a two-camp Doomsday-like pool."""

    def _seeded_con(self):
        from legacy_engine.ingestion import store

        con = store.connect(":memory:")
        store.init_schema(con)
        con.execute(
            "INSERT INTO tournaments VALUES ('t1', 'T', '2026-01-01', NULL, 'Legacy', 'src', 'online')"
        )

        deck_rows = []
        card_rows = []
        idx = 0
        for _ in range(35):
            deck_rows.append(("t1", idx, "p", "W", "Doomsday", None))
            card_rows.append(("t1", idx, "main", "Core Land", 4))
            card_rows.append(("t1", idx, "main", "Card A1", 4))
            card_rows.append(("t1", idx, "main", "Card A2", 3))
            idx += 1
        for _ in range(35):
            deck_rows.append(("t1", idx, "p", "W", "Doomsday", None))
            card_rows.append(("t1", idx, "main", "Core Land", 4))
            card_rows.append(("t1", idx, "main", "Card B1", 4))
            card_rows.append(("t1", idx, "main", "Card B2", 3))
            idx += 1
        # A single decoy deck of a DIFFERENT archetype must never leak into the pool.
        deck_rows.append(("t1", idx, "other", "L", "Lands", None))
        card_rows.append(("t1", idx, "main", "Dark Depths", 4))

        con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", deck_rows)
        con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", card_rows)
        return con

    def test_discover_subarchetypes_finds_the_split(self):
        con = self._seeded_con()
        try:
            split = discover_subarchetypes(con, "Doomsday", seed=0, n_boot=20)
        finally:
            con.close()

        assert split.parent == "Doomsday"
        assert split.passed is True
        assert len(split.camps) == 2
        assert sorted(c.n for c in split.camps) == [35, 35]

    def test_other_archetype_pool_not_included(self):
        """The query only pulls the requested archetype's decks — verified indirectly: the
        decoy 'Lands' deck's 'Dark Depths' never appears as a flex-band card for Doomsday."""
        con = self._seeded_con()
        try:
            split = discover_subarchetypes(con, "Doomsday", seed=0, n_boot=20)
        finally:
            con.close()
        all_sig_cards = {name for camp in split.camps for name, _ in camp.signature_cards}
        assert "Dark Depths" not in all_sig_cards

    def test_since_filter_narrows_pool(self):
        """A `since` in the future excludes every deck -> empty pool -> honest empty result."""
        con = self._seeded_con()
        try:
            split = discover_subarchetypes(con, "Doomsday", since="2099-01-01", seed=0, n_boot=5)
        finally:
            con.close()
        assert split.passed is False
        assert split.camps == []

    def test_unknown_archetype_returns_empty_honest_result(self):
        con = self._seeded_con()
        try:
            split = discover_subarchetypes(con, "Nonexistent Archetype", seed=0, n_boot=5)
        finally:
            con.close()
        assert split.parent == "Nonexistent Archetype"
        assert split.passed is False
        assert split.camps == []
