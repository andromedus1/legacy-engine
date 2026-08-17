"""Deterministic, staged, failure-safe multi-target Best Call publication."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

from .best_call_generator import generate_ranking as _generate_ranking
from .best_call_targets import (
    ReportBundleManifest,
    ReportTarget,
    ReportTargetEntry,
    validate_targets,
)

def _safe_json(value: object) -> str:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _inject_manifest(path: Path, manifest: ReportBundleManifest) -> None:
    text = path.read_text(encoding="utf-8")
    payload = _safe_json(manifest.model_dump(mode="json"))
    addition = (
        '<script type="application/json" id="report-bundle-manifest">'
        f"{payload}</script>"
    )
    marker = "<script>\nconst D ="
    if marker not in text:
        raise ValueError("generated report lacks data-script marker")
    path.write_text(text.replace(marker, addition + marker, 1), encoding="utf-8")


def _filename(out_path: Path, target: ReportTarget) -> str:
    return (
        out_path.name
        if target.mode == "current"
        else f"{out_path.stem}--{target.target_id}{out_path.suffix}"
    )


def _replace_path(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def _publish(staged: Sequence[tuple[Path, Path]], backup_root: Path) -> None:
    """Replace a bundle and restore every prior artifact if any replacement fails."""
    backup_root.mkdir(parents=True, exist_ok=True)
    backups: dict[Path, Path | None] = {}
    for _source, destination in staged:
        if destination.exists():
            backup = backup_root / destination.name
            shutil.copy2(destination, backup)
            backups[destination] = backup
        else:
            backups[destination] = None
    replaced: list[Path] = []
    try:
        for source, destination in staged:
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Record the attempted destination first: a fault injector or filesystem shim may
            # raise after the atomic rename has already crossed the publication boundary.
            replaced.append(destination)
            _replace_path(source, destination)
    except Exception:
        for destination in reversed(replaced):
            backup = backups[destination]
            if backup is None:
                destination.unlink(missing_ok=True)
            else:
                _replace_path(backup, destination)
        raise


def generate_ranking_bundle(
    *,
    db_path,
    out_path,
    targets: tuple[ReportTarget, ...],
    generated_at: datetime | None = None,
    unavailable_reasons: Mapping[str, Sequence[str]] | None = None,
    **ranking_options,
) -> ReportBundleManifest:
    """Build the whole self-contained bundle before replacing any canonical artifact."""
    targets = validate_targets(targets)
    unavailable_reasons = unavailable_reasons or {}
    unknown = set(unavailable_reasons) - {target.target_id for target in targets}
    if unknown:
        raise ValueError(f"unavailable target ids are not in the target set: {sorted(unknown)!r}")
    current = next(target for target in targets if target.mode == "current")
    if current.target_id in unavailable_reasons:
        raise ValueError("the canonical current target cannot be unavailable")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Knowledge provenance is a deterministic generation clock unless the operator supplies one.
    emitted_at = generated_at or max(target.knowledge_as_of for target in targets)
    with tempfile.TemporaryDirectory(
        prefix=f".{out_path.stem}-bundle-", dir=out_path.parent
    ) as temporary:
        stage_root = Path(temporary)
        generated: dict[str, Path] = {}
        for target in targets:
            if target.target_id in unavailable_reasons:
                continue
            staged_path = stage_root / _filename(out_path, target)
            _generate_ranking(
                db_path=Path(db_path),
                out_path=staged_path,
                target=target,
                **ranking_options,
            )
            generated[target.target_id] = staged_path

        entries = tuple(
            ReportTargetEntry(
                target_id=target.target_id,
                label=target.label,
                mode_label=target.mode_label,
                data_until=target.data_until,
                effective_data_until=target.effective_data_until,
                knowledge_as_of=target.knowledge_as_of,
                href=(
                    _filename(out_path, target)
                    if target.target_id in generated
                    else None
                ),
                status=(
                    "available" if target.target_id in generated else "unavailable"
                ),
                reasons=tuple(unavailable_reasons.get(target.target_id, ())),
            )
            for target in targets
        )
        degraded = any(entry.status == "unavailable" for entry in entries)
        bundle_reasons = tuple(
            f"{entry.target_id}: {reason}"
            for entry in entries
            for reason in entry.reasons
        )
        manifests = {
            target_id: ReportBundleManifest(
                selected_target_id=target_id,
                targets=entries,
                generated_at=emitted_at,
                status="degraded" if degraded else "complete",
                reasons=bundle_reasons,
            )
            for target_id in generated
        }
        for target_id, path in generated.items():
            _inject_manifest(path, manifests[target_id])

        # Historical siblings first, canonical current last.  Every staged page already
        # carries the complete manifest; rollback restores the full prior target set.
        publication = [
            (generated[target.target_id], out_path.with_name(_filename(out_path, target)))
            for target in targets
            if target.target_id in generated and target.mode != "current"
        ]
        publication.append((generated[current.target_id], out_path))
        _publish(publication, stage_root / "backups")
        return manifests[current.target_id]
