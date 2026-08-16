"""Construction of the one-and-only amplification evidence corpus."""
from __future__ import annotations

import json
from hashlib import sha256
from legacy_engine.analytics.match_results import SelectedOutcomeLedger
from legacy_engine.analytics.matchup import IntervalAdaptiveMatrix
from legacy_engine.analytics.eras.consume import MatchupEvidenceView
from .models import DirectBaseline, EligibleOutcome, IntervalEvidenceCorpus

def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def _view_digest(view: MatchupEvidenceView) -> str:
    return _digest(view.model_dump(mode="json"))

def build_direct_baselines(interval: IntervalAdaptiveMatrix) -> dict[tuple[str, str], DirectBaseline]:
    """Copy interval cells and bind their serialized bytes before any fit runs."""
    return {
        pair: DirectBaseline(
            current_only=views.current_only,
            certified_expanded=views.certified_expanded,
            current_sha256=_view_digest(views.current_only),
            expanded_sha256=_view_digest(views.certified_expanded),
        )
        for pair, views in interval.evidence.items()
    }

def _rows(ledger: SelectedOutcomeLedger) -> tuple[EligibleOutcome, ...]:
    current = {row.match.match_id for row in ledger.rows if row.view == "current-only"}
    expanded = {row.match.match_id for row in ledger.rows if row.view == "certified-expanded"}
    if not expanded.issuperset(current):
        raise ValueError("interval ledger current rows must be a subset of expanded rows")
    physical = [row for row in ledger.rows if row.view == "certified-expanded"]
    ids = [row.match.match_id for row in physical]
    if len(ids) != len(set(ids)):
        raise ValueError("interval ledger contains duplicate physical match ids")
    outcomes = []
    for row in physical:
        match = row.match
        if match.subject >= match.opponent:
            raise ValueError("interval ledger rows must be lexicographically oriented")
        outcomes.append(EligibleOutcome(
            match_id=match.match_id,
            unordered_pair_id=f"{match.subject}::{match.opponent}",
            subject=match.subject, opponent=match.opponent, subject_won=match.subject_won,
            event_id=match.event_id, event_date=match.event_date, provenance=match.provenance,
            pair_component_id=row.pair_component_id,
            subject_component_id=row.subject_component_id,
            opponent_component_id=row.opponent_component_id,
            subject_certificate_ids=row.subject_certificate_ids,
            opponent_certificate_ids=row.opponent_certificate_ids,
            origin="current-direct" if match.match_id in current else "certified-history",
        ))
    return tuple(sorted(outcomes, key=lambda item: (item.subject, item.opponent, item.event_date, item.event_id, item.match_id)))

def build_interval_evidence_corpus(interval: IntervalAdaptiveMatrix) -> IntervalEvidenceCorpus:
    """Adapt the canonical selected-row ledger; aggregate-only matrices are rejected."""
    ledger = interval.selected_outcomes
    outcomes = _rows(ledger)
    entities = tuple(sorted({x for row in outcomes for x in (row.subject, row.opponent)} | set(ledger.entity_eligibility)))
    eligibility = {key: value for key, value in sorted(ledger.entity_eligibility.items())}
    row_payload = [row.model_dump(mode="json") for row in outcomes]
    return IntervalEvidenceCorpus(
        corpus_id=ledger.content_sha256,
        clock=ledger.clock,
        certificate_run_id=ledger.certificate_run_id,
        entities=entities,
        outcomes=outcomes,
        pair_evidence_sha256=_digest(row_payload),
        entity_eligibility_sha256=_digest({key: value.model_dump(mode="json") for key, value in eligibility.items()}),
        source_rows_sha256=_digest(row_payload),
    )

def rows_for_pair(corpus: IntervalEvidenceCorpus, subject: str, opponent: str) -> tuple[EligibleOutcome, ...]:
    if subject == opponent:
        return ()
    left, right = sorted((subject, opponent))
    rows = tuple(row for row in corpus.outcomes if row.subject == left and row.opponent == right)
    if subject == left:
        return rows
    return tuple(row.model_copy(update={"subject": subject, "opponent": opponent, "subject_won": not row.subject_won, "subject_component_id": row.opponent_component_id, "opponent_component_id": row.subject_component_id, "subject_certificate_ids": row.opponent_certificate_ids, "opponent_certificate_ids": row.subject_certificate_ids}) for row in rows)
