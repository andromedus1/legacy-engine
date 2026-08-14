---
intent: terminate-in-position
output_kind: synthesis-brief
consumer: methodology-revisers
verification_rigor: standard
temporal_contract: write-once-on-converge
primitives_extends: []
primitives_opts_out: []
decision_relevance: Choose a defensible non-contiguous era model that recovers admissible pre-ban matchup evidence without outcome-driven interval selection or contamination, and define how historical Best Deck / Best Call snapshots should consume it.
scope_authority: mixed
analytical_artifact_type: per-campaign-brief
provenance: agent-synthesis
---

# Recurrent stable-era intervals

Research methods for representing an archetype's stable era as a union of compatible historical
intervals rather than one monotone `stable_since` suffix. The resulting contract must support
pairwise subject/opponent interval intersection, preserve confirmed-ban affectedness, and distinguish
retrospective historical reports from leakage-free as-known-then snapshots.

Confirmed decomposition:

1. Discover candidate recurrent intervals from temporally segmented deck composition and structural
   features, without consulting matchup outcomes.
2. Certify interval equivalence with explicit minimum support, multiplicity, external-context, and
   contamination safeguards.
3. Consume subject/opponent interval intersections in matchup reporting; validate coverage,
   calibration, decision regret, concentration, and historical-report time-travel semantics.

Known lens paths (never citation substrate):

- `docs/briefs/change-point-detection.md`
- `docs/analysis/best-call-ranking.md`
- `src/legacy_engine/analytics/eras/`
- `src/legacy_engine/analytics/affectedness.py`
- `scripts/refresh_best_call_ranking.py`
