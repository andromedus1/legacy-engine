---
id: epic-advisory-sideboard
kind: feature
stage: drafting
tags: [advisory]
parent: epic-advisory
depends_on: [epic-advisory-field-model, epic-advisory-whattoplay]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Sideboard Recommender (weighted max-coverage: ILP + greedy)

## Brief
Recommend a **15-card sideboard** as **weighted (budgeted) MAXIMUM-COVERAGE** (not set-cover): maximize
weighted coverage of the field within a hard 15-slot budget. Elements = archetypes (+ anti-hate
pseudo-elements); candidate sets = hoser cards each attacking a set of archetypes; **element weight
`w_a = field_share(a) × Δ_a`** (the win-rate swing the hoser provides). Use a **saturating/submodular**
value function `value(a) = w_a · g(n_a)` with `g` concave (e.g. `g(n)=1−(1−p)^n`) so the 2nd
anti-Reanimator card is worth less than the 1st. **Solver: ILP primary, greedy fallback** — PuLP/CBC
solves the exact optimum (<1s at this scale); the **greedy (1−1/e) marginal-gain trace is surfaced
alongside as the explainable "why each card."** Bounded-integer copies (2–3-ofs = multi-coverage),
**color/deck-fit pre-filter**, `reserved` slots held for flex/maindeck-overlap. **Anti-hate second order**:
model expected-opposing-hate as pseudo-elements (`h_k = Σ_a field_share(a)·P(a sideboards hate k vs you)`)
folded into one unified coverage pass so counter-hosers (Veil of Summer, Defense Grid) compete for slots.

Consumes `field-model` (field shares), the done `matchup-matrix` (swing `Δ`), and **`whattoplay`'s
vulnerability tags + hate-equity vector** (the weighting + anti-hate inputs), plus the `Card` model
(color pre-filter, copy limits via `banlist`).

Does NOT compute positioning (`positioning`) or render the combined report (`report`).

## Epic context
- Parent epic: `epic-advisory`
- Position in epic: consumer of `field-model` + `whattoplay` (+ done `matchup-matrix`/`Card`); producer of
  the `SideboardPackage` that `report` surfaces.

## Inherited design decisions
- **ILP default + greedy explanation**: PuLP/CBC exact-optimal 15; greedy marginal-gain trace surfaced as
  the legible per-card rationale.
- **Weighted max-coverage (not set-cover)**; saturating submodular value; bounded-integer copies; color
  pre-filter; `reserved` slots; **anti-hate pseudo-elements in one unified pass**.
- **Hate-equity / vulnerability inputs come from `whattoplay`** — not recomputed here.

## Research briefs
- `docs/briefs/advisory-methods.md` — §3 (max-coverage formulation, ILP shape, greedy fallback,
  saturating value, anti-hate pseudo-elements). **Open item (non-blocking): the NIU thesis (403 on auto
  fetch) is possible prior art for sideboard-as-MIP — flagged for a manual pull before claiming full
  novelty; the OR formulation is load-bearing regardless.**
- `docs/briefs/legacy-metagame.md` §6 — hosers-by-target (candidate-card inputs).

## Foundation references
- `docs/ARCHITECTURE.md` — `advisory/sideboard.py`; `SideboardPackage` model; the `pulp` dependency.
- `docs/SPEC.md` — SideboardPackage entity.
- `docs/PRINCIPLES.md` — #7 confidence-gate (gate BEST-CALL on established/evolving data only).

<!-- feature-design fills in: recommend_sideboard signature, ILP model, greedy trace, SideboardPackage, test approach. -->
