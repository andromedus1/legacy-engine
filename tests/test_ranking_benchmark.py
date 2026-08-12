from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from legacy_engine.advisory.ranking_benchmark import (
    ESTIMATOR_REGISTRY,
    BenchmarkFold,
    BenchmarkProtocol,
    BenchmarkEvaluationSummary,
    CardMetadataPolicy,
    CardMetadataQuarantineLedger,
    EvaluationSupport,
    ExternalRankingSnapshot,
    FrozenMatchupPrediction,
    FrozenOriginPredictions,
    FrozenRecommendation,
    HeldoutDeck,
    HeldoutMatch,
    HeldoutOutcomes,
    TaxonomySnapshotManifest,
    aggregate_benchmark,
    content_sha256,
    evaluate_origin,
    plan_walk_forward_folds,
    plan_card_metadata_quarantine,
    project_matchup_probability,
    protocol_sha256,
    render_benchmark_markdown,
)
from legacy_engine.ingestion import store
from legacy_engine.advisory.ranking_measurement import (
    MethodologyVariantSpec,
    RankingCellMeasurement,
)


def protocol(**updates) -> BenchmarkProtocol:
    values = {
        "protocol_id": "future-test",
        "created_at": "2026-01-01T00:00:00Z",
        "taxonomy_mode": "retrospective-fixed-parent",
        "first_cutoff": "2026-01-01",
        "final_evaluation_until": "2026-03-15",
    }
    values.update(updates)
    return BenchmarkProtocol(**values)


def test_protocol_preregisters_primary_and_estimators():
    configured = protocol()
    assert configured.primary_estimator == "production-ci-gated"
    assert len(configured.estimator_ids) == 10
    with pytest.raises(ValueError, match="preregistered estimator registry"):
        protocol(estimator_ids=("coin-50",))


def test_legacy_v1_protocol_and_summary_hashes_remain_byte_compatible():
    protocol_path = Path("data/benchmarks/best-deck-decision-trust-current-corpus-v1/protocol.json")
    summary_path = Path("data/benchmarks/best-deck-decision-trust-current-corpus-v1/summary.json")
    if not protocol_path.exists() or not summary_path.exists():
        pytest.skip("local frozen v1 artifacts unavailable")
    protocol_bytes = protocol_path.read_bytes()
    summary_bytes = summary_path.read_bytes()
    loaded_protocol = BenchmarkProtocol.model_validate_json(protocol_bytes)
    loaded_summary = BenchmarkEvaluationSummary.model_validate_json(summary_bytes)
    assert protocol_sha256(loaded_protocol) == hashlib.sha256(protocol_bytes).hexdigest()
    assert content_sha256(loaded_summary) == hashlib.sha256(summary_bytes).hexdigest()


def test_card_metadata_policy_is_closed_and_posthoc_quarantine_is_descriptive():
    with pytest.raises(ValueError, match="zero ceilings"):
        CardMetadataPolicy(mode="require-complete", max_deck_fraction=0.001)
    with pytest.raises(ValueError, match="require registered_at"):
        protocol(
            created_at="2026-08-12T00:00:00Z", first_cutoff="2025-01-01",
            card_metadata=CardMetadataPolicy(
                mode="quarantine-unresolved-decks", max_deck_fraction=0.005,
                max_round_fraction=0.02,
            ),
        )
    configured = protocol(
        created_at="2026-08-12T00:00:00Z", first_cutoff="2025-01-01",
        registered_at="2026-08-12T00:00:00Z", claim_ceiling="descriptive",
        card_metadata=CardMetadataPolicy(
            mode="quarantine-unresolved-decks", max_deck_fraction=0.005,
            max_round_fraction=0.02,
        ),
    )
    assert configured.claim_ceiling == "descriptive"


def test_same_cutoff_instant_is_posthoc_and_summary_type_rejects_ceiling_breach():
    quarantine = CardMetadataPolicy(
        mode="quarantine-unresolved-decks", max_deck_fraction=0.005,
        max_round_fraction=0.02,
    )
    with pytest.raises(ValueError, match="at or after first_cutoff"):
        protocol(
            first_cutoff="2026-01-01", created_at="2026-01-01T00:00:00Z",
            registered_at="2026-01-01T00:00:00Z", card_metadata=quarantine,
        )
    summary = aggregate_benchmark(_evaluation_protocol(), [])
    payload = summary.model_dump(mode="json")
    payload.update({"status": "predictive-claim-supported", "claim_ceiling": "descriptive"})
    with pytest.raises(ValueError, match="exceeds descriptive"):
        BenchmarkEvaluationSummary.model_validate(payload)


