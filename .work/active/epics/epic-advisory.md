---
id: epic-advisory
kind: epic
stage: implementing
tags: [advisory]
parent: null
depends_on: [epic-meta-analytics]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-30
---

# Meta Attack / Advisory

## Brief

The Legacy-specific differentiator and the MVP's headline value: *how to attack the field.* Given the
metagame and matchup matrix, compute a deck's **meta-positioning score** (expected WR vs the weighted
field, Bayesian Monte-Carlo over Beta cells + Dirichlet shares, with a user-supplied custom field),
recommend a **15-card sideboard** (weighted submodular max-coverage via an ILP with a greedy
explainable fallback, including the anti-hate second order), and surface a **what-to-play** read
(composition-derived proactivity, vulnerability tags, hate-equity, best-deck vs best-call).

Delivered as a coherent "Field Read & Deck Recommendation" report with an audit trail (every number
with its derivation, sample size, and a heuristic-vs-data-driven label). This is what a competitive
player actually uses. Does NOT cover simulation (goldfish) or deck generation.

## Research briefs
- `docs/briefs/advisory-methods.md` — the full methods: positioning score + uncertainty, sideboard ILP/greedy + anti-hate, what-to-play proactivity + vulnerability tags + hate-equity, the recommendation surface.
- `docs/briefs/legacy-metagame.md` §6-7 — hosers-by-target, sideboard strategy, the what-to-play framing, current strategic read.

## Foundation references
- `docs/ARCHITECTURE.md` — `advisory/` (positioning, sideboard, whattoplay, report); SideboardPackage + PositioningResult models; the `pulp` dependency.
- `docs/SPEC.md` — SideboardPackage entity; the advisory MVP capabilities.
- `docs/PRINCIPLES.md` — advisory is first-class; confidence-gate (BEST-CALL only on established/evolving data).

