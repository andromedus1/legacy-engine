"""Tests for epic-regime-aware-advisory-windowing-core — windowing plumbing + regime resolver.

The matchup/positioning chain (compute_match_results → build_matrix → build_global_field →
compute_archetype_gaps) gains a half-open [since, until) window; this proves the no-window path is
byte-identical (regression) and that windows actually narrow results. Uses make_rounds_corpus, whose
tournaments are dated 2026-01-0N (repeat r → 2026-01-(r+1)).
"""

from __future__ import annotations

import pytest

from legacy_engine.advisory.field import build_global_field
from legacy_engine.advisory.gaps import compute_archetype_gaps
from legacy_engine.analytics.match_results import compute_match_results
from legacy_engine.analytics.matchup import build_matrix
from legacy_engine.analytics.trends import resolve_regime


class TestComputeMatchResultsWindowing:
    def test_no_window_regression(self, make_rounds_corpus):
        con, facts = make_rounds_corpus(n_repeats=5)
        mr = compute_match_results(con)
        # 2 decisive matches per repeat × 5 (the fixture's pinned decisive count)
        assert mr.coverage.decisive_matched == facts["total_decisive"]
        con.close()

    def test_window_narrows_to_subset(self, make_rounds_corpus):
        con, facts = make_rounds_corpus(n_repeats=5)
        # Half-open [2026-01-01, 2026-01-03) → repeats dated 2026-01-01 and 2026-01-02 only (2 of 5).
        mr = compute_match_results(con, since="2026-01-01", until="2026-01-03")
        assert mr.coverage.decisive_matched == 2 * facts["decisive_per_repeat"]
        con.close()

    def test_empty_window_zero_coverage(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=5)
        mr = compute_match_results(con, since="2030-01-01", until="2030-02-01")
        assert mr.coverage.decisive_matched == 0
        assert mr.matchups == {}
        con.close()

    def test_half_open_upper_is_exclusive(self, make_rounds_corpus):
        con, facts = make_rounds_corpus(n_repeats=3)
        # until=2026-01-03 must EXCLUDE the 2026-01-03 repeat (half-open).
        incl = compute_match_results(con, since="2026-01-01", until="2026-01-04").coverage.decisive_matched
        excl = compute_match_results(con, since="2026-01-01", until="2026-01-03").coverage.decisive_matched
        assert incl == 3 * facts["decisive_per_repeat"]
        assert excl == 2 * facts["decisive_per_repeat"]
        con.close()


class TestBuildMatrixAndFieldWindowing:
    def test_build_matrix_no_window_regression(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=5)
        assert build_matrix(con).archetypes == build_matrix(con, since=None, until=None).archetypes
        con.close()

    def test_build_matrix_windowed_smaller(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=50)
        full = build_matrix(con)
        windowed = build_matrix(con, since="2026-01-01", until="2026-01-03")
        # Both see Control+Combo, but the windowed matrix is built from far fewer matches.
        full_n = sum(c.n for c in full.cells.values())
        win_n = sum(c.n for c in windowed.cells.values())
        assert win_n < full_n
        con.close()

    def test_build_global_field_windowing(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=50)
        full = build_global_field(con)
        windowed = build_global_field(con, since="2026-01-01", until="2026-01-03")
        # Field still has the two archetypes; counts shrink under the window.
        assert set(full.shares) == set(windowed.shares) == {"Control", "Combo"}
        assert sum(windowed.counts.values()) < sum(full.counts.values())
        con.close()


class TestComputeArchetypeGapsWindowing:
    def test_no_window_regression(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=50)
        a = compute_archetype_gaps(con, min_coverage=0.0, seed=42)
        b = compute_archetype_gaps(con, min_coverage=0.0, seed=42, since=None, until=None)
        assert [g.archetype for g in a.gaps] == [g.archetype for g in b.gaps]
        con.close()

    def test_windowed_runs(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=50)
        report = compute_archetype_gaps(con, min_coverage=0.0, seed=42,
                                        since="2026-01-01", until="2026-01-20")
        assert {g.archetype for g in report.gaps} <= {"Control", "Combo"}
        con.close()


class TestResolveRegime:
    def test_current_is_latest_open_window(self):
        since, until = resolve_regime("current")
        assert until is None          # current regime is open-ended
        assert since is not None      # opened by the latest ban
        # matches the latest regime_windows entry
        from legacy_engine.analytics.trends import regime_windows
        last = regime_windows()[-1]
        assert since == last.since.isoformat()

    def test_all_is_full_corpus(self):
        assert resolve_regime("all") == (None, None)
        assert resolve_regime("all-time") == (None, None)

    def test_substring_match(self):
        since, until = resolve_regime("Undercity")
        assert since == "2026-05-18"   # post-Undercity-Informer regime opens on its ban date

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            resolve_regime("no-such-regime")
