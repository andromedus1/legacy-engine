"""Field distribution model tests — Units 1–5 of epic-advisory-field-model.

House style: module-level raw dicts → ``parse_cache_item`` → ``store.load_tournament``
into ``:memory:``; labels pinned via direct SQL UPDATE; ``TestX`` classes; deterministic.
"""

from __future__ import annotations

import pytest

from legacy_engine.advisory import (
    FieldDistribution,
    build_custom_field,
    build_global_field,
)
from legacy_engine.advisory.field import _normalize_shares
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item

# ---------------------------------------------------------------------------
# Shared raw tournament fixtures
# ---------------------------------------------------------------------------

_CHALLENGE_ONLINE = {
    "Tournament": {
        "Name": "Advisory Field Test Challenge",
        "Date": "2026-05-30",
        "Uri": "https://www.mtgo.com/decklist/advisory-field-test-2026-05-30",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "alice",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "bob",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
        {
            "Player": "carol",
            "Result": "3rd Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
        {
            "Player": "dave",
            "Result": "4th Place",
            "Mainboard": [{"Count": 4, "CardName": "Ponder"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [
        {"Player1": "alice", "Player2": "bob", "Result": "2-1"},
        {"Player1": "carol", "Player2": "dave", "Result": "2-0"},
    ],
    "Standings": [
        {"Rank": 1, "Player": "alice", "Points": 18},
        {"Rank": 2, "Player": "bob", "Points": 15},
        {"Rank": 3, "Player": "carol", "Points": 9},
        {"Rank": 4, "Player": "dave", "Points": 6},
    ],
}

_PAPER_CHALLENGE = {
    "Tournament": {
        "Name": "Advisory Field Test Paper",
        "Date": "2026-05-29",
        "Uri": "https://melee.gg/Tournament/View/99999",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "eve",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Wasteland"}],
            "Sideboard": [],
        },
        {
            "Player": "frank",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Show and Tell"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [{"Player1": "eve", "Player2": "frank", "Result": "2-0"}],
    "Standings": [
        {"Rank": 1, "Player": "eve", "Points": 9},
        {"Rank": 2, "Player": "frank", "Points": 6},
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _con():
    return store.connect(":memory:")


def _load_labeled_corpus(con):
    """Load online challenge: alice=Delver, bob=Lands, carol=Reanimator, dave=Unknown.

    Returns tid.
    """
    tid = store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
    con.execute(
        "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
        ["Delver", tid, "alice"],
    )
    con.execute(
        "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
        ["Lands", tid, "bob"],
    )
    con.execute(
        "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
        ["Reanimator", tid, "carol"],
    )
    con.execute(
        "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
        ["Unknown", tid, "dave"],
    )
    return tid


# ---------------------------------------------------------------------------
# Unit 1 — TestNormalizeShares
# ---------------------------------------------------------------------------


class TestNormalizeShares:
    def test_already_normalized_unchanged_no_warning(self):
        """Shares summing exactly to 1.0 are returned unchanged with no warnings."""
        result, warnings = _normalize_shares({"A": 0.6, "B": 0.4})
        assert pytest.approx(result["A"]) == 0.6
        assert pytest.approx(result["B"]) == 0.4
        assert warnings == []

    def test_sub_one_sum_normalized_with_warning(self):
        """Shares summing to 0.9 are renormalized and a warning is emitted."""
        result, warnings = _normalize_shares({"A": 0.6, "B": 0.3})
        assert pytest.approx(result["A"], abs=1e-6) == 0.6 / 0.9
        assert pytest.approx(result["B"], abs=1e-6) == 0.3 / 0.9
        assert len(warnings) == 1
        assert "0.9000" in warnings[0]
        assert "normalized to 1.0" in warnings[0]

    def test_normalized_shares_sum_to_one(self):
        """Result shares always sum to ~1.0 after normalization."""
        result, _ = _normalize_shares({"A": 0.6, "B": 0.3})
        assert pytest.approx(sum(result.values()), abs=1e-9) == 1.0

    def test_over_one_sum_normalized_with_warning(self):
        """Shares summing to 1.2 are renormalized with a warning."""
        result, warnings = _normalize_shares({"A": 0.7, "B": 0.5})
        assert pytest.approx(sum(result.values()), abs=1e-9) == 1.0
        assert len(warnings) == 1
        assert "1.2000" in warnings[0]

    def test_empty_map_raises_value_error(self):
        """Empty map raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            _normalize_shares({})

    def test_negative_share_raises_value_error(self):
        """Any negative share raises ValueError."""
        with pytest.raises(ValueError, match="negative"):
            _normalize_shares({"A": -0.1, "B": 1.1})

    def test_all_zero_raises_value_error(self):
        """All-zero shares raises ValueError."""
        with pytest.raises(ValueError):
            _normalize_shares({"A": 0.0})

    def test_zero_sum_raises_value_error(self):
        """Zero-sum map (all zeros) raises ValueError."""
        with pytest.raises(ValueError):
            _normalize_shares({"A": 0.0, "B": 0.0})

    def test_single_archetype_normalized(self):
        """A single archetype with any positive share normalizes to share=1.0."""
        result, _ = _normalize_shares({"X": 0.7})
        assert pytest.approx(result["X"]) == 1.0

    def test_within_tolerance_no_warning(self):
        """Sum within _SUM_TOLERANCE of 1.0 emits no warning."""
        # Construct a sum that is exactly 1.0 + 5e-7 (within 1e-6 tolerance)
        result, warnings = _normalize_shares({"A": 1.0 + 5e-7})
        assert warnings == []


# ---------------------------------------------------------------------------
# Units 3 + 2 — TestBuildGlobalField
# ---------------------------------------------------------------------------


class TestBuildGlobalField:
    def test_shares_sum_to_one(self):
        """Global field shares sum to ~1.0 over positionable archetypes."""
        con = _con()
        _load_labeled_corpus(con)
        fd = build_global_field(con)
        assert pytest.approx(sum(fd.shares.values()), abs=1e-9) == 1.0
        con.close()

    def test_counts_match_entry_n(self):
        """counts[archetype] equals the deck count in the corpus for each archetype."""
        con = _con()
        _load_labeled_corpus(con)
        fd = build_global_field(con)
        # alice=Delver(1), bob=Lands(1), carol=Reanimator(1) → each count = 1
        assert fd.counts is not None
        assert fd.counts["Delver"] == 1
        assert fd.counts["Lands"] == 1
        assert fd.counts["Reanimator"] == 1
        con.close()

    def test_unknown_excluded_from_shares(self):
        """Unknown-labeled deck is NOT in shares."""
        con = _con()
        _load_labeled_corpus(con)
        fd = build_global_field(con)
        assert "Unknown" not in fd.shares
        con.close()

    def test_unknown_excluded_from_counts(self):
        """Unknown-labeled deck is NOT in counts."""
        con = _con()
        _load_labeled_corpus(con)
        fd = build_global_field(con)
        assert fd.counts is not None
        assert "Unknown" not in fd.counts
        con.close()

    def test_unknown_exclusion_triggers_warning(self):
        """Excluding an Unknown deck produces an exclusion warning with the fraction."""
        con = _con()
        _load_labeled_corpus(con)
        fd = build_global_field(con)
        exclusion_warnings = [w for w in fd.warnings if "unclassified" in w or "Unknown" in w]
        assert len(exclusion_warnings) >= 1
        assert "25.0%" in exclusion_warnings[0] or "0.2500" in exclusion_warnings[0] or "25%" in exclusion_warnings[0]
        con.close()

    def test_conflict_excluded_from_field(self):
        """Conflict(...)-labeled deck is excluded from shares."""
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(_CHALLENGE_ONLINE, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Delver", tid, "alice"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Lands", tid, "bob"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Reanimator", tid, "carol"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Conflict(A,B)", tid, "dave"],
        )
        fd = build_global_field(con)
        assert "Conflict(A,B)" not in fd.shares
        exclusion_warnings = [w for w in fd.warnings if "unclassified" in w]
        assert len(exclusion_warnings) >= 1
        con.close()

    def test_field_source_is_global(self):
        """field_source is always 'global'."""
        con = _con()
        _load_labeled_corpus(con)
        fd = build_global_field(con)
        assert fd.field_source == "global"
        con.close()

    def test_counts_is_not_none(self):
        """counts is a dict (not None) for global fields."""
        con = _con()
        _load_labeled_corpus(con)
        fd = build_global_field(con)
        assert fd.counts is not None
        assert isinstance(fd.counts, dict)
        con.close()

    def test_no_data_is_empty_frozenset(self):
        """no_data is an empty frozenset for global fields (all archetypes are data-backed)."""
        con = _con()
        _load_labeled_corpus(con)
        fd = build_global_field(con)
        assert fd.no_data == frozenset()
        con.close()

    def test_provenance_filter_paper_only(self):
        """provenance='paper' restricts the field to paper events only."""
        con = _con()
        # Load online first
        _load_labeled_corpus(con)
        # Load paper event: eve=Stompy, frank=Show
        tid2 = store.load_tournament(con, parse_cache_item(_PAPER_CHALLENGE, "mtgmelee"))
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Stompy", tid2, "eve"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Show", tid2, "frank"],
        )

        fd_paper = build_global_field(con, provenance="paper")
        # Only paper archetypes should be present
        assert "Delver" not in fd_paper.shares
        assert "Stompy" in fd_paper.shares or "Show" in fd_paper.shares
        con.close()

    def test_provenance_filter_online_excludes_paper(self):
        """provenance='online' excludes paper-only archetypes."""
        con = _con()
        _load_labeled_corpus(con)
        tid2 = store.load_tournament(con, parse_cache_item(_PAPER_CHALLENGE, "mtgmelee"))
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Stompy", tid2, "eve"],
        )
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            ["Show", tid2, "frank"],
        )

        fd_online = build_global_field(con, provenance="online")
        assert "Stompy" not in fd_online.shares
        assert "Show" not in fd_online.shares
        con.close()

    def test_renormalized_shares_after_unknown_exclusion(self):
        """After excluding Unknown, remaining shares sum to 1.0 (renormalized)."""
        con = _con()
        _load_labeled_corpus(con)  # alice=Delver, bob=Lands, carol=Reanimator, dave=Unknown
        fd = build_global_field(con)
        # 3 positionable archetypes, each with equal count → each share = 1/3
        for arch in ("Delver", "Lands", "Reanimator"):
            assert pytest.approx(fd.shares[arch], abs=1e-6) == 1.0 / 3.0
        con.close()


# ---------------------------------------------------------------------------
# Unit 4 — TestBuildCustomField
# ---------------------------------------------------------------------------


class TestBuildCustomField:
    def test_basic_custom_field(self):
        """Simple share dict returns field_source='custom', counts=None."""
        fd = build_custom_field({"Delver": 0.5, "Lands": 0.5})
        assert fd.field_source == "custom"
        assert fd.counts is None

    def test_shares_unchanged_when_already_normalized(self):
        """Shares summing to 1.0 are returned unchanged."""
        fd = build_custom_field({"Delver": 0.5, "Lands": 0.5})
        assert pytest.approx(fd.shares["Delver"]) == 0.5
        assert pytest.approx(fd.shares["Lands"]) == 0.5

    def test_shares_normalized_when_not_summing_to_one(self):
        """Shares summing to 0.8 are normalized to 1.0."""
        fd = build_custom_field({"Delver": 0.4, "Lands": 0.4})
        assert pytest.approx(sum(fd.shares.values()), abs=1e-9) == 1.0
        assert pytest.approx(fd.shares["Delver"], abs=1e-6) == 0.5
        assert pytest.approx(fd.shares["Lands"], abs=1e-6) == 0.5

    def test_normalization_warning_emitted(self):
        """When sum != 1.0, a normalization warning is included."""
        fd = build_custom_field({"Delver": 0.4, "Lands": 0.4})
        norm_warnings = [w for w in fd.warnings if "normalized to 1.0" in w]
        assert len(norm_warnings) == 1

    def test_point_shares_warning_always_present(self):
        """The point-shares warning is always emitted regardless of normalization."""
        # Already-normalized shares
        fd1 = build_custom_field({"Delver": 0.5, "Lands": 0.5})
        pt_warnings = [w for w in fd1.warnings if "point shares" in w]
        assert len(pt_warnings) == 1

        # Non-normalized shares
        fd2 = build_custom_field({"Delver": 0.4, "Lands": 0.4})
        pt_warnings2 = [w for w in fd2.warnings if "point shares" in w]
        assert len(pt_warnings2) == 1

    def test_no_data_empty_when_no_known_archetypes(self):
        """no_data is empty frozenset when known_archetypes is not provided."""
        fd = build_custom_field({"Delver": 0.5, "Lands": 0.5})
        assert fd.no_data == frozenset()

    def test_no_data_flags_archetypes_absent_from_known(self):
        """Archetypes absent from known_archetypes are in no_data."""
        known = frozenset({"Delver", "Lands"})
        fd = build_custom_field(
            {"Delver": 0.4, "Lands": 0.4, "Rogue": 0.2},
            known_archetypes=known,
        )
        assert "Rogue" in fd.no_data
        assert "Delver" not in fd.no_data
        assert "Lands" not in fd.no_data

    def test_no_data_archetype_still_in_shares(self):
        """Archetypes in no_data are still present in shares (kept for downstream imputation)."""
        known = frozenset({"Delver"})
        fd = build_custom_field(
            {"Delver": 0.5, "Rogue": 0.5},
            known_archetypes=known,
        )
        assert "Rogue" in fd.shares
        assert "Rogue" in fd.no_data

    def test_no_data_warning_emitted_when_unknown_archetypes(self):
        """A warning is emitted naming the archetypes absent from known_archetypes."""
        known = frozenset({"Delver"})
        fd = build_custom_field(
            {"Delver": 0.5, "Rogue": 0.5},
            known_archetypes=known,
        )
        no_data_warnings = [w for w in fd.warnings if "no matchup data" in w or "Rogue" in w]
        assert len(no_data_warnings) >= 1

    def test_counts_is_none(self):
        """Custom field always has counts=None (share-only)."""
        fd = build_custom_field({"A": 0.6, "B": 0.4})
        assert fd.counts is None

    def test_field_source_is_custom(self):
        """field_source is 'custom'."""
        fd = build_custom_field({"A": 0.5, "B": 0.5})
        assert fd.field_source == "custom"

    def test_empty_shares_raises(self):
        """Empty share dict raises ValueError."""
        with pytest.raises(ValueError):
            build_custom_field({})

    def test_negative_share_raises(self):
        """Negative share raises ValueError."""
        with pytest.raises(ValueError):
            build_custom_field({"A": -0.1, "B": 1.1})

    def test_all_zero_raises(self):
        """All-zero shares raises ValueError."""
        with pytest.raises(ValueError):
            build_custom_field({"A": 0.0, "B": 0.0})

    def test_all_archetypes_in_known_no_data_empty(self):
        """When all archetypes are in known_archetypes, no_data is empty."""
        known = frozenset({"Delver", "Lands"})
        fd = build_custom_field(
            {"Delver": 0.5, "Lands": 0.5},
            known_archetypes=known,
        )
        assert fd.no_data == frozenset()


# ---------------------------------------------------------------------------
# Unit 2 — TestFieldDistribution
# ---------------------------------------------------------------------------


class TestFieldDistribution:
    def test_global_field_has_field_source_set(self):
        """Global FieldDistribution always has a non-null field_source."""
        con = _con()
        _load_labeled_corpus(con)
        fd = build_global_field(con)
        assert fd.field_source is not None
        assert fd.field_source == "global"
        con.close()

    def test_custom_field_has_field_source_set(self):
        """Custom FieldDistribution always has a non-null field_source."""
        fd = build_custom_field({"X": 0.6, "Y": 0.4})
        assert fd.field_source is not None
        assert fd.field_source == "custom"

    def test_global_counts_is_dict(self):
        """Global field has counts as a dict (not None)."""
        con = _con()
        _load_labeled_corpus(con)
        fd = build_global_field(con)
        assert isinstance(fd.counts, dict)
        con.close()

    def test_custom_counts_is_none(self):
        """Custom field has counts=None."""
        fd = build_custom_field({"X": 0.5, "Y": 0.5})
        assert fd.counts is None

    def test_warnings_is_tuple(self):
        """warnings field is always a tuple (immutable)."""
        con = _con()
        _load_labeled_corpus(con)
        fd_global = build_global_field(con)
        assert isinstance(fd_global.warnings, tuple)
        con.close()

        fd_custom = build_custom_field({"A": 0.5, "B": 0.5})
        assert isinstance(fd_custom.warnings, tuple)

    def test_no_data_is_frozenset(self):
        """no_data is always a frozenset."""
        con = _con()
        _load_labeled_corpus(con)
        fd_global = build_global_field(con)
        assert isinstance(fd_global.no_data, frozenset)
        con.close()

        fd_custom = build_custom_field({"A": 0.5, "B": 0.5})
        assert isinstance(fd_custom.no_data, frozenset)


# ---------------------------------------------------------------------------
# Regression tests for peer-review bug fixes
# ---------------------------------------------------------------------------


class TestRegressionPeerReviewFixes:
    """One regression test per field-related finding (2026-05-30 peer review)."""

    # --- Fix 8: _normalize_shares rejects NaN and Inf ---

    def test_fix8_nan_share_raises_value_error(self):
        """Bug: float('nan') passes the <0 check and float() accepts it.
        Fix: add math.isfinite() guard → ValueError on NaN inputs.
        """
        with pytest.raises(ValueError, match="non-finite"):
            _normalize_shares({"A": float("nan")})

    def test_fix8_inf_share_raises_value_error(self):
        """Bug: float('inf') passes the <0 check silently.
        Fix: math.isfinite() catches +inf.
        """
        with pytest.raises(ValueError, match="non-finite"):
            _normalize_shares({"A": float("inf")})

    def test_fix8_neg_inf_share_raises_value_error(self):
        """-inf is also non-finite and must be rejected before the <0 check."""
        with pytest.raises(ValueError, match="non-finite"):
            _normalize_shares({"A": float("-inf")})

    def test_fix8_valid_shares_still_pass(self):
        """Confirming valid finite shares are unaffected by the NaN/inf guard."""
        result, warnings = _normalize_shares({"A": 0.6, "B": 0.4})
        assert pytest.approx(result["A"]) == 0.6
        assert pytest.approx(result["B"]) == 0.4


# ---------------------------------------------------------------------------
# FieldDistribution.restrict_to — epic-advisory-output-honesty-positioning-coverage
# ---------------------------------------------------------------------------


class TestRestrictTo:
    """Pure renormalization of a field over a covered subset + excluded-share accounting."""

    def _field(self) -> FieldDistribution:
        return FieldDistribution(
            shares={"A": 0.5, "B": 0.3, "C": 0.2},
            field_source="global",
            counts={"A": 50, "B": 30, "C": 20},
            no_data=frozenset({"C"}),
            warnings=("preexisting",),
        )

    def test_renormalizes_to_one(self):
        restricted, excluded = self._field().restrict_to({"A", "B"})
        assert pytest.approx(sum(restricted.shares.values())) == 1.0
        # A:B was 0.5:0.3 → renormalized 0.625:0.375
        assert pytest.approx(restricted.shares["A"]) == 0.625
        assert pytest.approx(restricted.shares["B"]) == 0.375

    def test_excluded_share_is_dropped_mass(self):
        _, excluded = self._field().restrict_to({"A", "B"})
        assert pytest.approx(excluded) == 0.2  # C dropped

    def test_counts_filtered_not_renormalized(self):
        restricted, _ = self._field().restrict_to({"A", "B"})
        assert restricted.counts == {"A": 50, "B": 30}

    def test_counts_none_stays_none(self):
        f = FieldDistribution(
            shares={"A": 0.5, "B": 0.5}, field_source="custom",
            counts=None, no_data=frozenset(), warnings=(),
        )
        restricted, _ = f.restrict_to({"A"})
        assert restricted.counts is None

    def test_no_data_intersected_and_source_preserved(self):
        restricted, _ = self._field().restrict_to({"A", "B"})
        assert restricted.no_data == frozenset()  # C was the only no_data, now excluded
        assert restricted.field_source == "global"
        assert restricted.warnings == ("preexisting",)

    def test_keep_superset_is_noop(self):
        restricted, excluded = self._field().restrict_to({"A", "B", "C", "Z"})
        assert pytest.approx(excluded) == 0.0
        assert pytest.approx(restricted.shares["A"]) == 0.5

    def test_empty_keep_raises(self):
        with pytest.raises(ValueError, match="zero share mass"):
            self._field().restrict_to({"Z"})

    def test_restrict_does_not_emit_normalize_warning(self):
        # Intentional restriction must NOT add a "summed to X" data-quality warning.
        restricted, _ = self._field().restrict_to({"A", "B"})
        assert not any("summed to" in w for w in restricted.warnings)
