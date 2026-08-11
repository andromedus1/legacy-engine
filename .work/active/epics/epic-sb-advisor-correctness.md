---
id: epic-sb-advisor-correctness
kind: epic
stage: implementing
tags: [advisory, deferred]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-11
---

# Sideboard-advisor correctness — close the gap between recommendations and observed boards

## Deferred decision (2026-08-11)

Deferred by operator direction. Trust in the modeled recommender is low, the remaining mechanism
work is large with uncertain payoff, and observed top-finisher sideboard choices are the primary
decision evidence for now. This epic and its children are outside the best-deck-decision-trust
autopilot scope; retain the findings for a future explicit resumption.

## Brief

Dogfooding keeps producing the same class of finding: the sideboard advisor recommends cards
real top-finisher boards never run (Defense Grid at 4x vs 0% of 258 boards; Damping Sphere vs
2.7%) and never recommends cards virtually every real board runs (the creature-interaction
cluster: Sheoldred's Edict 50.4%, Toxic Deluge, Snuff Out). The mechanisms are verified — the
`_hate:` coverage path applies no impact factor, element weights are hard-gated by the GLOBAL
best hoser's castability, the base mean-field model is greedy at alpha=1.0, and the
matchup-plan OUT side is adoption-locked into fetchland cuts. This epic makes the advisor's
output agree with observed reality — or surface the divergence honestly per the
divergence-as-diagnostic pattern — and fixes the correctness bugs found alongside
(off-color acquire suggestions, missing combined main+SB 4-of guard).

Three verified bugs with known fixes are promoted as immediate child stories (see below);
the model-level items are absorbed here as design inputs for epic-design.

**Deferable stretch member:** opponent-boarding-response (adversarial post-board modeling) —
epic-design may defer it or route it to epic-sb-config-evaluation; it needs a pre/post-board
data split that does not exist yet.

## Child stories (promoted at scope time, stage: implementing)
- epic-sb-advisor-correctness-acquire-color-filter — color-identity filter for acquire/SB candidate pool
- epic-sb-advisor-correctness-fourof-guard — combined main+SB 4-of legality guard
- epic-sb-advisor-correctness-sweep-polish — sweep report near-dupe clusters + Σ-adoption formatting

## Design decisions
<!-- captured 2026-07-31 via epic-design --only-questions; feature-design treats these as fixed inputs -->
- **Calibration philosophy**: Mechanism fixes only; adoption stays diagnostic — fix the
  verified defects (impact factor on `_hate:` coverage, castability gating, OUT-side flex,
  alpha greediness); observed adoption remains a divergence diagnostic per the
  divergence-as-diagnostic pattern, never blended into scores.
- **Backtest CI gate**: Yes — a hermetic backtest fixture with a pinned divergence budget
  runs in CI; advisory changes that widen divergence vs the observed-boards reference fail.
- **Opponent-boarding-response**: Deferred — stays an absorbed member, not decomposed into
  v1 features; revisit when a game-level pre/post-board data path exists.

<!-- resolved 2026-07-31 during epic-design (autopilot delegation, judgment-resolved) -->
- **Element-gate form**: Take the MAX impact over the candidates that actually COVER the element
  for this deck — not "the best CASTABLE-for-this-deck hoser" as the member finding proposed.
  Reading the code showed the global-best gate has two faces, not one: the hard-zero
  (off-color best → `castability_factor` 0.0 → element dies for castable colorless alternatives)
  AND a symmetry-floor face (a `symmetric` global best sharing an axis with the deck's own
  vulnerability tags → `_SYMMETRY_FLOOR` 0.15 → that tag's elements deflate ~6.7x for every
  archetype). `creature-based` is attacked by Toxic Deluge (`symmetric`) and Sheoldred's Edict
  (`asymmetric`) at identical `dedicated` swing, so Step 1's arbitrary tie-break decides which
  regime the whole model runs in — the leading hypothesis for the winners-only creature cluster.
  Max-over-covering fixes both faces with one change; "best castable hoser" fixes only one.
- **Self-cost representation home**: A curated schema extension on `data/hosers/legacy.json`
  (protection/self-cost with scope semantics) lands in THIS epic; `epic-card-semantics-ir`'s
  validated IR later becomes a derivation source for the same field per
  hybrid-derived-curated-registry. Rationale: `docs/briefs/card-semantics-ir.md` already specifies
  the `polarity` / `owner_scope` vocabulary and names the Defense Grid case, but that epic is
  unscoped and brief-gated — the scorer fix must not wait on it, and anticipating the IR's
  vocabulary means no second migration.
- **`_hate:` objective structure**: Keep `_hate:` pseudo-elements inside the SINGLE coverage
  objective, priced by an impact multiplier. Do not split protective coverage into its own
  sub-objective with a separate slot budget (`docs/briefs/scorer-flexibility-valuation.md`'s open
  question). The multiplier is smaller, reversible, and does not perturb the τ / core+hedge
  machinery; the budget split stays available if it proves insufficient.
- **No alpha tuning**: `_DEFAULT_OPTION_VALUE_ALPHA` is NOT a lever for the Damping Sphere
  divergence. The near-miss is pre-existing in the base greedy model at alpha=1.0, so tuning alpha
  would be adoption-matching by another name — exactly what the calibration philosophy locks out.
- **Matchup-plan OUT-side form**: Hard-exempt lands from the OUT/flex pool and degrade honestly
  when no legal non-land flex remains, rather than lowering `lock_threshold` globally. Lowering the
  threshold unlocks spells indiscriminately across every archetype; the land exemption is targeted
  at the verified failure and preserves the consensus-core protection the threshold exists for.
- **Winners-only work is diagnosis, not calibration**: The winners-only member becomes an
  explain-absence surface plus a missing-mechanic / engine-edge classification whose findings emit
  substrate items. It is explicitly NOT a "make the scorer match winners" feature — that would
  violate the locked calibration philosophy.

## Decomposition

Split by **mechanism**, not by symptom. The three headline divergences (Defense Grid 0%, Damping
Sphere 2.7%, the winners-only creature cluster) are three faces of two code defects plus one
representability gap, so the decomposition follows the defects: a measuring stick that lands first,
one element-weight gate fix, one self-cost representability fix that builds on it, an independent
matchup-plan fix that shares no code with either, and a residual triage that runs after the gate
fix so it triages a repaired engine rather than a known-broken one.

Why this shape over the alternatives. **One "scorer correctness" feature** was rejected as far past
the 5-15-unit sizing rule — a curated schema extension with load-time validation, an impact-model
change, an element-gate change, a graded self-cost, and the goldens for all of it. **Splitting per
symptom card** (a Defense Grid feature, a Damping Sphere feature) was rejected because both cards
share one root cause and would fight over the same ~80 lines of `_build_coverage_model`. **Folding
the triage into the gate fix** was rejected because the triage's un-catalogued half (Snuff Out,
Barrowgoyf, Feed the Cycle) is an attack-derivation gap owned by `epic-card-semantics-ir` — it
needs a classification-and-park surface, not a scorer change. The one deliberate serialization is
`hate-self-cost` after `per-deck-castability`: both edit the same element-weight block, and the
per-candidate impact evaluation the gate fix introduces is exactly the seam the `_hate:` modulation
consumes. `matchup-plan-flex` is fully parallel — `_plan_matchups` output is not part of the
backtest's recommended-board partition, so it neither depends on nor perturbs the ratchet.