## Design decisions
*(Captured via `/epic-design --only-questions`, 2026-05-29 — locked inputs for the feature-design pass; do not re-ask.)*
- **MVP scope:** **Full Field-Read & Deck-Recommendation report.** Build the whole surface — field composition + vulnerability profile, decks ranked by meta-positioning score, a recommended 15-card sideboard package, and an audit trail (every figure with derivation + sample size). It's the differentiator pillar and directly serves the project goal "how to attack the meta."
- **Sideboard solver:** **ILP default + greedy explanation.** PuLP/CBC computes the exact-optimal 15; the greedy marginal-gain trace is surfaced alongside as the legible "why each card." (Brief's recommendation.)
- **Custom field:** **Included in the MVP.** Ship user-supplied expected-field input (archetype→share map; auto-normalize; warn on no-data archetypes) from the start — the "best metagame call for MY room" headline feature, not just global-meta scoring.
- **(Pinned by advisory-methods brief, not forks):** matchup cells = Wilson CI + Beta-Binomial shrinkage + n<30 display gate; positioning = Bayesian Monte-Carlo (Beta cells + Dirichlet shares), rank by probability-of-being-best, report S *and* the unweighted aggregate (best-call vs best-deck); confidence-gate everything.

## Decomposition

Split by **capability**, with one shared **foundation feature extracted** — the same shape that worked for
`epic-meta-analytics`. The architecture's `advisory/` table maps 1:1 to four files (positioning, sideboard,
whattoplay, report); the realized decomposition adds a fifth, `field-model`, pulled out in front: the field
distribution (global-from-`metashare` + custom-field override + Other/rogue + the Dirichlet `counts`
positioning needs) is consumed by all three advisory engines, so owning it once is the SSOT that avoids
three re-implementations of custom-field normalization / impute / Other-handling. The dependency graph is a
clean DAG (`field-model` source → `report` sink) with `positioning ∥ whattoplay` after the foundation, then
`sideboard` (which needs `whattoplay`'s hate-equity vector), then `report`.

### Child features

- `epic-advisory-field-model` — `FieldDistribution` (global from `metashare` + custom-field override, normalize/warn/impute, Other/rogue explicit, mirror at share, `field_source` label, Dirichlet counts) — depends on: `[]`
- `epic-advisory-positioning` — `S(D)` Bayesian Monte-Carlo (Beta cells + Dirichlet shares), `Ū` aggregate, rank by `P(best)` from shared-field draws, best-call-vs-best-deck, `--risk-averse`; `PositioningResult` — depends on: `[epic-advisory-field-model]`
- `epic-advisory-whattoplay` — composition proactivity score, vulnerability tags, hate-equity (coverage), best-deck/best-call (matchup-spread variance), plan-clash WHY strings — depends on: `[epic-advisory-field-model]`
- `epic-advisory-sideboard` — weighted max-coverage (ILP PuLP/CBC + greedy explainable trace), saturating submodular value, bounded-int copies, color pre-filter, reserved slots, anti-hate pseudo-elements; `SideboardPackage` — depends on: `[epic-advisory-field-model, epic-advisory-whattoplay]`
- `epic-advisory-report` — "Field Read & Deck Recommendation" surface (field composition + vulnerability profile + ranked decks + sideboard package + audit trail); wires the `advise positioning|sideboard|whattoplay` CLI group + combined report — depends on: `[epic-advisory-positioning, epic-advisory-whattoplay, epic-advisory-sideboard]`

### Decomposition decisions
(Resolved under autopilot delegation — Phase 4.7. No strategic 50/50s; pinned by the brief + the locked
`## Design decisions` above + the codebase.)

- **`field-model` extracted as a foundation feature** (beyond the architecture's 4-file advisory table, adding `advisory/field.py`): the field distribution is a genuine 3-way-shared concern (positioning `w` + Dirichlet counts, sideboard `field_share` weighting, whattoplay hate-equity). Owning it once is the SSOT; the alternative — positioning owns it and sideboard/whattoplay import from positioning — would couple the consumers and muddy the DAG. Mirrors the `match-results` extraction in `epic-meta-analytics`.
- **best-deck/best-call classification lives in `whattoplay`** (from matchup-spread variance), independent of `positioning`'s `S` ranking — so `whattoplay` does NOT depend on `positioning`; the two combine only in `report`. This keeps `positioning ∥ whattoplay` parallel.
- **`sideboard` depends on `whattoplay`** (not just the foundation): the anti-hate pseudo-elements and the element weighting consume `whattoplay`'s vulnerability tags + hate-equity vector (the brief states the hate-equity vector "is exactly the sideboard recommender's weighting input").
- **`report` owns the `advise` CLI wiring** (the three `_not_implemented` stubs + a combined field-read leaf); each advise command threads the `--field` custom field through `field-model`. No `advise` charts (analytics `charts` owns visuals).

### Decomposition risks

- **`sideboard` is the riskiest feature** (ILP modeling, saturating-coverage linearization, the two-layer anti-hate graph). Sized as its own feature; the greedy fallback is a built-in escape hatch if the ILP linearization proves fiddly. Design the anti-hate unified pass first within the feature.
- **NIU thesis prior-art open item** (advisory-methods §3): a 403-blocked thesis is the likeliest direct prior art for sideboard-as-MIP. Non-blocking — our max-coverage/submodular formulation is load-bearing and community-confirmed; flagged in the `sideboard` feature for a manual pull before claiming full novelty.
- **Matchup-data sparsity downstream**: positioning's MC and sideboard's `Δ` ride on matchup cells that are n<30-gated and bimodal-coverage-skewed. Mitigated by the inherited confidence-gating (BEST-CALL only on established/evolving cells) and the MC carrying honest CIs — not a new risk, but it bounds how confident the advisory output can be.

### UI alignment
- Skipped — `epic-advisory` is a CLI-only surface (`advise` text reports + audit trail); no net-new screens. `ux-ui-design` mockups N/A.
