"""Local reports must make their field comparison and evidence basis visible."""
from tests.test_refresh_best_call_ranking import _run_template_javascript


def test_local_report_shows_calls_both_shares_and_effective_sample_basis():
    decision = {
        "active": True, "eligible": True, "performance": .6, "floor": .4,
        "performance_low": .5, "performance_high": .7, "floor_low": .3,
        "floor_high": .5, "worst_low": .3, "worst_high": .5,
        "field_share": .3, "global_field_share": .1, "coverage": 1,
        "worst_opponent": "B", "cells": [],
    }
    calls = {"global": {"performance": "A", "floor": "B"},
             "scenario": {"performance": "B", "floor": "A"}}
    blob = {
        "meta": {"corpus_max": "2026-09-03", "field_since": "2026-08-10",
                 "field_scenario": {"label": "Expected room", "count_basis": "declared-effective-concentration",
                                    "declared_effective_n": 2, "supplied_total": None,
                                    "global_vs_scenario": {"arch": calls, "camps": calls}}},
        "arch": [{"subject": "A", "decision": decision}], "camps": [],
        "plans": [{"id": "go-off", "label": "Combo", "field_share": 1,
                   "scenario_unavailable": "custom plan estimates unavailable", "decision": None}],
    }
    result = _run_template_javascript(blob, "({caption:document.getElementById('scenario-caption').textContent, comparison:document.getElementById('scenario-comparison').textContent, camps:document.getElementById('camp-scenario-comparison').textContent, plans:document.getElementById('t-plan').innerHTML, planCaption:document.getElementById('plan-caption').textContent, tooltip:mapTooltipHtml(D.arch[0]), table:document.getElementById('t-arch').innerHTML})")
    assert "effective sample 2" in result["caption"]
    assert "shares only" not in result["caption"]
    assert "Performance A → B" in result["comparison"]
    assert "Floor B → A" in result["comparison"]
    assert result["camps"] == result["comparison"]
    assert "<td>100.0%</td>" in result["plans"]
    assert "100.0% of this field" in result["planCaption"]
    assert "Global share 10.0%" in result["tooltip"]
    assert "30.0%<small>Global 10.0%</small>" in result["table"]
