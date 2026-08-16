"""Construction and validation of the one-and-only amplification corpus."""

from __future__ import annotations

import copy
import json
from hashlib import sha256

from legacy_engine.analytics.match_results import (
    SelectedOutcomeLedger,
    selected_outcome_ledger_digest,
    selected_rows_for_pair,
)
from legacy_engine.analytics.matchup import IntervalAdaptiveMatrix
from legacy_engine.analytics.eras.consume import MatchupEvidenceView

from .models import DirectBaseline, EligibleOutcome, IntervalEvidenceCorpus


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: object) -> str:
    return sha256(canonical_json(value).encode()).hexdigest()


def pair_key(subject: str, opponent: str) -> str:
    """Collision-free JSON key which retains the directed typed pair identity."""
    return json.dumps([subject, opponent], ensure_ascii=False, separators=(",", ":"))


def pair_from_key(value: str) -> tuple[str, str]:
    pair = json.loads(value)
    if (
        not isinstance(pair, list)
        or len(pair) != 2
        or not all(isinstance(x, str) for x in pair)
    ):
        raise ValueError(f"invalid directed pair key: {value!r}")
    return pair[0], pair[1]


def _view_digest(view: MatchupEvidenceView) -> str:
    return digest(view.model_dump(mode="json"))


def build_direct_baselines(
    interval: IntervalAdaptiveMatrix,
) -> dict[str, DirectBaseline]:
    """Deep-copy both exact interval views and bind both serialized identities."""
    baselines: dict[str, DirectBaseline] = {}
    for (subject, opponent), views in sorted(interval.evidence.items()):
        current = copy.deepcopy(views.current_only)
        expanded = copy.deepcopy(views.certified_expanded)
        baselines[pair_key(subject, opponent)] = DirectBaseline(
            current_only=current,
            certified_expanded=expanded,
            current_sha256=_view_digest(current),
            expanded_sha256=_view_digest(expanded),
        )
    return baselines


def _rows(ledger: SelectedOutcomeLedger) -> tuple[EligibleOutcome, ...]:
    current = {row.match.match_id for row in ledger.rows if row.view == "current-only"}
    expanded = {
        row.match.match_id for row in ledger.rows if row.view == "certified-expanded"
    }
    if not expanded.issuperset(current):
        raise ValueError(
            "interval ledger current rows must be a subset of expanded rows"
        )
    physical = [row for row in ledger.rows if row.view == "certified-expanded"]
    ids = [row.match.match_id for row in physical]
    if len(ids) != len(set(ids)):
        raise ValueError("interval ledger contains duplicate physical match ids")
    outcomes = []
    for row in physical:
        match = row.match
        if match.subject >= match.opponent:
            raise ValueError("interval ledger rows must be lexicographically oriented")
        outcomes.append(
            EligibleOutcome(
                match_id=match.match_id,
                unordered_pair_id=pair_key(match.subject, match.opponent),
                subject=match.subject,
                opponent=match.opponent,
                subject_won=match.subject_won,
                event_id=match.event_id,
                event_date=match.event_date,
                provenance=match.provenance,
                pair_component_id=row.pair_component_id,
                subject_component_id=row.subject_component_id,
                opponent_component_id=row.opponent_component_id,
                subject_certificate_ids=row.subject_certificate_ids,
                opponent_certificate_ids=row.opponent_certificate_ids,
                origin="current-direct"
                if match.match_id in current
                else "certified-history",
            )
        )
    return tuple(
        sorted(
            outcomes,
            key=lambda x: (x.subject, x.opponent, x.event_date, x.event_id, x.match_id),
        )
    )


def _validate_wrapper(interval: IntervalAdaptiveMatrix) -> None:
    ledger = interval.selected_outcomes
    if selected_outcome_ledger_digest(ledger) != ledger.content_sha256:
        raise ValueError("selected outcome ledger content digest mismatch")
    if interval.clock != ledger.clock:
        raise ValueError("interval and ledger analysis clocks differ")
    if interval.certificate_run_id != ledger.certificate_run_id:
        raise ValueError("interval and ledger certificate identities differ")
    for pair, views in interval.evidence.items():
        if views.clock != ledger.clock:
            raise ValueError(f"evidence clock differs for {pair!r}")
        selected = selected_rows_for_pair(ledger, *pair)
        by_view = {
            "current-only": tuple(
                sorted(r.match.match_id for r in selected if r.view == "current-only")
            ),
            "certified-expanded": tuple(
                sorted(
                    r.match.match_id for r in selected if r.view == "certified-expanded"
                )
            ),
        }
        if tuple(sorted(views.current_only.match_ids)) != by_view["current-only"]:
            raise ValueError(
                f"current evidence membership differs from ledger for {pair!r}"
            )
        if (
            tuple(sorted(views.certified_expanded.match_ids))
            != by_view["certified-expanded"]
        ):
            raise ValueError(
                f"expanded evidence membership differs from ledger for {pair!r}"
            )
        expected_added = set(by_view["certified-expanded"]) - set(
            by_view["current-only"]
        )
        if set(views.added_history.match_ids) != expected_added:
            raise ValueError(
                f"added-history evidence membership differs from ledger for {pair!r}"
            )


def build_interval_evidence_corpus(
    interval: IntervalAdaptiveMatrix,
) -> IntervalEvidenceCorpus:
    """Adapt a verified selected-row ledger; aggregate-only or altered wrappers refuse."""
    _validate_wrapper(interval)
    ledger = interval.selected_outcomes
    outcomes = _rows(ledger)
    entities = tuple(
        sorted(
            {x for row in outcomes for x in (row.subject, row.opponent)}
            | set(ledger.entity_eligibility)
        )
    )
    row_payload = [row.model_dump(mode="json") for row in outcomes]
    source_payload = [
        {
            "match_id": row.match_id,
            "provenance": row.provenance,
            "subject_certificate_ids": row.subject_certificate_ids,
            "opponent_certificate_ids": row.opponent_certificate_ids,
        }
        for row in outcomes
    ]
    return IntervalEvidenceCorpus(
        corpus_id=ledger.content_sha256,
        clock=ledger.clock,
        certificate_run_id=ledger.certificate_run_id,
        entities=entities,
        outcomes=outcomes,
        pair_evidence_sha256=digest(row_payload),
        entity_eligibility_sha256=digest(
            {
                k: v.model_dump(mode="json")
                for k, v in sorted(ledger.entity_eligibility.items())
            }
        ),
        source_rows_sha256=digest(source_payload),
    )


def rows_for_pair(
    corpus: IntervalEvidenceCorpus, subject: str, opponent: str
) -> tuple[EligibleOutcome, ...]:
    if subject == opponent:
        return ()
    left, right = sorted((subject, opponent))
    rows = tuple(
        row for row in corpus.outcomes if row.subject == left and row.opponent == right
    )
    if subject == left:
        return rows
    return tuple(
        row.model_copy(
            update={
                "subject": subject,
                "opponent": opponent,
                "subject_won": not row.subject_won,
                "subject_component_id": row.opponent_component_id,
                "opponent_component_id": row.subject_component_id,
                "subject_certificate_ids": row.opponent_certificate_ids,
                "opponent_certificate_ids": row.subject_certificate_ids,
            }
        )
        for row in rows
    )