def test_quarantine_ledger_removes_whole_decks_and_is_result_blind():
    con = store.connect(":memory:")
    store.init_schema(con)
    con.execute("INSERT INTO cards VALUES ('Known', '', 0, '', '', '', '', 'normal', false, NULL, NULL)")
    con.execute("INSERT INTO tournaments VALUES ('e', 'E', '2025-01-01', 'uri', 'Legacy', 'src', 'prov')")
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
        [('e', 0, 'Alice', '1-0', None, None), ('e', 1, 'Bob', '0-1', None, None)],
    )
    con.executemany(
        "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
        [('e', 0, 'main', 'Unknown', 4), ('e', 1, 'main', 'Known', 4)],
    )
    con.execute("INSERT INTO rounds VALUES ('e', 0, 'Alice', 'Bob', '2-0')")
    policy = CardMetadataPolicy(
        mode="quarantine-unresolved-decks", max_deck_fraction=0.005, max_round_fraction=0.02,
    )
    first = plan_card_metadata_quarantine(con, start=None, end="2025-02-01", policy=policy)
    assert not first.within_ceiling
    con.execute("UPDATE rounds SET result='0-2'")
    # The planner reads card/deck/player dimensions only; changing a result cannot affect it.
    changed = plan_card_metadata_quarantine(con, start=None, end="2025-02-01", policy=policy)
    assert changed == first


def test_quarantine_blank_and_duplicate_identity_remove_rounds_conservatively():
    con = store.connect(":memory:")
    store.init_schema(con)
    con.execute("INSERT INTO tournaments VALUES ('e', 'E', '2025-01-01', '', 'Legacy', 'src', '')")
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("e", 0, "", "", None, None),
            ("e", 1, "Bob", "", None, None),
            ("e", 2, "Alice", "", None, None),
            ("e", 3, "alice", "", None, None),
        ],
    )
    con.executemany(
        "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
        [("e", 0, "main", "Unknown blank", 1), ("e", 2, "main", "Unknown duplicate", 1)],
    )
    con.executemany(
        "INSERT INTO rounds VALUES (?, ?, ?, ?, ?)",
        [("e", 0, "", "Bob", "2-0"), ("e", 1, "Alice", "Bob", "2-0")],
    )
    policy = CardMetadataPolicy(
        mode="quarantine-unresolved-decks", max_deck_fraction=0.005,
        max_round_fraction=0.02,
    )
    ledger = plan_card_metadata_quarantine(con, start=None, end="2025-02-01", policy=policy)
    assert {item.deck_idx for item in ledger.excluded_decks} == {0, 2}
    assert all(item.identity_ambiguous for item in ledger.excluded_decks)
    assert ledger.excluded_round_keys == (("e", 0), ("e", 1))
    assert ledger.round_fraction == 1.0


def test_walk_forward_folds_keep_dates_whole_and_reset_at_ban():
    folds = plan_walk_forward_folds(
        ["2026-01-02", "2026-01-15", "2026-01-15", "2026-01-20", "2026-02-10"],
        ["2026-01-15"],
        protocol(),
    )
    assert [(fold.cutoff, fold.evaluation_until) for fold in folds[:3]] == [
        ("2026-01-01", "2026-01-15"),
        ("2026-01-15", "2026-02-12"),
        ("2026-02-12", "2026-03-12"),
    ]
    assert folds[0].event_dates == ("2026-01-02",)
    assert folds[1].event_dates == ("2026-01-15", "2026-01-20", "2026-02-10")
    assert all(left.evaluation_until <= right.cutoff for left, right in zip(folds, folds[1:]))
    assert protocol_sha256(protocol()) == protocol_sha256(protocol())
    frozen_plan = protocol().model_copy(update={
        "planned_folds": folds,
        "ban_events_as_of": (("2026-01-15", "Example", "banned"),),
    })
    assert protocol_sha256(frozen_plan) != protocol_sha256(protocol())
    assert frozen_plan.planned_folds == folds


