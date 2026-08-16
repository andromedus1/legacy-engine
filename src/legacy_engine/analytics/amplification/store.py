from __future__ import annotations

import json

from ._common import digest
from .corpus import digest as corpus_digest
from .models import AMPLIFICATION_METHOD_IDS
from .run import (
    AmplificationRun,
    amplification_run_identity,
    comparison_audit_identity,
    joint_draws_identity,
)


def init_amplification_schema(con) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS amplification_runs (run_id VARCHAR PRIMARY KEY, payload JSON NOT NULL)"
    )


def validate_amplification_run(run: AmplificationRun) -> None:
    if run.authority != "diagnostic-only" or run.profile.authority != "diagnostic-only":
        raise ValueError("amplification authority must be diagnostic-only")
    if run.profile_sha256 != digest(run.profile.model_dump(mode="json")):
        raise ValueError("amplification profile digest mismatch")
    enabled = tuple(spec.method_id for spec in run.profile.method_specs if spec.enabled)
    if any(method not in AMPLIFICATION_METHOD_IDS for method in enabled):
        raise ValueError("unknown amplification method")
    if tuple(candidate.method_id for candidate in run.candidates) != enabled:
        raise ValueError("candidate registry/order differs from enabled profile")
    pair_universe = tuple(sorted(run.baselines))
    if run.comparison.common_pair_universe_sha256 != digest(pair_universe):
        raise ValueError("comparison pair universe digest mismatch")
    outcome_ids = tuple(sorted(row.match_id for row in run.corpus.outcomes))
    if run.comparison.common_outcome_ids_sha256 != digest(outcome_ids):
        raise ValueError("comparison outcome identity digest mismatch")
    if run.corpus.pair_evidence_sha256 != corpus_digest(
        [row.model_dump(mode="json") for row in run.corpus.outcomes]
    ):
        raise ValueError("corpus outcome digest mismatch")
    source_payload = [
        {
            "match_id": row.match_id,
            "provenance": row.provenance,
            "subject_certificate_ids": row.subject_certificate_ids,
            "opponent_certificate_ids": row.opponent_certificate_ids,
        }
        for row in run.corpus.outcomes
    ]
    if run.corpus.source_rows_sha256 != corpus_digest(source_payload):
        raise ValueError("corpus source-row digest mismatch")
    for baseline in run.baselines.values():
        if baseline.current_sha256 != corpus_digest(
            baseline.current_only.model_dump(mode="json")
        ) or baseline.expanded_sha256 != corpus_digest(
            baseline.certified_expanded.model_dump(mode="json")
        ):
            raise ValueError("direct baseline view digest mismatch")
    if run.comparison.audit_id != comparison_audit_identity(run.comparison):
        raise ValueError("comparison audit digest mismatch")
    if run.aligned_draws is None:
        raise ValueError("amplification run lacks aligned draws")
    if run.aligned_draws.artifact_id != joint_draws_identity(run.aligned_draws):
        raise ValueError("aligned draw artifact digest mismatch")
    plan = run.aligned_draws.replay_plan
    if (
        plan.origin_snapshot_id != run.aligned_draws.origin_snapshot_id
        or plan.seed != run.aligned_draws.seed
    ):
        raise ValueError("aligned draw replay-plan metadata mismatch")
    if plan.plan_id != digest(
        {
            "origin_snapshot_id": plan.origin_snapshot_id,
            "seed": plan.seed,
            "event_blocks": plan.event_blocks,
        }
    ):
        raise ValueError("aligned draw replay-plan digest mismatch")
    if run.aligned_draws.event_blocks_sha256 != digest(plan.event_blocks):
        raise ValueError("aligned draw event-block digest mismatch")
    if run.aligned_draws.draws_sha256 != digest(
        [x.model_dump(mode="json") for x in run.aligned_draws.series]
    ):
        raise ValueError("aligned draw value digest mismatch")
    if run.aligned_draws.method_ids != enabled:
        raise ValueError("aligned draw method registry differs from profile")
    if run.aligned_draws.replicate_count != run.profile.bootstrap_replicates:
        raise ValueError("aligned draw replicate count differs from profile")
    candidate_by_method = {
        candidate.method_id: candidate for candidate in run.candidates
    }
    expected_series = set()
    for candidate in run.candidates:
        if candidate.status == "failed":
            if candidate.predictions:
                raise ValueError("failed candidate unexpectedly retains predictions")
            continue
        prediction_pairs = {
            json.dumps(
                [value.subject, value.opponent],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            for value in candidate.predictions
        }
        if prediction_pairs != set(pair_universe):
            raise ValueError("candidate prediction universe differs from common pairs")
        expected_series.update((candidate.method_id, pair) for pair in pair_universe)
    actual_series = set()
    for series in run.aligned_draws.series:
        key = json.dumps(
            [series.subject, series.opponent], ensure_ascii=False, separators=(",", ":")
        )
        candidate = candidate_by_method[series.method_id]
        if series.fit_id != candidate.fit_id:
            raise ValueError("aligned draw fit identity differs from candidate")
        if len(series.probabilities) != run.aligned_draws.replicate_count:
            raise ValueError("aligned draw series is incomplete")
        actual_series.add((series.method_id, key))
    if actual_series != expected_series:
        raise ValueError("aligned draw series universe differs from candidates")
    if run.comparison.aligned_draws_sha256 != run.aligned_draws.draws_sha256:
        raise ValueError("comparison and aligned-draw identities differ")
    if run.comparison.common_corpus_id != run.corpus.corpus_id:
        raise ValueError("comparison corpus differs from run corpus")
    if run.comparison.baseline_sha256 != digest(
        {k: v.model_dump(mode="json") for k, v in run.baselines.items()}
    ):
        raise ValueError("baseline digest mismatch")
    if run.run_id != amplification_run_identity(run):
        raise ValueError("amplification run content digest mismatch")


def write_amplification_run(con, run: AmplificationRun) -> None:
    validate_amplification_run(run)
    init_amplification_schema(con)
    payload = json.dumps(
        run.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    existing = con.execute(
        "SELECT payload FROM amplification_runs WHERE run_id=?", [run.run_id]
    ).fetchone()
    if existing and json.loads(existing[0]) != json.loads(payload):
        raise ValueError("amplification run id collision")
    con.execute(
        "INSERT OR IGNORE INTO amplification_runs VALUES (?, ?)", [run.run_id, payload]
    )


def read_amplification_run(con, run_id: str) -> AmplificationRun | None:
    row = con.execute(
        "SELECT payload FROM amplification_runs WHERE run_id=?", [run_id]
    ).fetchone()
    if row is None:
        return None
    run = AmplificationRun.model_validate(json.loads(row[0]))
    if run.run_id != run_id:
        raise ValueError("stored amplification key differs from payload id")
    validate_amplification_run(run)
    return run
