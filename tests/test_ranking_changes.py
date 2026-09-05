"""Focused contracts for published Deck Rankings refresh explanations."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from legacy_engine.advisory.ranking_changes import (
    compare_ranking_snapshots,
    ranking_snapshot,
)


def _blob(
    shares: dict[str, float],
    cells: dict[str, dict[str, float]],
    *,
    date: str = "2026-01-31",
    method: str = "deck-rankings-v1",
    regime: str | None = "Entomb",
    performance_call: str | None = "Alpha",
    floor_call: str | None = "Alpha",
    observed_field_n: int = 100,
) -> dict:
    rows = []
    for subject, means in cells.items():
        floor_opponent = min(means, key=means.get) if means else None
        rows.append({
            "subject": subject,
            "decision": {
                "eligible": True,
                "field_share": shares.get(subject, 0.0),
                "performance": sum(shares.get(opponent, 0.0) * mean for opponent, mean in means.items()),
                "floor": min(means.values()) if means else None,
                "worst_opponent": floor_opponent,
                "cells": [
                    {"opponent": opponent, "mean": mean}
                    for opponent, mean in means.items()
                ],
            },
        })
    return {
        "meta": {
            "field_since": "2026-01-01",
            "corpus_max": date,
            "observed_field_n": observed_field_n,
            "regime_card": regime,
            "deck_rankings": {
                "method_id": method,
                "performance_call": performance_call,
                "floor_call": floor_call,
                "field": {"shares": shares},
            },
        },
        "arch": rows,
    }


def _snap(**kwargs) -> dict:
    return ranking_snapshot(_blob(**kwargs))


def _script_module():
    path = Path(__file__).parents[1] / "scripts" / "refresh_best_call_ranking.py"
    spec = importlib.util.spec_from_file_location("refresh_ranking_for_changes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_snapshot_captures_global_inputs_and_implicit_mirrors():
    snapshot = _snap(
        shares={"Alpha": 0.6, "Beta": 0.4},
        cells={"Alpha": {"Beta": 0.55}, "Beta": {"Alpha": 0.45}},
    )

    assert snapshot["scenario"] == "global"
    assert snapshot["field_shares"] == {"Alpha": 0.6, "Beta": 0.4}
    assert snapshot["eligible_candidates"] == ["Alpha", "Beta"]
    assert snapshot["calls"] == {"performance": "Alpha", "floor": "Alpha"}
    assert snapshot["cell_means"]["Alpha"] == {"Beta": 0.55}


def test_custom_field_snapshots_bind_refresh_comparison_to_scenario_identity():
    blob = _blob(
        shares={"Alpha": 0.6, "Beta": 0.4},
        cells={"Alpha": {"Beta": 0.55}, "Beta": {"Alpha": 0.45}},
    )
    blob["meta"]["field_scenario"] = {
        "kind": "custom", "label": "Saved room", "source_sha256": "source-a",
        "shares": {"Alpha": 0.6, "Beta": 0.4},
    }
    same = ranking_snapshot(blob)
    changed = dict(blob)
    changed["meta"] = {**blob["meta"], "field_scenario": {
        **blob["meta"]["field_scenario"], "source_sha256": "source-b",
    }}
    other = ranking_snapshot(changed)

    assert same["scenario"].startswith("custom:")
    assert same["scenario"] != other["scenario"]
    result = compare_ranking_snapshots(other, same)
    assert result["status"] == "incompatible"
    assert "scenario" in result["reason"]


def test_first_and_same_data_publications_are_honest():
    first = _snap(
        shares={"Alpha": 0.6, "Beta": 0.4},
        cells={"Alpha": {"Beta": 0.55}, "Beta": {"Alpha": 0.45}},
    )
    baseline = compare_ranking_snapshots(first, None)
    assert baseline["status"] == "baseline"
    assert baseline["insights"][0]["type"] == "baseline"

    later = _snap(
        shares={"Alpha": 0.6, "Beta": 0.4},
        cells={"Alpha": {"Beta": 0.55}, "Beta": {"Alpha": 0.45}},
        date="2026-02-01",
    )
    unchanged = compare_ranking_snapshots(later, first)
    assert unchanged["status"] == "unchanged"
    assert "elapsed" not in unchanged["insights"][0]["text"]
    assert unchanged["comparison"] == {
        "from": "2026-01-31", "to": "2026-02-01", "field_since": "2026-01-01",
    }


def test_zero_previous_observed_field_suppresses_movement():
    previous = _snap(
        shares={"Alpha": 1.0},
        cells={"Alpha": {}},
        observed_field_n=0,
    )
    current = _snap(
        shares={"Alpha": 1.0},
        cells={"Alpha": {}},
        date="2026-02-01",
    )
    result = compare_ranking_snapshots(current, previous)

    assert result["status"] == "unavailable"
    assert result["insights"][0]["type"] == "unavailable"
    assert "zero observed field" in result["reason"]


@pytest.mark.parametrize(
    ("field", "old", "new"),
    [
        ("method", "deck-rankings-v1", "deck-rankings-v2"),
        ("regime", "Entomb", "Griselbrand"),
        ("scenario", "global", "custom"),
    ],
)
def test_incompatible_snapshots_name_the_boundary(field, old, new):
    kwargs = {
        "shares": {"Alpha": 0.6, "Beta": 0.4},
        "cells": {"Alpha": {"Beta": 0.55}, "Beta": {"Alpha": 0.45}},
    }
    previous = _snap(**kwargs, **({"method": old} if field == "method" else {}), **({"regime": old} if field == "regime" else {}))
    current_blob = _blob(**kwargs, **({"method": new} if field == "method" else {}), **({"regime": new} if field == "regime" else {}))
    if field == "scenario":
        current_blob["meta"]["scenario"] = new
    current = ranking_snapshot(current_blob)
    if field == "scenario":
        previous_blob = _blob(**kwargs)
        previous_blob["meta"]["scenario"] = old
        previous = ranking_snapshot(previous_blob)
    result = compare_ranking_snapshots(current, previous)
    assert result["status"] == "incompatible"
    assert field in result["reason"]
    assert "new baseline" in result["insights"][0]["text"]


def test_change_reports_field_movement_beneficiary_and_symmetric_attribution():
    previous = _snap(
        shares={"Alpha": 0.5, "Beta": 0.5},
        cells={"Alpha": {"Beta": 0.50}, "Beta": {"Alpha": 0.50}},
    )
    current = _snap(
        shares={"Alpha": 0.7, "Beta": 0.3},
        cells={"Alpha": {"Beta": 0.60}, "Beta": {"Alpha": 0.40}},
        performance_call="Alpha",
        floor_call="Beta",
        date="2026-02-01",
    )
    result = compare_ranking_snapshots(current, previous)
    by_type = {insight["type"]: insight for insight in result["insights"]}

    assert result["status"] == "changed"
    assert len(result["insights"]) <= 3
    assert set(by_type) == {"field_movement", "beneficiary", "recommendation"}
    beneficiary = by_type["beneficiary"]["evidence"]
    assert beneficiary["candidate"] == "Alpha"
    assert beneficiary["field_contribution"] + beneficiary["matchup_contribution"] == pytest.approx(
        beneficiary["performance_delta"]
    )
    assert "field weights contributed" in by_type["beneficiary"]["text"]
    assert "floor call Alpha → Beta" in by_type["recommendation"]["text"]


def test_missing_new_opponent_forecast_is_explicit_and_never_imputed():
    previous = _snap(
        shares={"Alpha": 1.0},
        cells={"Alpha": {}},
    )
    current = _snap(
        shares={"Alpha": 0.7, "Beta": 0.3},
        cells={"Alpha": {}},
        date="2026-02-01",
    )
    result = compare_ranking_snapshots(current, previous)

    assert result["status"] == "unavailable"
    assert result["unavailable_attributions"]
    missing = result["unavailable_attributions"][0]
    assert missing["available"] is False
    assert missing["missing_opponents"] == ["Beta"]
    assert "missing matchup forecast" in result["reason"]
    assert all("imput" not in str(insight).lower() for insight in result["insights"])


def test_fixed_support_floor_movement_has_no_field_weight_attribution():
    previous = _snap(
        shares={"Alpha": 0.5, "Beta": 0.5},
        cells={"Alpha": {"Beta": 0.50}, "Beta": {"Alpha": 0.50}},
    )
    current = _snap(
        shares={"Alpha": 0.9, "Beta": 0.1},
        cells={"Alpha": {"Beta": 0.55}, "Beta": {"Alpha": 0.50}},
        floor_call="Beta",
        date="2026-02-01",
    )
    result = compare_ranking_snapshots(current, previous)
    recommendation = next(i for i in result["insights"] if i["type"] == "recommendation")
    floor_evidence = recommendation["evidence"]["calls"]["floor"]
    assert floor_evidence["support_changed"] is False
    assert "minimum pairing" in recommendation["text"]
    assert "field share" not in recommendation["text"]


def test_reader_uses_json_decoder_and_distinguishes_legacy_and_malformed(tmp_path):
    module = _script_module()
    path = tmp_path / "ranking.html"
    assert module.read_published_ranking(path) is None
    path.write_text("<script>const D = {\"old\": true};</script>", encoding="utf-8")
    assert module.read_published_ranking(path) is None

    valid = _blob(
        {"Alpha": 1.0}, {"Alpha": {}},
    )
    path.write_text(
        "<script>const D = " + json.dumps(valid) + ";</script>", encoding="utf-8",
    )
    assert module.read_published_ranking(path)["meta"]["deck_rankings"]["method_id"] == "deck-rankings-v1"

    path.write_text(
        '<script>const D = {"meta":{"deck_rankings":{"method_id":"deck-rankings-v1"}};</script>',
        encoding="utf-8",
    )
    with pytest.raises(module.PublishedRankingPayloadError, match="malformed"):
        module.read_published_ranking(path)


def test_count_only_refresh_is_unchanged_and_snapshot_omits_derived_support():
    kwargs = dict(shares={"Alpha": .6, "Beta": .4},
                  cells={"Alpha": {"Beta": .55}, "Beta": {"Alpha": .45}})
    previous = _snap(**kwargs, observed_field_n=100)
    current = _snap(**kwargs, observed_field_n=101)
    assert compare_ranking_snapshots(current, previous)["status"] == "unchanged"
    assert all("support" not in row for row in current["candidates"].values())


def test_changed_call_explains_relative_shift_when_both_decks_decline():
    previous = _snap(shares={"Room": 1}, cells={"Alpha": {"Room": .60}, "Beta": {"Room": .58}})
    current = _snap(shares={"Room": 1}, cells={"Alpha": {"Room": .52}, "Beta": {"Room": .54}},
                    performance_call="Beta")
    result = compare_ranking_snapshots(current, previous)
    recommendation = next(item for item in result["insights"] if item["type"] == "recommendation")
    assert "Alpha → Beta" in recommendation["text"]
    assert "field +0.0pp" in recommendation["text"]
    assert "matchup estimates +4.0pp" in recommendation["text"]


def test_recognized_empty_payload_is_malformed_not_a_new_baseline(tmp_path):
    module = _script_module()
    path = tmp_path / "empty.html"
    path.write_text('const D = {"meta":{"deck_rankings":{"method_id":"deck-rankings-v1"}},"arch":[]};')
    with pytest.raises(module.PublishedRankingPayloadError, match="missing rows"):
        module.read_published_ranking(path)


def test_unavailable_other_candidate_does_not_hide_valid_changed_recommendation():
    previous = _snap(shares={"Room": .5, "Other": .5},
                     cells={"Alpha": {"Room": .6, "Other": .6}, "Beta": {"Room": .5, "Other": .5},
                            "Gone": {"Room": .4}})
    current = _snap(shares={"Room": .7, "Other": .3},
                    cells={"Alpha": {"Room": .6, "Other": .6}, "Beta": {"Room": .7, "Other": .7}},
                    performance_call="Beta")
    result = compare_ranking_snapshots(current, previous)
    assert result["unavailable_attributions"]
    assert {item["type"] for item in result["insights"]} == {"field_movement", "beneficiary", "recommendation"}
