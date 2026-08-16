"""Outcome-amplification challenger contracts.

This package deliberately has no database selection logic: callers provide the
canonical interval-selected outcome ledger and frozen structural snapshots.
"""

from .models import (
    AmplificationProfile,
    DirectBaseline,
    EligibleOutcome,
    IntervalEvidenceCorpus,
    StructureSnapshot,
    JointPredictiveDraws,
)
from .corpus import build_interval_evidence_corpus, build_direct_baselines
from .profile import load_amplification_profile

__all__ = [
    "AmplificationProfile",
    "DirectBaseline",
    "EligibleOutcome",
    "IntervalEvidenceCorpus",
    "StructureSnapshot",
    "JointPredictiveDraws",
    "build_interval_evidence_corpus",
    "build_direct_baselines",
    "load_amplification_profile",
]
