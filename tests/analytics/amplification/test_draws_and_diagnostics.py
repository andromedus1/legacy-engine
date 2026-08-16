from __future__ import annotations


def test_draws_are_cross_cell_aligned_whole_event_refits(amplification_run):
    draws = amplification_run.aligned_draws
    assert draws is not None
    assert len(draws.series) == len(amplification_run.candidates) * len(
        amplification_run.baselines
    )
    assert all(
        len(series.probabilities) == draws.replicate_count for series in draws.series
    )
    by_method = {}
    for series in draws.series:
        by_method.setdefault(series.method_id, set()).add(len(series.probabilities))
    assert all(lengths == {draws.replicate_count} for lengths in by_method.values())
    assert any(len(set(series.probabilities)) > 1 for series in draws.series)
    assert draws.replay_plan.origin_snapshot_id == draws.origin_snapshot_id
    assert len(draws.replay_plan.event_blocks) == draws.replicate_count


def test_directed_predictions_are_complement_derived(amplification_run):
    for candidate in amplification_run.candidates:
        predictions = {(p.subject, p.opponent): p for p in candidate.predictions}
        for (subject, opponent), prediction in predictions.items():
            reverse = predictions[(opponent, subject)]
            assert abs(prediction.all_case.mean + reverse.all_case.mean - 1.0) < 1e-8


def test_all_case_is_retained_independently_from_service_refusal(amplification_run):
    predictions = [
        p for candidate in amplification_run.candidates for p in candidate.predictions
    ]
    refused = [p for p in predictions if p.served is None]
    assert refused
    assert all(p.all_case is not None and p.reasons for p in refused)
    assert all(
        p.all_case.draws == amplification_run.profile.bootstrap_replicates
        for p in predictions
    )


def test_decomposition_and_borrowing_concentration_are_auditable(amplification_run):
    borrowed = [
        p
        for candidate in amplification_run.candidates
        for p in candidate.predictions
        if p.borrowed_match_ids_sha256 is not None
    ]
    assert borrowed
    assert all(p.borrowing_concentration is not None for p in borrowed)
    assert all(p.ablations.leave_target_pair_out is not None for p in borrowed)
    assert any(p.ablations.nonadditive_remainder not in (None, 0.0) for p in borrowed)
    assert all(p.borrowing_concentration.effective_donor_pairs > 0 for p in borrowed)


def test_current_history_borrowed_id_partitions_do_not_alias(amplification_run):
    for candidate in amplification_run.candidates:
        for prediction in candidate.predictions:
            assert prediction.current_match_ids_sha256 != ""
            assert prediction.historical_match_ids_sha256 != ""
            if prediction.borrowed_match_ids_sha256:
                assert prediction.borrowed_match_ids_sha256 not in {
                    prediction.current_match_ids_sha256,
                    prediction.historical_match_ids_sha256,
                }
