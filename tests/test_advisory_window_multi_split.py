"""Tests for the multi-split composition layer (feature-multi-split-matrix Unit 4).

``build_multi_split_inputs`` is a NEW entry point beside ``build_advisory_inputs`` — same
``WindowResolution`` mode dispatch, same audit conventions, but a rectangular
``MultiSplitMatrix`` return shape that the ~15 spine call sites deliberately never see. Covered
here: mode dispatch (adaptive / uniform / full), the audit lines each mode emits, the end-to-end
``ranking_view()`` -> ``rank_decks`` cross-camp P(best) path, and ``staged_split_parents`` over a
tmp registry.

Hermetic only — the corpus + era fixture come from ``test_matchup_multi_split``.
"""

from __future__ import annotations

import json

import pytest

from legacy_engine.advisory.field import build_custom_field
from legacy_engine.advisory.positioning import rank_decks
from legacy_engine.advisory.window import (
    MultiSplitAdvisoryInputs,
    WindowResolution,
    build_multi_split_inputs,
    resolve_advisory_window,
)
from legacy_engine.analytics.matchup import MultiSplitMatrix
from legacy_engine.archetype.discovered import staged_split_parents

from test_match_results_multi_split import (  # noqa: E402  (sibling test module, sys.path via rootdir)
    LATE_DATE,
    PARENTS,
    two_parent_con,
)
from test_matchup_multi_split import (  # noqa: E402
    MID_DATE,
    adaptive_con,
)

_ADAPTIVE = WindowResolution(None, None, None, "adaptive", mode="adaptive")
_UNIFORM = WindowResolution(LATE_DATE, None, None, f"{LATE_DATE}..—", mode="uniform")
_FULL = WindowResolution(None, None, None, "full-corpus", mode="full")


def _multi_line(inputs) -> str:
    return next(line for line in inputs.audit if line.startswith("// multi-split:"))


class TestModeDispatch:
    def test_adaptive_mode_carries_the_adaptive_matrix_and_era_audit(self):
        con = adaptive_con()
        inputs = build_multi_split_inputs(con, _ADAPTIVE, parents=PARENTS)
        con.close()
        assert isinstance(inputs, MultiSplitAdvisoryInputs)
        assert isinstance(inputs.multi, MultiSplitMatrix)
        assert inputs.adaptive is not None
        assert inputs.adaptive.multi is inputs.multi
        assert inputs.field_until is None

        adaptive_line = next(line for line in inputs.audit if line.startswith("// adaptive:"))
        assert f"Doomsday since {LATE_DATE}" in adaptive_line
        assert f"Doomsday [Murktide] since {MID_DATE}" in adaptive_line
        assert "ban-only" in adaptive_line
        assert any(line.startswith("// field: since ") for line in inputs.audit)

    def test_uniform_mode_windows_both_legs_and_skips_era_audit(self):
        con = adaptive_con()
        inputs = build_multi_split_inputs(con, _UNIFORM, parents=PARENTS)
        con.close()
        assert inputs.adaptive is None
        assert (inputs.field_since, inputs.field_until) == (LATE_DATE, None)
        assert not any(line.startswith("// adaptive:") for line in inputs.audit)
        assert inputs.audit == (_multi_line(inputs),)

    def test_uniform_mode_matrix_equals_the_direct_windowed_build(self):
        from legacy_engine.analytics.matchup import build_multi_split_matrix

        con = adaptive_con()
        inputs = build_multi_split_inputs(con, _UNIFORM, parents=PARENTS)
        direct = build_multi_split_matrix(con, parents=PARENTS, since=LATE_DATE)
        con.close()
        assert inputs.multi.cells.keys() == direct.cells.keys()
        assert inputs.multi.subjects == direct.subjects

    def test_full_mode_is_the_full_corpus_matrix(self):
        from legacy_engine.analytics.matchup import build_multi_split_matrix

        con = adaptive_con()
        inputs = build_multi_split_inputs(con, _FULL, parents=PARENTS)
        direct = build_multi_split_matrix(con, parents=PARENTS)
        con.close()
        assert inputs.adaptive is None
        assert (inputs.field_since, inputs.field_until) == (None, None)
        assert inputs.multi.subjects == direct.subjects
        assert inputs.multi.total_matches == direct.total_matches

    def test_no_era_data_preamble_reaches_the_audit(self):
        con = two_parent_con()
        inputs = build_multi_split_inputs(con, _ADAPTIVE, parents=PARENTS)
        con.close()
        assert inputs.audit[0] == "// eras: no era data — ban-only horizons; run `eras run`"

    def test_provenance_and_min_row_share_thread_through(self):
        con = adaptive_con()
        inputs = build_multi_split_inputs(
            con, _FULL, parents=PARENTS, provenance="online", min_row_share=0.0,
        )
        con.close()
        assert inputs.multi.provenance == "online"
        assert "Elves" in inputs.multi.subjects  # fringe row only clears a 0.0 floor

    def test_resolve_advisory_window_composes_with_the_entry_point(self):
        """The advisory-window-resolution-block shape: resolve → build, no bespoke window logic."""
        con = adaptive_con()
        win = resolve_advisory_window(con)
        inputs = build_multi_split_inputs(con, win, parents=PARENTS)
        con.close()
        assert win.mode == "adaptive"
        assert inputs.adaptive is not None


