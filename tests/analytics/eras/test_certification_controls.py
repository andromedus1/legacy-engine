from datetime import date, timedelta

import numpy as np
import legacy_engine.analytics.eras.certification as certification_module
import pytest

from legacy_engine.analytics.eras.certification import (
    CandidateCertificationInput,
    CertificationCalibration,
    HalfOpenInterval,
    SemanticFact,
    certify_candidate_family,
    estimate_candidate_discrepancies,
)
from legacy_engine.analytics.eras.discovery import DiscoveryCard, DiscoveryDeck


def _calibration(**overrides):
    raw = {
        "profile_id": "equivalence-test-v1",
        "profile_state": "promoted",
        "method_id": "cluster-bootstrap-equivalence-v1",
        "feature_schema_version": "recurrent-certification-features-v1",
        "control_evidence_sha256": "3" * 64,
        "partition": {"plan_id": "p", "salt": "s", "modulus": 2, "discovery_buckets": [0]},
        "family_alpha": 0.05,
        "bootstrap_replicates": 19,
        "min_candidate_events": 3,
        "min_reference_events": 3,
        "min_time_buckets": 2,
        "min_effective_events": 2.0,
        "max_event_share": 0.7,
        "max_source_share": 0.9,
        "max_context_weight": 4.0,
        "max_unsupported_context_share": 0.5,
        "context_smoothing": 0.5,
        "rbf_bandwidth": 1.0,
        "margins": {"main_js": 0.2, "side_js": 0.2, "mixture_energy": 0.2, "field_js": 0.2, "source_js": 0.2, "omnibus_mmd2": 0.2},
    }
    raw.update(overrides)
    return CertificationCalibration.model_validate(raw)


def _deck(event: str, when: date, *, parent: str = "X", source: str = "mtgo", card: str = "A", idx: int = 0):
    return DiscoveryDeck(
        event_id=event, event_date=when, deck_idx=idx, pilot_key=f"{event}-pilot-{idx}",
        parent_archetype=parent, source=source, provenance="online",
        mainboard=(DiscoveryCard(name=card, copies=4),),
        sideboard=(DiscoveryCard(name="Side", copies=2),),
    )


def _candidate(candidate_id="candidate-1", *, shifted=False):
    start = date(2026, 1, 1)
    old = tuple(_deck(f"old-{i}", start + timedelta(days=i * 7), source="mtgo" if i % 2 else "paper") for i in range(3))
    new = tuple(_deck(f"new-{i}", start + timedelta(days=35 + i * 7), source="mtgo" if i % 2 else "paper",
                      card="B" if shifted else "A") for i in range(3))
    old_context = (*old, _deck("old-field", start, parent="Y", source="paper"))
    new_context = (*new, _deck("new-field", start + timedelta(days=35), parent="Y", source="paper"))
    return CandidateCertificationInput(
        entity="X", candidate_id=candidate_id, historical_segment_id=f"segment-{candidate_id}",
        reference_segment_id="segment-current",
        historical_interval=HalfOpenInterval(start=start, end=start + timedelta(days=21)),
        reference_interval=HalfOpenInterval(start=start + timedelta(days=35), end=start + timedelta(days=56)),
        candidate_decks=old, reference_decks=new,
        candidate_context_decks=old_context, reference_context_decks=new_context,
    )


def test_positive_equivalence_requires_all_channels_and_is_order_invariant():
    calibration = _calibration()
    positive = _candidate()
    first = certify_candidate_family([positive], [], calibration, seed=7)
    second = certify_candidate_family([positive], [], calibration, seed=7)
    assert first == second
    assert first[0].statistical_status == "certified"
    assert first[0].final_status == "certified"
    assert first[0].equivalence is not None
    assert all(channel.simultaneous_upper < 1.0 for channel in first[0].equivalence.channels)


def test_component_shift_rejects_by_named_channel():
    decision = certify_candidate_family([_candidate(shifted=True)], [], _calibration(), seed=3)[0]
    assert decision.final_status != "certified"
    assert "component-non-equivalent" in decision.reasons or "omnibus-non-equivalent" in decision.reasons


def test_realistic_high_dimensional_half_replaced_lists_do_not_false_reunite():
    base = _candidate()
    shared = [f"Shared-{i:02d}" for i in range(30)]
    replaced = [f"Old-{i:02d}" for i in range(30)]
    current = [f"New-{i:02d}" for i in range(30)]
    old_cards = tuple(DiscoveryCard(name=name, copies=1) for name in (*shared, *replaced))
    new_cards = tuple(DiscoveryCard(name=name, copies=1) for name in (*shared, *current))
    old = tuple(deck.model_copy(update={"mainboard": old_cards}) for deck in base.candidate_decks)
    new = tuple(deck.model_copy(update={"mainboard": new_cards}) for deck in base.reference_decks)
    candidate = base.model_copy(update={"candidate_decks": old, "reference_decks": new})
    estimate = estimate_candidate_discrepancies(candidate, _calibration())["main-js"]
    assert estimate > 0.2
    decision = certify_candidate_family([candidate], [], _calibration(), seed=11)[0]
    assert decision.final_status != "certified"


