from datetime import date, datetime, timezone

import pytest

from legacy_engine.advisory.plan_borrowing import build_plan_borrowing_priors
from legacy_engine.analytics.amplification.models import EligibleOutcome, IntervalEvidenceCorpus
from legacy_engine.analytics.eras.consume import AnalysisClock


@pytest.fixture
def make_corpus():
    def _make(records):
        outcomes = tuple(
            EligibleOutcome(
                match_id=f"match-{i}", unordered_pair_id=f"{a}/{b}",
                subject=a, opponent=b, subject_won=won,
                event_id=f"event-{i % 3}", event_date=date(2026, 7, 12),
                provenance="online", pair_component_id="pair-current",
                subject_component_id="subject-current", opponent_component_id="opponent-current",
                subject_certificate_ids=(), opponent_certificate_ids=(),
                origin="certified-history" if i % 2 else "current-direct",
            )
            for i, (a, b, won) in enumerate(records)
        )
        return IntervalEvidenceCorpus(
            corpus_id="test-corpus", clock=AnalysisClock(
                data_until=date(2026, 7, 13),
                knowledge_as_of=datetime(2026, 7, 13, tzinfo=timezone.utc),
                knowledge_mode="retrospective-current-model",
            ), certificate_run_id=None,
            entities=tuple(sorted({x for a, b, _ in records for x in (a, b)})),
            outcomes=outcomes, pair_evidence_sha256="pairs",
            entity_eligibility_sha256="eligibility", source_rows_sha256="sources",
        )
    return _make


class TestPlanBorrowing:
    def test_target_outcomes_do_not_change_donor_prior(self, make_corpus):
        donors = [("A", "C", True), ("C", "A", False), ("A", "D", False)]
        plans = {"B": "combo", "C": "combo", "D": "combo"}
        first = build_plan_borrowing_priors(
            make_corpus(donors + [("A", "B", True)] * 20), plans, [("A", "B")],
        )["A", "B"]
        second = build_plan_borrowing_priors(
            make_corpus(donors + [("B", "A", True)] * 20), plans, [("A", "B")],
        )["A", "B"]
        assert (first.mean, first.strength) == (second.mean, second.strength) == (3 / 5, 3)
        assert first.donor_wins == 2
        assert first.donor_n == 3
        assert first.donor_opponents == 2
        assert first.donor_events == 3

    def test_unobserved_target_gets_informative_bounded_prior(self, make_corpus):
        corpus = make_corpus([("A", "C", True)] * 20)
        result = build_plan_borrowing_priors(corpus, {"B": "wide", "C": "wide"}, [("A", "B")])
        prior = result["A", "B"]
        assert prior.mean == pytest.approx(21 / 22)
        assert prior.strength == 15
        assert prior.history_donor_n == 10
        assert prior.donor_n == 20
        assert len(prior.selection_sha256) == 64
        assert prior.corpus_id == corpus.corpus_id

    def test_no_donor_or_mapping_retains_original_prior_by_omission(self, make_corpus):
        corpus = make_corpus([("A", "B", True)])
        assert build_plan_borrowing_priors(corpus, {"B": "combo"}, [("A", "B")]) == {}
        assert build_plan_borrowing_priors(corpus, {}, [("A", "C")]) == {}

    def test_unrelated_plan_and_mirror_targets_do_not_supply_donors(self, make_corpus):
        corpus = make_corpus([("A", "C", True), ("A", "D", False)])
        result = build_plan_borrowing_priors(
            corpus, {"A": "combo", "B": "combo", "C": "combo", "D": "wide"},
            [("A", "B"), ("A", "A"), ("A", "B")],
        )
        assert list(result) == [("A", "B")]
        assert result["A", "B"].mean == pytest.approx(2 / 3)
        assert result["A", "B"].donor_n == 1

    def test_duplicate_physical_match_is_rejected(self, make_corpus):
        corpus = make_corpus([("A", "C", True)])
        corpus = corpus.model_copy(update={"outcomes": corpus.outcomes * 2})
        with pytest.raises(ValueError, match="duplicate physical"):
            build_plan_borrowing_priors(corpus, {"B": "combo", "C": "combo"}, [("A", "B")])

    def test_cutoff_day_is_not_training(self, make_corpus):
        corpus = make_corpus([("A", "C", True)])
        future = corpus.outcomes[0].model_copy(update={"event_date": date(2026, 7, 13)})
        corpus = corpus.model_copy(update={"outcomes": (future,)})
        with pytest.raises(ValueError, match="exclusive cutoff"):
            build_plan_borrowing_priors(corpus, {"B": "combo", "C": "combo"}, [("A", "B")])
