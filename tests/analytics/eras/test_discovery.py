from datetime import date, timedelta

from legacy_engine.analytics.eras.discovery import (
    DiscoveryCalibration,
    DiscoveryCard,
    DiscoveryDeck,
    DiscoveryBoundary,
    OutcomeFreeCorpus,
    compare_segment_fingerprints,
    discover_recurrent_states,
    segment_parent_archetype,
)
import legacy_engine.analytics.eras.discovery as discovery_module


def _calibration(**overrides):
    raw = {
        "calibration_id": "test-v1",
        "method_id": "segment-fingerprint-complete-link-v2",
        "bucket_days": 7,
        "min_segment_buckets": 3,
        "min_segment_decks": 3,
        "min_segment_events": 1,
        "min_subject_decks": 3,
        "pelt_penalty": 0.5,
        "smoothing_alpha": 0.5,
        "weights": {"main": 0.4, "side": 0.25, "field": 0.2, "source": 0.1, "subject_share": 0.05},
        "thresholds": {"main_js_max": 0.12, "side_js_max": 0.18, "mixture_energy_max": 0.2, "field_js_max": 0.25, "source_js_max": 0.25},
    }
    raw.update(overrides)
    return DiscoveryCalibration.model_validate(raw)


def _deck(event: str, when: date, parent: str, card: str, idx: int = 0) -> DiscoveryDeck:
    return DiscoveryDeck(
        event_id=event,
        event_date=when,
        deck_idx=idx,
        pilot_key=f"{event}-pilot-{idx}",
        parent_archetype=parent,
        source="mtgo",
        provenance="online",
        mainboard=(DiscoveryCard(name=card, copies=4),),
        sideboard=(DiscoveryCard(name="Side", copies=2),),
    )


def _recurrence_corpus(boundaries=()):
    decks = []
    for week in range(12):
        when = date(2026, 1, 5) + timedelta(days=7 * week)
        card = "A" if week < 4 or week >= 8 else "B"
        for idx in range(3):
            decks.append(_deck(f"x-{week}-{idx}", when, "X", card, idx))
        decks.append(_deck(f"other-{week}", when, "Other", "Other", 0))
    return OutcomeFreeCorpus(
        as_of=date(2026, 3, 30), taxonomy_version="tax-v1", legality_version="leg-v1",
        provenance_filter=None, semantic_boundaries=tuple(boundaries), decks=tuple(decks),
        source_sha256="0" * 64,
    )


def test_segments_are_deterministic_and_return_to_prior_state():
    corpus = _recurrence_corpus()
    calibration = _calibration()
    first = segment_parent_archetype(corpus, "X", calibration, seed=4)
    second = segment_parent_archetype(corpus, "X", calibration, seed=4)
    assert first == second
    assert len(first) == 3
    assert first[-1].reference is True
    assert first[0].main_slots != first[1].main_slots
    result = next(result for result in discover_recurrent_states(corpus, calibration, seed=4) if result.entity == "X")
    assert result.status == "candidate"
    assert result.candidate is not None
    assert len(result.candidate.historical_segment_ids) == 1


def test_sideboard_channel_and_mixture_are_persisted():
    corpus = _recurrence_corpus()
    calibration = _calibration()
    segments = segment_parent_archetype(corpus, "X", calibration)
    comparison = compare_segment_fingerprints(corpus, segments[0], segments[-1], calibration)
    assert comparison.compatible
    assert comparison.distances is not None
    assert comparison.distances.side_js == 0
    assert comparison.distances.mixture_energy == 0


def test_hard_boundary_forces_an_epoch_and_refusal():
    boundary = DiscoveryBoundary(
        boundary_id="taxonomy-2026-02", effective_on=date(2026, 2, 2),
        kind="taxonomy", hard=True, detail="new taxonomy",
    )
    corpus = _recurrence_corpus((boundary,))
    segments = segment_parent_archetype(corpus, "X", _calibration())
    assert any(segment.crossed_boundary_ids == () for segment in segments)
    assert len({segment.contract_epoch for segment in segments}) == 2
    comparison = compare_segment_fingerprints(corpus, segments[0], segments[-1], _calibration())
    assert comparison.compatible is False
    assert comparison.reasons == ("contract-incompatible",)


def test_mid_bucket_hard_boundary_is_exact_and_changes_epoch():
    boundary = DiscoveryBoundary(
        boundary_id="taxonomy-midweek", effective_on=date(2026, 2, 4),
        kind="taxonomy", hard=True, detail="midweek taxonomy release",
    )
    segments = segment_parent_archetype(_recurrence_corpus((boundary,)), "X", _calibration())
    after = next(segment for segment in segments if segment.start == date(2026, 2, 4))
    before = next(segment for segment in segments if segment.end == date(2026, 2, 4))
    assert before.contract_epoch == "epoch:initial"
    assert after.contract_epoch == "epoch:taxonomy-midweek"
    assert before.end == after.start == date(2026, 2, 4)


def test_disjoint_field_and_source_support_is_rejected():
    corpus = _recurrence_corpus()
    segments = segment_parent_archetype(corpus, "X", _calibration())
    right = segments[-1].model_copy(update={
        "field_context": (discovery_module.NamedMass(key="different-field", mass=1.0),),
        "source_mix": (discovery_module.NamedMass(key="different-source", mass=1.0),),
    })
    comparison = compare_segment_fingerprints(corpus, segments[-1], right, _calibration())
    assert comparison.compatible is False
    assert "field-shift" in comparison.reasons
    assert "source-shift" in comparison.reasons
    assert comparison.distances is not None
    assert comparison.distances.field_js == 1.0
    assert comparison.distances.source_js == 1.0


def test_subject_share_participates_in_boundary_score():
    calibration = _calibration()
    when = date(2026, 1, 5)
    left = [_deck(f"left-{idx}", when, "X", "A", idx) for idx in range(3)]
    left += [_deck("left-other", when, "Other", "Other")]
    right = [_deck(f"right-{idx}", when, "X", "A", idx) for idx in range(9)]
    right += [_deck("right-other", when, "Other", "Other")]
    score = discovery_module._segment_distance_for_weeks(
        left[:3], right[:9], left, right, "X", calibration,
    )
    assert score >= abs((3 / 4) - (9 / 10)) * calibration.weights.subject_share


def test_historical_duration_floor_is_explicit():
    corpus = _recurrence_corpus()
    segments = segment_parent_archetype(corpus, "X", _calibration())
    thin = segments[0].model_copy(update={"end": segments[0].start + timedelta(days=2)})
    comparison = compare_segment_fingerprints(corpus, segments[-1], thin, _calibration())
    assert "insufficient-historical-duration" in comparison.reasons


def test_unknown_and_conflict_labels_are_not_entities():
    corpus = _recurrence_corpus()
    extra = list(corpus.decks) + [
        _deck("unknown", date(2026, 1, 5), "Unknown", "U"),
        _deck("conflict", date(2026, 1, 5), "Conflict(A/B)", "C"),
    ]
    corpus = corpus.model_copy(update={"decks": tuple(extra)})
    assert segment_parent_archetype(corpus, "Unknown", _calibration()) == ()
    assert {result.entity for result in discover_recurrent_states(corpus, _calibration())} == {"Other", "X"}
