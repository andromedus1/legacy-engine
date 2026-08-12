"""Pure format-change state and candidate transitions.

Machine observations live under ``data/ops`` and never mutate the curated B&R
ledger.  The only authority for accepted Legacy bans remains ``eras confirm``.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterable
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import field_validator

from legacy_engine.ingestion.scryfall import normalize_name
from legacy_engine.models.base import LegacyEngineModel

if TYPE_CHECKING:
    from legacy_engine.ingestion.ban_monitor import WotcAnnouncement
    from legacy_engine.ingestion.releases import ReleaseScan


LegacyLegality = Literal["legal", "not_legal", "restricted", "banned"]
LEGALITY_VALUES = frozenset({"legal", "not_legal", "restricted", "banned"})


class SignalState(StrEnum):
    CLEAR = "clear"
    PENDING = "pending"
    NOT_DUE = "not_due"
    UNAVAILABLE = "unavailable"


class CandidateDisposition(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CONFIRMED = "confirmed"


class LegalityObservation(LegacyEngineModel):
    oracle_id: str | None = None
    name: str
    legacy: LegacyLegality


class MonitorEvidence(LegacyEngineModel):
    source: Literal["scryfall", "wotc", "scryfall_sets", "card_diff"]
    source_url: str
    observed_at: datetime
    effective_date: date | None = None
    detail: str

    @field_validator("observed_at")
    @classmethod
    def _aware_time(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("monitor evidence observed_at must be timezone-aware")
        return value


class FormatCandidate(LegacyEngineModel):
    candidate_id: str
    kind: Literal["legality", "release"]
    subject_id: str
    subject_name: str
    prior_value: str | None = None
    current_value: str
    disposition: CandidateDisposition = CandidateDisposition.OPEN
    evidence: tuple[MonitorEvidence, ...]
    evidence_hash: str
    acknowledged_evidence_hash: str | None = None
    unsupported_acceptance_reason: str | None = None


class FormatMonitorState(LegacyEngineModel):
    schema_version: Literal[1] = 1
    legality_baseline_observed_at: datetime | None = None
    last_good_legalities: tuple[LegalityObservation, ...] = ()
    candidates: tuple[FormatCandidate, ...] = ()
    next_wotc_announcement: date | None = None
    last_good_wotc_url: str | None = None
    updated_at: datetime

    @field_validator("legality_baseline_observed_at", "updated_at")
    @classmethod
    def _aware_times(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("format-monitor timestamps must be timezone-aware")
        return value


class FormatMonitorResult(LegacyEngineModel):
    legality_state: SignalState
    wotc_state: SignalState
    release_state: SignalState
    candidates: tuple[FormatCandidate, ...]
    pending_actions: tuple[str, ...] = ()
    unavailable_reasons: tuple[str, ...] = ()


class FormatMonitorPorts(Protocol):
    def oracle_rows(self) -> Iterable[dict[str, object]]: ...
    def fetch_wotc(self, url: str) -> str: ...


class DefaultFormatMonitorPorts:
    """Production external adapters; monitor orchestration remains hermetic."""

    def oracle_rows(self) -> Iterable[dict[str, object]]:
        from legacy_engine.ingestion.scryfall import ORACLE_CARDS_PATH, iter_bulk_rows

        return iter_bulk_rows(ORACLE_CARDS_PATH)

    def fetch_wotc(self, url: str) -> str:
        import httpx

        from legacy_engine.config import USER_AGENT

        response = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            follow_redirects=True,
            timeout=30.0,
        )
        if response.status_code == 404:
            raise FileNotFoundError(url)
        response.raise_for_status()
        return response.text


def _subject_id(observation: LegalityObservation) -> str:
    return observation.oracle_id or normalize_name(observation.name).casefold()


def extract_legacy_legalities(
    rows: Iterable[dict[str, object]],
) -> tuple[LegalityObservation, ...]:
    """Validate and normalize the Legacy legality projection from oracle rows."""
    observations: dict[str, LegalityObservation] = {}
    for index, row in enumerate(rows):
        name = row.get("name")
        legalities = row.get("legalities")
        oracle_id = row.get("oracle_id")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Scryfall legality row {index} is missing required name")
        if oracle_id is not None and (not isinstance(oracle_id, str) or not oracle_id.strip()):
            raise ValueError(f"Scryfall legality row {index} has invalid oracle_id")
        if not isinstance(legalities, dict):
            raise ValueError(f"Scryfall legality row {index} is missing legalities")
        legacy = legalities.get("legacy")
        if legacy not in LEGALITY_VALUES:
            raise ValueError(
                f"Scryfall legality row {index} has unknown Legacy legality {legacy!r}; "
                f"expected one of {sorted(LEGALITY_VALUES)}"
            )
        observation = LegalityObservation(
            oracle_id=oracle_id,
            name=normalize_name(name),
            legacy=legacy,
        )
        key = _subject_id(observation)
        if key in observations:
            raise ValueError(f"duplicate Scryfall legality identity {key!r}")
        observations[key] = observation
    if not observations:
        raise ValueError("Scryfall legality snapshot contains no rows")
    return tuple(observations[key] for key in sorted(observations))


def _candidate_id(
    subject_id: str, prior_value: str, current_value: str,
) -> str:
    payload = f"legacy\0{subject_id}\0{prior_value}\0{current_value}".encode()
    return hashlib.sha256(payload).hexdigest()


def _release_candidate_id(set_codes: tuple[str, ...], new_names: tuple[str, ...]) -> str:
    payload = json.dumps(
        ["legacy", "release", sorted(code.casefold() for code in set_codes), sorted(new_names)],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _evidence_key(evidence: MonitorEvidence) -> tuple[str, str, str, str]:
    return (
        evidence.source,
        evidence.source_url,
        evidence.effective_date.isoformat() if evidence.effective_date else "",
        evidence.detail,
    )


def _evidence_hash(evidence: tuple[MonitorEvidence, ...]) -> str:
    semantic = sorted(_evidence_key(item) for item in evidence)
    payload = json.dumps(semantic, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _merge_evidence(
    prior: tuple[MonitorEvidence, ...], incoming: Iterable[MonitorEvidence],
) -> tuple[MonitorEvidence, ...]:
    by_key = {_evidence_key(item): item for item in prior}
    for item in incoming:
        key = _evidence_key(item)
        existing = by_key.get(key)
        if existing is None or item.observed_at < existing.observed_at:
            by_key[key] = item
    return tuple(by_key[key] for key in sorted(by_key))


def _is_registered(
    candidate: FormatCandidate,
    registered_events: tuple[tuple[date, str, str], ...],
) -> bool:
    if candidate.current_value != "banned":
        return False
    normalized = normalize_name(candidate.subject_name)
    return any(normalize_name(card) == normalized for _when, card, _reason in registered_events)


def merge_legality_observation(
    state: FormatMonitorState,
    *,
    observed: tuple[LegalityObservation, ...],
    evidence: MonitorEvidence,
    registered_events: tuple[tuple[date, str, str], ...],
) -> FormatMonitorState:
    """Merge one fully validated snapshot without ever changing curated truth."""
    if not observed:
        raise ValueError("cannot merge an empty legality observation")
    current = {_subject_id(item): item for item in observed}
    if len(current) != len(observed):
        raise ValueError("legality observation contains duplicate identities")

    if state.legality_baseline_observed_at is None:
        return state.model_copy(update={
            "legality_baseline_observed_at": evidence.observed_at,
            "last_good_legalities": observed,
            "updated_at": evidence.observed_at,
        })

    prior = {_subject_id(item): item for item in state.last_good_legalities}
    missing = sorted(set(prior) - set(current))
    if missing:
        raise ValueError(
            f"Scryfall legality snapshot lost {len(missing)} prior identities; "
            f"first missing={missing[0]!r}"
        )

    candidates = {item.candidate_id: item for item in state.candidates}
    for subject_id in sorted(set(prior) & set(current)):
        before = prior[subject_id]
        after = current[subject_id]
        if before.legacy == after.legacy:
            continue
        candidate_id = _candidate_id(subject_id, before.legacy, after.legacy)
        old = candidates.get(candidate_id)
        if old is None:
            name_key = normalize_name(after.name).casefold()
            matching = [
                item for item in candidates.values()
                if item.kind == "legality"
                and normalize_name(item.subject_name).casefold() == name_key
                and item.prior_value == before.legacy
                and item.current_value == after.legacy
            ]
            if len(matching) > 1:
                raise ValueError(
                    f"ambiguous monitor candidates for Scryfall transition {after.name!r}"
                )
            if matching:
                old = matching[0]
                candidates.pop(old.candidate_id)
        merged_evidence = _merge_evidence(old.evidence if old else (), (evidence,))
        evidence_hash = _evidence_hash(merged_evidence)
        acknowledged_hash = old.acknowledged_evidence_hash if old else None
        disposition = (
            CandidateDisposition.ACKNOWLEDGED
            if acknowledged_hash == evidence_hash
            else CandidateDisposition.OPEN
        )
        unsupported = None
        if not (before.legacy == "legal" and after.legacy == "banned"):
            unsupported = (
                f"eras confirm cannot represent Legacy {before.legacy}->{after.legacy}; "
                "requires a separately designed ledger evolution"
            )
        candidate = FormatCandidate(
            candidate_id=candidate_id,
            kind="legality",
            subject_id=subject_id,
            subject_name=after.name,
            prior_value=before.legacy,
            current_value=after.legacy,
            disposition=disposition,
            evidence=merged_evidence,
            evidence_hash=evidence_hash,
            acknowledged_evidence_hash=acknowledged_hash,
            unsupported_acceptance_reason=unsupported,
        )
        if _is_registered(candidate, registered_events):
            candidates.pop(candidate_id, None)
        else:
            candidates[candidate_id] = candidate

    candidates = {
        key: candidate for key, candidate in candidates.items()
        if not _is_registered(candidate, registered_events)
    }
    return state.model_copy(update={
        "legality_baseline_observed_at": evidence.observed_at,
        "last_good_legalities": observed,
        "candidates": tuple(candidates[key] for key in sorted(candidates)),
        "updated_at": evidence.observed_at,
    })


def add_candidate_evidence(
    state: FormatMonitorState,
    candidate_id: str,
    evidence: MonitorEvidence,
) -> FormatMonitorState:
    """Enrich one exact candidate; materially new evidence reopens it."""
    candidates = list(state.candidates)
    for index, candidate in enumerate(candidates):
        if candidate.candidate_id != candidate_id:
            continue
        merged = _merge_evidence(candidate.evidence, (evidence,))
        evidence_hash = _evidence_hash(merged)
        disposition = (
            CandidateDisposition.ACKNOWLEDGED
            if candidate.acknowledged_evidence_hash == evidence_hash
            else CandidateDisposition.OPEN
        )
        candidates[index] = candidate.model_copy(update={
            "evidence": merged,
            "evidence_hash": evidence_hash,
            "disposition": disposition,
        })
        return state.model_copy(update={
            "candidates": tuple(candidates),
            "updated_at": evidence.observed_at,
        })
    raise ValueError(f"unknown format-monitor candidate id: {candidate_id}")


def merge_wotc_announcement(
    state: FormatMonitorState,
    announcement: "WotcAnnouncement",
    *,
    observed_at: datetime,
) -> FormatMonitorState:
    """Correlate attributable WotC actions to candidates by exact normalized name."""
    candidates = {candidate.candidate_id: candidate for candidate in state.candidates}
    for action in announcement.legacy_actions:
        name_key = normalize_name(action.card).casefold()
        current_value = {
            "banned": "banned", "unbanned": "legal",
            "restricted": "restricted", "unrestricted": "legal",
        }[action.action]
        prior_value = "banned" if action.action in {"unbanned", "unrestricted"} else "legal"
        matching = [
            candidate for candidate in candidates.values()
            if normalize_name(candidate.subject_name).casefold() == name_key
            and candidate.current_value == current_value
        ]
        if len(matching) > 1:
            raise ValueError(f"ambiguous monitor candidates for WotC action {action.card!r}")
        evidence = MonitorEvidence(
            source="wotc",
            source_url=announcement.source_url,
            observed_at=observed_at,
            effective_date=announcement.effective_date,
            detail=f"{action.card} is {action.action}.",
        )
        if matching:
            candidate = matching[0]
            state = add_candidate_evidence(state, candidate.candidate_id, evidence)
            candidates = {item.candidate_id: item for item in state.candidates}
            continue
        subject_id = name_key
        candidate_id = _candidate_id(subject_id, prior_value, current_value)
        evidence_tuple = (evidence,)
        unsupported = None
        if not (prior_value == "legal" and current_value == "banned"):
            unsupported = (
                f"eras confirm cannot represent Legacy {prior_value}->{current_value}; "
                "requires a separately designed ledger evolution"
            )
        candidates[candidate_id] = FormatCandidate(
            candidate_id=candidate_id,
            kind="legality",
            subject_id=subject_id,
            subject_name=normalize_name(action.card),
            prior_value=prior_value,
            current_value=current_value,
            evidence=evidence_tuple,
            evidence_hash=_evidence_hash(evidence_tuple),
            unsupported_acceptance_reason=unsupported,
        )
        state = state.model_copy(update={
            "candidates": tuple(candidates[key] for key in sorted(candidates)),
            "updated_at": observed_at,
        })
    return state.model_copy(update={
        "next_wotc_announcement": announcement.next_announcement,
        "last_good_wotc_url": announcement.source_url,
        "updated_at": observed_at,
    })


def merge_release_observation(
    state: FormatMonitorState,
    *,
    release_scan: "ReleaseScan",
    new_card_names: tuple[str, ...],
    observed_at: datetime,
    source_url: str,
) -> FormatMonitorState:
    """Record recent sets only when the authoritative card ingest saw new names."""
    if not new_card_names:
        return state
    candidates = {candidate.candidate_id: candidate for candidate in state.candidates}
    detail = f"{len(new_card_names)} new card name(s): {', '.join(sorted(new_card_names)[:10])}"
    recent = tuple(sorted(release_scan.recently_released, key=lambda item: item.code))
    if not recent:
        return state
    codes = tuple(item.code for item in recent)
    candidate_id = _release_candidate_id(codes, new_card_names)
    evidence = MonitorEvidence(
        source="card_diff", source_url=source_url, observed_at=observed_at,
        effective_date=max(
            (item.released_at for item in recent if item.released_at is not None),
            default=None,
        ),
        detail=detail,
    )
    old = candidates.get(candidate_id)
    merged = _merge_evidence(old.evidence if old else (), (evidence,))
    evidence_hash = _evidence_hash(merged)
    acknowledged_hash = old.acknowledged_evidence_hash if old else None
    candidates[candidate_id] = FormatCandidate(
        candidate_id=candidate_id,
        kind="release",
        subject_id="+".join(code.casefold() for code in codes),
        subject_name="New card ingest during recent set window: "
        + ", ".join(f"{item.code} ({item.name})" for item in recent),
        current_value=f"{len(new_card_names)} new card name(s)",
        disposition=(CandidateDisposition.ACKNOWLEDGED
                     if acknowledged_hash == evidence_hash else CandidateDisposition.OPEN),
        evidence=merged,
        evidence_hash=evidence_hash,
        acknowledged_evidence_hash=acknowledged_hash,
    )
    return state.model_copy(update={
        "candidates": tuple(candidates[key] for key in sorted(candidates)),
        "updated_at": observed_at,
    })


def _project_result(
    state: FormatMonitorState,
    *,
    legality_state: SignalState,
    wotc_state: SignalState,
    release_state: SignalState,
    unavailable_reasons: Iterable[str] = (),
) -> FormatMonitorResult:
    unavailable = tuple(unavailable_reasons)
    pending: list[str] = []
    for candidate in state.candidates:
        if candidate.disposition is CandidateDisposition.ACKNOWLEDGED:
            continue
        action = (
            candidate.unsupported_acceptance_reason
            or (f"review and confirm with eras confirm: {candidate.subject_name}"
                if candidate.kind == "legality" else
                f"review new release evidence: {candidate.subject_name}")
        )
        pending.append(f"format candidate {candidate.candidate_id}: {action}")
    pending.extend(f"format monitor unavailable: {reason}" for reason in unavailable)
    return FormatMonitorResult(
        legality_state=legality_state,
        wotc_state=wotc_state,
        release_state=release_state,
        candidates=state.candidates,
        pending_actions=tuple(pending),
        unavailable_reasons=unavailable,
    )


def run_format_monitor(
    ports: FormatMonitorPorts,
    *,
    state_path: Path,
    observed_at: datetime,
    release_scan: "ReleaseScan | None",
    release_scan_reason: str | None,
    new_card_names: tuple[str, ...],
    registered_events: tuple[tuple[date, str, str], ...],
) -> FormatMonitorResult:
    """Run all monitor signals while preserving each signal's last-good evidence."""
    from legacy_engine.ingestion.ban_monitor import (
        announcement_candidate_urls,
        parse_wotc_legacy_announcement,
    )

    if observed_at.utcoffset() is None:
        raise ValueError("format monitor observed_at must be timezone-aware")
    state = load_monitor_state(state_path) or FormatMonitorState(updated_at=observed_at)
    reasons: list[str] = []

    try:
        observed = extract_legacy_legalities(ports.oracle_rows())
        state = merge_legality_observation(
            state,
            observed=observed,
            evidence=MonitorEvidence(
                source="scryfall",
                source_url="https://data.scryfall.io/oracle-cards",
                observed_at=observed_at,
                detail="Legacy legalities bulk snapshot",
            ),
            registered_events=registered_events,
        )
        legality_state = (
            SignalState.PENDING
            if any(candidate.kind == "legality" for candidate in state.candidates)
            else SignalState.CLEAR
        )
    except Exception as exc:
        legality_state = SignalState.UNAVAILABLE
        reasons.append(f"Scryfall legality check: {exc}")

    expected = state.next_wotc_announcement or observed_at.date()
    if observed_at.date() < expected:
        wotc_state = SignalState.NOT_DUE
    else:
        announcement = None
        missing = 0
        try:
            for url in announcement_candidate_urls(expected):
                try:
                    html = ports.fetch_wotc(url)
                except FileNotFoundError:
                    missing += 1
                    continue
                announcement = parse_wotc_legacy_announcement(html, source_url=url)
                break
            if announcement is None:
                raise ValueError(
                    f"no announcement page found in {missing} bounded URL candidate(s)"
                )
            state = merge_wotc_announcement(state, announcement, observed_at=observed_at)
            wotc_state = (
                SignalState.PENDING if announcement.legacy_actions else SignalState.CLEAR
            )
        except Exception as exc:
            wotc_state = SignalState.UNAVAILABLE
            reasons.append(f"WotC attribution check: {exc}")

    if release_scan_reason is not None:
        release_state = SignalState.UNAVAILABLE
        reasons.append(f"release check: {release_scan_reason}")
    elif release_scan is None:
        release_state = SignalState.UNAVAILABLE
        reasons.append("release check: no typed release observation")
    else:
        state = merge_release_observation(
            state,
            release_scan=release_scan,
            new_card_names=new_card_names,
            observed_at=observed_at,
            source_url="https://api.scryfall.com/sets",
        )
        release_state = (
            SignalState.PENDING
            if new_card_names and release_scan.recently_released
            else SignalState.CLEAR
        )

    write_monitor_state(state_path, state)
    return _project_result(
        state,
        legality_state=legality_state,
        wotc_state=wotc_state,
        release_state=release_state,
        unavailable_reasons=reasons,
    )


