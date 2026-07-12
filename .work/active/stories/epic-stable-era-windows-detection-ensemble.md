---
id: epic-stable-era-windows-detection-ensemble
kind: story
stage: review
tags: [analytics, methodology]
parent: epic-stable-era-windows-detection
depends_on: [epic-stable-era-windows-detection-detectors, epic-stable-era-windows-detection-bocpd]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Ensemble + FDR + floors + stable_since, ruptures dep, calibration fixtures (analytics/eras/ensemble.py)

## Brief
Merge candidates across signals (±2-bucket tolerance), fleet-wide Benjamini–Hochberg FDR at
α=0.05, ≥30-decks-in-new-era floor, camp parent-inheritance, per-entity stable_since derivation.
Adds ruptures to core deps; freezes the ledger calibration fixtures (Tron cliff, Flow State ×3,
stable non-event, seeded null fleet) that pin the operating point.

## Implementation
Parent feature `epic-stable-era-windows-detection` — Units 4+5 (exact signatures + acceptance
criteria there).

## Implementation notes

Built `src/legacy_engine/analytics/eras/ensemble.py` per the Unit 4 contract: `EraBoundary`,
`EntityEras`, `derive_eras(series, candidates, *, alpha=0.05, merge_tolerance_buckets=2,
min_new_era_decks=30)`. Four passes: (1) per-entity single-linkage merge within tolerance,
distance measured on the entity's own bucket grid (density-adaptive widths respected; merged date
= min-p component's date, all components kept in `signals`); (2) fleet-wide BH-FDR via
`statsmodels.stats.multitest.multipletests(method="fdr_bh")`; (3) deck floor AFTER BH — a
surviving boundary with < 30 entity decks in buckets at/after its date gets `floor_rejected=True`
(sanctioned extra field on `EraBoundary`, documented in its docstring: "survived FDR but era too
thin" is an audit-relevant state distinct from "failed FDR"); (4) camp inheritance — a camp with
zero own accepted boundaries whose parent HAS accepted boundaries inherits the parent's
boundaries/stable_since with `inherited_from_parent=True`; a camp with its own accepted
boundaries keeps them but its effective stable_since is `max(own, parent's)` (a parent-wide
disturbance disturbs every camp; a camp can be MORE recently disturbed than its parent, never
less). `stable_since` = date of the last boundary that is `bh_accepted and not floor_rejected`,
else None. Pure — no DB, no persistence. Unit 5: `ruptures>=1.1,<2` added to `[project]`
dependencies (import stays lazy inside detect.py); resolves via `uv pip install -e ".[dev]"`
(ruptures 1.1.10 in the venv). Package `__init__.py` exports extended for detect + ensemble.

**Tests**: `tests/analytics/eras/test_ensemble.py` (18 tests). Null fleet twice (synthetic
p >= 0.02 candidates over 20 of 100 stationary entities -> 0 accepted at the pinned seed, AND the
real detector stack over all 100 stationary series -> 0 candidates at all); real-case integration
(Flow State ×3 + Tron through the full stack); merge semantics (1-bucket-apart merge with min-p
date, beyond-tolerance separation, bucket-grid distance on a 2-week-bucket entity); deck floor
(floor_rejected with bh_accepted retained; stable_since fallback to the prior accepted boundary);
camp inheritance (inherit, max rule both directions, nothing-to-inherit stays uninherited);
end-to-end seam shape.

## Implementation discovery

Two of the real-case integration expectations are falsified by the frozen real corpus + the
design's own binding false-positive controls; the tests pin the TRUE behavior with explanatory
comments rather than gaming the expectations:

1. **Tron `stable_since` is None at this snapshot, not the cliff date.** The Candelabra cliff is
   ONE complete bucket old at the corpus edge (2026-06-22 = 20 decks; 06-29 partial). Two
   independent binding defenses hold it back: (a) a segment-permutation p-value for a boundary
   2 buckets from the series end is mathematically bounded below at ~1/n_pooled — the min_size-
   legal split at 2026-06-15 pools (28,36,50,58,59 | 59,20) and scores p≈0.55, and even a
   min_size=1 split at the true cliff can't beat ~1/7 of permutations — so it cannot clear
   fleet BH at any calibration; (b) the true cliff bucket leaves 21 decks in the new era, below
   the 30-deck floor regardless. This is the brief §4 "confirmation asymmetry" case working as
   designed: the offline derivation must NOT truncate on a 1-week-old era; the BOCPD drift alarm
   (bocpd.py, consumed by the era-ledger feature) is the designed mechanism that flags it NOW.
   The detect-level test (story `-detectors`) pins that the share detector FIRES at the
   transition; the ensemble test pins that the boundary is recorded (audit trail) but honestly
   held below acceptance until the era accumulates sample. Unit 4's "Tron fixture boundary
   survives FDR + floor" acceptance criterion is unsatisfiable as written for THIS corpus
   snapshot — flagged for the parent feature review; a Tron fixture extended 2-3 more post-ban
   weeks would satisfy it and is the right shape for a follow-up regression fixture.
2. **Dimir Tempo's `stable_since` is 2026-05-11, not the 04-20 adoption bucket.** The frozen
   real data contains a genuine SECOND disturbance: Dimir's play rate halves after the Flow
   State meta shift (~40-45 decks/wk pre-adoption vs ~17-24 from mid-May); the share detector
   dates that settling 2026-05-11 with permutation p=0.005 — 3 buckets after adoption, outside
   the 2-bucket merge tolerance — and it survives BH + floor on its own merits. The adoption
   boundary itself IS separately accepted for all three archetypes (asserted). stable_since =
   last accepted boundary by contract, so the later settling wins — the conservative windowing
   choice. Doomsday (04-20) and Izzet (04-13) match the original ±1-bucket expectation.