### Child features

- `epic-sb-advisor-correctness-backtest-ci-gate` — hermetic backtest fixture + pinned divergence
  budget in CI (the measuring stick every mechanism fix proves itself against) — depends on:
  `[epic-sb-advisor-correctness-fourof-guard, epic-sb-advisor-correctness-acquire-color-filter]`
- `epic-sb-advisor-correctness-per-deck-castability` — replace the global-best-hoser element gate
  with max impact over the candidates that actually cover the element for this deck (fixes both the
  hard-zero and symmetry-floor faces) — depends on:
  `[epic-sb-advisor-correctness-backtest-ci-gate]`
- `epic-sb-advisor-correctness-hate-self-cost` — representable protection/self-cost semantics on
  the curated catalog + impact-modulated `_hate:` coverage + graded (not cliff) reactive self-cost;
  the shared Defense Grid / Damping Sphere root cause — depends on:
  `[epic-sb-advisor-correctness-per-deck-castability]`
- `epic-sb-advisor-correctness-matchup-plan-flex` — exempt lands from the OUT/flex pool, degrade
  honestly when no flex remains, gate IN candidates on coverage-axis relevance not correlation
  alone — depends on: `[]`
- `epic-sb-advisor-correctness-winners-only-triage` — explain-absence diagnostic + cluster
  classification (missing mechanic vs engine edge) over the residual blind spots — depends on:
  `[epic-sb-advisor-correctness-per-deck-castability]`

