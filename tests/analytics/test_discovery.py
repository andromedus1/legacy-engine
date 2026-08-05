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
    camp_centroid,
    cluster_and_validate,
    discover_subarchetypes,
    nearest_camp,
    project_flex_vector,
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
        """UMAP path is a smoke test only — skipped if umap-learn isn't usable.

        Skips on any ImportError, not just a missing ``umap`` itself: the optional
        extra pulls in numba, which caps the NumPy/Python versions it supports, so a
        current interpreter can have umap installed but unimportable. That is an
        optional-dependency gap, not a failure of this repo's code.
        """
        try:
            import umap  # noqa: F401
        except ImportError as exc:  # pragma: no cover — environment-dependent
            pytest.skip(f"umap-learn not usable in this environment: {exc}")
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


class TestCampNameCollision:
    """Two distinct camps sharing a top signature card must get DISTINCT names —
    a collision would merge their decks.variant labels on apply (bug found in the
    2026-07-11 top-meta sweep: Lands produced two camps both named 'Sphere of
    Resistance')."""

    def test_shared_top_signature_disambiguates(self):
        # three camps, two of which share the same top card but differ on the second
        def deck(i, cards):
            return DeckVector(key=("t", i), counts=cards)
        camp_a = [deck(i, {"Sphere": 4, "Port": 4, "Shared": 2}) for i in range(40)]
        camp_b = [deck(100 + i, {"Sphere": 4, "Tomb": 4, "Shared": 2}) for i in range(40)]
        camp_c = [deck(200 + i, {"Once": 4, "Rumble": 4, "Shared": 2}) for i in range(40)]
        decks = camp_a + camp_b + camp_c
        fm = build_feature_matrix(decks, flex_lo=0.05, flex_hi=1.1)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=10)
        names = [c.name for c in split.camps]
        assert len(names) == len(set(names)), f"camp name collision: {names}"


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
# Gate C — temporal mixing (epic-stable-era-windows-discovery-gate Unit 1)
#
# Two calibration fixtures pin _TEMPORAL_GAP_DAYS = 120 (see the constant's docstring):
#   - a two-generation split (old camp median ~2025-06, new camp median ~2026-05) FLAGS.
#   - a contemporaneous split (both camps dated within the same ~30-day window) does NOT flag.
# ---------------------------------------------------------------------------

def _dated_two_camp_decks(
    dates_a: list[str], dates_b: list[str],
) -> list[DeckVector]:
    """``_two_camp_decks``' well-separated fixture, but every deck also carries a date.

    ``dates_a``/``dates_b`` are cycled over each camp's decks (35 each) so any list length
    works; a single-date list stamps every deck in that camp with the same date.
    """
    decks: list[DeckVector] = []
    idx = 0
    for i in range(35):
        wobble = i % 2
        decks.append(DeckVector(
            key=("t1", idx),
            counts={"Core Land": 4, "Card A1": 4 - wobble, "Card A2": 3 + wobble},
            date=dates_a[i % len(dates_a)],
        ))
        idx += 1
    for i in range(35):
        wobble = i % 2
        decks.append(DeckVector(
            key=("t1", idx),
            counts={"Core Land": 4, "Card B1": 4 - wobble, "Card B2": 3 + wobble},
            date=dates_b[i % len(dates_b)],
        ))
        idx += 1
    return decks


