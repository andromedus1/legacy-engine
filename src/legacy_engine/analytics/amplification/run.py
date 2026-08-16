from __future__ import annotations
import json
from hashlib import sha256
from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.analytics.matchup import IntervalAdaptiveMatrix
from .corpus import build_interval_evidence_corpus, build_direct_baselines
from .models import AmplificationProfile, IntervalEvidenceCorpus, DirectBaseline
from .hierarchical import fit_component_hierarchy, predict_component_hierarchy
from .composition import fit_composition_kernel, predict_composition_kernel
from .family import fit_family_ladders, predict_family_ladders
from .low_rank import fit_skew_low_rank, predict_skew_low_rank


class CandidateResult(LegacyEngineModel):
    method_id: str
    fit_id: str
    predictions: tuple
    all_case_pairs: tuple[str, ...] = ()
    served_pairs: tuple[str, ...] = ()
    status: str = "complete"
    reasons: tuple[str, ...] = ()


class ComparisonAudit(LegacyEngineModel):
    common_corpus_id: str
    common_pair_universe_sha256: str
    common_outcome_ids_sha256: str
    baseline_sha256: str
    per_method_input_sha256: dict[str, str]
    fair: bool = True
    reasons: tuple[str, ...] = ()


class AmplificationRun(LegacyEngineModel):
    run_id: str
    corpus: IntervalEvidenceCorpus
    profile_id: str
    profile_sha256: str
    structure_snapshot_id: str
    baselines: dict[str, DirectBaseline]
    candidates: tuple[CandidateResult, ...]
    comparison: ComparisonAudit
    authority: str = "diagnostic-only"
    status: str = "complete"
    reasons: tuple[str, ...] = ()


def run_amplification(
    interval: IntervalAdaptiveMatrix, structure, profile: AmplificationProfile
) -> AmplificationRun:
    corpus = build_interval_evidence_corpus(interval)
    baselines = build_direct_baselines(interval)
    candidates = []
    jobs = [
        (
            "component-hierarchical-v1",
            lambda: (
                fit_component_hierarchy(corpus, profile),
                lambda fit: predict_component_hierarchy(fit, corpus, baselines),
            ),
        ),
        (
            "composition-kernel-v1",
            lambda: (
                fit_composition_kernel(corpus, structure, profile),
                lambda fit: predict_composition_kernel(fit, corpus, baselines, profile),
            ),
        ),
        (
            "strategic-family-ladder-v1",
            lambda: (
                fit_family_ladders(corpus, structure, profile),
                lambda fit: predict_family_ladders(fit, corpus, baselines, profile),
            ),
        ),
    ]
    for rank in (1, 2, 4):
        jobs.append(
            (
                f"skew-low-rank-r{rank}-v1",
                lambda rank=rank: (
                    fit_skew_low_rank(corpus, rank=rank, profile=profile),
                    lambda fit: predict_skew_low_rank(fit, corpus, baselines, profile),
                ),
            )
        )
    for method, job in jobs:
        try:
            fit, predict = job()
            values = predict(fit)
            preds = tuple(values.values())
            candidates.append(
                CandidateResult(
                    method_id=method,
                    fit_id=fit.fit_id,
                    predictions=preds,
                    all_case_pairs=tuple(f"{a}::{b}" for a, b in sorted(baselines)),
                    served_pairs=tuple(
                        f"{p.subject}::{p.opponent}" for p in preds if p.served
                    ),
                )
            )
        except Exception as exc:
            candidates.append(
                CandidateResult(
                    method_id=method,
                    fit_id="",
                    predictions=(),
                    status="degraded",
                    reasons=(f"{type(exc).__name__}: {exc}",),
                )
            )
    pair_digest = sha256(
        json.dumps(sorted(f"{a}::{b}" for a, b in baselines)).encode()
    ).hexdigest()
    outcome_digest = sha256(
        json.dumps(sorted(row.match_id for row in corpus.outcomes)).encode()
    ).hexdigest()
    baseline_digest = sha256(
        json.dumps(
            {k: v.expanded_sha256 for k, v in sorted(baselines.items())}, sort_keys=True
        ).encode()
    ).hexdigest()
    audit = ComparisonAudit(
        common_corpus_id=corpus.corpus_id,
        common_pair_universe_sha256=pair_digest,
        common_outcome_ids_sha256=outcome_digest,
        baseline_sha256=baseline_digest,
        per_method_input_sha256={c.method_id: corpus.corpus_id for c in candidates},
    )
    payload = {
        "corpus": corpus.model_dump(mode="json"),
        "profile": profile.model_dump(mode="json"),
        "structure": structure.snapshot_id,
        "baselines": {k: v.model_dump(mode="json") for k, v in baselines.items()},
        "candidates": [c.model_dump(mode="json") for c in candidates],
    }
    run_id = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return AmplificationRun(
        run_id=run_id,
        corpus=corpus,
        profile_id=profile.profile_id,
        profile_sha256=sha256(
            json.dumps(profile.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest(),
        structure_snapshot_id=structure.snapshot_id,
        baselines={f"{a}::{b}": v for (a, b), v in baselines.items()},
        candidates=tuple(candidates),
        comparison=audit,
        status="complete"
        if all(c.status == "complete" for c in candidates)
        else "degraded",
    )