Not decomposed: `idea-opponent-boarding-response` stays an absorbed member per the locked deferral
(needs a game-level pre/post-board data split that does not exist).

### Decomposition risks

1. **The cheap version of `hate-self-cost` is a silent no-op.** Simply "turning on impact
   modulation for `_hate:` coverage" without the new self-cost representation yields
   `symmetry_factor == 1.0` for every `_hate`-only card — the symmetry gate fires on
   `hoser.attacks & my_vulnerability_tags` and `"_hate"` is never a vulnerability tag, so Defense
   Grid's `symmetric` flag is dead data on every code path today. The representable self-cost is
   load-bearing, not polish. `feature-design` must not sequence the modulation before the schema.
2. **`per-deck-castability` rescales the whole element-weight distribution.** Max-over-covering
   only ever RAISES element weights, and the natural-budget τ stop and `_coverage_scale` read that
   distribution's scale. Boards could get systematically larger or smaller for reasons unrelated to
   the bug. The freshness-stripped CLI-body goldens will move loudly — that is the intended alarm;
   re-baseline deliberately with the τ interaction checked, never silently.
3. **`hate-self-cost` can over-correct.** Twelve of 37 catalog entries are `symmetry: "symmetric"`,
   including cards that are genuinely correct picks (Engineered Explosives, Chalice, Blood Moon,
   Toxic Deluge). A blunt symmetric tax would trade the `scorer_only` false positives for
   `winners_only` blind spots. The ratchet must pin BOTH partition sides, and acceptance needs a
   should-stay control case, not only a should-drop case.
4. **Thin evidence on the winners-only side.** The sweep labels the creature-based cluster THIN
   (speculative winner samples). The triage must not promote a thin cluster to "confirmed missing
   mechanic", and the CI budget must not pin on a thin metric.
5. **Boundary pressure against `epic-card-semantics-ir`.** Self-cost/protection semantics and
   attack derivation both live at that seam. The split is: PRICING self-cost in the advisory scorer
   (curated field, here) vs DERIVING polarity/owner-scope from oracle text at ingest (the IR,
   there). `winners-only-triage` classifies and parks un-catalogued cards; it does not extend the
   derivation rules.
6. **Scope elasticity on `winners-only-triage`.** If `per-deck-castability` resolves the creature
   cluster outright, the triage shrinks. That is a success, not a reason to drop the feature — the
   un-catalogued residual (Barrowgoyf 83.7%, Feed the Cycle, Snuff Out) and the documented-dissent
   cases still need the surface.

## Member findings (absorbed from backlog; full text below)

---

### idea-hate-coverability-overvalues-defense-grid


# `_hate:` coverage applies no impact factor — Defense Grid false positive (CONFIRMED mechanism)

Field-scoped backtest: Defense Grid recommended at 4 copies; **0%** of 258 local-field-relevant
top-finisher boards run it. Independent deep review (2026-07-03, pinned f53e6a4) confirmed the
mechanism — stronger than first filed:

1. **`_hate:` element weights are never impact-modulated** (sideboard.py ~1783: `weight =
   interactive_share * _SWING_SOFT`, full stop) — the centrality×symmetry×castability modulation
   runs only for `(archetype, tag)` opponent elements. Post-deflation-fix, real elements are
   ~0.01-0.015 while each hate element is ~0.07-0.09 — and hate weight is identical for every deck
   tag, unconditioned on whether the field actually attacks that axis.
