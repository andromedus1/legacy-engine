"""Typed report-target and offline bundle contracts."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from legacy_engine.models.base import LegacyEngineModel

class ReportTarget(LegacyEngineModel):
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

    def model_post_init(self, __context) -> None:
        if self.mode == "current" and self.mode_label != "Current":
            raise ValueError("current target must be labeled Current")
        if self.mode == "retrospective-current-model" and self.mode_label != "Today's model":
            raise ValueError("retrospective targets must be labeled Today's model")
        if self.knowledge_as_of.tzinfo is None:
            raise ValueError("knowledge_as_of must be timezone-aware")

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

class ReportBundleManifest(LegacyEngineModel):
    selected_target_id: str
    targets: tuple[ReportTargetEntry, ...]
    generated_at: datetime
    status: Literal["complete", "degraded"]
    reasons: tuple[str, ...] = ()

def validate_targets(targets: tuple[ReportTarget, ...]) -> tuple[ReportTarget, ...]:
    if not targets:
        raise ValueError("at least one report target is required")
    ids = [target.target_id for target in targets]
    if len(ids) != len(set(ids)):
        raise ValueError("report target ids must be unique")
    cutoffs = [target.effective_data_until for target in targets]
    if cutoffs != sorted(set(cutoffs)):
        raise ValueError("report target cutoffs must be ordered and unique")
    return targets