def test_future_dated_taxonomy_manifest_shape_is_typed():
    payload = b"rules"
    manifest = TaxonomySnapshotManifest(
        source="operator fixture", effective_at="2027-01-01", rules_manifest="rules.json",
        rules_sha256=hashlib.sha256(payload).hexdigest(),
    )
    assert json.loads(manifest.model_dump_json())["action_level"] == "parent"


def test_unresolved_production_projection_is_explicit_unserved_half():
    cell = RankingCellMeasurement(
        subject="A", opponent="B", field_share=1.0, era=None, fallback=None,
        selected_kind=None, selected=None, selection_reason="none", measured=False,
        concentration_warning=None,
    )
    projected = project_matchup_probability(cell, spec=MethodologyVariantSpec(
        id="ci-gated", label="gated", source_policy="selected", rate_basis="shrunk",
        evidence_n=8,
    ))
    assert projected.probability == 0.5
    assert projected.imputed is True and projected.served is False
    assert "no frozen matchup evidence" in projected.refusal_reason


def _evaluation_protocol() -> BenchmarkProtocol:
    return protocol(
        final_evaluation_until="2026-01-29", bootstrap_draws=50,
        support=EvaluationSupport(
            min_common_matches=2, min_events=2, min_event_dates=2,
            min_calibration_matches=2, min_supported_actions=2, min_action_matches=1,
            min_future_field_coverage=0.8, min_claim_folds=2, min_claim_regimes=1,
        ),
    )


def _predictions(configured: BenchmarkProtocol) -> FrozenOriginPredictions:
    fold = BenchmarkFold(
        fold_id="f", cutoff="2026-01-01", evaluation_until="2026-01-29",
        regime_start="2025-11-10", regime_end=None,
        event_dates=("2026-01-02", "2026-01-03"),
    )
    matchup = []
    recommendations = []
    for estimator in ESTIMATOR_REGISTRY:
        for subject in ("A", "B"):
            for opponent in ("A", "B"):
                probability = 0.5
                if estimator == "production-ci-gated" and subject != opponent:
                    probability = 0.8 if subject == "A" else 0.2
                matchup.append(FrozenMatchupPrediction(
                    estimator=estimator, subject=subject, opponent=opponent,
                    probability=probability, served=True, source_kind="fixture",
                    imputed=False, refusal_reason=None,
                ))
        recommendations.append(FrozenRecommendation(
            estimator=estimator, chosen_action="A", ranked_actions=("A", "B"),
            scores={"A": 0.6, "B": 0.4}, served=True, refusal_reason=None,
        ))
    return FrozenOriginPredictions(
        protocol_hash=protocol_sha256(configured), snapshot_manifest_sha256="snapshot",
        fold=fold, generated_at=configured.created_at, code_commit="commit",
        taxonomy_mode=configured.taxonomy_mode, taxonomy_effective_at=None,
        taxonomy_sha256="taxonomy", rules_sha256="rules",
        estimator_registry=ESTIMATOR_REGISTRY, action_universe=("A", "B"),
        field_shares={"A": 0.5, "B": 0.5}, matchup_predictions=tuple(matchup),
        recommendations=tuple(recommendations), methodology={}, seeds={"benchmark": configured.seed},
    )


def _heldout(*, a_wins: bool = True) -> list[HeldoutMatch]:
    return [
        HeldoutMatch(
            event_id=f"e{index}", event_date=f"2026-01-0{index + 2}", provenance="online",
            subject="A", opponent="B", subject_player_key=None, opponent_player_key=None,
            subject_won=a_wins, exclusion_reason=None,
        )
        for index in range(2)
    ]


