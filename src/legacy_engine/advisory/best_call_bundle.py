"""Offline, failure-safe multi-target Best Call artifact generation."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from .best_call_targets import ReportBundleManifest, ReportTarget, ReportTargetEntry, validate_targets

def _inject_manifest(path: Path, manifest: ReportBundleManifest) -> None:
    text = path.read_text(encoding="utf-8")
    payload = json.dumps(manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    addition = f'<script type="application/json" id="report-bundle-manifest">{payload}</script>'
    path.write_text(text.replace("</body>", addition + "</body>", 1), encoding="utf-8")

def generate_ranking_bundle(*, db_path, out_path, targets: tuple[ReportTarget, ...], **ranking_options) -> ReportBundleManifest:
    targets = validate_targets(targets)
    out_path = Path(out_path)
    generated: list[tuple[ReportTarget, Path]] = []
    try:
        from scripts.refresh_best_call_ranking import generate_ranking
        for target in targets:
            filename = out_path.name if target.mode == "current" else f"{out_path.stem}--{target.target_id}{out_path.suffix}"
            path = out_path.with_name(filename)
            generate_ranking(db_path=Path(db_path), out_path=path, field_since=target.field_since.isoformat(), data_until=target.effective_data_until.isoformat(), **ranking_options)
            generated.append((target, path))
        entries = tuple(ReportTargetEntry(target_id=t.target_id, label=t.label, mode_label=t.mode_label, data_until=t.data_until, effective_data_until=t.effective_data_until, knowledge_as_of=t.knowledge_as_of, href=p.name, status="available") for t, p in generated)
        manifest = ReportBundleManifest(selected_target_id=next(t.target_id for t in targets if t.mode == "current"), targets=entries, generated_at=datetime.now(UTC), status="complete")
        for _, path in generated:
            _inject_manifest(path, manifest)
        return manifest
    except Exception:
        for _, path in generated:
            if path != out_path:
                path.unlink(missing_ok=True)
        raise