class TestClusterAndValidateGateC:
    def test_two_generation_split_flags_temporal_mixing(self):
        """Old camp median 2025-06, new camp median 2026-05 (~334d apart) -> FLAG."""
        decks = _dated_two_camp_decks(
            dates_a=["2025-06-01"], dates_b=["2026-05-01"],
        )
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20)

        assert split.passed is True  # Gate C never fails a statistically-valid split
        assert split.temporal_mixing is True
        assert split.temporal_note == "camps may be list generations"
        assert any("gate C temporal" in r and "FLAG" in r for r in split.reasons)
        for camp in split.camps:
            assert camp.median_date in {"2025-06-01", "2026-05-01"}

    def test_contemporaneous_split_does_not_flag(self):
        """Both camps dated within the same ~30-day window -> no flag."""
        decks = _dated_two_camp_decks(
            dates_a=["2026-06-01", "2026-06-10"], dates_b=["2026-06-05", "2026-06-15"],
        )
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20)

        assert split.passed is True
        assert split.temporal_mixing is False
        assert split.temporal_note is None
        assert any(
            "gate C temporal" in r and "no temporal mixing" in r for r in split.reasons
        )

    def test_undated_decks_report_insufficient_data_honestly(self):
        """No dates at all -> Gate C can't compare, and says so rather than fabricating a gap."""
        decks = _two_camp_decks()  # DeckVector.date defaults to None
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20)

        assert split.temporal_mixing is False
        assert split.temporal_note is None
        assert all(c.median_date is None for c in split.camps)
        assert any(
            "gate C temporal" in r and "insufficient dated decks" in r for r in split.reasons
        )

    def test_pct_current_none_without_current_since(self):
        decks = _dated_two_camp_decks(dates_a=["2026-06-01"], dates_b=["2026-06-05"])
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20)
        assert all(c.pct_current is None for c in split.camps)

    def test_pct_current_computed_against_current_since(self):
        """One camp entirely before current_since, the other entirely on/after it."""
        decks = _dated_two_camp_decks(dates_a=["2026-01-01"], dates_b=["2026-06-10"])
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20, current_since="2026-06-01")

        pct_by_camp = {c.median_date: c.pct_current for c in split.camps}
        assert pct_by_camp["2026-01-01"] == pytest.approx(0.0)
        assert pct_by_camp["2026-06-10"] == pytest.approx(1.0)

    def test_timestamp_format_dates_do_not_crash(self):
        """Real-corpus MTGO dates carry a time component ("2026-06-10T10:00:00").

        Regression: date.fromisoformat rejects the time part, so a camp containing such a
        deck used to crash the whole discovery run (Cephalid Breakfast never swept). The
        date-portion normalization must keep median_date/pct_current working.
        """
        decks = _dated_two_camp_decks(
            dates_a=["2026-01-01T10:00:00"], dates_b=["2026-06-10T18:30:00"],
        )
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20, current_since="2026-06-01")

        pct_by_camp = {c.median_date: c.pct_current for c in split.camps}
        assert pct_by_camp["2026-01-01"] == pytest.approx(0.0)   # median normalized to date only
        assert pct_by_camp["2026-06-10"] == pytest.approx(1.0)

    def test_existing_hand_built_camp_and_split_constructors_still_work(self):
        """Additive-defaults contract: old call shapes (no temporal kwargs) stay green."""
        camp = Camp(name="X", member_keys=[], signature_cards=[], n=40, tier="evolving")
        assert camp.median_date is None
        assert camp.pct_current is None
        assert camp.centroid is None


# ---------------------------------------------------------------------------
# Frozen flex-band projection + nearest-camp assignment
# ---------------------------------------------------------------------------

class TestProjectFlexVector:
    def test_overlapping_deck_projects_to_unit_norm(self):
        vec = project_flex_vector({"A": 4, "B": 3, "Unknown": 2}, ["A", "B", "C"])
        assert vec.shape == (3,)
        assert vec[2] == 0.0                                   # absent card -> 0, never dropped
        assert np.linalg.norm(vec) == pytest.approx(1.0)
        # Direction preserved: A outweighs B in the same 4:3 ratio as the raw counts.
        assert vec[0] / vec[1] == pytest.approx(4 / 3)

    def test_no_overlap_gives_all_zero_vector(self):
        vec = project_flex_vector({"Z": 4}, ["A", "B"])
        assert not vec.any()
        assert not np.isnan(vec).any()

    def test_empty_counts_does_not_raise_or_nan(self):
        vec = project_flex_vector({}, ["A", "B"])
        assert not vec.any()
        assert not np.isnan(vec).any()

    def test_empty_flex_cards_gives_empty_vector(self):
        vec = project_flex_vector({"A": 4}, [])
        assert vec.shape == (0,)

    def test_copy_counts_matter_not_just_presence(self):
        """Raw counts, not a presence indicator — a 4-of and a 1-of project differently."""
        four_of = project_flex_vector({"A": 4, "B": 1}, ["A", "B"])
        one_of = project_flex_vector({"A": 1, "B": 4}, ["A", "B"])
        assert float(np.dot(four_of, one_of)) < 1.0


