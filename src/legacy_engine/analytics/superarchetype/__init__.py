"""Superarchetype layer — strategy clusters over archetypes (the third taxonomy level).

``cluster.py`` is the pure, DB-free clustering core plus one thin read-only corpus wrapper;
``registry.py`` owns persistence (derived JSON SSOT + rebuildable DuckDB cache), the curated
override merge, cluster identity across refreshes, and the churn diagnostic.

**This package reads ``deck_cards`` and never ``rounds``.** The property is structural, not a
convention: the pure core's only input type carries card names, so a matchup-coverage objective is
not expressible against it. Enforced by ``tests/analytics/superarchetype/test_no_rounds.py``.
"""

from __future__ import annotations

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
    "ArchetypeComposition",
    "ArchetypeDeck",
    "BranchSupport",
    "ChurnReport",
    "ClusterMember",
    "ClusterSolution",
    "CuratedCluster",
    "DerivedCluster",
    "RegistryCluster",
    "RunResult",
    "SuperarchetypeRegistry",
    "build_compositions",
    "cluster_archetypes",
    "init_superarchetype_schema",
    "jaccard_dissimilarity",
    "load_archetype_decks",
    "load_curated_superarchetypes",
    "read_derived_registry",
    "read_superarchetype_members",
    "rebuild_superarchetype_members",
    "run_superarchetypes",
    "write_derived_registry",
]