def format_monitor_audit_lines(
    result: FormatMonitorResult, *, brief: bool = False,
) -> tuple[str, ...]:
    """Render signal and candidate state using the project audit-line convention."""
    signal_values = (
        f"legality={result.legality_state.value}, wotc={result.wotc_state.value}, "
        f"releases={result.release_state.value}"
    )
    warning = bool(result.pending_actions or result.unavailable_reasons)
    prefix = "// ⚠" if warning else "//"
    lines = [f"{prefix} format monitor: {signal_values}"]
    if brief:
        if result.pending_actions:
            lines[0] += f" — {len(result.pending_actions)} pending operator action(s)"
        return tuple(lines)
    for candidate in result.candidates:
        lines.append(
            f"// format candidate: {candidate.candidate_id} — {candidate.kind} — "
            f"{candidate.disposition.value} — {candidate.subject_name}: "
            f"{candidate.prior_value or 'n/a'} -> {candidate.current_value}"
        )
    lines.extend(f"// ⚠ pending action: {action}" for action in result.pending_actions)
    return tuple(lines)


def acknowledge_candidate(
    state: FormatMonitorState, candidate_id: str, *, acknowledged_at: datetime,
) -> FormatMonitorState:
    """Acknowledge exactly the evidence currently attached to one candidate."""
    if acknowledged_at.utcoffset() is None:
        raise ValueError("acknowledgement time must be timezone-aware")
    candidates = list(state.candidates)
    for index, candidate in enumerate(candidates):
        if candidate.candidate_id != candidate_id:
            continue
        candidates[index] = candidate.model_copy(update={
            "disposition": CandidateDisposition.ACKNOWLEDGED,
            "acknowledged_evidence_hash": candidate.evidence_hash,
        })
        return state.model_copy(update={
            "candidates": tuple(candidates),
            "updated_at": acknowledged_at,
        })
    raise ValueError(f"unknown format-monitor candidate id: {candidate_id}")


def load_monitor_state(path: Path) -> FormatMonitorState | None:
    if not path.exists():
        return None
    return FormatMonitorState.model_validate_json(path.read_text(encoding="utf-8"))


def write_monitor_state(path: Path, state: FormatMonitorState) -> None:
    """Atomically replace monitor state; a failed replace preserves last-good."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(state.model_dump_json(indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
