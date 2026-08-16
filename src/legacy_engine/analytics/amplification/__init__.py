"""Diagnostic evidence-amplification boundary; no ranking authority or winner selector."""

from .corpus import (
    build_direct_baselines,
    build_interval_evidence_corpus,
    pair_from_key,
    pair_key,
)
from .models import (
    AMPLIFICATION_METHOD_IDS,
    AlignedDrawSeries,
    AmplificationProfile,
    ChallengerPrediction,
    DirectBaseline,
    EligibleOutcome,
    EventBootstrapPlan,
    IntervalEvidenceCorpus,
    JointPredictiveDraws,
    MethodId,
    MethodSpec,
    StructureSnapshot,
)
from .profile import load_amplification_profile
from .run import (
    AmplificationRun,
    CandidateResult,
    ComparisonAudit,
    amplification_run_identity,
    comparison_audit_identity,
    joint_draws_identity,
    make_event_bootstrap_plan,
    run_amplification,
)
from .store import (
    init_amplification_schema,
    read_amplification_run,
    validate_amplification_run,
    write_amplification_run,
)

__all__ = [
    "AMPLIFICATION_METHOD_IDS",
    "AlignedDrawSeries",
    "AmplificationProfile",
    "AmplificationRun",
    "CandidateResult",
    "ChallengerPrediction",
    "ComparisonAudit",
    "DirectBaseline",
    "EligibleOutcome",
    "EventBootstrapPlan",
    "IntervalEvidenceCorpus",
    "JointPredictiveDraws",
    "MethodId",
    "MethodSpec",
    "StructureSnapshot",
    "amplification_run_identity",
    "build_direct_baselines",
    "build_interval_evidence_corpus",
    "comparison_audit_identity",
    "init_amplification_schema",
    "joint_draws_identity",
    "load_amplification_profile",
    "make_event_bootstrap_plan",
    "pair_from_key",
    "pair_key",
    "read_amplification_run",
    "run_amplification",
    "validate_amplification_run",
    "write_amplification_run",
]
