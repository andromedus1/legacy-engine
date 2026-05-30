---
id: epic-advisory
kind: epic
stage: drafting
tags: [advisory]
parent: null
depends_on: [epic-meta-analytics]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
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

## Anticipated child features
- Meta-positioning score (Bayesian MC: Beta cells + Dirichlet shares; custom field; rank by P(best); report S and unweighted aggregate)
- Sideboard recommender (weighted submodular max-coverage; PuLP ILP + greedy fallback; bounded-integer copies; color pre-filter; anti-hate pseudo-elements)
- What-to-play (composition proactivity score; vulnerability tags; hate-equity coverage; best-deck vs best-call)
- Field-read report surface (field composition + ranked decks + sideboard package + audit trail)
