from __future__ import annotations

import os
import fcntl
import threading
from datetime import date, datetime, timedelta, timezone

import pytest

from legacy_engine.ingestion.ban_monitor import parse_wotc_legacy_announcement
from legacy_engine.ingestion.releases import ReleaseScan, SetRelease
from legacy_engine.ops.format_monitor import (
    CandidateDisposition,
    FormatMonitorState,
    MonitorEvidence,
    acknowledge_candidate,
    acknowledge_monitor_candidate,
    add_candidate_evidence,
    extract_legacy_legalities,
    load_monitor_state,
    merge_legality_observation,
    write_monitor_state,
    run_format_monitor,
    format_monitor_audit_lines,
    merge_wotc_announcement,
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
        candidate_id = state.candidates[0].candidate_id
        state = add_candidate_evidence(state, candidate_id, MonitorEvidence(
            source="wotc", source_url="https://magic.wizards.com/example",
            observed_at=NOW + timedelta(hours=1), effective_date=date(2026, 8, 12),
            detail="Example Card is banned.",
        ))
        retired = merge_legality_observation(
            state, observed=extract_legacy_legalities(_rows("banned")), evidence=SCRYFALL,
            registered_events=((date(2026, 8, 12), "Example Card", "confirmed"),),
        )
        assert retired.candidates[0].disposition is CandidateDisposition.CONFIRMED

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

    def test_scryfall_identity_enriches_wotc_first_candidate_without_duplicate(self):
        baseline = merge_legality_observation(
            _empty_state(), observed=extract_legacy_legalities(_rows()),
            evidence=SCRYFALL, registered_events=(),
        )
        announcement = parse_wotc_legacy_announcement(
            _wotc_page("Example Card is banned."),
            source_url="https://magic.wizards.com/example",
        )
        wotc_first = merge_wotc_announcement(
            baseline, announcement, observed_at=NOW + timedelta(hours=1),
        )
        correlated = merge_legality_observation(
            wotc_first, observed=extract_legacy_legalities(_rows("banned")),
            evidence=SCRYFALL.model_copy(update={"observed_at": NOW + timedelta(days=1)}),
            registered_events=(),
        )

        assert len(correlated.candidates) == 1
        assert correlated.candidates[0].subject_id == "oracle-1"
        assert {item.source for item in correlated.candidates[0].evidence} == {
            "scryfall", "wotc",
        }


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

    def test_acknowledgement_waits_for_active_state_transaction(self, tmp_path):
        path = tmp_path / "format-monitor.json"
        state = _candidate_state()
        write_monitor_state(path, state)
        lock_path = path.with_name(f".{path.name}.lock")
        lock_path.touch()
        finished = threading.Event()

        with lock_path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            worker = threading.Thread(target=lambda: (
                acknowledge_monitor_candidate(
                    path, state.candidates[0].candidate_id,
                    acknowledged_at=NOW + timedelta(days=2),
                ),
                finished.set(),
            ))
            worker.start()
            assert not finished.wait(0.05)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        worker.join(timeout=1)

        assert finished.is_set()
        assert load_monitor_state(path).candidates[0].disposition is CandidateDisposition.ACKNOWLEDGED


class MonitorPorts:
    def __init__(self, rows, pages):
        self.rows = rows
        self.pages = pages
        self.urls = []

    def oracle_rows(self):
        if isinstance(self.rows, Exception):
            raise self.rows
        return self.rows

    def fetch_wotc(self, url):
        self.urls.append(url)
        value = self.pages.get(url)
        if value is None:
            raise FileNotFoundError(url)
        if isinstance(value, Exception):
            raise value
        return value, url


def _wotc_page(legacy="No changes."):
    return (
        "<p>Changes effective as of August 11, 2026.</p>"
        f"<h2>Legacy</h2><p>{legacy}</p><h2>Vintage</h2><p>No changes.</p>"
        "<p>Next announcement: October 12, 2026.</p>"
    )


class TestFormatMonitorComposition:
    def test_clear_requires_successful_legality_wotc_and_release_checks(self, tmp_path):
        url = "https://magic.wizards.com/en/news/announcements/banned-and-restricted-august-11-2026"
        result = run_format_monitor(
            MonitorPorts(_rows(), {url: _wotc_page()}),
            state_path=tmp_path / "state.json", observed_at=NOW,
            release_scan=ReleaseScan(upcoming=[], recently_released=[], scanned_at=NOW.date()),
            release_scan_reason=None, new_card_names=(), registered_events=(),
        )
        assert result.legality_state.value == "clear"
        assert result.wotc_state.value == "clear"
        assert result.release_state.value == "clear"
        assert result.unavailable_reasons == ()

    def test_signal_failures_retain_prior_state_and_are_never_false_clear(self, tmp_path):
        path = tmp_path / "state.json"
        baseline = merge_legality_observation(
            _empty_state(), observed=extract_legacy_legalities(_rows()),
            evidence=SCRYFALL, registered_events=(),
        ).model_copy(update={"next_wotc_announcement": NOW.date()})
        write_monitor_state(path, baseline)
        result = run_format_monitor(
            MonitorPorts(RuntimeError("bulk offline"), {}),
            state_path=path, observed_at=NOW,
            release_scan=None, release_scan_reason="sets offline", new_card_names=(),
            registered_events=(),
        )
        assert result.legality_state.value == "unavailable"
        assert result.wotc_state.value == "unavailable"
        assert result.release_state.value == "unavailable"
        assert len(result.unavailable_reasons) == 3
        assert load_monitor_state(path).last_good_legalities == baseline.last_good_legalities

    def test_wotc_action_opens_candidate_without_scryfall_transition(self, tmp_path):
        url = "https://magic.wizards.com/en/news/announcements/banned-and-restricted-august-11-2026"
        result = run_format_monitor(
            MonitorPorts(_rows(), {url: _wotc_page("Example Card is banned.")}),
            state_path=tmp_path / "state.json", observed_at=NOW,
            release_scan=ReleaseScan(upcoming=[], recently_released=[], scanned_at=NOW.date()),
            release_scan_reason=None, new_card_names=(), registered_events=(),
        )
        assert result.wotc_state.value == "pending"
        assert len([item for item in result.candidates if item.kind == "legality"]) == 1

    def test_wotc_redirect_outside_provider_is_unavailable(self, tmp_path):
        class RedirectPorts(MonitorPorts):
            def fetch_wotc(self, url):
                return _wotc_page(), "https://example.com/captured"

        result = run_format_monitor(
            RedirectPorts(_rows(), {}), state_path=tmp_path / "state.json", observed_at=NOW,
            release_scan=ReleaseScan(upcoming=[], recently_released=[], scanned_at=NOW.date()),
            release_scan_reason=None, new_card_names=(), registered_events=(),
        )
        assert result.wotc_state.value == "unavailable"
        assert "outside provider boundary" in result.unavailable_reasons[0]

    def test_release_metadata_needs_actual_new_card_diff(self, tmp_path):
        url = "https://magic.wizards.com/en/news/announcements/banned-and-restricted-august-11-2026"
        scan = ReleaseScan(
            upcoming=[],
            recently_released=[SetRelease(
                code="eoe", name="Edge of Eternities", released_at=NOW.date(),
            )],
            scanned_at=NOW.date(),
        )
        clear = run_format_monitor(
            MonitorPorts(_rows(), {url: _wotc_page()}),
            state_path=tmp_path / "state.json", observed_at=NOW,
            release_scan=scan, release_scan_reason=None, new_card_names=(), registered_events=(),
        )
        assert clear.release_state.value == "clear"
        pending = run_format_monitor(
            MonitorPorts(_rows(), {}),
            state_path=tmp_path / "state.json", observed_at=NOW + timedelta(days=1),
            release_scan=scan, release_scan_reason=None,
            new_card_names=("New Card",), registered_events=(),
        )
        assert pending.release_state.value == "pending"
        assert len([item for item in pending.candidates if item.kind == "release"]) == 1

    def test_audit_lines_keep_unavailable_and_pending_visible(self, tmp_path):
        result = run_format_monitor(
            MonitorPorts(RuntimeError("bulk offline"), {}),
            state_path=tmp_path / "state.json", observed_at=NOW,
            release_scan=None, release_scan_reason="sets offline", new_card_names=(),
            registered_events=(),
        )
        brief = format_monitor_audit_lines(result, brief=True)
        full = format_monitor_audit_lines(result)
        assert brief[0].startswith("// ⚠ format monitor:")
        assert "unavailable" in brief[0]
        assert any("pending action" in line for line in full)
