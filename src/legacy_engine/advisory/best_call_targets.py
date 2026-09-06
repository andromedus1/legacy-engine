"""Typed report-target, data-audit, and offline-bundle contracts."""

from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import json
import re
from typing import Literal

from pydantic import model_validator

from legacy_engine.ingestion.banlist import BAN_EVENTS
from legacy_engine.models.base import LegacyEngineModel


_TARGET_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def confirmed_bans_before(cutoff: date) -> tuple[tuple[date, str, str], ...]:
    """Return confirmed actions effective strictly before an exclusive cutoff."""
    return tuple(event for event in BAN_EVENTS if event[0] < cutoff)


def target_regime(cutoff: date) -> tuple[date, tuple[str, ...]]:
    """Resolve the last confirmed ban boundary strictly before ``cutoff``."""
    eligible = confirmed_bans_before(cutoff)
    if not eligible:
        raise ValueError("report target cutoff has no confirmed prior ban boundary")
    boundary = max(event[0] for event in eligible)
    return boundary, tuple(event[1] for event in eligible if event[0] == boundary)


class ReportTarget(LegacyEngineModel):
    """One current or retrospective-current-model report target.

    ``data_until`` is the requested ranking cutoff.  Current ranking remains open on its
    frozen connection, so that field is null, while ``effective_data_until`` binds exact
    interval/certificate/amplification evidence to one finite exclusive clock.
    """

    target_id: str
    label: str
    mode: Literal["current", "retrospective-current-model"]
    mode_label: Literal["Current", "Today's model"]
    data_until: date | None = None
    effective_data_until: date
    knowledge_as_of: datetime
    field_since: date
    regime_card: str | None = None
    certificate_run_id: str | None = None
    amplification_run_id: str | None = None

    @model_validator(mode="after")
    def _target_contract(self) -> "ReportTarget":
        if not _TARGET_ID.fullmatch(self.target_id):
            raise ValueError("target_id must be a filesystem-safe kebab-case token")
        if not self.label.strip():
            raise ValueError("report target label must not be blank")
        if self.knowledge_as_of.tzinfo is None or self.knowledge_as_of.utcoffset() is None:
            raise ValueError("knowledge_as_of must be timezone-aware")
        if self.mode == "current":
            if self.mode_label != "Current" or self.data_until is not None:
                raise ValueError("current target requires label Current and data_until=None")
        elif (
            self.mode_label != "Today's model"
            or self.data_until is None
            or self.data_until != self.effective_data_until
        ):
            raise ValueError(
                "retrospective target requires Today's model and an exact effective cutoff"
            )
        if self.field_since >= self.effective_data_until:
            raise ValueError("field_since must precede the exclusive report cutoff")
        boundary, cards = target_regime(self.effective_data_until)
        if self.field_since != boundary:
            raise ValueError("field_since must equal the latest confirmed prior ban boundary")
        if self.regime_card not in cards:
            raise ValueError("regime_card must identify the target's confirmed ban boundary")
        if any(value is not None and not value.strip() for value in (
            self.certificate_run_id, self.amplification_run_id,
        )):
            raise ValueError("requested evidence run ids cannot be blank")
        return self


class ReportDataSectionAudit(LegacyEngineModel):
    section: Literal[
        "corpus",
        "field",
        "recent",
        "camps",
        "matchups",
        "plans",
        "affectedness",
        "interval-evidence",
    ]
    row_count: int
    max_event_date: date | None
    input_sha256: str

    @model_validator(mode="after")
    def _section_contract(self) -> "ReportDataSectionAudit":
        if self.row_count < 0:
            raise ValueError("report audit row counts cannot be negative")
        if not _SHA256.fullmatch(self.input_sha256):
            raise ValueError("report audit input digest must be lowercase sha256")
        return self