class TestMultiSplitAuditLine:
    def test_line_counts_parents_and_camp_rows(self):
        con = adaptive_con()
        inputs = build_multi_split_inputs(con, _FULL, parents=PARENTS)
        con.close()
        n_camps = sum(1 for s in inputs.multi.subjects if s in inputs.multi.camp_parent)
        assert n_camps == 6  # 3 camps each for Doomsday and Painter
        assert _multi_line(inputs) == f"// multi-split: 2 parents, {n_camps} camp rows"

    def test_line_is_present_in_every_mode(self):
        con = adaptive_con()
        for win in (_ADAPTIVE, _UNIFORM, _FULL):
            inputs = build_multi_split_inputs(con, win, parents=PARENTS)
            assert _multi_line(inputs).startswith("// multi-split: ")
        con.close()

    def test_no_parents_reports_zero(self):
        con = adaptive_con()
        inputs = build_multi_split_inputs(con, _FULL, parents=[])
        con.close()
        assert _multi_line(inputs) == "// multi-split: 0 parents, 0 camp rows"


class TestCrossCampRanking:
    """The payoff: one shared-field MC over camps AND unsplit archetypes → comparable P(best)."""

    def test_rank_decks_over_the_adaptive_ranking_view(self):
        con = adaptive_con()
        inputs = build_multi_split_inputs(con, _ADAPTIVE, parents=PARENTS)
        con.close()
        field = build_custom_field(
            {"Doomsday": 0.4, "Painter": 0.3, "Control": 0.2, "Delver": 0.1},
            counts={"Doomsday": 120, "Painter": 90, "Control": 60, "Delver": 30},
        )
        candidates = list(inputs.multi.subjects)
        ranking = rank_decks(inputs.multi.ranking_view(), field, candidates, n_draws=200, seed=11)
        assert set(ranking.decks) == set(candidates)
        # Camps and unsplit archetypes ranked in ONE call, so P(best) is comparable across them.
        assert any(d in inputs.multi.camp_parent for d in ranking.decks)
        assert any(d not in inputs.multi.camp_parent for d in ranking.decks)
        assert sum(ranking.p_best.values()) == pytest.approx(1.0, abs=1e-6)

        again = rank_decks(inputs.multi.ranking_view(), field, candidates, n_draws=200, seed=11)
        assert again.p_best == ranking.p_best


class TestStagedSplitParents:
    def _write_registry(self, path, splits: list[dict]) -> None:
        path.write_text(json.dumps({"version": "1", "splits": splits}) + "\n")

    def _record(self, parent: str, status: str = "candidate") -> dict:
        return {
            "parent": parent, "generated_from": "test", "params": {},
            "camps": [], "stability": 0.9, "status": status,
        }

    def test_returns_candidate_parents_sorted_and_deduped(self, tmp_path):
        path = tmp_path / "discovered.json"
        self._write_registry(path, [self._record("Painter"), self._record("Doomsday")])
        assert staged_split_parents(path) == ["Doomsday", "Painter"]

    def test_promoted_splits_are_excluded(self, tmp_path):
        path = tmp_path / "discovered.json"
        self._write_registry(
            path, [self._record("Painter"), self._record("Doomsday", status="promoted")],
        )
        assert staged_split_parents(path) == ["Painter"]

    def test_missing_file_is_empty(self, tmp_path):
        assert staged_split_parents(tmp_path / "nope.json") == []

    def test_empty_registry_is_empty(self, tmp_path):
        path = tmp_path / "discovered.json"
        self._write_registry(path, [])
        assert staged_split_parents(path) == []

    def test_malformed_registry_fails_loudly(self, tmp_path):
        path = tmp_path / "discovered.json"
        path.write_text("{not json")
        with pytest.raises(ValueError, match="malformed staging registry"):
            staged_split_parents(path)

    def test_output_feeds_the_builder_directly(self, tmp_path):
        """``staged_split_parents`` -> ``parents=`` is the whole contract with the matrix."""
        path = tmp_path / "discovered.json"
        self._write_registry(path, [self._record(p) for p in PARENTS])
        con = adaptive_con()
        inputs = build_multi_split_inputs(con, _FULL, parents=staged_split_parents(path))
        con.close()
        assert inputs.multi.parents == sorted(PARENTS)
