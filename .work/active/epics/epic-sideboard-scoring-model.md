---
id: epic-sideboard-scoring-model
kind: epic
stage: done
tags: [advisory, analytics]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Sideboard scoring model

## Brief

Raise the *quality* of the sideboard advisory's card-scoring so recommendations are
principled, explainable, and field-tuned. Today `advise sideboard` field-weights candidate
hosers by `field_share × swing` per vulnerability tag, but the swing is a curated constant
(`_SWING_DEDICATED`/`_SWING_SOFT`) or a presence-correlational proxy, the effect-tagging is
coarse and has known errors, and it double-counts axes the maindeck already covers. This
epic replaces that scoring core with a decomposed, auditable, mechanics-grounded model.

**Distinct from `epic-sb-config-evaluation`.** That epic is the *evaluation/comparison* arc
(the WITH/WITHOUT matchup-slot test and the whole-75 config/transform comparator — it shipped
`report cards --contrast` and `advise compare`). This epic is the *scoring model* that feeds
recommendations. They compose: the comparator measures configs; this scores the cards that go
into them.

### Three commitments (from a first-principles pass — must shape every feature)

1. **Objective = expected match-win contribution `Σ(field_share × Δequity)`, not "coverage %".**
   Coverage % (e.g. "Null Rod hits ~26% of the field") is a human-readable *diagnostic* layer,
   never the optimization target. Don't optimize the proxy.
2. **Impact decomposes into auditable, mechanics-grounded factors:**
   `impact(card, opp) = centrality × symmetry × castability × draw-probability`
   - **centrality** — does the card hit a *linchpin* of the opponent's gameplan (Null Rod
     stops Painter's Grindstone = lock) or a redundant piece (Null Rod taxes an Eldrazi Mox)?
   - **symmetry** — does it hose me too (Grafdigger's Cage vs my own Nethergoyf/Flow State)?
   - **castability** — can I actually cast it in *that* matchup (double-white Massacre needs
     their Plains; a `{U}{U}` card in a deck that Wastelands itself)?
   - **draw-probability** — `P(draw ≥1 in a Bo3)` given copy count; this is how "how many
     copies?" gets answered.
3. **Explainability substitutes for proof.** Card-level impact CANNOT be empirically validated
   with our data (corpus has decklists + match results, no game-level with/without outcomes).
   So every score must decompose into factors the pilot can audit — on-ethos with the project's
   HONEST-DEGRADE POLICY. The closest thing to validation is backtesting recommended boards
   against what actually wins (Feature E).

### Feature arc (foundation-first dependency order)

- **A · `feature-sb-effect-tagging-model`** (foundation, no deps) — fix + deepen the card→effect
  model: the quick catalog fixes (Hydroblast mis-tag; add Blue/Red Elemental Blast; dedupe
  identical hosers), plus color-contingent-hate, the symmetry flag, finer graveyard tags, an
  archetype **linchpin** model, and **castability** attributes. Folds `idea-sb-color-contingent-hate`
  + `idea-granular-effect-tagging` + new linchpin/castability.
- **B · `feature-sb-field-weighted-scorer`** (deps: A) — the scorer: coverage% diagnostic +
  decomposed impact, objective `Σ(share × Δequity)`, owned-only via the collection, Dirichlet
  field-share-uncertainty robustness, honest-degrade gating, and an explainable per-card
  breakdown. Folds `idea-field-weighted-sideboard-optimizer` + draw-probability.
- **C · `feature-sb-maindeck-aware-coverage`** (deps: B) — discount coverage the maindeck already
  supplies (the "SB'd Ghost Quarter while running 4 Wasteland" double-count).
- **D · `feature-sb-slot-roi-punt`** (deps: B) — rank matchups by ROI-per-slot; recommend
  conceding matchups where max realistic dedication can't cross 0.5 or beat the next-best slot.
- **E · `feature-sb-board-backtest`** (deps: B) — validate recommended boards against top-finisher
  boards for a comparable field; the only empirical anchor available.

### Second-wave (parked, not in this epic)

- **Marginal acquisition recommender** — "the one card you don't own that most raises your board's
  field-score" (ties to `idea-acquire-color-identity-filter`).
- **Swap-plan / OUT-side cost** — model what you *cut*, not just what you add (cutting combo pieces
  vs Izzet weakens other games). Extends D.

### Motivating context

Dogfooding Andrew's Dimir Tempo board vs the 107-player Boulder field (2026-07-03): hand-computing
coverage% against the Null Rod benchmark (~26%) surfaced Mystical Dispute (~43%) and Spell Pierce
(~54%) as high-coverage anti-blue cards absent from his board — and exposed the coverage-vs-impact
gap this epic exists to close. Respect `data/collection/inventory.json`, `advisory/sideboard.py`,
`data/hosers/legacy.json`, `analytics/card_value.py`, and the adaptive ban-aware matchup matrix.

## Completion (2026-07-03)

All 5 features + 8 stories done; epic advanced review → done after a Phase-8 fresh-context completion review returned COMPLETE. Full suite green (2464 passed, +156 net from 2308 at epic start). Every feature passed an independent fresh-context deep review (A / B / C+D+E — all APPROVE, all "no gamed tests"); end-to-end verified on the real Dimir Tempo deck + Boulder field (maindeck discount, plays-red coverage, impact breakdown, coverage% diagnostic, slot-ROI + PUNT all render honestly).

Three commitments delivered end-to-end: (a) objective = Σ(share×Δequity), coverage% diagnostic-only; (b) decomposed auditable impact (centrality×symmetry×castability×draw-prob, multiplicative gates) with per-card breakdown + Dirichlet confidence; (c) `advise backtest` validation surface.

Tracked follow-ups (legitimate deferrals, not blockers): `idea-docs-align-sideboard-scoring-model` (foundation-doc drift → release docs gate), `idea-scorer-element-weight-drawprob` (draw-prob double-count nit), `idea-derive-attacks-land-destruction-mislabel` (latent, dormant). Not shipped: no `/release-deploy` run — items remain unbound (late-binding).
