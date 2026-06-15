---
id: epic-advisory-hardening
kind: epic
stage: done
tags: [advisory, hardening]
parent: null
depends_on: [epic-advisory]
release_binding: v0.1.0
gate_origin: null
created: 2026-05-30
updated: 2026-06-14
---

# Advisory Pillar Hardening

## Brief

Accuracy + correctness hardening of the shipped advisory pillar (`epic-advisory`, done), driven by two
post-ship signals this session: (1) **real-data use** of the engine on the 2,449-tournament corpus, and
(2) a **cross-model peer review** (peeragent → Codex xhigh). The advisory pillar's *structure* is sound and
test-green; these are the heuristic-calibration and correctness gaps that real data and a fresh model
surfaced — none block the pillar's existing behavior, but they're what make `advise`/generation trustworthy
enough to lean on.

This epic is an organizational umbrella over already-filed standalone items (decomposition pre-existed —
no re-decomposition). Sibling pillars have their own findings as standalone features
(`fix-analytics-peer-review-findings`, `fix-spine-peer-review-findings`) — not parented here.

## Decomposition

### Child features

- `fix-advisory-peer-review-bugs` — concrete correctness bugs from the Codex review (no-data Beta de-centering, `rank_decks` argmax ties, exclude-mirror S=0, Surgical/Faerie color gating, `best_deck_vs_best_call` n<30 inclusion, NaN guard). Fixes are specified per finding — depends on: `[]`
- `improve-positioning-pbest-uneven-sample` — P(best) is biased toward thin-matchup-data decks; gate/down-weight ranking by data sufficiency — depends on: `[]`
- `improve-whattoplay-proactivity-threat-signal` — proactivity mis-rates creature-tempo (no threat signal); vulnerability tags use presence not density — depends on: `[]`
- `improve-sideboard-realdata-quality` — binary coverage under-fills the 15-slot budget (needs saturating g(n)); vulnerability-tag inflation — depends on: `[improve-whattoplay-proactivity-threat-signal]`

### Design forks to resolve (candidates for `/feature-design --only-questions`)

The `fix-advisory-peer-review-bugs` bundle is concrete (file:line + specified fix) — safe for autopilot
judgment. The three `improve-*` items carry genuine directional choices worth pinning before autopilot:

- **whattoplay threat signal:** add a `power` field to the `Card` model (ingestion change, general) vs a
  curated threat-card list (simpler, less general)? And the density threshold for vulnerability tags.
- **positioning ranking:** keep `P(best)` but gate by matchup-data sufficiency, vs switch the default headline
  to a risk-adjusted lower-quantile rank?
- **sideboard coverage:** implement the full saturating `g(n)=1-(1-p)^n` objective (faithful, bigger) vs a
  simpler diminishing-duplicate fill to reach the 15-slot budget?

## Children complete + epic review (2026-05-30, autopilot)
All 4 children done: `improve-whattoplay-proactivity-threat-signal`, `fix-advisory-peer-review-bugs`,
`improve-positioning-pbest-uneven-sample`, `improve-sideboard-realdata-quality`. Suite 581 → 651 (+70).

**Verdict**: Approve (pending Phase 8 final peer review). Aggregate outcomes:
- Proactivity now rates creature-tempo correctly (Izzet Delver 0.00→0.510; combo>tempo>control); `Card.power/
  toughness` added (re-seed `seed cards` to backfill the real DB — tests use fresh `:memory:`).
- 8 peer-review correctness bugs fixed (imputation centering, rank ties, exclude-mirror, sideboard coverage
  keys + `_hate` weight, Surgical/Faerie color, best_deck n≥30 gate, NaN guard).
- Positioning default ranking → risk-adjusted lower-quantile (P(best) secondary) + `data_coverage`; the
  thin-data spiker artifact is gone.
- Sideboard saturating `g(n)` fills the 15-slot budget (was 2).
- Foundation-doc drift fixed: ARCHITECTURE positioning row now says risk-adjusted rank (P(best) secondary).

## Phase 8 fixes (2026-05-30, completion-review)

Four findings from the cross-model completion review resolved. Suite 651 → 654 (+3 new tests; finding 4 replaced weak test with deterministic one).

1. **BLOCKER — cards migration for power/toughness** (`src/legacy_engine/ingestion/store.py`): `init_schema()` now runs `ALTER TABLE cards ADD COLUMN IF NOT EXISTS power/toughness VARCHAR` after the CREATE, so existing 9-column DBs are upgraded without data loss. `load_cards` INSERT now uses an explicit column list to prevent silent column-count drift. Test: `test_migration_old_9column_schema_gains_power_toughness` — creates old 9-column table, calls `init_schema`, loads a creature with power/toughness, asserts round-trip.

2. **BLOCKER — ILP underfills budget** (`src/legacy_engine/advisory/sideboard.py`): the hard `_ILP_T_CAP = 4` coverage-level cap was replaced with `_ILP_T_CAP = budget`. The old cap prevented the ILP from allocating more than 4 slots to any element, causing it to stop at ~12 slots on multi-copy models where greedy (using uncapped `g(n)`) correctly fills 15. With budget as the cap the ILP objective matches the uncapped `g(n)` objective. Test: `test_ilp_fills_budget_multi_copy_saturating` — 3-element / 3×8-copy model asserts ILP fills 15 slots and its objective ≥ greedy.

3. **IMPORTANT — positioning `--candidates` display** (`src/legacy_engine/cli.py`): ranking output now shows `Q{quantile_level}=...` (the sort key) and `cov=...` (data coverage) per deck, plus `[low_coverage]` flag when triggered. The header also surfaces which quantile is the sort key. Test: `test_positioning_candidates_output_shows_quantile_and_coverage` — asserts `Q0.` and `cov=` appear in CLI output.

4. **NIT — tie regression test was weak** (`tests/test_positioning.py`): `test_fix2_rank_decks_identical_candidates_split_pbest_evenly` replaced by `test_fix2_rank_decks_exact_tie_splits_pbest_exactly`. New test monkeypatches `_sample_S` to return identical arrays for both candidates, making every draw an exact tie. Without the fix (argmax → index-0 wins) P(best) would be 1.0/0.0; with the fix both get exactly 0.5 to floating-point precision.

## Phase 8 outcome + completion (2026-05-30)
Cross-model final review (Codex xhigh) flagged 2 blockers + 1 important + 1 nit — all fixed inline with tests
(cards-table migration via ALTER ADD COLUMN IF NOT EXISTS + explicit insert column list; ILP T_a cap raised
to budget so the default solver fills 15; positioning CLI shows Q-quantile + data_coverage; deterministic
tie test). No new substrate items required; queue empty; suite 654 green. **Goal outcome: complete.**