def test_future_outcome_swap_changes_evaluation_not_frozen_prediction():
    configured = _evaluation_protocol()
    frozen = _predictions(configured)
    frozen_hash = content_sha256(frozen)
    favorable = evaluate_origin(frozen, _heldout(a_wins=True), protocol=configured)
    adverse = evaluate_origin(frozen, _heldout(a_wins=False), protocol=configured)
    good = next(item for item in favorable.estimators if item.estimator == "production-ci-gated")
    bad = next(item for item in adverse.estimators if item.estimator == "production-ci-gated")
    assert good.log_loss < bad.log_loss
    assert content_sha256(frozen) == frozen_hash
    assert favorable.status == "descriptive"
    assert favorable.player_sensitivity_reason.startswith("player-component sensitivity unavailable")


def test_exclusions_common_case_and_bootstrap_are_deterministic():
    configured = _evaluation_protocol()
    frozen = _predictions(configured)
    rows = [
        *_heldout(),
        HeldoutMatch(
            event_id="mirror", event_date="2026-01-04", provenance="online",
            subject="A", opponent="A", subject_player_key="p", opponent_player_key="q",
            subject_won=True, exclusion_reason=None,
        ),
        HeldoutMatch(
            event_id="new", event_date="2026-01-05", provenance="online",
            subject="New", opponent="Other", subject_player_key="p", opponent_player_key="q",
            subject_won=True, exclusion_reason=None,
        ),
    ]
    first = evaluate_origin(frozen, rows, protocol=configured)
    second = evaluate_origin(frozen, rows, protocol=configured)
    assert first == second
    assert first.exclusions["mirror"] == 1
    assert first.exclusions["emerging-label"] == 1
    assert {item.common_matches for item in first.estimators} == {2}


def test_player_component_sensitivity_is_coverage_gated_and_seeded():
    configured = _evaluation_protocol()
    frozen = _predictions(configured)
    rows = [match.model_copy(update={
        "subject_player_key": f"a{index}", "opponent_player_key": f"b{index}",
    }) for index, match in enumerate(_heldout())]
    result = evaluate_origin(frozen, rows, protocol=configured)
    assert result.player_sensitivity_reason is None
    assert result.player_sensitivity["identity_coverage"] == 1.0
    assert result.player_sensitivity["components"] == 2.0
    assert result.player_sensitivity["primary_log_loss_ci_low"] <= result.player_sensitivity[
        "primary_log_loss_ci_high"
    ]


def test_external_snapshot_is_dated_exact_and_partial():
    configured = _evaluation_protocol()
    frozen = _predictions(configured)
    with pytest.raises(ValueError, match="future-dated"):
        evaluate_origin(frozen, _heldout(), protocol=configured, external=[
            ExternalRankingSnapshot(
                source="future", observed_at="2026-01-02T00:00:00Z", taxonomy="parent",
                ranks={"A": 1},
            )
        ])
    result = evaluate_origin(frozen, _heldout(), protocol=configured, external=[
        ExternalRankingSnapshot(
            source="dated", observed_at="2025-12-31T00:00:00Z", taxonomy="parent",
            scores={"A": 1.0}, matchup_probabilities={"A|||B": 0.7},
        )
    ])
    assert result.external[0].estimator == "external:dated"
    assert result.external[0].common_matches == 2
    assert result.external[0].eligible_matches == 2
    assert result.external[0].common_case_coverage == 1.0
    assert result.external[0].missing_actions == ()

    with pytest.raises(ValueError, match="taxonomy must be 'parent'"):
        evaluate_origin(frozen, _heldout(), protocol=configured, external=[
            ExternalRankingSnapshot(
                source="wrong-taxonomy", observed_at="2025-12-31T00:00:00Z",
                taxonomy="variant", ranks={"A": 1},
            )
        ])


def test_field_coverage_uses_deck_mass_not_match_activity():
    configured = _evaluation_protocol()
    frozen = _predictions(configured)
    decks = tuple(
        HeldoutDeck(
            event_id=f"e{index}", event_date="2026-01-02", provenance="online",
            archetype="A" if index < 8 else "New", exclusion_reason=None,
        )
        for index in range(10)
    )
    result = evaluate_origin(
        frozen, HeldoutOutcomes(matches=tuple(_heldout()), decks=decks), protocol=configured,
    )
    assert result.field_coverage.future_field_coverage == 0.8
    assert result.field_coverage.covered_decks == 8
    assert result.estimators[0].support.future_field_coverage == 0.8
    changed = evaluate_origin(
        frozen,
        HeldoutOutcomes(
            matches=tuple(_heldout()),
            decks=decks[:-1] + (decks[-1].model_copy(update={"archetype": "A"}),),
        ),
        protocol=configured,
    )
    assert changed.evaluation_data_sha256 != result.evaluation_data_sha256


