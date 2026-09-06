from __future__ import annotations

import copy
import json
from collections import Counter
from typing import Literal

import numpy as np
from pydantic import ConfigDict

from legacy_engine.analytics.matchup import IntervalAdaptiveMatrix
from legacy_engine.models.base import LegacyEngineModel

from ._common import digest, summary
from .composition import fit_composition_kernel, predict_composition_kernel
from .corpus import (
    build_direct_baselines,
    build_interval_evidence_corpus,
    pair_from_key,
)
from .family import fit_family_ladders, predict_family_ladders
from .hierarchical import fit_component_hierarchy, predict_component_hierarchy
from .low_rank import fit_skew_low_rank, predict_skew_low_rank
from .models import (
    AlignedDrawSeries,
    AmplificationProfile,
    ChallengerPrediction,
    DirectBaseline,
    EventBootstrapPlan,
    IntervalEvidenceCorpus,
    JointPredictiveDraws,
    MethodId,
    StructureSnapshot,
)


class _ClosedModel(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid")


class CandidateResult(_ClosedModel):
    method_id: MethodId
    fit_id: str
    predictions: tuple[ChallengerPrediction, ...]
    all_case_pairs: tuple[str, ...] = ()
    served_pairs: tuple[str, ...] = ()
    status: Literal["complete", "degraded", "failed"] = "complete"
    reasons: tuple[str, ...] = ()


class ComparisonAudit(_ClosedModel):
    audit_id: str
    common_corpus_id: str
    common_pair_universe_sha256: str
    common_outcome_ids_sha256: str
    baseline_sha256: str
    per_method_input_sha256: dict[MethodId, str]
    fair: bool = True
    reasons: tuple[str, ...] = ()
    aligned_draws_sha256: str | None = None


class AmplificationRun(_ClosedModel):
    run_id: str
    corpus: IntervalEvidenceCorpus
    profile: AmplificationProfile
    profile_sha256: str
    structure: StructureSnapshot
    baselines: dict[str, DirectBaseline]
    candidates: tuple[CandidateResult, ...]
    comparison: ComparisonAudit
    authority: Literal["diagnostic-only"] = "diagnostic-only"
    status: Literal["complete", "degraded", "failed"] = "complete"
    reasons: tuple[str, ...] = ()
    aligned_draws: JointPredictiveDraws | None = None

    @property
    def profile_id(self) -> str:
        return self.profile.profile_id

    @property
    def structure_snapshot_id(self) -> str:
        return self.structure.snapshot_id


def _complement_summary(value):
    if value is None:
        return None
    return value.model_copy(
        update={
            "mean": 1 - value.mean,
            "median": 1 - value.median,
            "ci_low": 1 - value.ci_high,
            "ci_high": 1 - value.ci_low,
        }
    )


def _complement_prediction(value, subject, opponent):
    ablations = value.ablations
    probability_fields = (
        "direct_baseline",
        "without_certified_history",
        "without_borrowing",
        "leave_target_pair_out",
        "full",
    )
    updates = {
        name: None if getattr(ablations, name) is None else 1 - getattr(ablations, name)
        for name in probability_fields
    }
    for name in ("history_delta", "borrowing_delta", "nonadditive_remainder"):
        updates[name] = (
            None if getattr(ablations, name) is None else -getattr(ablations, name)
        )
    return value.model_copy(
        update={
            "subject": subject,
            "opponent": opponent,
            "all_case": _complement_summary(value.all_case),
            "served": _complement_summary(value.served),
            "ablations": ablations.model_copy(update=updates),
        }
    )


def _derive_reverse_predictions(values, baselines):
    result = dict(values)
    for key in sorted(baselines):
        subject, opponent = pair_from_key(key)
        if subject < opponent:
            continue
        canonical = json.dumps(
            [opponent, subject], ensure_ascii=False, separators=(",", ":")
        )
        if canonical in result:
            result[key] = _complement_prediction(result[canonical], subject, opponent)
    return result


def _method_run(method_id, corpus, structure, profile, baselines, *, diagnostics=True):
    if method_id == "component-hierarchical-v1":
        fit = fit_component_hierarchy(corpus, profile)
        values = predict_component_hierarchy(fit, corpus, baselines, profile)
        return fit, _derive_reverse_predictions(values, baselines)
    if method_id == "composition-kernel-v1":
        fit = fit_composition_kernel(corpus, structure, profile)
        values = predict_composition_kernel(fit, corpus, baselines, profile)
        return fit, _derive_reverse_predictions(values, baselines)
    if method_id == "strategic-family-ladder-v1":
        fit = fit_family_ladders(corpus, structure, profile)
        values = predict_family_ladders(fit, corpus, baselines, profile, structure)
        return fit, _derive_reverse_predictions(values, baselines)
    rank = int(method_id.removeprefix("skew-low-rank-r").removesuffix("-v1"))
    fit = fit_skew_low_rank(corpus, rank=rank, profile=profile)
    values = predict_skew_low_rank(
        fit, corpus, baselines, profile, diagnostics=diagnostics
    )
    return fit, _derive_reverse_predictions(values, baselines)


def make_event_bootstrap_plan(corpus, *, origin_snapshot_id, seed, replicates):
    events = tuple(sorted({row.event_id for row in corpus.outcomes}))
    rng = np.random.default_rng(seed)
    blocks = tuple(
        tuple(str(x) for x in rng.choice(events, size=len(events), replace=True))
        if events
        else ()
        for _ in range(replicates)
    )
    payload = {
        "origin_snapshot_id": origin_snapshot_id,
        "seed": seed,
        "event_blocks": blocks,
    }
    return EventBootstrapPlan(
        plan_id=digest(payload),
        origin_snapshot_id=origin_snapshot_id,
        seed=seed,
        event_blocks=blocks,
    )


def _validate_plan(plan, corpus, origin_snapshot_id, profile):
    if plan.origin_snapshot_id != origin_snapshot_id or plan.seed != profile.seed:
        raise ValueError("bootstrap plan origin or seed mismatch")
    if len(plan.event_blocks) != profile.bootstrap_replicates:
        raise ValueError("bootstrap plan replicate count mismatch")
    if plan.plan_id != digest(
        {
            "origin_snapshot_id": plan.origin_snapshot_id,
            "seed": plan.seed,
            "event_blocks": plan.event_blocks,
        }
    ):
        raise ValueError("bootstrap plan content digest mismatch")
    known = {row.event_id for row in corpus.outcomes}
    if any(event not in known for block in plan.event_blocks for event in block):
        raise ValueError("bootstrap plan contains an unavailable event")


def _resampled_corpus(corpus, block, replicate):
    by_event = {
        event: tuple(row for row in corpus.outcomes if row.event_id == event)
        for event in set(block)
    }
    rows = tuple(row for event in block for row in by_event[event])
    return corpus.model_copy(
        update={
            "corpus_id": digest(
                {"origin": corpus.corpus_id, "replicate": replicate, "events": block}
            ),
            "outcomes": rows,
        }
    )


def joint_draws_identity(draws: JointPredictiveDraws) -> str:
    return digest(
        {
            "origin_snapshot_id": draws.origin_snapshot_id,
            "seed": draws.seed,
            "replicate_count": draws.replicate_count,
            "replay_plan": draws.replay_plan.model_dump(mode="json"),
            "event_blocks_sha256": draws.event_blocks_sha256,
            "method_ids": draws.method_ids,
            "series": [x.model_dump(mode="json") for x in draws.series],
            "draws_sha256": draws.draws_sha256,
        }
    )


def comparison_audit_identity(audit: ComparisonAudit) -> str:
    payload = audit.model_dump(mode="json", exclude={"audit_id"})
    return digest(payload)


def amplification_run_identity(run: AmplificationRun) -> str:
    return digest(run.model_dump(mode="json", exclude={"run_id"}))


def run_amplification(
    interval: IntervalAdaptiveMatrix,
    structure: StructureSnapshot,
    profile: AmplificationProfile,
    *,
    origin_snapshot_id: str | None = None,
    bootstrap_plan: EventBootstrapPlan | None = None,
) -> AmplificationRun:
    corpus = build_interval_evidence_corpus(interval)
    if structure.knowledge_as_of > corpus.clock.knowledge_as_of:
        raise ValueError("structure snapshot postdates the analysis knowledge clock")
    origin = origin_snapshot_id or corpus.corpus_id
    baselines = build_direct_baselines(interval)
    baseline_payload = {k: v.model_dump(mode="json") for k, v in baselines.items()}
    baseline_sha = digest(baseline_payload)
    frozen_baselines = copy.deepcopy(baselines)
    enabled = tuple(spec.method_id for spec in profile.method_specs if spec.enabled)
    plan = bootstrap_plan or make_event_bootstrap_plan(
        corpus,
        origin_snapshot_id=origin,
        seed=profile.seed,
        replicates=profile.bootstrap_replicates,
    )
    _validate_plan(plan, corpus, origin, profile)
    base_results = {}
    failures = {}
    for method_id in enabled:
        try:
            base_results[method_id] = _method_run(
                method_id, corpus, structure, profile, frozen_baselines
            )
        except (
            Exception
        ) as exc:  # method failures are typed and cannot shrink another method's cases
            failures[method_id] = f"{type(exc).__name__}: {exc}"
    draw_values = {
        method: {key: [] for key in frozen_baselines} for method in base_results
    }
    bootstrap_failures = Counter({method: 0 for method in base_results})
    for replicate, block in enumerate(plan.event_blocks):
        sampled = _resampled_corpus(corpus, block, replicate)
        for method_id in base_results:
            try:
                _, predictions = _method_run(
                    method_id,
                    sampled,
                    structure,
                    profile,
                    frozen_baselines,
                    diagnostics=False,
                )
                for key in frozen_baselines:
                    value = predictions[key].all_case
                    if value is None:
                        raise ValueError(
                            "bootstrap refit produced no all-case prediction"
                        )
                    draw_values[method_id][key].append(value.mean)
            except Exception:
                bootstrap_failures[method_id] += 1
    candidates = []
    series = []
    for method_id in enabled:
        if method_id in failures:
            candidates.append(
                CandidateResult(
                    method_id=method_id,
                    fit_id="",
                    predictions=(),
                    status="failed",
                    reasons=(failures[method_id],),
                )
            )
            continue
        fit, prediction_map = base_results[method_id]
        success_fraction = (
            profile.bootstrap_replicates - bootstrap_failures[method_id]
        ) / profile.bootstrap_replicates
        predictions = []
        for key in frozen_baselines:
            original = prediction_map[key]
            values = tuple(draw_values[method_id][key])
            all_case = summary(values) if values else original.all_case
            reasons = list(original.reasons)
            state = original.service_state
            served = all_case if original.served is not None else None
            if success_fraction < profile.service_gates.min_bootstrap_success_fraction:
                reasons.append("insufficient-bootstrap-refit-success")
                state = "computationally-unreliable"
                served = None
            predictions.append(
                original.model_copy(
                    update={
                        "all_case": all_case,
                        "served": served,
                        "service_state": state,
                        "reasons": tuple(dict.fromkeys(reasons)),
                    }
                )
            )
            a, b = pair_from_key(key)
            series.append(
                AlignedDrawSeries(
                    method_id=method_id,
                    subject=a,
                    opponent=b,
                    fit_id=fit.fit_id,
                    probabilities=values,
                )
            )
        candidates.append(
            CandidateResult(
                method_id=method_id,
                fit_id=fit.fit_id,
                predictions=tuple(predictions),
                all_case_pairs=tuple(
                    key
                    for key, p in zip(frozen_baselines, predictions, strict=True)
                    if p.all_case is not None
                ),
                served_pairs=tuple(
                    key
                    for key, p in zip(frozen_baselines, predictions, strict=True)
                    if p.served is not None
                ),
                status="complete" if bootstrap_failures[method_id] == 0 else "degraded",
                reasons=(
                    ()
                    if bootstrap_failures[method_id] == 0
                    else (f"{bootstrap_failures[method_id]} bootstrap refits failed",)
                ),
            )
        )
    if (
        digest({k: v.model_dump(mode="json") for k, v in frozen_baselines.items()})
        != baseline_sha
    ):
        raise RuntimeError("challenger mutated a frozen direct baseline")
    series_tuple = tuple(series)
    draws_sha = digest([x.model_dump(mode="json") for x in series_tuple])
    aligned = JointPredictiveDraws(
        artifact_id="",
        origin_snapshot_id=origin,
        seed=profile.seed,
        replicate_count=profile.bootstrap_replicates,
        replay_plan=plan,
        event_blocks_sha256=digest(plan.event_blocks),
        method_ids=enabled,
        series=series_tuple,
        draws_sha256=draws_sha,
    )
    aligned = aligned.model_copy(update={"artifact_id": joint_draws_identity(aligned)})
    pair_digest = digest(sorted(frozen_baselines))
    outcome_digest = digest(sorted(row.match_id for row in corpus.outcomes))
    profile_sha = digest(profile.model_dump(mode="json"))
    per_method = {
        spec.method_id: digest(
            {
                "corpus": corpus.corpus_id,
                "baseline": baseline_sha,
                "structure": structure.model_dump(mode="json"),
                "spec": spec.model_dump(mode="json"),
                "seed": profile.seed + spec.seed_offset,
            }
        )
        for spec in profile.method_specs
        if spec.enabled
    }
    audit = ComparisonAudit(
        audit_id="",
        common_corpus_id=corpus.corpus_id,
        common_pair_universe_sha256=pair_digest,
        common_outcome_ids_sha256=outcome_digest,
        baseline_sha256=baseline_sha,
        per_method_input_sha256=per_method,
        fair=True,
        aligned_draws_sha256=draws_sha,
    )
    audit = audit.model_copy(update={"audit_id": comparison_audit_identity(audit)})
    status = (
        "complete" if all(x.status == "complete" for x in candidates) else "degraded"
    )
    run = AmplificationRun(
        run_id="",
        corpus=corpus,
        profile=profile,
        profile_sha256=profile_sha,
        structure=structure,
        baselines=frozen_baselines,
        candidates=tuple(candidates),
        comparison=audit,
        aligned_draws=aligned,
        status=status,
    )
    return run.model_copy(update={"run_id": amplification_run_identity(run)})
