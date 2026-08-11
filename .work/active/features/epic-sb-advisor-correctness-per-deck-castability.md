---
id: epic-sb-advisor-correctness-per-deck-castability
kind: feature
stage: drafting
tags: [advisory, deferred]
parent: epic-sb-advisor-correctness
depends_on: [epic-sb-advisor-correctness-backtest-ci-gate]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-11
---

# Per-deck element impact — replace the global-best-hoser gate

## Brief

Every `(archetype, tag)` element weight in `_build_coverage_model` is currently multiplied by the
impact of `best_hoser_for_tag[tag]` — a hoser selected GLOBALLY by swing with no castability or
symmetry input — but evaluated with THIS deck's colors and vulnerability tags
(`src/legacy_engine/advisory/sideboard.py:1871-1893`, Step 2; the global selection is Step 1 at
`:1828-1845`). The gate therefore prices an element by a card the deck may not be able to play.
This feature replaces that with a per-deck impact multiplier derived from the candidates that
actually cover the element for THIS deck.

The defect has two faces and one fix. **Face 1 (hard zero):** if the global best answer for a tag
is off-color (best for `creature-based` = a `{B}` card, deck = mono-U), `castability_factor`
returns 0.0 and the element weight zeroes for EVERY candidate — including castable colorless
answers such as Engineered Explosives that cover the same tag. **Face 2 (symmetry floor):** if the
global best is `symmetry: "symmetric"` and shares an axis with the deck's own vulnerability tags,
`symmetry_factor` returns `_SYMMETRY_FLOOR` (0.15) and deflates that tag's elements ~6.7x for every
archetype — even when an asymmetric, castable alternative exists. Both faces are live in the
shipped catalog: `creature-based` is attacked by Toxic Deluge (`symmetric`, `{B}`) and Sheoldred's
Edict (`asymmetric`, `{B}`) at identical `dedicated` swing, so which one Step 1 happens to select
decides whether every `creature-based` element in the model runs at full weight or at 0.15. That
is the leading hypothesis for the epic's winners-only creature-interaction cluster, and this
feature is where it gets tested rather than asserted.

Does NOT cover: the `_hate:` pseudo-elements (their impact modulation needs a representable
self-cost first — that's `hate-self-cost`, which builds on the per-candidate evaluation seam this
feature introduces); changing `impact.py`'s factor definitions or its multiplicative-hard-gate
philosophy; anything about matchup plans; blending observed adoption into scores (locked out).

## Epic context

- Parent epic: `epic-sb-advisor-correctness`
- Position in epic: first mechanism fix. Depends on `backtest-ci-gate` for hermetic before/after
  evidence and re-pins the ratchet when it lands. Produces the per-candidate impact-evaluation
  seam that `hate-self-cost` reuses, and the fix whose effect `winners-only-triage` triages the
  residual of — both depend on it.

## Inherited design decisions

- **Calibration philosophy** (epic): mechanism fixes only; observed adoption stays a diagnostic and
  is NEVER blended into scores. This feature changes which hoser's impact prices an element — it
  never reads adoption.
- **Element-gate form** (epic `## Design decisions`): use the MAX impact over the candidates that
  actually cover the element for this deck, not "the best castable hoser for the tag". The
  max-over-covering form fixes both the hard-zero and the symmetry-floor face with one change.
- **Backtest CI gate**: this feature re-pins the divergence budget after it lands; widening
  requires epic-level justification.

## Research briefs

- `docs/briefs/scorer-flexibility-valuation.md` — §2 distortion analysis (D1/D2/D3) on element
  weighting and the deflation of real opponent elements; the direct precedent for this change.
- `docs/briefs/advisory-methods.md` — advisory surface conventions.
- `docs/briefs/sideboard-core-and-hedge.md` — the core+hedge / natural-budget τ machinery whose
  scale this change perturbs.

## Foundation references

- `docs/ARCHITECTURE.md` — the `sideboard.py` row states the element-weight formula as
  `field_share × swing × impact(best_hoser, archetype, ...).score_without_draw_prob()`; this
  feature rolls that assertion forward.
- `docs/ARCHITECTURE.md` — the `impact.py` row (multiplicative hard gates, floors).
- `docs/SPEC.md` — Pillar 4 (Meta Attack / Advisory).
- Patterns: `.agents/skills/patterns/objective-search-split.md` (keep the per-candidate impact
  computation a pure, hand-testable loop), `.agents/skills/patterns/gated-additive-augmentation.md`
  (the `opponent_linchpins=None` no-op path must stay byte-identical),
  `.agents/skills/patterns/freshness-stripped-cli-body-golden.md` (goldens will move — that is the
  point; move them deliberately, do not re-baseline silently).

<!-- The /feature-design pass will fill in interfaces, signatures, and implementation units. -->
