from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import pytest

from legacy_engine.ops.format_monitor import (
    CandidateDisposition,
    FormatMonitorState,
    MonitorEvidence,
    acknowledge_candidate,
    add_candidate_evidence,
    extract_legacy_legalities,
    load_monitor_state,
    merge_legality_observation,
    write_monitor_state,
)


NOW = datetime(2026, 8, 11, 18, tzinfo=timezone.utc)
SCRYFALL = MonitorEvidence(
    source="scryfall",
    source_url="https://data.scryfall.io/oracle.jsonl.gz",
    observed_at=NOW,
    detail="Legacy legalities bulk snapshot",
)


def _rows(legality="legal"):
    return [{
        "oracle_id": "oracle-1",
        "name": "Example Card",
        "legalities": {"legacy": legality},
    }]


def _empty_state() -> FormatMonitorState:
    return FormatMonitorState(updated_at=NOW)


def _candidate_state(current="banned") -> FormatMonitorState:
    state = merge_legality_observation(
        _empty_state(), observed=extract_legacy_legalities(_rows()),
        evidence=SCRYFALL, registered_events=(),
    )
    return merge_legality_observation(
        state, observed=extract_legacy_legalities(_rows(current)),
        evidence=SCRYFALL.model_copy(update={"observed_at": NOW + timedelta(days=1)}),
        registered_events=(),
    )


class TestLegalityProjection:
    def test_first_valid_snapshot_establishes_baseline_without_candidate(self):
        state = merge_legality_observation(
            _empty_state(), observed=extract_legacy_legalities(_rows()),
            evidence=SCRYFALL, registered_events=(),
        )
        assert state.legality_baseline_observed_at == NOW
        assert state.candidates == ()

    def test_unknown_vocabulary_duplicate_and_missing_prior_fail_loudly(self):
        with pytest.raises(ValueError, match="unknown Legacy legality"):
            extract_legacy_legalities(_rows("future_value"))
        with pytest.raises(ValueError, match="duplicate"):
            extract_legacy_legalities(_rows() * 2)

        baseline = merge_legality_observation(
            _empty_state(), observed=extract_legacy_legalities(_rows()),
            evidence=SCRYFALL, registered_events=(),
        )
        other = extract_legacy_legalities([{
            "oracle_id": "oracle-2", "name": "Other",
            "legalities": {"legacy": "legal"},
        }])
        with pytest.raises(ValueError, match="lost 1 prior identities"):
            merge_legality_observation(
                baseline, observed=other, evidence=SCRYFALL, registered_events=(),
            )


class TestCandidateLifecycle:
    def test_legal_to_banned_has_stable_identity_and_no_duplicate_on_repeat(self):
        state = _candidate_state()
        assert len(state.candidates) == 1
        candidate = state.candidates[0]
        assert candidate.prior_value == "legal"
        assert candidate.current_value == "banned"
        assert candidate.unsupported_acceptance_reason is None

        repeated = merge_legality_observation(
            state, observed=extract_legacy_legalities(_rows("banned")),
            evidence=SCRYFALL.model_copy(update={"observed_at": NOW + timedelta(days=2)}),
            registered_events=(),
        )
        assert repeated.candidates == state.candidates

    def test_acknowledgement_suppresses_unchanged_evidence_but_new_wotc_reopens(self):
        state = _candidate_state()
        candidate_id = state.candidates[0].candidate_id
        acknowledged = acknowledge_candidate(
            state, candidate_id, acknowledged_at=NOW + timedelta(days=1, minutes=1),
        )
        assert acknowledged.candidates[0].disposition is CandidateDisposition.ACKNOWLEDGED

        repeated = merge_legality_observation(
            acknowledged, observed=extract_legacy_legalities(_rows("banned")),
            evidence=SCRYFALL.model_copy(update={"observed_at": NOW + timedelta(days=2)}),
            registered_events=(),
        )
        assert repeated.candidates[0].disposition is CandidateDisposition.ACKNOWLEDGED

        wotc = MonitorEvidence(
            source="wotc", source_url="https://magic.wizards.com/example",
            observed_at=NOW + timedelta(days=2), effective_date=date(2026, 8, 12),
            detail="Example Card is banned.",
        )
        enriched = add_candidate_evidence(repeated, candidate_id, wotc)
        assert enriched.candidates[0].disposition is CandidateDisposition.OPEN
        assert len(enriched.candidates[0].evidence) == 2

    def test_registered_ban_retires_candidate_and_unban_stays_unsupported(self):
        state = _candidate_state()
        retired = merge_legality_observation(
            state, observed=extract_legacy_legalities(_rows("banned")), evidence=SCRYFALL,
            registered_events=((date(2026, 8, 12), "Example Card", "confirmed"),),
        )
        assert retired.candidates == ()

        unban = _candidate_state("not_legal")
        # Move from not_legal to legal to exercise a transition the cumulative ledger cannot encode.
        unban = merge_legality_observation(
            unban, observed=extract_legacy_legalities(_rows("legal")), evidence=SCRYFALL,
            registered_events=(),
        )
        assert "cannot represent" in unban.candidates[-1].unsupported_acceptance_reason

    def test_unknown_acknowledgement_fails_loudly(self):
        with pytest.raises(ValueError, match="unknown format-monitor candidate"):
            acknowledge_candidate(_empty_state(), "missing", acknowledged_at=NOW)


class TestMonitorStatePersistence:
    def test_round_trip_and_failed_replace_preserve_last_good(self, tmp_path, monkeypatch):
        path = tmp_path / "format-monitor.json"
        original = _candidate_state()
        write_monitor_state(path, original)
        assert load_monitor_state(path) == original
        previous = path.read_text()

        def fail_replace(source, destination):
            raise OSError("replace failed")

        monkeypatch.setattr(os, "replace", fail_replace)
        with pytest.raises(OSError, match="replace failed"):
            write_monitor_state(path, original.model_copy(update={"updated_at": NOW + timedelta(days=3)}))
        assert path.read_text() == previous
        assert list(tmp_path.glob("*.tmp")) == []
