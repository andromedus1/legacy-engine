"""Superarchetype layer — strategy clusters over archetypes (the third taxonomy level).

``cluster.py`` is the pure, DB-free clustering core plus one thin read-only corpus wrapper;
``registry.py`` owns persistence (derived JSON SSOT + rebuildable DuckDB cache), the curated
override merge, cluster identity across refreshes, and the churn diagnostic; ``aggregate.py`` is
the pure random-effects estimator that pools member TALLIES into one honest cluster cell.

**The taxonomy (``cluster``/``registry``) reads ``deck_cards`` and never ``rounds``.** The
property is structural, not a convention: the clustering core's only input type carries card
names, so a matchup-coverage objective is not expressible against it. Enforced by
``tests/analytics/superarchetype/test_no_rounds.py``. The estimator (``aggregate``) necessarily
consumes match OUTCOMES — but it is DB-free (tallies in, typed cells out) and sits strictly
downstream of the taxonomy, so outcomes still cannot tune membership (the double-dip guard).
"""

from __future__ import annotations

from legacy_engine.analytics.superarchetype.aggregate import (
    I2_ONE_SIDED_NOTE,
    Concentration,
    Heterogeneity,
    ImputationLicense,
    ImputedCell,
    MemberSplit,
    MemberTally,
    PooledCell,
    PriorStrength,
    RandomEffects,
    aggregate_cluster_cell,
    concentration,
    dersimonian_laird,
    effective_n,
    heterogeneity,
    imputation_license,
    impute_cell,
    prior_strength,
)
from legacy_engine.analytics.superarchetype.cluster import (
    ArchetypeComposition,
    ArchetypeDeck,
    BranchSupport,
    ClusterMember,
    ClusterSolution,
    DerivedCluster,
    build_compositions,
    cluster_archetypes,
    jaccard_dissimilarity,
    load_archetype_decks,
)
from legacy_engine.analytics.superarchetype.registry import (
    ChurnReport,
    CuratedCluster,
    RegistryCluster,
    RunResult,
    SuperarchetypeRegistry,
    init_superarchetype_schema,
    load_curated_superarchetypes,
    read_derived_registry,
    read_superarchetype_members,
    rebuild_superarchetype_members,
    run_superarchetypes,
    write_derived_registry,
)

__all__ = [
    "I2_ONE_SIDED_NOTE",
    "ArchetypeComposition",
    "ArchetypeDeck",
    "BranchSupport",
    "ChurnReport",
    "ClusterMember",
    "ClusterSolution",
    "Concentration",
    "CuratedCluster",
    "DerivedCluster",
    "Heterogeneity",
    "ImputationLicense",
    "ImputedCell",
    "MemberSplit",
    "MemberTally",
    "PooledCell",
    "PriorStrength",
    "RandomEffects",
    "RegistryCluster",
    "RunResult",
    "SuperarchetypeRegistry",
    "aggregate_cluster_cell",
    "build_compositions",
    "cluster_archetypes",
    "concentration",
    "dersimonian_laird",
    "effective_n",
    "heterogeneity",
    "imputation_license",
    "impute_cell",
    "init_superarchetype_schema",
    "jaccard_dissimilarity",
    "load_archetype_decks",
    "load_curated_superarchetypes",
    "prior_strength",
    "read_derived_registry",
    "read_superarchetype_members",
    "rebuild_superarchetype_members",
    "run_superarchetypes",
    "write_derived_registry",
]