2. **Coverage is binary set-membership** (~1882-1886): any `"_hate"`-attacking card covers every
   `_hate:<tag>` element at full weight; `_build_impact_annotations` skips `_hate` cards, so the
   self-cost never even shows in explainability output.
3. **The `symmetry: "symmetric"` flag is structurally inert for `_hate`-only cards**: the symmetry
   gate fires on `hoser.attacks ∩ my_vulnerability_tags ≠ ∅`, and `"_hate"` is never a deck
   vulnerability tag — empty by construction. Defense Grid's symmetric flag is dead data on every
   code path.
4. **The self-cost model is a binary cliff**: `_ANTI_SYNERGY_MAP` → reactive at fraction ≥0.40;
   Dimir Tempo sits just under, so the tax on its OWN instant-speed FoW/Daze/Brainstorm is priced
   at exactly zero. Domain reality: Defense Grid's protection is own-turn-scoped — right for a
   proactive combo deck, wrong for a deck that operates at instant speed on both turns; the `_hate`
   tag has no notion of protection *kind*.
5. **The removed guard**: pre-`feature-sfv-weights`, the empirical-pool filter (0% adoption) was
   the only thing blocking exactly this false-positive class; the exemption removed it on principled
   grounds with no compensating mechanical discount. Also: the Step 4c cap applies only to
   UNCOVERED hate elements — covered ones keep full weight (~5-10× the largest real element).

**Fix directions** (from the review): impact-modulate `_hate` coverage per covering card (requires a
representable self-cost — e.g. a `protects` field with scope semantics: own-turn vs both-turns);
and/or condition Step-3 hate weights on which tags the interactive field actually attacks; and/or a
graded (not cliff) reactive self-cost. Validate: Defense Grid drops out of the recommended board on
the field-scoped backtest. Relates to [[idea-card-semantics-rules-layer]] (protection-kind semantics).

## Sweep confirmation (2026-07-04, validated harness)

The archetype sweep confirms this at full scale: **Defense Grid is scorer-only in 18 of 26
swept archetypes** (global current-regime field; also scorer-only for Dimir Tempo vs the
local field) — the single most systematic false positive in the engine. Top-ranked
scorer_only `_hate` cluster; winners' adoption ≤12% everywhere it's recommended.

---

### idea-damping-sphere-base-model-near-miss


# Damping Sphere scorer-only divergence — base-model near-miss (verified)

Field-scoped backtest (Dimir Tempo + the local meta): Damping Sphere recommended but only **2.7%** of 258
top-finisher boards run it. Verified mechanism (option-value deep review, 2026-07-03): it is a
PRE-EXISTING near-miss in the base mean-field model — greedy at `alpha=1.0` (option-value term
fully disabled) already recommends it; the default ILP sits right at the margin (absent at α=1.0,
present at α=0.7). Not manufactured by the option-value term.

Likely axis: its `attacks: ["ramp", "storm-reliant"]` + symmetric flag — the base model prices its
ramp/storm coverage as competitive for this field while real pilots don't play it in Dimir Tempo
(its "spells cost {1} more per prior spell" tax also hits the caster's own cantrip turns — the same
symmetric-self-cost representability gap as [[idea-hate-coverability-overvalues-defense-grid]]).
Investigate with the divergence-as-diagnostic discipline; candidate systematic fix shared with the
Defense Grid item (graded self-cost for symmetric cards). Never auto-calibrate it away.

## Sweep confirmation (2026-07-04, validated harness)

Archetype sweep: **Damping Sphere is scorer-only in 6 archetypes** (global field, `ramp`
cluster) and scorer-only for Dimir Tempo vs the local field — session-1's finding is
systematic, shares the symmetric-self-cost root cause with Defense Grid (18 archetypes).

---

### idea-element-weight-global-best-castability-gate


# Element weights hard-gated by the GLOBAL best hoser's deck-specific castability

