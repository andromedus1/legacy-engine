from __future__ import annotations

import copy
from dataclasses import replace
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from legacy_engine.analytics.amplification import StructureSnapshot
from legacy_engine.analytics.amplification.composition import (
    _donor_rows,
    fit_composition_kernel,
)
from legacy_engine.analytics.amplification.corpus import (
    build_direct_baselines,
    build_interval_evidence_corpus,
    pair_from_key,
    pair_key,
    rows_for_pair,
)
from legacy_engine.analytics.amplification.family import (
    _donors,
    _rung,
    fit_family_ladders,
)
from legacy_engine.analytics.amplification.hierarchical import fit_component_hierarchy
from legacy_engine.analytics.amplification.low_rank import (
    fit_skew_low_rank,
    low_rank_probability,
)
from legacy_engine.analytics.amplification.models import (
    EligibleOutcome,
    IntervalEvidenceCorpus,
)
from legacy_engine.analytics.eras.consume import AnalysisClock


def test_real_challengers_materialize_parameters_donors_and_frozen_ladders(
    interval_matrix, structure, diagnostic_profile
):
    corpus = build_interval_evidence_corpus(interval_matrix)
    hierarchy = fit_component_hierarchy(corpus, diagnostic_profile)
    composition = fit_composition_kernel(corpus, structure, diagnostic_profile)
    family = fit_family_ladders(corpus, structure, diagnostic_profile)
    assert hierarchy.pair_parameters
    assert hierarchy.component_offsets
    assert any(composition.donors.values())
    for target, donors in composition.donors.items():
        target_pair = frozenset(pair_from_key(target))
        assert all(
            frozenset(pair_from_key(donor.donor_pair_id)) != target_pair
            for donor in donors
        )
        borrowed, _ = _donor_rows(composition, corpus, target)
        assert len({row.match_id for row in borrowed}) == len(borrowed)
    assert family.ladders
    assert all(
        ladder[0].resolution == "target-pair" and not ladder[0].admissible
        for ladder in family.ladders.values()
    )
    target = pair_key("A", "B")
    target_ids = {row.match_id for row in rows_for_pair(corpus, "A", "B")}
    for rung in family.ladders[target][1:]:
        donor_ids = {
            row.match_id
            for row in _donors(
                corpus, structure.strategic_families, "A", "B", rung.resolution
            )
        }
        assert donor_ids.isdisjoint(target_ids)
        rows = _donors(
            corpus,
            structure.strategic_families,
            "A",
            "B",
            rung.resolution,
        )
        assert len({row.match_id for row in rows}) == len(rows)


def test_outcome_free_structure_and_post_origin_snapshot_are_enforced(
    interval_matrix, structure, diagnostic_profile
):
    with pytest.raises(ValidationError):
        StructureSnapshot.model_validate(
            {**structure.model_dump(mode="json"), "outcome_columns_accessed": ["wins"]}
        )
    future = structure.model_copy(
        update={"knowledge_as_of": datetime(2027, 1, 1, tzinfo=UTC)}
    )
    with pytest.raises(ValueError, match="postdates"):
        fit_composition_kernel(
            build_interval_evidence_corpus(interval_matrix), future, diagnostic_profile
        )


def test_wrapper_ledger_membership_and_certificate_tampering_refuse(interval_matrix):
    bad = copy.deepcopy(interval_matrix)
    bad.selected_outcomes = replace(bad.selected_outcomes, content_sha256="0" * 64)
    with pytest.raises(ValueError, match="ledger content"):
        build_interval_evidence_corpus(bad)
    bad = copy.deepcopy(interval_matrix)
    bad.certificate_run_id = "different-certificate"
    with pytest.raises(ValueError, match="certificate"):
        build_interval_evidence_corpus(bad)
    bad = copy.deepcopy(interval_matrix)
    pair = next(iter(bad.evidence))
    views = bad.evidence[pair]
    bad.evidence[pair] = views.model_copy(
        update={
            "current_only": views.current_only.model_copy(
                update={"match_ids": ("injected-target",)}
            )
        }
    )
    with pytest.raises(ValueError, match="membership"):
        build_interval_evidence_corpus(bad)


def test_direct_baselines_are_deep_copies_of_both_views(interval_matrix):
    baselines = build_direct_baselines(interval_matrix)
    key = next(iter(baselines))
    pair = pair_from_key(key)
    before = baselines[key].model_dump(mode="json")
    interval_matrix.evidence[pair].current_only.match_ids = ("mutated",)
    assert baselines[key].model_dump(mode="json") == before


def _cycle_corpus() -> IntervalEvidenceCorpus:
    entities = tuple("ABCDE")
    outcomes = []
    match = 0
    # A directed five-cycle with unequal edge strengths requires more than one skew component.
    for i, subject in enumerate(entities):
        opponent = entities[(i + 1) % len(entities)]
        left, right = sorted((subject, opponent))
        for repeat in range(5 + i):
            match += 1
            subject_won = subject == left
            outcomes.append(
                EligibleOutcome(
                    match_id=f"m{match}",
                    unordered_pair_id=pair_key(left, right),
                    subject=left,
                    opponent=right,
                    subject_won=subject_won,
                    event_id=f"event-{i}-{repeat}",
                    event_date=date(2026, 1, 1),
                    provenance="synthetic",
                    pair_component_id=f"pair-{i}",
                    subject_component_id=f"subject-{left}",
                    opponent_component_id=f"subject-{right}",
                    subject_certificate_ids=(),
                    opponent_certificate_ids=(),
                    origin="current-direct",
                )
            )
    clock = AnalysisClock(
        data_until=date(2026, 2, 1),
        knowledge_as_of=datetime(2026, 2, 1, tzinfo=UTC),
        knowledge_mode="retrospective-current-model",
    )
    return IntervalEvidenceCorpus(
        corpus_id="cycle-v1",
        clock=clock,
        certificate_run_id=None,
        entities=entities,
        outcomes=tuple(outcomes),
        pair_evidence_sha256="1" * 64,
        entity_eligibility_sha256="2" * 64,
        source_rows_sha256="3" * 64,
    )


def test_low_rank_models_have_distinct_dimensions_behavior_and_refusals(
    diagnostic_profile,
):
    corpus = _cycle_corpus()
    fits = [
        fit_skew_low_rank(corpus, rank=rank, profile=diagnostic_profile)
        for rank in (1, 2, 4)
    ]
    assert [len(fit.left_factors[0]) for fit in fits] == [1, 2, 4]
    assert len({fit.fit_id for fit in fits}) == 3
    signatures = {
        tuple(
            round(low_rank_probability(fit, a, b), 6)
            for a, b in zip("ABCDE", "BCDEA", strict=True)
        )
        for fit in fits
    }
    assert len(signatures) >= 2
    assert "insufficient-rank-support" in fits[2].reasons


def test_family_negative_transfer_rung_refuses_heterogeneous_members(
    diagnostic_profile,
):
    corpus = _cycle_corpus()
    params = next(
        spec.parameters
        for spec in diagnostic_profile.method_specs
        if spec.method_id == "strategic-family-ladder-v1"
    )
    wins = tuple(
        row.model_copy(update={"subject_won": True})
        for row in corpus.outcomes
        if row.subject == "A"
    )
    losses = tuple(
        row.model_copy(update={"subject_won": False, "subject": "B"})
        for row in corpus.outcomes
        if row.subject == "C"
    )
    rung = _rung("family-vs-family", (*wins, *losses), params)
    assert rung.heterogeneity == 1.0
    assert not rung.admissible
    assert "family-heterogeneity" in rung.reasons
