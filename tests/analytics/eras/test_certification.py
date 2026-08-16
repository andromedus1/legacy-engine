from datetime import date, timedelta

from legacy_engine.analytics.eras.certification import (
    CandidateCertificationInput,
    CertificationCalibration,
    ContextOverlapEvidence,
    HalfOpenInterval,
    SemanticFact,
    evaluate_context_overlap,
    evaluate_semantic_guards,
    evaluate_support,
)
from legacy_engine.analytics.eras.discovery import DiscoveryCard, DiscoveryDeck


def _calibration(**overrides):
    raw = {
        "profile_id": "guard-test-v1",
        "profile_state": "promoted",
        "method_id": "cluster-bootstrap-equivalence-v1",
        "feature_schema_version": "recurrent-certification-features-v1",
        "control_evidence_sha256": "1" * 64,
        "partition": {"plan_id": "p", "salt": "s", "modulus": 2, "discovery_buckets": [0]},
        "family_alpha": 0.05,
        "bootstrap_replicates": 9,
        "power_replicates": 9,
        "safely_inside_ratio": 0.8,
        "target_power": 0.5,
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


def _deck(event: str, when: date, *, parent: str = "X", source: str = "mtgo", idx: int = 0, card: str = "A"):
    return DiscoveryDeck(
        event_id=event, event_date=when, deck_idx=idx, pilot_key=f"{event}-pilot-{idx}",
        parent_archetype=parent, source=source, provenance="online",
        mainboard=(DiscoveryCard(name=card, copies=4),), sideboard=(),
    )


def _candidate(*, duplicate=False, context_shift=False):
    start = date(2026, 1, 1)
    candidate = tuple(_deck(f"old-{i}", start + timedelta(days=i * 7), source="mtgo" if i % 2 else "paper") for i in range(3))
    reference = tuple(_deck(f"new-{i}", start + timedelta(days=35 + i * 7), source="mtgo" if i % 2 else "paper") for i in range(3))
    if duplicate:
        candidate = (*candidate, candidate[0])
    old_context = (*candidate, *(_deck("old-field", start, parent="Y", source="paper"),))
    new_context = (*reference, *(_deck("new-field", start + timedelta(days=35), parent="Y" if not context_shift else "Z", source="paper"),))
    return CandidateCertificationInput(
        entity="X", candidate_id="candidate-1", historical_segment_id="segment-old",
        reference_segment_id="segment-current",
        historical_interval=HalfOpenInterval(start=start, end=start + timedelta(days=21)),
        reference_interval=HalfOpenInterval(start=start + timedelta(days=35), end=start + timedelta(days=56)),
        candidate_decks=candidate, reference_decks=reference,
        candidate_context_decks=old_context, reference_context_decks=new_context,
    )


def test_confirmed_semantic_fact_rejects_only_affected_entity():
    candidate = _candidate()
    fact = SemanticFact(fact_id="ban-1", kind="affectedness", state="confirmed", effective_on=date(2026, 1, 8),
                        affected_entities=("X",), source="curated-ban-ledger", evidence_sha256="1" * 64, detail="confirmed")
    assert evaluate_semantic_guards(candidate, [fact]).disposition == "reject"
    unaffected = candidate.model_copy(update={"entity": "Y"})
    assert evaluate_semantic_guards(unaffected, [fact]).disposition == "pass"


def test_pending_monitor_fact_abstains_and_is_not_a_veto():
    fact = SemanticFact(fact_id="monitor-1", kind="legality", state="pending", effective_on=date(2026, 1, 8),
                        affected_entities=("X",), source="format-monitor", evidence_sha256="2" * 64, detail="pending")
    evidence = evaluate_semantic_guards(_candidate(), [fact])
    assert evidence.disposition == "abstain"
    assert evidence.confirmed_veto_ids == ()
    assert evidence.unresolved_fact_ids == ("monitor-1",)


def test_duplicate_deck_rows_cannot_buy_event_support():
    calibration = _calibration()
    normal = evaluate_support(_candidate(), calibration, seed=0)
    duplicate = evaluate_support(_candidate(duplicate=True), calibration, seed=0)
    assert duplicate.candidate_decks == normal.candidate_decks
    assert duplicate.candidate_events == normal.candidate_events
    assert duplicate.effective_events == normal.effective_events


def test_thin_support_is_named_abstention():
    candidate = _candidate().model_copy(update={"candidate_decks": _candidate().candidate_decks[:1]})
    evidence = evaluate_support(candidate, _calibration(), seed=0)
    assert evidence.disposition == "abstain"
    assert "insufficient-candidate-events" in evidence.reasons


def test_context_overlap_is_diagnostic_and_abstains_when_reference_category_is_unsupported():
    evidence = evaluate_context_overlap(_candidate(context_shift=True), _calibration(max_unsupported_context_share=0.05))
    assert isinstance(evidence, ContextOverlapEvidence)
    assert evidence.disposition == "abstain"
    assert "context-overlap-failed" in evidence.reasons
