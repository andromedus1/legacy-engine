---
id: epic-advisory-hardening
kind: epic
stage: review
tags: [advisory, hardening]
parent: null
depends_on: [epic-advisory]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
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