class TestCampCentroid:
    def test_single_member_centroid_equals_that_members_vector(self):
        counts = {"A": 4, "B": 2}
        centroid = camp_centroid([counts], ["A", "B", "C"])
        assert centroid == pytest.approx(list(project_flex_vector(counts, ["A", "B", "C"])))

    def test_multi_member_centroid_is_renormalized_mean(self):
        cards = ["A", "B"]
        members = [{"A": 4}, {"B": 4}]
        centroid = camp_centroid(members, cards)
        assert np.linalg.norm(centroid) == pytest.approx(1.0)
        # Mean of the two orthogonal unit vectors, renormalized -> the 45-degree bisector.
        assert centroid == pytest.approx([2 ** -0.5, 2 ** -0.5])

    def test_empty_member_list_gives_zero_vector(self):
        centroid = camp_centroid([], ["A", "B"])
        assert centroid == [0.0, 0.0]

    def test_members_sharing_no_flex_card_give_zero_vector(self):
        assert camp_centroid([{"Z": 4}, {"Y": 2}], ["A", "B"]) == [0.0, 0.0]

    def test_empty_flex_cards_gives_empty_centroid(self):
        assert camp_centroid([{"A": 4}], []) == []


class TestNearestCamp:
    _CARDS = ["A1", "A2", "B1", "B2"]

    def _centroids(self) -> dict[str, list[float]]:
        return {
            "camp-A": camp_centroid([{"A1": 4, "A2": 3}], self._CARDS),
            "camp-B": camp_centroid([{"B1": 4, "B2": 3}], self._CARDS),
        }

    def test_picks_the_closer_camp_and_reports_runner_up(self):
        result = nearest_camp({"A1": 4, "A2": 3}, self._CARDS, self._centroids())
        assert result.camp == "camp-A"
        assert result.runner_up == "camp-B"
        assert result.best_similarity == pytest.approx(1.0)
        assert result.reason

    def test_picks_the_other_camp_for_the_mirror_deck(self):
        result = nearest_camp({"B1": 4, "B2": 3}, self._CARDS, self._centroids())
        assert result.camp == "camp-B"
        assert result.runner_up == "camp-A"

    def test_below_floor_declines_with_a_named_reason(self):
        # Orthogonal-ish deck: one shared card at 1 copy against a 4/3 centroid.
        result = nearest_camp(
            {"A1": 1, "B1": 1}, self._CARDS, self._centroids(), min_similarity=0.9,
        )
        assert result.camp is None
        assert "min_similarity" in result.reason
        assert result.best_similarity < 0.9

    def test_declines_when_deck_shares_no_flex_card(self):
        result = nearest_camp({"Unrelated": 4}, self._CARDS, self._centroids())
        assert result.camp is None
        assert result.best_similarity == 0.0
        assert "shares no card" in result.reason

    def test_empty_flex_cards_declines_honestly(self):
        result = nearest_camp({"A1": 4}, [], {"camp-A": [1.0]})
        assert result.camp is None
        assert "no frozen flex vocabulary" in result.reason

    def test_empty_centroids_declines_honestly(self):
        result = nearest_camp({"A1": 4}, self._CARDS, {})
        assert result.camp is None
        assert "no camp centroid" in result.reason

    def test_centroid_length_mismatch_fails_fast(self):
        """Corrupt persisted state, not thin data — never silently score a truncated centroid."""
        with pytest.raises(ValueError, match="dimension"):
            nearest_camp({"A1": 4}, self._CARDS, {"camp-A": [1.0, 0.0]})

    def test_ties_resolve_deterministically_by_name(self):
        centroids = {
            "zebra": camp_centroid([{"A1": 4}], self._CARDS),
            "alpha": camp_centroid([{"A1": 4}], self._CARDS),
        }
        assert nearest_camp({"A1": 4}, self._CARDS, centroids).camp == "alpha"

    def test_single_camp_has_no_runner_up(self):
        centroids = {"only": camp_centroid([{"A1": 4}], self._CARDS)}
        assert nearest_camp({"A1": 4}, self._CARDS, centroids).runner_up is None