class ReportDataAudit(LegacyEngineModel):
    requested_data_until: date | None
    effective_data_until: date
    sections: tuple[ReportDataSectionAudit, ...]
    audit_sha256: str

    @model_validator(mode="after")
    def _audit_contract(self) -> "ReportDataAudit":
        names = tuple(section.section for section in self.sections)
        required = (
            "corpus", "field", "recent", "camps", "matchups", "plans",
            "affectedness", "interval-evidence",
        )
        if names != required:
            raise ValueError("report data audit requires every ordered outcome section")
        if self.requested_data_until not in (None, self.effective_data_until):
            raise ValueError("requested report cutoff must be null or the effective cutoff")
        if any(
            section.max_event_date is not None
            and section.max_event_date >= self.effective_data_until
            for section in self.sections
        ):
            raise ValueError("report audit contains data at or after its exclusive cutoff")
        if not _SHA256.fullmatch(self.audit_sha256):
            raise ValueError("report audit digest must be lowercase sha256")
        payload = {
            "requested_data_until": self.requested_data_until.isoformat()
            if self.requested_data_until
            else None,
            "effective_data_until": self.effective_data_until.isoformat(),
            "sections": [section.model_dump(mode="json") for section in self.sections],
        }
        expected = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if self.audit_sha256 != expected:
            raise ValueError("report data audit digest does not match its sections")
        return self


class ReportTargetEntry(LegacyEngineModel):
    target_id: str
    label: str
    mode_label: Literal["Current", "Today's model"]
    data_until: date | None
    effective_data_until: date
    knowledge_as_of: datetime
    href: str | None = None
    status: Literal["available", "unavailable"]
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _availability(self) -> "ReportTargetEntry":
        if not _TARGET_ID.fullmatch(self.target_id) or not self.label.strip():
            raise ValueError("manifest target identity is invalid")
        if self.knowledge_as_of.tzinfo is None or self.knowledge_as_of.utcoffset() is None:
            raise ValueError("manifest target knowledge clock must be timezone-aware")
        if self.mode_label == "Current" and self.data_until is not None:
            raise ValueError("current manifest target cannot expose a retrospective cutoff")
        if self.mode_label == "Today's model" and self.data_until != self.effective_data_until:
            raise ValueError("Today’s-model manifest target requires its exact cutoff")
        if self.status == "available" and (self.href is None or self.reasons):
            raise ValueError("available report target requires href and no reasons")
        if self.href is not None and (
            not self.href.strip() or "/" in self.href or "\\" in self.href or ":" in self.href
        ):
            raise ValueError("available report target href must be a relative sibling filename")
        if self.status == "unavailable" and (self.href is not None or not self.reasons):
            raise ValueError("unavailable report target requires reasons and no href")
        return self


class ReportBundleManifest(LegacyEngineModel):
    selected_target_id: str
    targets: tuple[ReportTargetEntry, ...]
    generated_at: datetime
    status: Literal["complete", "degraded"]
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _selected(self) -> "ReportBundleManifest":
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        selected = [x for x in self.targets if x.target_id == self.selected_target_id]
        if len(selected) != 1 or selected[0].status != "available":
            raise ValueError("selected target must be exactly one available manifest entry")
        ids = [target.target_id for target in self.targets]
        if len(ids) != len(set(ids)):
            raise ValueError("manifest report target ids must be unique")
        unavailable = [target for target in self.targets if target.status == "unavailable"]
        if self.status == "complete" and (unavailable or self.reasons):
            raise ValueError("complete report manifest cannot carry unavailable targets")
        if self.status == "degraded" and (not unavailable or not self.reasons):
            raise ValueError("degraded report manifest requires unavailable target reasons")
        return self


def validate_targets(targets: tuple[ReportTarget, ...]) -> tuple[ReportTarget, ...]:
    if not targets:
        raise ValueError("at least one report target is required")
    ids = [target.target_id for target in targets]
    if len(ids) != len(set(ids)):
        raise ValueError("report target ids must be unique")
    current = [target for target in targets if target.mode == "current"]
    if len(current) != 1:
        raise ValueError("report bundle requires exactly one current target")
    cutoffs = [target.effective_data_until for target in targets]
    if cutoffs != sorted(set(cutoffs)):
        raise ValueError("report target cutoffs must be ordered and unique")
    return targets
