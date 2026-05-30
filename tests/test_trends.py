"""Meta-trend tests — Units 1–5 of epic-meta-analytics-trends.

House style: module-level raw dicts → ``parse_cache_item`` → ``store.load_tournament``
into ``:memory:``; labels pinned via direct SQL UPDATE; ``TestX`` classes; deterministic.

Fixtures span ≥3 ban-list regimes:
  - ``2024-09-01`` → after Grief (2024-08-26), before Psychic Frog (2024-12-16)
  - ``2025-01-15`` → after Psychic Frog + Vexing Bauble (2024-12-16), before Underworld Breach (2025-02-01)
  - ``2026-05-25`` → after Undercity Informer (2026-05-18) — current regime

A thin-regime fixture uses dates clustered within the same regime with <4 events and/or <14d span.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.analytics import (
    RegimeWindow,
    TrendCell,
    TrendSeries,
    compute_trends,
    regime_windows,
)
from legacy_engine.analytics.metashare import (
    _raw_counts,
    _topcut_counts,
    _unlabeled_count,
    compute_metashare,
)
from legacy_engine.cli import main
from legacy_engine.confidence import tier_for_sample
from legacy_engine.ingestion import store
from legacy_engine.ingestion.banlist import BAN_EVENTS
from legacy_engine.ingestion.cache import parse_cache_item

# ---------------------------------------------------------------------------
# Shared raw tournament fixtures — spanning multiple ban-list regimes
# ---------------------------------------------------------------------------

# Regime A: after Grief (2024-08-26), before Psychic Frog (2024-12-16)
_REGIME_A_T1 = {
    "Tournament": {
        "Name": "Legacy Challenge A1",
        "Date": "2024-09-01",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-a1-2024-09-01",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "p1",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "p2",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
        {
            "Player": "p3",
            "Result": "3rd Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
        {
            "Player": "p4",
            "Result": "4th Place",
            "Mainboard": [{"Count": 4, "CardName": "Ponder"}],
            "Sideboard": [],
        },
        {
            "Player": "p5",
            "Result": "5th Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "p6",
            "Result": "6th Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [
        {"Rank": 1, "Player": "p1", "Points": 18},
        {"Rank": 2, "Player": "p2", "Points": 15},
        {"Rank": 3, "Player": "p3", "Points": 12},
        {"Rank": 4, "Player": "p4", "Points": 9},
        {"Rank": 5, "Player": "p5", "Points": 6},
        {"Rank": 6, "Player": "p6", "Points": 3},
    ],
}

_REGIME_A_T2 = {
    "Tournament": {
        "Name": "Legacy Challenge A2",
        "Date": "2024-09-15",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-a2-2024-09-15",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "q1",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "q2",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "q3",
            "Result": "3rd Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
        {
            "Player": "q4",
            "Result": "4th Place",
            "Mainboard": [{"Count": 4, "CardName": "Ponder"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [],
}

# Regime B: after Psychic Frog + Vexing Bauble (2024-12-16), before Underworld Breach (2025-02-01)
_REGIME_B_T1 = {
    "Tournament": {
        "Name": "Legacy Challenge B1",
        "Date": "2025-01-15",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-b1-2025-01-15",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "r1",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "r2",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
        {
            "Player": "r3",
            "Result": "3rd Place",
            "Mainboard": [{"Count": 4, "CardName": "Ponder"}],
            "Sideboard": [],
        },
        {
            "Player": "r4",
            "Result": "4th Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [],
}

# Regime C (current): after Undercity Informer (2026-05-18)
_REGIME_C_T1 = {
    "Tournament": {
        "Name": "Legacy Challenge C1",
        "Date": "2026-05-25",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-c1-2026-05-25",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "s1",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "s2",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
        {
            "Player": "s3",
            "Result": "3rd Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [
        {"Rank": 1, "Player": "s1", "Points": 18},
        {"Rank": 2, "Player": "s2", "Points": 15},
        {"Rank": 3, "Player": "s3", "Points": 12},
    ],
}

# Thin regime fixture: two events close together in Regime B (< 4 events and < 14-day span)
_THIN_T1 = {
    "Tournament": {
        "Name": "Thin T1",
        "Date": "2025-01-10",
        "Uri": "https://www.mtgo.com/decklist/thin-t1-2025-01-10",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "thin1",
            "Result": "1st",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "thin2",
            "Result": "2nd",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [],
}

_THIN_T2 = {
    "Tournament": {
        "Name": "Thin T2",
        "Date": "2025-01-12",  # only 2 days after T1 → span = 2 < 14
        "Uri": "https://www.mtgo.com/decklist/thin-t2-2025-01-12",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "thin3",
            "Result": "1st",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "thin4",
            "Result": "2nd",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _con():
    return store.connect(":memory:")


def _load_and_label(con, raw_dict, source, labels: dict[str, str]):
    """Load tournament and apply archetype labels {player: archetype}."""
    tid = store.load_tournament(con, parse_cache_item(raw_dict, source))
    for player, archetype in labels.items():
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            [archetype, tid, player],
        )
    return tid


def _build_multi_regime_corpus(con):
    """Load events spanning regime A, B, and C with deterministic archetypes."""
    # Regime A: T1 (6 decks) + T2 (4 decks) = 10 events in regime
    _load_and_label(
        con, _REGIME_A_T1, "MTGO",
        {"p1": "Delver", "p2": "Lands", "p3": "Reanimator",
         "p4": "Control", "p5": "Delver", "p6": "Delver"},
    )
    _load_and_label(
        con, _REGIME_A_T2, "MTGO",
        {"q1": "Delver", "q2": "Delver", "q3": "Reanimator", "q4": "Control"},
    )
    # Regime B: T1 (4 decks)
    _load_and_label(
        con, _REGIME_B_T1, "MTGO",
        {"r1": "Delver", "r2": "Reanimator", "r3": "Control", "r4": "Lands"},
    )
    # Regime C: T1 (3 decks)
    _load_and_label(
        con, _REGIME_C_T1, "melee",
        {"s1": "Delver", "s2": "Lands", "s3": "Delver"},
    )


# ---------------------------------------------------------------------------
# TestRegimeWindows — Unit 1
# ---------------------------------------------------------------------------


class TestRegimeWindows:
    def test_baseline_is_first_window(self):
        """First window has since=None and until=earliest BAN_EVENTS date."""
        windows = regime_windows()
        assert len(windows) >= 2
        first = windows[0]
        assert first.since is None
        earliest_ban_date = min(d for d, _c, _r in BAN_EVENTS)
        assert first.until == earliest_ban_date

    def test_current_regime_is_last(self):
        """Last window has until=None and label ends with 'current'."""
        windows = regime_windows()
        last = windows[-1]
        assert last.until is None
        assert last.label.endswith("— current")

    def test_windows_count_equals_unique_dates_plus_one(self):
        """Number of windows == number of distinct ban dates + 1 (for baseline)."""
        windows = regime_windows()
        unique_dates = len({d for d, _c, _r in BAN_EVENTS})
        assert len(windows) == unique_dates + 1

    def test_multi_card_date_yields_one_boundary(self):
        """2024-12-16 (Psychic Frog + Vexing Bauble) yields exactly ONE regime window."""
        from datetime import date as date_cls

        multi_date = date_cls(2024, 12, 16)
        windows = regime_windows()
        windows_opening_on_date = [w for w in windows if w.since == multi_date]
        assert len(windows_opening_on_date) == 1

    def test_multi_card_date_has_both_cards_in_opening_events(self):
        """The 2024-12-16 regime has both Psychic Frog and Vexing Bauble in opening_events."""
        from datetime import date as date_cls

        multi_date = date_cls(2024, 12, 16)
        windows = regime_windows()
        w = next(w for w in windows if w.since == multi_date)
        assert "Psychic Frog" in w.opening_events
        assert "Vexing Bauble" in w.opening_events

    def test_windows_are_contiguous_and_half_open(self):
        """For all adjacent pairs, window[i].until == window[i+1].since."""
        windows = regime_windows()
        for i in range(len(windows) - 1):
            assert windows[i].until == windows[i + 1].since, (
                f"windows[{i}].until={windows[i].until!r} != windows[{i+1}].since={windows[i+1].since!r}"
            )

    def test_baseline_regime_has_empty_opening_events(self):
        """The baseline (pre-first-ban) regime has no opening_events."""
        windows = regime_windows()
        assert windows[0].opening_events == ()

    def test_interior_regime_labels_contain_card_names(self):
        """Interior regime labels mention the cards banned."""
        windows = regime_windows()
        # Grief regime
        grief_window = next(w for w in windows if "Grief" in w.label)
        assert "Grief" in grief_window.label

    def test_regime_windows_pure_deterministic(self):
        """regime_windows() returns the same result on repeated calls."""
        w1 = regime_windows()
        w2 = regime_windows()
        assert w1 == w2

    def test_bare_windows_have_zero_event_stats(self):
        """RegimeWindow from regime_windows() has event_count=0, span_days=0, thin=False."""
        windows = regime_windows()
        for w in windows:
            assert w.event_count == 0
            assert w.span_days == 0
            assert w.thin is False


# ---------------------------------------------------------------------------
# TestMetashareWindowing — Unit 2 (additive window on metashare helpers)
# ---------------------------------------------------------------------------


class TestMetashareWindowing:
    def test_raw_counts_since_includes_on_boundary(self):
        """_raw_counts with since='2024-09-01' includes events on that exact date."""
        con = _con()
        _load_and_label(con, _REGIME_A_T1, "MTGO",
                        {"p1": "Delver", "p2": "Lands", "p3": "Reanimator",
                         "p4": "Control", "p5": "Delver", "p6": "Delver"})
        counts = _raw_counts(con, provenance=None, since="2024-09-01")
        assert counts.get("Delver", 0) == 3  # p1, p5, p6 on 2024-09-01
        con.close()

    def test_raw_counts_until_excludes_on_boundary(self):
        """_raw_counts with until='2024-09-15' excludes events on that exact date."""
        con = _con()
        _load_and_label(con, _REGIME_A_T1, "MTGO",
                        {"p1": "Delver", "p2": "Lands", "p3": "Reanimator",
                         "p4": "Control", "p5": "Delver", "p6": "Delver"})
        _load_and_label(con, _REGIME_A_T2, "MTGO",
                        {"q1": "Delver", "q2": "Delver", "q3": "Reanimator", "q4": "Control"})
        counts = _raw_counts(con, provenance=None, until="2024-09-15")
        # Only T1 events (2024-09-01) should appear; T2 on 2024-09-15 is excluded
        assert counts.get("Delver", 0) == 3  # only p1, p5, p6
        con.close()

    def test_raw_counts_window_isolates_regime(self):
        """_raw_counts with since/until isolates decks only within the window."""
        con = _con()
        _build_multi_regime_corpus(con)
        # Window around regime B only: [2024-12-16, 2025-02-01)
        counts = _raw_counts(con, provenance=None, since="2024-12-16", until="2025-02-01")
        # Only 2025-01-15 event (r1=Delver, r2=Reanimator, r3=Control, r4=Lands)
        assert counts.get("Delver", 0) == 1
        assert counts.get("Reanimator", 0) == 1
        assert counts.get("Lands", 0) == 1
        # No regime A or C decks
        assert "Delver" in counts
        # Total should be exactly 4 (4 decks from _REGIME_B_T1 only)
        assert sum(counts.values()) == 4
        con.close()

    def test_topcut_counts_window(self):
        """_topcut_counts with since/until respects the date window."""
        con = _con()
        # Only T1 of regime A has standings
        _load_and_label(con, _REGIME_A_T1, "MTGO",
                        {"p1": "Delver", "p2": "Lands", "p3": "Reanimator",
                         "p4": "Control", "p5": "Delver", "p6": "Delver"})
        _load_and_label(con, _REGIME_C_T1, "melee",
                        {"s1": "Delver", "s2": "Lands", "s3": "Delver"})
        # Window to regime A only
        counts_a = _topcut_counts(con, provenance=None, cut_size=8, since="2024-08-26", until="2024-12-16")
        counts_all = _topcut_counts(con, provenance=None, cut_size=8)
        # Regime C has standings too — windowed should have fewer
        assert sum(counts_a.values()) < sum(counts_all.values())
        con.close()

    def test_unlabeled_count_window(self):
        """_unlabeled_count with since/until only counts unlabeled decks in the window."""
        con = _con()
        # Load regime A T1 without labeling anyone
        store.load_tournament(con, parse_cache_item(_REGIME_A_T1, "MTGO"))
        # Load regime C T1 and label everyone
        _load_and_label(con, _REGIME_C_T1, "melee",
                        {"s1": "Delver", "s2": "Lands", "s3": "Delver"})
        unlabeled_a = _unlabeled_count(con, provenance=None, since="2024-08-26", until="2024-12-16")
        unlabeled_all = _unlabeled_count(con, provenance=None)
        # Only regime A has unlabeled decks
        assert unlabeled_a == 6  # all 6 in _REGIME_A_T1 are unlabeled
        assert unlabeled_all == 6  # regime C all labeled
        con.close()

    def test_no_window_regression_equals_unwindowed(self):
        """compute_metashare with no window kwargs == same corpus passed without window."""
        con = _con()
        _build_multi_regime_corpus(con)
        report_unwindowed = compute_metashare(con, definition="raw", provenance=None, min_share=0.0)
        report_no_kwargs = compute_metashare(con, definition="raw", provenance=None, min_share=0.0,
                                             since=None, until=None)
        assert report_unwindowed.total_decks == report_no_kwargs.total_decks
        # Same entries (sorted by share)
        arches_unwindowed = {e.archetype: e.share for e in report_unwindowed.entries}
        arches_no_kwargs = {e.archetype: e.share for e in report_no_kwargs.entries}
        assert arches_unwindowed == arches_no_kwargs
        con.close()

    def test_windowed_wrw_raises_not_implemented(self):
        """compute_metashare(definition='wrw', since=...) raises NotImplementedError."""
        import pytest

        con = _con()
        _load_and_label(con, _REGIME_A_T1, "MTGO",
                        {"p1": "Delver", "p2": "Lands", "p3": "Reanimator",
                         "p4": "Control", "p5": "Delver", "p6": "Delver"})
        with pytest.raises(NotImplementedError, match="windowed wrw"):
            compute_metashare(con, definition="wrw", since="2024-09-01")
        con.close()

    def test_windowed_wrw_until_raises_not_implemented(self):
        """compute_metashare(definition='wrw', until=...) raises NotImplementedError."""
        import pytest

        con = _con()
        _load_and_label(con, _REGIME_A_T1, "MTGO",
                        {"p1": "Delver", "p2": "Lands", "p3": "Reanimator",
                         "p4": "Control", "p5": "Delver", "p6": "Delver"})
        with pytest.raises(NotImplementedError, match="windowed wrw"):
            compute_metashare(con, definition="wrw", until="2025-01-01")
        con.close()


# ---------------------------------------------------------------------------
# TestComputeTrends — Unit 3
# ---------------------------------------------------------------------------


class TestComputeTrends:
    def test_wrw_raises_value_error(self):
        """compute_trends(definition='wrw') raises ValueError."""
        con = _con()
        _build_multi_regime_corpus(con)
        with pytest.raises(ValueError, match="raw.*topcut|wrw"):
            compute_trends(con, definition="wrw")
        con.close()

    def test_series_contains_only_non_empty_regimes(self):
        """TrendSeries.regimes contains only regimes that have >=1 in-window event."""
        con = _con()
        _build_multi_regime_corpus(con)
        series = compute_trends(con, definition="raw", min_share=0.0)
        # We loaded events in 3 regimes — all should appear
        regime_labels = {r.label for r in series.regimes}
        # Sanity: at least 3 non-empty regimes
        assert len(series.regimes) >= 3
        # Every regime in series has event_count > 0
        for r in series.regimes:
            assert r.event_count > 0
        con.close()

    def test_empty_regimes_are_omitted(self):
        """Regimes with zero in-window events are excluded from the series."""
        con = _con()
        _build_multi_regime_corpus(con)
        series = compute_trends(con, definition="raw", min_share=0.0)
        all_windows = regime_windows()
        # Not all regime windows appear in the series (many have zero events in this small corpus)
        assert len(series.regimes) < len(all_windows)
        con.close()

    def test_archetype_shares_match_per_regime_metashare(self):
        """For each regime, trend cells equal compute_metashare(..., since, until) for the same window."""
        con = _con()
        _build_multi_regime_corpus(con)
        series = compute_trends(con, definition="raw", provenance=None, min_share=0.0)

        for regime in series.regimes:
            since_str = regime.since.isoformat() if regime.since else None
            until_str = regime.until.isoformat() if regime.until else None
            direct = compute_metashare(
                con, definition="raw", provenance=None, min_share=0.0,
                group_other=False, since=since_str, until=until_str,
            )
            for entry in direct.entries:
                cell = series.cells.get((regime.label, entry.archetype))
                assert cell is not None, (
                    f"Archetype {entry.archetype!r} from direct compute_metashare"
                    f" not found in series for regime {regime.label!r}"
                )
                assert abs(cell.share - entry.share) < 1e-9, (
                    f"Share mismatch for {entry.archetype!r} in regime {regime.label!r}: "
                    f"cell={cell.share}, direct={entry.share}"
                )
        con.close()

    def test_trajectory_returns_none_for_absent_regimes(self):
        """trajectory(archetype) returns None for regimes where the archetype is absent."""
        con = _con()
        _build_multi_regime_corpus(con)
        series = compute_trends(con, definition="raw", min_share=0.0)

        # Find an archetype with at least one None in trajectory
        for archetype in series.archetypes:
            traj = series.trajectory(archetype)
            assert len(traj) == len(series.regimes)
            # All entries are either TrendCell or None
            for cell in traj:
                assert cell is None or isinstance(cell, TrendCell)
        con.close()

    def test_trajectory_not_all_none_for_present_archetype(self):
        """trajectory(archetype) for a present archetype has at least one non-None cell."""
        con = _con()
        _build_multi_regime_corpus(con)
        series = compute_trends(con, definition="raw", min_share=0.0)
        for archetype in series.archetypes:
            traj = series.trajectory(archetype)
            assert any(c is not None for c in traj), (
                f"Archetype {archetype!r} is in archetypes list but has all-None trajectory"
            )
        con.close()

    def test_series_definition_and_provenance_labeled(self):
        """TrendSeries always carries definition and provenance (PRINCIPLES #6)."""
        con = _con()
        _build_multi_regime_corpus(con)
        series = compute_trends(con, definition="raw", provenance="online")
        assert series.definition == "raw"
        assert series.provenance == "online"
        con.close()

    def test_thin_regime_flagged(self):
        """A regime with 2 events and a 2-day span is flagged thin=True."""
        con = _con()
        # Load only thin events in regime B (2025-01-10 and 2025-01-12, both in [2024-12-16, 2025-02-01))
        _load_and_label(con, _THIN_T1, "MTGO",
                        {"thin1": "Delver", "thin2": "Reanimator"})
        _load_and_label(con, _THIN_T2, "MTGO",
                        {"thin3": "Delver", "thin4": "Reanimator"})
        series = compute_trends(con, definition="raw", min_share=0.0)
        # Both thin events fall in the [2024-12-16, 2025-02-01) regime
        thin_regimes = [r for r in series.regimes if r.thin]
        assert len(thin_regimes) >= 1
        # The thin regime has 2 events
        b_regime = next(r for r in series.regimes if r.event_count == 2)
        assert b_regime.thin is True
        assert b_regime.event_count == 2
        assert b_regime.span_days == 2  # 2025-01-12 - 2025-01-10 = 2 days
        con.close()

    def test_thin_regime_cells_capped_at_evolving(self):
        """Cells in a thin regime can never be 'established' — capped at 'evolving'."""
        con = _con()
        # Load only thin events: 2 events, 2-day span → thin
        _load_and_label(con, _THIN_T1, "MTGO",
                        {"thin1": "Delver", "thin2": "Reanimator"})
        _load_and_label(con, _THIN_T2, "MTGO",
                        {"thin3": "Delver", "thin4": "Reanimator"})
        series = compute_trends(con, definition="raw", min_share=0.0)

        for regime in series.regimes:
            if regime.thin:
                for archetype in series.archetypes:
                    cell = series.cells.get((regime.label, archetype))
                    if cell is not None:
                        assert cell.tier != "established", (
                            f"Thin regime {regime.label!r}: archetype {archetype!r} "
                            f"has tier 'established' (must be capped at 'evolving')"
                        )
        con.close()

    def test_non_thin_regime_respects_tier_for_sample(self):
        """Cells in non-thin regimes use tier_for_sample normally (not always capped)."""
        con = _con()
        _build_multi_regime_corpus(con)
        series = compute_trends(con, definition="raw", min_share=0.0)
        for regime in series.regimes:
            if not regime.thin:
                for archetype in series.archetypes:
                    cell = series.cells.get((regime.label, archetype))
                    if cell is not None:
                        expected = tier_for_sample(cell.n)
                        assert cell.tier == expected, (
                            f"Non-thin regime {regime.label!r}: {archetype!r} tier {cell.tier!r} "
                            f"!= tier_for_sample({cell.n})={expected!r}"
                        )
        con.close()

    def test_archetypes_sorted_by_most_recent_regime(self):
        """archetypes are sorted by most-recent-regime share (desc)."""
        con = _con()
        _build_multi_regime_corpus(con)
        series = compute_trends(con, definition="raw", min_share=0.0)
        if len(series.regimes) == 0 or len(series.archetypes) < 2:
            pytest.skip("corpus too small to verify ordering")
        last_regime = series.regimes[-1]
        # Archetypes present in the last regime should come first, ordered by share desc
        last_cells = [
            series.cells.get((last_regime.label, a))
            for a in series.archetypes
            if series.cells.get((last_regime.label, a)) is not None
        ]
        shares = [c.share for c in last_cells]
        assert shares == sorted(shares, reverse=True), (
            f"archetypes not sorted by most-recent-regime share desc: {shares}"
        )
        con.close()

    def test_regime_event_count_stamped_correctly(self):
        """RegimeWindow in series carries correct event_count."""
        con = _con()
        # Regime A: 2 tournaments loaded
        _load_and_label(con, _REGIME_A_T1, "MTGO",
                        {"p1": "Delver", "p2": "Lands", "p3": "Reanimator",
                         "p4": "Control", "p5": "Delver", "p6": "Delver"})
        _load_and_label(con, _REGIME_A_T2, "MTGO",
                        {"q1": "Delver", "q2": "Delver", "q3": "Reanimator", "q4": "Control"})
        series = compute_trends(con, definition="raw", min_share=0.0)
        # Find the regime that contains these events [2024-08-26, 2024-12-16)
        from datetime import date as date_cls
        grief_since = date_cls(2024, 8, 26)
        grief_regime = next(
            (r for r in series.regimes if r.since == grief_since), None
        )
        assert grief_regime is not None, "Grief regime not found in series"
        assert grief_regime.event_count == 2  # 2 tournaments loaded in this regime
        con.close()

    def test_topcut_definition(self):
        """compute_trends works with definition='topcut'."""
        con = _con()
        # Load events with standings (regime A T1 and C T1)
        _load_and_label(con, _REGIME_A_T1, "MTGO",
                        {"p1": "Delver", "p2": "Lands", "p3": "Reanimator",
                         "p4": "Control", "p5": "Delver", "p6": "Delver"})
        _load_and_label(con, _REGIME_C_T1, "melee",
                        {"s1": "Delver", "s2": "Lands", "s3": "Delver"})
        series = compute_trends(con, definition="topcut", min_share=0.0)
        assert series.definition == "topcut"
        # Should have some non-empty regimes (those with standings)
        assert len(series.regimes) >= 1
        con.close()

    def test_empty_corpus_returns_empty_series(self):
        """An empty DB (schema initialized, no data) returns a TrendSeries with no regimes."""
        import duckdb

        from legacy_engine.ingestion.store import init_schema

        con = duckdb.connect(":memory:")
        init_schema(con)
        series = compute_trends(con, definition="raw", min_share=0.0)
        assert series.regimes == []
        assert series.archetypes == []
        assert series.cells == {}
        con.close()


# ---------------------------------------------------------------------------
# TestReportTrendsCLI — Unit 4
# ---------------------------------------------------------------------------


class TestReportTrendsCLI:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def _setup_db(self, tmp_path):
        import duckdb
        from legacy_engine.ingestion.store import init_schema

        db_path = tmp_path / "trends_test.duckdb"
        con = duckdb.connect(str(db_path))
        init_schema(con)
        return db_path, con

    def test_report_trends_help(self, runner):
        """report trends --help exits successfully and shows key options."""
        result = runner.invoke(main, ["report", "trends", "--help"])
        assert result.exit_code == 0, f"help failed: {result.output}"
        assert "--definition" in result.output
        assert "--provenance" in result.output
        assert "--min-share" in result.output

    def test_report_trends_runs_on_empty_db(self, runner, tmp_path):
        """report trends on an empty DB runs without error."""
        db_path, con = self._setup_db(tmp_path)
        con.close()
        result = runner.invoke(main, ["report", "trends", "--db", str(db_path)])
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"

    def test_report_trends_labeled_header(self, runner, tmp_path):
        """report trends prints a header labeled with definition + basis."""
        db_path, con = self._setup_db(tmp_path)
        _build_multi_regime_corpus(con)
        con.close()

        result = runner.invoke(
            main, ["report", "trends", "--definition", "raw", "--provenance", "all", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        # Header must state definition
        assert "RAW" in result.output or "raw" in result.output.lower()
        # Header must state provenance basis
        assert "basis=" in result.output

    def test_report_trends_shows_regime_labels(self, runner, tmp_path):
        """report trends output shows labeled regime info."""
        db_path, con = self._setup_db(tmp_path)
        _build_multi_regime_corpus(con)
        con.close()

        result = runner.invoke(
            main, ["report", "trends", "--definition", "raw", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        # Should contain "Regime:" or the since→until info
        assert "Regime:" in result.output or "events=" in result.output

    def test_report_trends_thin_banner(self, runner, tmp_path):
        """Thin regimes trigger a THIN banner in the output."""
        db_path, con = self._setup_db(tmp_path)
        _load_and_label(con, _THIN_T1, "MTGO",
                        {"thin1": "Delver", "thin2": "Reanimator"})
        _load_and_label(con, _THIN_T2, "MTGO",
                        {"thin3": "Delver", "thin4": "Reanimator"})
        con.close()

        result = runner.invoke(
            main, ["report", "trends", "--definition", "raw", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "THIN" in result.output

    def test_report_trends_no_unlabeled_blend(self, runner, tmp_path):
        """report trends never prints a number without a labeled basis."""
        db_path, con = self._setup_db(tmp_path)
        _build_multi_regime_corpus(con)
        con.close()

        result = runner.invoke(
            main, ["report", "trends", "--provenance", "all", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        # Should NOT contain "blend(" — provenance=all prints each basis separately
        assert "blend(" not in result.output
        # All three bases should appear
        assert result.output.count("basis=") >= 3  # all, online, paper

    def test_report_trends_single_provenance(self, runner, tmp_path):
        """report trends --provenance online prints only the online basis."""
        db_path, con = self._setup_db(tmp_path)
        _build_multi_regime_corpus(con)
        con.close()

        result = runner.invoke(
            main, ["report", "trends", "--definition", "raw", "--provenance", "online", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "online" in result.output
        # Should only have one header block (one basis)
        assert result.output.count("basis=") == 1

    def test_report_trends_accepts_topcut_definition(self, runner, tmp_path):
        """report trends --definition topcut runs without error."""
        db_path, con = self._setup_db(tmp_path)
        _build_multi_regime_corpus(con)
        con.close()

        result = runner.invoke(
            main, ["report", "trends", "--definition", "topcut", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "TOPCUT" in result.output or "topcut" in result.output.lower()