def test_confirmed_semantic_veto_precedes_statistical_evidence():
    fact = SemanticFact(fact_id="ban-1", kind="affectedness", state="confirmed", effective_on=date(2026, 1, 8),
                        affected_entities=("X",), source="curated-ban-ledger", evidence_sha256="4" * 64, detail="confirmed")
    decision = certify_candidate_family([_candidate()], [fact], _calibration(), seed=0)[0]
    assert decision.final_status == "rejected"
    assert decision.equivalence is None
    assert decision.reasons == ("confirmed-affectedness",)


def test_candidate_profile_can_record_statistical_certificate_but_never_authority():
    decision = certify_candidate_family([_candidate()], [], _calibration(profile_state="candidate"), seed=0)[0]
    assert decision.final_status == "inconclusive"
    assert decision.statistical_status in {"certified", "inconclusive"}
    if decision.statistical_status == "certified":
        assert "unpromoted-calibration" in decision.reasons


def test_family_growth_cannot_narrow_existing_band():
    calibration = _calibration()
    one = certify_candidate_family([_candidate()], [], calibration, seed=5)[0]
    two = certify_candidate_family([_candidate(), _candidate("candidate-2", shifted=True)], [], calibration, seed=5)[0]
    assert one.equivalence is not None
    assert two.equivalence is not None
    assert two.equivalence.critical_value >= one.equivalence.critical_value


def test_bootstrap_preserves_replacement_multiplicity_and_shared_reference_draws(monkeypatch):
    calls = []
    original = certification_module._resample_events

    def traced(decks, rng):
        sampled = original(decks, rng)
        calls.append(tuple(deck.event_id for deck in sampled))
        return sampled

    monkeypatch.setattr(certification_module, "_resample_events", traced)
    calibration = _calibration(bootstrap_replicates=3)
    first = _candidate("candidate-a")
    second = _candidate("candidate-b").model_copy(update={"candidate_decks": _candidate("candidate-b").candidate_decks[:1]})
    certify_candidate_family([first, second], [], calibration, seed=9)
    # Each replicate has one shared current-reference and context draw, while
    # both candidates retain their own historical/context draws.
    assert len(calls) == 3 * 6
    reference_calls = [call for call in calls if any(event.startswith("new-") for event in call)]
    assert len(reference_calls) == 3 * 2

    class AlwaysFirst:
        def choice(self, n, size, replace):
            return np.zeros(size, dtype=int)

    repeated = certification_module._resample_events(first.candidate_decks, AlwaysFirst())
    assert len(repeated) == len(first.candidate_decks)
    assert len({deck.event_id for deck in repeated}) == 1
    assert repeated.count(repeated[0]) >= 2


def test_candidate_input_order_does_not_change_family_ids_or_decisions():
    calibration = _calibration()
    forward = certify_candidate_family([_candidate("b"), _candidate("a")], [], calibration, seed=4)
    reverse = certify_candidate_family([_candidate("a"), _candidate("b")], [], calibration, seed=4)
    assert forward == reverse


def test_observation_weighted_hhi_abstains_at_one_point_ninety_eight_effective_events():
    base = _candidate()
    start = date(2026, 1, 1)
    old = tuple(_deck(event, start + timedelta(days=offset), source="mtgo" if index % 2 else "paper", idx=index)
                for event, count, offset in (("e0", 60, 0), ("e1", 38, 7), ("e2", 1, 14), ("e3", 1, 21))
                for index in range(count))
    new = tuple(_deck(event, start + timedelta(days=35 + offset), source="mtgo" if index % 2 else "paper", idx=index)
                for event, count, offset in (("n0", 60, 0), ("n1", 38, 7), ("n2", 1, 14), ("n3", 1, 21))
                for index in range(count))
    candidate = base.model_copy(update={"candidate_decks": old, "reference_decks": new,
                                        "candidate_context_decks": old, "reference_context_decks": new})
    evidence = certification_module.evaluate_support(candidate, _calibration(min_effective_events=2.0), seed=0)
    assert evidence.effective_events == pytest.approx(1.98, rel=2e-3)
    assert "effective-support-below-floor" in evidence.reasons
    assert evidence.disposition == "abstain"
    context = certification_module.evaluate_context_overlap(candidate, _calibration(min_effective_events=2.0))
    assert context.effective_events == pytest.approx(1.98, rel=2e-3)
    assert context.disposition == "abstain"
