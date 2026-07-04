---
id: epic-scorer-flexibility-valuation
kind: epic
stage: done
tags: [advisory, analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Scorer flexibility valuation — model breadth from first principles

## Brief

The sideboard scorer (shipped in `epic-sideboard-scoring-model`) **structurally undervalues broad,
flexible interaction**, and its own backtest surface caught it: on the maintainer's real Dimir Tempo deck vs
the 107-player local field, `advise backtest` (670 top-finisher boards, established tier) shows
**Force of Negation in 96.4% of winning boards** while the scorer scores it **`gain=0.0001`** and never
recommends it — a ~1000× disagreement on the format's single most-played sideboard card. Consign to
Memory (96% of winners) is likewise ignored; Damping Sphere (3.6% of winners) is recommended as a
likely false positive. Adding the missing cards to the catalog (attempted, reverted) did **not** change
the recommendation — proving the gap is in the **scoring model**, not the catalog.

This epic fixes the valuation model, using the backtest as the empirical anchor. It is distinct from
`epic-sideboard-scoring-model` (which BUILT the scorer + backtest); this one corrects how that scorer
*values* cards.

## Strategic decisions

- **Valuation philosophy — pure mechanics; NO empirical signal in scores; backtest is a divergence
  diagnostic, not a calibration.** We do NOT fold winning-board inclusion% into the score as a prior —
  that would regress the engine to consensus and make it a *follower*, forfeiting legacy-engine's reason
  to exist (seeing mispricings before the field does). Instead we **model flexibility as a mechanic from
  first principles**: a card like Force of Negation is near-universal *because* it is flexible, free,
  instant-speed interaction that answers many matchups at once — a property the current model can't
  represent. Model that property, and the engine values flexibility correctly *everywhere*: it will
  agree with consensus on FoN **and** be able to surface an underrated flexible card the consensus
  hasn't found. The backtest's role is **diagnostic + acceptance gate only**: model-vs-winning-boards
  divergence is a *flag to investigate* (missing mechanic **or** a genuine edge the engine sees first — a
  human decides which), never an auto-calibration. This preserves the "transparency substitutes for
  proof" ethos and the ambition to see further than the field. *Scope precision (2026-07-03 review):*
  the guardrail enforced is specifically **no winning-board inclusion% in scores** (backtest.py never
  feeds scoring); pre-existing empirical components from earlier epics (the ≥5% adoption pool filter,
  presence-correlational swing proxies, empirical promotion) remain and are a separate, labeled concern.
- **Research depth — brief first (DONE).** Blocking brief written:
  [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md).
  Key result: the coverage objective is **already monotone submodular**, so marginal-gain maximization
  credits breadth by construction — the fix repairs three distortions (misapplied concavity, deflated/
  uncoverable element weights, missing attachments) rather than adding a flexibility heuristic — plus a
  pure-mechanics **option-value term** (CVaR-style tail-robustness over the Dirichlet field) so
  flexibility is valued under uncertainty with no empirical prior. Grounded in submodular/max-coverage
  theory + CVaR + Legacy sideboard-construction sources. `[needs-brief]` cleared.
- **`_hate:` self-protection — make protective cards coverable.** The largest element weights today are
  uncoverable `_hate:` pseudo-elements (protect the deck's own manabase/colors, ~0.089 each) that crowd
  out real opponent coverage. Represent counter-hosers / protective cards (Veil of Summer, Defense Grid,
  Carpet of Flowers, …) so those needs are actually *served* by the board — turning dead crowding weight
  into real coverage — rather than only rebalancing it away.

## The gap: five root causes (design inputs, grounded in the 2026-07-03 dogfooding session)

1. **No mechanical axis for broad/flexible interaction.** Soft counters (FoN, Spell Pierce, Mystical
   Dispute) are absent from `data/hosers/legacy.json`; when empirically promoted they mis-tag to the
   generic `combo` fallback. Deeper: there is no vulnerability/capability axis for "flexible free
   interaction answering the whole combo/control plurality," so a broad counter's value fragments across
   tiny per-(archetype,tag) `combo`/`storm-reliant` elements and never aggregates into a competitive
   score. **This is the core modeling problem the brief must crack.**
2. **`plays-blue` never fires as an OPPONENT vulnerability** (only `plays-red` does, for the blasts), so
   Mystical Dispute is inert against a ~45%-blue field. Gap in `_color_contingent_tags` / the field
   vulnerability derivation (`advisory/whattoplay.py`).
3. **Uncoverable `_hate:` self-protection weights dominate and crowd out opponent coverage** (see
   strategic decision #3).
4. **Opponent elements are impact-deflated to ~0.003–0.005** by the uniform `draw_prob(1)≈0.4` factor in
   the element-weight impact multiplier (`copies=1`) plus baseline centrality 0.5, so flexible counters
   score near-zero and lose every slot to concrete hosers (Hydroblast/Null Rod/EE). (Folds
   `idea-scorer-element-weight-drawprob`.)
5. **Coverage can't express "flexibility value"** — one card answering many matchups — because coverage
   is per-element; breadth earns no aggregate credit.

## Acceptance oracle (empirical anchor, NOT a score input)

The epic is "done" when `advise backtest` shows the recommended board's **overlap with top-finisher
boards materially improves** — FoN / Consign move from *winners-only* into *overlap*; the Damping Sphere
false-positive drops — AND the mechanism producing that is first-principles flexibility valuation, not
an empirical prior. Any remaining model-vs-consensus divergence is surfaced for human judgment, not
scored away. Re-run on the maintainer's Dimir Tempo board + local field as the concrete regression case.

## Folded backlog items

- `idea-hoser-catalog-missing-blue-and-fon` — the catalog gap + the "no broad-interaction axis" finding
  (absorbed; becomes the catalog + axis features).
- `idea-scorer-element-weight-drawprob` — the draw-prob deflation nit (root cause #4; absorbed).
- Related but NOT folded (distinct small fix, stays in backlog): `idea-derive-attacks-land-destruction-mislabel`.

## Touches

`advisory/sideboard.py` (`_build_coverage_model`, element weights, `_hate` elements, the ILP objective),
`advisory/impact.py` (multiplicative factors, draw-prob), `advisory/whattoplay.py` (vulnerability-tag
derivation, `_color_contingent_tags`), `advisory/backtest.py` (the diagnostic/acceptance harness),
`data/hosers/legacy.json`. No foundation-doc roll-forward at scope — the modeling approach is
undecided pending the brief + epic-design; docs update once the design settles (and at the release docs
gate), consistent with how `epic-sideboard-scoring-model` was handled.

## Design decisions (epic-design, 2026-07-03)

- **Breadth mechanism**: **reformulate the coverage objective to true submodular marginal-gain** — a card credited by its total marginal coverage across every element it answers (inherits the 1−1/e greedy guarantee). Chosen over an additive breadth term (double-count risk) or a minimal sums-only fix (may not capture breadth). The principled fix, least likely to need rework.
- **Option value (CVaR)**: **in-scope for this epic** — the pure-mechanics flexibility-under-uncertainty lever is the deepest expression of "see further than consensus"; ship it here rather than defer.
- **Backtest scope**: **enhance to field/window-scoped in this epic** — validation must be local-field-specific, not global-Dimir polluted by graveyard-meta tech, for an honest acceptance gate.

## Decomposition

Split by capability along the brief's causal chain: cards must **attach** to what they answer and their weights must not be **deflated/crowded** before breadth can **aggregate**; the **option-value** term sits on the repaired objective; the **field-scoped backtest** is the acceptance oracle that lands early to validate the rest. Reformulating the objective (breadth-objective) is the trickiest, highest-leverage feature and gates on the two foundations.

### Child features

- `feature-sfv-attachments` — plays-<color> as opponent vuln + broad-interaction attribution + missing counters (FoN/Spell Pierce/Mystical Dispute) — depends on: `[]`
- `feature-sfv-weights` — remove draw-prob deflation; make `_hate` self-protection coverable — depends on: `[]`
- `feature-sfv-backtest-scoped` — field/window-scoped `advise backtest` acceptance harness — depends on: `[]`
- `feature-sfv-breadth-objective` — **(trickiest)** reformulate the objective to true submodular marginal-gain — depends on: `[feature-sfv-attachments, feature-sfv-weights]`
- `feature-sfv-option-value` — CVaR tail-robustness over the Dirichlet field (risk-appetite dial) — depends on: `[feature-sfv-breadth-objective]`
- `feature-sfv-colorless-axis` — colorless-reliant vulnerability axis (promoted mid-completion; closes the Consign acceptance criterion) — depends on: `[feature-sfv-attachments]`

### Decomposition risks

- **Objective reformulation regresses the reviewed scorer.** breadth-objective rewrites the core `_build_coverage_model`/ILP path. *Mitigation*: the 2400+ existing tests + the field-scoped backtest as regression gate; feature-design forces 2-3 sub-options and picks the least-invasive that captures breadth; preserve τ/hedge machinery.
- **CVaR option-value hard to make deterministic/testable.** *Mitigation*: closed-form Beta-marginal of the Dirichlet (positioning already computes it) over Monte-Carlo; named α; keep strictly separate from the copy-count taper axis.
- **Critical path** attachments∥weights∥backtest-scoped → breadth-objective → option-value is 3 deep; parallelism is in the wave-1 trio. Acceptable for a 5-feature epic.


## Completion (2026-07-03)

All 6 features done (5 planned + `feature-sfv-colorless-axis` promoted mid-completion because the
acceptance oracle names Consign). Phase-8 fresh-context completion review: **COMPLETE** — threshold
calibration independently reproduced to three decimals against the DB; mechanism purity verified
(no winning-board signal in any scoring path; the α/scale constants are offline-selected and
disclosed in-source); suite 2556 green.

**Acceptance oracle adjudication:** FoN winners-only→overlap (99.2%) MET · Consign
winners-only→overlap (95.7%) MET · "Damping Sphere false-positive drops" NOT met — adjudicated
covered by the oracle's own "surfaced for human judgment, not scored away" clause: verified
pre-existing base-model near-miss (greedy at α=1.0 with option-value disabled already recommends
it; a symmetric-self-cost representability gap shared with Defense Grid), not introduced or
strengthened by this epic, diagnosed + tracked (`idea-damping-sphere-base-model-near-miss`,
`idea-hate-coverability-overvalues-defense-grid`). The only in-epic ways to force it to drop were
an empirical prior (forbidden by the same oracle) or a new self-cost mechanic no feature scoped.

**Determinism caveat (recorded per review Finding 1):** backtest agreement reads 6/9 or 7/9
depending on an untracked ILP tie in slot 9 (Snuff Out 30.2% vs Long Goodbye 1.2% —
`idea-ilp-tiebreak-nondeterminism`); the acceptance facts (Consign/FoN in overlap; Damping
Sphere/Defense Grid the stable scorer-only pair) hold across both optima.

Tracked follow-ups (legitimate deferrals): the two scorer-only divergences above, the ILP
tie-break, the winners-only creature-interaction cluster triage, regex/capability nits, and the
strategic arcs (`idea-card-semantics-rules-layer`, `idea-archetype-sweep-backtest-loop`).