Found by independent review (2026-07-03), pre-existing from epic-1 B3 wiring (sideboard.py
~1718-1733): each `(archetype, tag)` element's weight is multiplied by the impact of
`best_hoser_for_tag[tag]` — selected globally by swing with no castability input — evaluated with
THIS deck's colors. If the global best answer for a tag is off-color for the deck (e.g. best =
Sheoldred's Edict {B}, deck = mono-U), `castability_factor` returns 0.0 and the element weight
zeroes FOR EVERY CANDIDATE — including castable colorless answers (e.g. Engineered Explosives)
that cover the same tag. Milder variant: a symmetric-floored global best deflates the element
×0.15 for asymmetric alternatives.

Fix: evaluate the impact multiplier with the best CASTABLE-for-this-deck hoser for the tag, or take
the max impact over covering candidates. Test: a mono-U deck's creature-based element stays live
via EE when the global best is off-color black.

---

### idea-winners-only-triage-creature-interaction


# Triage the remaining winners-only divergences — creature-interaction cluster looks systematic

The field-scoped backtest (Dimir Tempo + the local meta, 2026-07-03) shows 9 winners-only cards at ≥20%
adoption; only Consign was investigated. The un-recommended creature-interaction cluster —
Sheoldred's Edict (50.4%), Toxic Deluge, Snuff Out (each ~virtually always in real boards) — being
absent from recommendations is a candidate SYSTEMATIC gap (is creature-based coverage under-weighted
for this field? is removal's swing under-credited vs hosers?), not per-card noise. Also un-triaged:
Barrowgoyf (83.7%), Feed the Cycle, Grafdigger's Cage, Harbinger (partially recommended), Surgical
(graveyard-meta pollution candidate even field-scoped). Investigate cluster-by-cluster with the
divergence-as-diagnostic discipline: each is either a missing mechanic (fix) or an engine edge
(document why the engine dissents).

## Sweep confirmation (2026-07-04, validated harness)

The generalizing sweep (feature-archetype-sweep-backtest) reproduces this as a first-class
cluster: winners-only `creature-based` across 7 archetypes — Sheoldred's Edict / Long
Goodbye / Fatal Push (3 each: Dimir family + Doomsday), Toxic Deluge (Dimir Tempo 86%),
Snuff Out — honestly labeled THIN (speculative winner samples). Copy-count note from the
study: winners run reactive fixers ~60% as 1-ofs, so the gap is WHICH cards get credited,
not their copy counts.

---

### idea-matchup-plan-out-side-weak


# Matchup-plan OUT side is adoption-locked into fetchland cuts

Found while grounding the Dimir primer (2026-07-04): `_plan_matchups`' OUT selection locks
every card at >=65% archetype adoption, which for a consensus-tight deck leaves only
FETCHLANDS as flex — its data-driven plans proposed cutting 2-3 lands (Scalding Tarn,
Bloodstained Mire) for spells vs Izzet/Jeskai/mirror, and the mirror plan boarded Hydroblast
into a UB deck (correlational card-value noise). The IN side had real signal (Consign vs
Izzet n=71, Hydroblast vs Doomsday n=30 corroborated judgment). Candidate fixes: exempt
lands from the flex pool (or cap land cuts at 0-1), and/or gate INs on the coverage model's
axis relevance (Hydroblast needs a red target in the matchup), not correlation alone. The
primers used judgment plans with engine signals cited/rejected explicitly — the audit trail
for this item.

---

### idea-opponent-boarding-response


Model opponent sideboarding response in matchup/card-value signals.

Current state: all winrates are match-level Bo3 (post-board games included), so the
*average* opponent boarding is priced in — but there is no pre/post-board split and no
adversarial response modeling. When the sideboard advisor tunes our 15 toward the field,
opponents' counter-adaptation to our new configuration isn't modeled; the signal is
corpus-equilibrium, presence-correlational, and explicitly labeled "NOT before/after-board"
in `advisory/sideboard.py` + `analytics/card_value.py`.

Candidate direction (from the capture conversation): condition card values on the opponent
archetype's typical side-in package against our macro-archetype (derive per-archetype
boarding tendencies from registered 75s' side compositions vs field), and surface the delta
as a diagnostic (divergence-as-diagnostic pattern), not a blended number.

Surfaced while answering "does the winrate account for opponent sideboarding?" during
best-call/best-deck analysis.
