---
id: epic-stable-era-windows-consumption-consensus
kind: story
stage: done
tags: [analytics, generation]
parent: epic-stable-era-windows-consumption
depends_on: [epic-stable-era-windows-consumption-matrix]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Consensus family era windows + golden re-pins

## Brief
Units 4+5: entity_era_window replacing the 4 _latest_regime_window cli sites with audit echoes; verify-then-re-pin the full-body goldens with explainable diffs.

## Implementation
Parent feature `epic-stable-era-windows-consumption` — exact contracts + acceptance criteria there.

## Implementation notes

Units 4+5 delivered (finished inline by the orchestrator after the implementation agent was
terminated twice by API/stream failures mid-story; stories 1-2 were the agent's, committed clean).

- `generation/consensus.py::entity_era_window(con, archetype) -> (since, until, label)` — era-aware
  single-archetype default: absent from entity_eras → exact `_latest_regime_window()` fallback
  ("ban regime"); stable_since date → [date, now) labeled with the winning boundary's attribution
  detail; analyzed-undisturbed → full corpus ("undisturbed — full corpus"). Wired INSIDE
  consensus.py's own defaults (card_frequencies + consensus generation) and at the two
  single-archetype cli sites (report cards --conditioned and report cards --archetype), each with
  a `// window:` audit echo.
- Three `_latest_regime_window` sites deliberately KEPT and documented in-line: `report variants`
  (cross-parent summary), `advise sweep` (one shared field window for cross-archetype
  comparability), `identify strong` (players are not archetype entities). Rationale comments cite
  this unit.
- Goldens: both pinned full-body golden files re-run UNCHANGED — hermetic test DBs carry no
  entity_eras table, so the fallback path is byte-identical (the Unit 2 fallback test proves the
  matrix side; the consensus fallback is pinned by the entity_era_window absent-case test).
- Tests: test_generation_consensus.py (+~100 lines: resolution branches, undisturbed-widens
  regression, fallback exactness), test_conditioned_card_winrate.py (+12: window echo). Full
  suite 2911 passed + 1 xfail.
