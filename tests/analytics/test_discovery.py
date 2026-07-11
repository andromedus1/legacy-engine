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
    DeckVector,
    build_feature_matrix,
    reduce_dims,
)


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
