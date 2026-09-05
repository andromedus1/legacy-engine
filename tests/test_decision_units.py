from __future__ import annotations

from pathlib import Path

import pytest

from legacy_engine.advisory import decision_units
from legacy_engine.ingestion import store


def _cell(opponent: str, mean: float, *, n: int = 12, share: float = 0.5, prior: float = 0.0) -> dict:
    return {
        "opponent": opponent,
        "mean": mean,
        "n": n,
        "share": share,
        "prior_contribution_fraction": prior,
    }


def _row(subject: str, cells: list[dict], *, share: float = 0.3, parent: str | None = None, camp: str | None = None) -> dict:
    return {
        "subject": subject,
        "parent": parent,
        "camp": camp,
        "field_share": share,
        "decision": {"field_share": share, "cells": cells},
    }


def test_crossing_profiles_measure_pure_pooling_uplift_and_keep_n0_visible():
    parent = _row("Parent", [_cell("Opp A", 0.50), _cell("Opp B", 0.50, n=0, prior=1.0)])
    camp_a = _row("Parent [A]", [_cell("Opp A", 0.80), _cell("Opp B", 0.20)], parent="Parent", camp="A")
    camp_b = _row("Parent [B]", [_cell("Opp A", 0.20), _cell("Opp B", 0.80)], parent="Parent", camp="B")

    result = decision_units.compare_build_floors(parent, [camp_a, camp_b], {"Parent": 0.2, "Opp A": 0.4, "Opp B": 0.4})

    assert result["common_opponents"] == ["Opp A", "Opp B"]
    assert result["pooling_uplift"] == pytest.approx(0.30)
    assert result["weighted_camp_floor"] == pytest.approx(0.20)
    assert result["mixed_vector_floor"] == pytest.approx(0.50)
    assert result["parent_minus_weighted_camp_floor"] == pytest.approx(0.30)
    assert result["n0_cells_visible"] is True
    assert {camp["direct_n"] for camp in result["camps"]} == {12}


def test_parent_is_excluded_and_missing_opponents_are_not_zero_filled():
    parent = _row("Parent", [_cell("Parent", 0.01), _cell("Opp A", 0.6), _cell("Opp B", 0.4)])
    camp_a = _row("Parent [A]", [_cell("Parent", 0.1), _cell("Opp A", 0.7), _cell("Opp B", 0.3)], parent="Parent")
    camp_b = _row("Parent [B]", [_cell("Parent", 0.9), _cell("Opp A", 0.5)], parent="Parent")

    result = decision_units.compare_build_floors(parent, [camp_a, camp_b], {"Parent": 0.2, "Opp A": 0.3, "Opp B": 0.5})

    assert result["common_opponents"] == ["Opp A"]
    assert result["missing_opponents"] == ["Opp B"]
    assert result["external_opponent_count"] == 2
    assert result["modeled_parent_coverage"] == pytest.approx(0.3 / 0.8)
    assert result["available"] is True


def test_floor_comparison_degrades_honestly_without_weighted_common_cells():
    parent = _row("Parent", [_cell("Opp", 0.5)])
    camp = _row("Parent [A]", [], share=0.0, parent="Parent")
    result = decision_units.compare_build_floors(parent, [camp], {"Parent": 0.5, "Opp": 0.5})
    assert result["available"] is False
    assert "pooling_uplift" not in result
    assert "unavailable_reason" in result


def _analysis_blob() -> dict:
    return {
        "meta": {"deck_rankings": {"field": {"shares": {"P": 0.2, "O": 0.8}}}},
        "arch": [_row("P", [_cell("O", 0.5)], share=0.2)],
        "camps": [
            _row("P [A]", [_cell("O", 0.7)], share=0.1, parent="P", camp="A"),
            _row("P [B]", [_cell("O", 0.3)], share=0.1, parent="P", camp="B"),
        ],
    }


def _build_analysis_db():
    con = store.connect(":memory:")
    store.init_schema(con)
    con.executemany(
        "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("t1", "one", "2026-08-11", "", "Legacy", "MTGO", "online"),
            ("t2", "two", "2026-08-12", "", "Legacy", "MTGO", "online"),
            ("t3", "future", "2026-09-01", "", "Legacy", "MTGO", "online"),
        ],
    )
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("t1", 0, " Alice ", "", "P", "A"),
            ("t1", 1, "Bob", "", "P", "B"),
            ("t2", 0, "alice", "", "P", "A"),
            ("t2", 1, "Bob", "", "P", "B"),
            ("t3", 0, "future", "", "P", "B"),
        ],
    )
    con.executemany(
        "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
        [
            ("t1", 0, "main", "A Card", 4), ("t1", 0, "side", "A Side", 2),
            ("t1", 1, "main", "B Card", 4), ("t1", 1, "side", "B Side", 3),
            ("t2", 0, "main", "A Card", 2), ("t2", 0, "side", "A Side", 1),
            # t2/B intentionally has no card records: its coverage remains visible.
            ("t3", 0, "main", "Future Card", 4),
        ],
    )
    return con


