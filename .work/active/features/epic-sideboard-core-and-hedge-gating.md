---
id: epic-sideboard-core-and-hedge-gating
kind: feature
stage: done
tags: [advisory, sideboard]
parent: epic-sideboard-core-and-hedge
depends_on: [epic-sideboard-core-and-hedge-dedicated-core, epic-sideboard-core-and-hedge-output-contract]
release_binding: v0.2.0
gate_origin: null
created: 2026-06-15
updated: 2026-06-15
---

# Gating + operator controls (core wave)

## Brief

Wire the new core behavior behind an opt-in flag and expose the core's operator dials, then flip the
default once trusted. Gated-additive: with the flag off, `recommend_sideboard` is **byte-identical**
to today's forced-15 max-coverage output, so every existing test and caller is unaffected; with the
flag on, it returns the dedicated core (<15) with the new output contract. Exposes the core dials:
the natural-budget floor τ (tier-aware default), a total budget cap, and the access/redundancy curve
parameters (sensible defaults from the brief). Completes the v1 (core-first) wave; the "flip the
default once trusted" step is the closing move once the core path is validated on real prep.

This feature covers ONLY the core's flag + dials. The hedge feature adds its own dials
(hedge on/off, risk-appetite α, blend width) when it lands.

## Epic context
- Parent epic: `epic-sideboard-core-and-hedge`
- Position in epic: closes the v1 core wave — depends on the core solver and the output contract.
  The default flip is the last v1 step.

## Inherited design decisions
- Opt-in flag first, byte-identical until opted in; flip default once trusted (gated-additive).
- Operator-tunable τ + curve params with brief defaults; don't hardcode.

## Research briefs
- `docs/briefs/sideboard-core-and-hedge.md` §"Implementation Notes" (gating) + §4 (τ as a dial).

## Foundation references
- `src/legacy_engine/advisory/sideboard.py` (`recommend_sideboard` signature), `src/legacy_engine/cli.py`
  (`advise sideboard` flags).
- Patterns: [[gated-additive-augmentation]] (the defining shape — no-op path byte-identical to
  baseline, existing tests stay green untouched), [[cli-nested-groups]].

## Design + implementation (2026-06-15)
**CLI flags** on `advise sideboard`: `--smart/--no-smart` (default off — the opt-in master switch), plus power-user absolute overrides `--redundancy-strength FLOAT` and `--tau FLOAT`. Off + zero strengths → byte-identical forced-15 baseline.

**Key calibration fix** (the real correctness work): absolute redundancy/τ tuned on unit models (weight≈1.0) would be wildly over-strong on a real field (element marginals ~0.005–0.02 → 1-of-everything). Smart-mode derives both as FRACTIONS of the model's own coverage scale via `_coverage_scale(model)` (= the best single first-pick value, `max_c Σ_e weight_e·Δg(1)`): `_SMART_REDUNDANCY_FRACTION=0.5` (2nd copy of even the best card competes; weak cards → 1-of), `_SMART_TAU_FRACTION=0.1` (stop when a slot is worth <10% of the best pick). Field-scale-invariant. Explicit non-zero `--redundancy-strength`/`--tau` always win (power-user override).

**Files**: `src/legacy_engine/advisory/sideboard.py` (`_coverage_scale` + `_SMART_*` constants + `smart` param + the calibration block before solve), `src/legacy_engine/cli.py` (3 flags + threaded into the `recommend_sideboard` call). **Tests**: `tests/test_sideboard.py::TestGating` (6 — `_coverage_scale` value + empty; smart-off baseline; smart-on activates the contract without exploding to a sane 1..budget subset; explicit τ override wins; CLI exposes the flags).

**Review (self, focused)**: smart-scaling is a pure pre-solve derivation of the already-reviewed strength/τ params; explicit values bypass it; off → no-op. Gated-additive verified: sideboard suite 269 green byte-identical with --smart off, full suite 2236, no new ruff errors (still 16 pre-existing cli.py F821 forward-ref hints). No blockers. The `--smart` default stays OFF ("flip default once trusted" is a deliberate later step — the user can test-drive via `advise sideboard --smart`).