def test_regret_names_tied_oracle_censor_and_report_exposes_full_evidence():
    configured = _evaluation_protocol()
    frozen = _predictions(configured)
    tied = [*_heldout(a_wins=True), *_heldout(a_wins=False)]
    tied = [match.model_copy(update={"event_id": f"e{index}"}) for index, match in enumerate(tied)]
    fold = evaluate_origin(frozen, tied, protocol=configured)
    primary = next(item for item in fold.estimators if item.estimator == configured.primary_estimator)
    assert primary.regret is None
    assert primary.regret_censor_reason == "practical-tie"
    rendered = render_benchmark_markdown(aggregate_benchmark(configured, [fold]))
    for evidence in ("Brier", "Cal. int./slope", "Coverage", "Rank τ", "Top 3", "Regret"):
        assert evidence in rendered
    assert "Cumulative calibration residuals" in rendered


def test_markdown_renders_exact_quarantine_evidence():
    configured = _evaluation_protocol()
    ledger = CardMetadataQuarantineLedger(
        policy=CardMetadataPolicy(), raw_decks=100, retained_decks=99,
        raw_rounds=100, retained_rounds=98,
        excluded_decks=(
            {
                "tournament_id": "event-1", "deck_idx": 4, "player_key": "player",
                "event_date": "2025-12-20", "source": "MTGmelee", "event_uri": "https://event",
                "unresolved_names": ("Unknown Card",), "identity_ambiguous": False,
            },
        ),
        excluded_round_keys=(("event-1", 3),), deck_fraction=0.01, round_fraction=0.02,
        counts_by_source={"MTGmelee": {"raw_decks": 100, "retained_decks": 99,
                                        "raw_rounds": 100, "retained_rounds": 98}},
        within_ceiling=False, reasons=("round ceiling reason",),
    )
    fold = evaluate_origin(_predictions(configured), _heldout(), protocol=configured).model_copy(
        update={"card_metadata_quarantine": ledger},
    )
    rendered = render_benchmark_markdown(aggregate_benchmark(configured, [fold]))
    for evidence in ("event-1:4", "player", "Unknown Card", "https://event", "round ceiling reason"):
        assert evidence in rendered
    assert ledger.digest in rendered


def test_aggregate_remains_descriptive_without_claim_support():
    configured = _evaluation_protocol()
    fold = evaluate_origin(_predictions(configured), _heldout(), protocol=configured)
    summary = aggregate_benchmark(configured, [fold])
    assert summary.status == "descriptive"
    assert "evaluable folds 1 < 2" in summary.reasons
    rendered = render_benchmark_markdown(summary)
    assert "Evaluation is read-only" in rendered
    assert "Paired primary-minus-baseline log loss" in rendered


def test_descriptive_protocol_claim_ceiling_is_serialized_and_enforced():
    configured = _evaluation_protocol().model_copy(update={"claim_ceiling": "descriptive"})
    fold = evaluate_origin(_predictions(configured), _heldout(), protocol=configured)
    summary = aggregate_benchmark(configured, [fold])
    assert summary.claim_ceiling == "descriptive"
    assert summary.status == "descriptive"
    assert any("claim ceiling is descriptive" in reason for reason in summary.reasons)
    assert "Claim ceiling: **descriptive**" in render_benchmark_markdown(summary)


def test_aggregate_requires_both_calibration_coefficients():
    configured = _evaluation_protocol()
    fold = evaluate_origin(_predictions(configured), _heldout(), protocol=configured)
    estimators = tuple(
        item.model_copy(update={"calibration_intercept": None, "calibration_slope": 1.0})
        if item.estimator == configured.primary_estimator else item
        for item in fold.estimators
    )
    summary = aggregate_benchmark(configured, [
        fold.model_copy(update={"estimators": estimators}),
        fold.model_copy(update={"estimators": estimators}),
    ])
    assert "required primary calibration metrics are unavailable" in summary.reasons