def test_analysis_is_cutoff_bounded_and_keeps_main_side_and_source_scoped_pilots():
    con = _build_analysis_db()
    try:
        result = decision_units.analyze_decision_units(
            con, _analysis_blob(), since="2026-08-10", until="2026-08-20",
        )
    finally:
        con.close()
    parent = result["parents"][0]
    assert parent["current_list_count"] == 4
    composition = parent["composition"]
    pair = composition["camp_pairs"][0]
    assert pair["main"]["slot_distance"] is not None
    assert pair["side"]["slot_distance"] is not None
    assert pair["main"]["slot_distance"] != pair["side"]["slot_distance"]
    assert pair["side"]["card_lists_b"] == 1
    assert pair["side"]["list_count_b"] == 2
    assert pair["side"]["card_coverage_b"] == pytest.approx(0.5)
    # Alice/alice is one normalized pilot in the source-scoped set; Bob is distinct.
    assert pair["pilot_overlap"]["jaccard"] == 0.0
    assert pair["pilot_overlap"]["scope"] == "source + normalize_player(handle)"
    assert result["window"] == {"since": "2026-08-10", "until": "2026-08-20", "until_exclusive": True}


def test_analysis_has_no_parent_diagnostic_without_two_camps_and_validates_dates():
    con = store.connect(":memory:")
    store.init_schema(con)
    try:
        blob = {"meta": {}, "arch": [_row("P", [])], "camps": []}
        result = decision_units.analyze_decision_units(con, blob, since="2026-01-01", until="2026-01-02")
    finally:
        con.close()
    assert result["summary"]["parents_analyzed"] == 0
    with pytest.raises(ValueError, match="after since"):
        decision_units.analyze_decision_units(con, blob, since="2026-01-02", until="2026-01-01")


def test_template_contains_escaped_build_disclosure_and_cli_defaults_are_report_bound():
    template = Path("scripts/best_call_ranking_template.html").read_text()
    assert "decisionUnitHtml" in template
    assert "escT(label)" in template
    from scripts.analyze_decision_units import _default_window

    assert _default_window({"meta": {"field_since": "2026-01-01", "corpus_max": "2026-01-10"}}) == (
        "2026-01-01", "2026-01-11",
    )


def test_template_escapes_decision_unit_camp_and_opponent_labels():
    from tests.test_refresh_best_call_ranking import _run_template_javascript

    unsafe_camp = "<img src=x onerror=alert(1)>"
    blob = {
        "meta": {"corpus_max": "2026-01-10", "field_since": "2026-01-01"},
        "arch": [{
            "subject": "P", "_idx": 0,
            "decision": {
                "active": True, "eligible": True, "performance": .5, "floor": .4,
                "performance_low": .3, "performance_high": .7, "floor_low": .2,
                "floor_high": .6, "worst_low": .2, "worst_high": .6,
                "field_share": .2, "coverage": 1, "cells": [],
            },
            "decision_units": {
                "floor_comparison": {
                    "available": True, "modeled_parent_coverage": 1,
                    "pooling_uplift": .1, "parent_minus_weighted_camp_floor": .2,
                    "camp_weights": {f"P [{unsafe_camp}]": 1},
                    "camps": [{
                        "camp": f"P [{unsafe_camp}]", "floor": .3,
                        "toughest_pairing": {"opponent": "<unsafe opponent>", "n": 0},
                    }],
                },
                "composition": {"camps": [{"camp": f"P [{unsafe_camp}]", "list_count": 1}], "camp_pairs": []},
            },
        }],
        "camps": [{"subject": f"P [{unsafe_camp}]", "_idx": 0, "decision": {"active": True, "eligible": True, "cells": []}}],
        "plans": [],
    }
    rendered = _run_template_javascript(blob, "decisionUnitHtml(D.arch[0])")
    assert "<img" not in rendered
    assert "&lt;img src=x onerror=alert(1)&gt;" in rendered
    assert "&lt;unsafe opponent&gt;" in rendered