class TestReconstructionAccuracy:
    """The load-bearing validation of the simplified representation.

    Nearest-centroid assignment runs on RAW L2-normalized flex-band counts — deliberately
    dropping the TF-IDF reweighting and SVD reduction HDBSCAN actually clustered on, neither of
    which is persisted. The floor that makes that trade-off defensible: projecting a split's OWN
    member decks back through `nearest_camp` must recover their real camp labels. Below 90% the
    representation isn't trustworthy enough to assign decks HDBSCAN never saw, and the fitted
    `idf_` vector would have to be persisted alongside `flex_cards` instead.

    Measured on the real corpus at implementation time (30 staged splits, 21,130 member decks):
    98.6% overall, worst split 92.1%. This fixture is the hermetic regression floor.
    """

    def _agreement(self, decks: list[DeckVector], **kwargs) -> float:
        fm = build_feature_matrix(decks, **kwargs)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20)
        assert len(split.camps) >= 2, "fixture must produce a real multi-camp split"
        assert split.flex_cards == fm.cards

        counts_by_key = {d.key: d.counts for d in decks}
        centroids = {c.name: c.centroid for c in split.camps}
        recovered = 0
        total = 0
        for camp in split.camps:
            for key in camp.member_keys:
                total += 1
                result = nearest_camp(counts_by_key[key], split.flex_cards, centroids)
                recovered += result.camp == camp.name
        return recovered / total

    def test_two_camp_split_recovers_its_own_members(self):
        assert self._agreement(_two_camp_decks()) >= 0.90

    def test_three_camp_split_with_shared_staples_recovers_its_own_members(self):
        """The harder case flagged in Risks: camps sharing staples make raw-count cosine less
        discriminative than TF-IDF+SVD would be."""
        def deck(i, cards):
            return DeckVector(key=("t", i), counts=cards)
        camp_a = [deck(i, {"Sphere": 4, "Port": 4, "Shared": 2}) for i in range(40)]
        camp_b = [deck(100 + i, {"Sphere": 4, "Tomb": 4, "Shared": 2}) for i in range(40)]
        camp_c = [deck(200 + i, {"Once": 4, "Rumble": 4, "Shared": 2}) for i in range(40)]
        agreement = self._agreement(camp_a + camp_b + camp_c, flex_lo=0.05, flex_hi=1.1)
        assert agreement >= 0.90


class TestClusterAndValidateCentroids:
    def test_passing_split_stamps_centroids_and_flex_cards(self):
        decks = _two_camp_decks()
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20)

        assert split.flex_cards == fm.cards
        assert len(fm.cards) >= 2
        for camp in split.camps:
            assert camp.centroid is not None
            assert len(camp.centroid) == len(fm.cards)
            assert np.linalg.norm(camp.centroid) == pytest.approx(1.0)

    def test_centroids_separate_the_two_camps(self):
        decks = _two_camp_decks()
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=20)
        a, b = (c.centroid for c in split.camps)
        assert float(np.dot(a, b)) < 0.5

    def test_no_flex_band_stamps_nothing_fabricated(self):
        """The degenerate early return: no camps, no centroids, empty flex vocabulary."""
        decks = [DeckVector(key=("t1", i), counts={"Core Land": 4}) for i in range(40)]
        fm = build_feature_matrix(decks)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=5)
        assert split.camps == []
        assert split.flex_cards == []

    def test_blob_split_stamps_flex_cards_without_a_validated_camp(self):
        """A FAILing split still records whatever the matrix really built — never fabricated,
        never suppressed."""
        decks = _blob_decks()
        fm = build_feature_matrix(decks, flex_hi=1.0)
        split = cluster_and_validate(fm, decks, seed=0, n_boot=10)
        assert split.passed is False
        assert split.flex_cards == fm.cards
        for camp in split.camps:   # k<2, so at most a single-cluster camp
            assert len(camp.centroid) == len(fm.cards)


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

    def test_tournament_date_rides_the_pool_query_into_gate_c(self):
        """t.date joins onto every deck row -> DeckVector.date -> Gate C median/flag."""
        from legacy_engine.ingestion import store

        con = store.connect(":memory:")
        store.init_schema(con)
        con.execute(
            "INSERT INTO tournaments VALUES ('old', 'Old', '2025-06-01', NULL, "
            "'Legacy', 'src', 'online')"
        )
        con.execute(
            "INSERT INTO tournaments VALUES ('new', 'New', '2026-05-01', NULL, "
            "'Legacy', 'src', 'online')"
        )
        deck_rows = []
        card_rows = []
        idx = 0
        for _ in range(35):
            deck_rows.append(("old", idx, "p", "W", "Doomsday", None))
            card_rows += [
                ("old", idx, "main", "Core Land", 4),
                ("old", idx, "main", "Card A1", 4),
                ("old", idx, "main", "Card A2", 3),
            ]
            idx += 1
        idx = 0
        for _ in range(35):
            deck_rows.append(("new", idx, "p", "W", "Doomsday", None))
            card_rows += [
                ("new", idx, "main", "Core Land", 4),
                ("new", idx, "main", "Card B1", 4),
                ("new", idx, "main", "Card B2", 3),
            ]
            idx += 1
        con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", deck_rows)
        con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", card_rows)

        try:
            split = discover_subarchetypes(con, "Doomsday", seed=0, n_boot=20)
        finally:
            con.close()

        assert split.passed is True
        assert split.temporal_mixing is True
        assert split.temporal_note == "camps may be list generations"
        assert {c.median_date for c in split.camps} == {"2025-06-01", "2026-05-01"}
