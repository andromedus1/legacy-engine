---
id: epic-sb-advisor-correctness-hate-self-cost
kind: feature
stage: drafting
tags: [advisory, deferred]
parent: epic-sb-advisor-correctness
depends_on: [epic-sb-advisor-correctness-per-deck-castability]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-11
---

# Representable self-cost for symmetric cards — price `_hate:` coverage honestly

## Brief

Defense Grid (recommended at 4x vs **0%** of 258 real boards; scorer-only in 18 of 26 swept
archetypes) and Damping Sphere (recommended vs 2.7% adoption; scorer-only in 6 archetypes) share
one root cause: the engine has no way to represent what a symmetric card costs its own pilot, so
it never charges for it. Four verified mechanisms compose into the false positive:
(1) `_hate:` element weights are `interactive_share * _SWING_SOFT` full stop
(`sideboard.py:1943`) — never impact-modulated, identical for every deck tag, and unconditioned on
whether the interactive field actually attacks that axis; (2) `_hate:` coverage is binary
set-membership (`:2066-2070`) — any `_hate`-attacking card covers every `_hate:<tag>` element at
full weight; (3) the `symmetry: "symmetric"` flag is structurally INERT for `_hate`-only cards,
because `symmetry_factor` fires on `hoser.attacks & my_vulnerability_tags` and `"_hate"` is never a
vulnerability tag — empty by construction, so Defense Grid's symmetric flag is dead data on every
code path; (4) the self-cost model is a binary cliff — `_ANTI_SYNERGY_MAP` blocks Defense Grid only
above `_REACTIVE_FRACTION_THRESHOLD` (0.40), and Dimir Tempo sits just under, pricing the tax on
its own instant-speed Force of Will / Daze / Brainstorm at exactly zero.

This feature makes self-cost representable and then charges for it. Scope: a curated schema
extension on the hoser catalog carrying protection/self-cost semantics with SCOPE (own-turn vs
both-turns, per-player vs opponent-only) validated at load time; consumption of that field in the
impact model so `_hate:` coverage is impact-modulated per covering card (reusing the
per-candidate evaluation seam from `per-deck-castability`); replacement of the binary reactive
cliff with a graded self-cost; and — as an explicit cut line if the feature runs long — conditioning
Step-3 `_hate:` weights on which tags the interactive field actually attacks. Acceptance is
mechanical, not adoption-matching: Defense Grid drops out of the recommended board on the
field-scoped backtest for Dimir Tempo vs the local meta, Damping Sphere's near-miss resolves at the
DEFAULT alpha, and a control symmetric card that is genuinely correct for its deck (e.g. Engineered
Explosives in a colorless-capable shell) is NOT suppressed.

Does NOT cover: tuning `_DEFAULT_OPTION_VALUE_ALPHA` (locked out — the Damping Sphere near-miss is
pre-existing in the base greedy model at alpha=1.0, so tuning alpha would be auto-calibration by
another name); deriving polarity/owner-scope from oracle text at ingest (that is
`epic-card-semantics-ir`'s IR — this feature ships the curated field the IR will later populate);
restructuring `_hate:` into a separate protective-coverage sub-objective with its own budget
(locked out — see inherited decisions); the `(archetype, tag)` element gate (shipped by
`per-deck-castability`).

## Epic context

- Parent epic: `epic-sb-advisor-correctness`
- Position in epic: the epic's highest-value and highest-risk mechanism fix. Consumer of
  `per-deck-castability`'s per-candidate impact seam; it and `winners-only-triage` are the two
  parallel arcs after that fix lands.

## Inherited design decisions

- **Calibration philosophy** (epic): mechanism fixes only; observed adoption stays a diagnostic and
  is NEVER blended into scores. The 0% / 2.7% adoption figures are the SYMPTOM that motivated this
  work — they are never an input to the fix, and the fix is accepted on mechanism, not on matching
  those numbers.
- **Self-cost representation home** (epic `## Design decisions`): a curated schema extension on
  `data/hosers/legacy.json` lives HERE; `epic-card-semantics-ir`'s IR later becomes a derivation
  source for the same field (hybrid-derived-curated-registry). This epic does not wait on the IR.
- **`_hate:` objective structure** (epic `## Design decisions`): keep `_hate:` inside the single
  coverage objective and price it with an impact multiplier. Do NOT split it into a separate
  protective-coverage sub-objective with its own slot budget — that restructuring stays available
  if the multiplier proves insufficient, but it is not this feature's scope.
- **No alpha tuning** (epic `## Design decisions`): the option-value alpha is not a lever for this
  divergence.
- **Backtest CI gate**: re-pin the ratchet when this lands; a widening in EITHER direction
  (`scorer_only` or `winners_only`) fails.

## Research briefs

- `docs/briefs/card-semantics-ir.md` — the polarity / owner-scope analysis; explicitly names the
  Defense Grid false positive as "symmetry detected but **self-impact** never priced" and proposes
  a `protects` channel with a `polarity` vocabulary (`answers | protects | exploits | enables |
  taxes`). This is the vocabulary this feature's curated field should anticipate so the IR can
  populate it later without a second migration.
- `docs/briefs/scorer-flexibility-valuation.md` — §2 D2 (uncoverable `_hate:` pseudo-elements
  crowding out real coverage) and the open question "does `_hate` self-protection belong in the
  same objective" (answered by the inherited decision above).
- `docs/briefs/sideboard-core-and-hedge.md` — the objective the multiplier feeds.

## Foundation references

- `docs/ARCHITECTURE.md` — the `whattoplay.py` row currently asserts "a card's value in PROTECTING
  its own manabase is deliberately not modeled by `attacks`"; this feature rolls that forward.
- `docs/ARCHITECTURE.md` — the `sideboard.py` row (anti-hate pseudo-elements) and the `impact.py`
  row (the four factors).
- `docs/SPEC.md` — Pillar 4 + the HONEST-DEGRADE NFR.
- Patterns: `.agents/skills/patterns/curated-json-resource-loader.md` and
  `.agents/skills/patterns/closed-vocabulary-fail-fast-token.md` (the new catalog field must get a
  module-level allow-set and a `ValueError` naming the token and the sorted allowed set, matching
  `_VALID_SYMMETRY` / `_VALID_ATTACK_TAGS`); `.agents/skills/patterns/gated-additive-augmentation.md`
  (absent field → byte-identical baseline); `.agents/skills/patterns/honest-degrade-marker.md`
  (a card with no self-cost data must be labeled unknown, not assumed free).

<!-- The /feature-design pass will fill in interfaces, signatures, and implementation units. -->
