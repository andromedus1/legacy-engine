---
id: feature-sb-field-weighted-scorer
kind: feature
stage: done
tags: [advisory]
parent: epic-sideboard-scoring-model
depends_on: [feature-sb-effect-tagging-model]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Field-weighted card scorer (coverage diagnostic + decomposed impact)

## Brief

Core feature (B) of `epic-sideboard-scoring-model`. The scorer that consumes the effect-tagging /
linchpin model (Feature A) and ranks/optimizes the 15 over the owned card pool.

Commitments (from the epic):
- **Objective = `Σ(field_share × Δequity)`** (expected match-win contribution). Coverage % is a
  *diagnostic* surfaced alongside, never the optimization target.
- **Decomposed impact** — `impact(card, opp) = centrality × symmetry × castability × draw-probability`
  (draw-probability = `P(draw ≥1 in a Bo3)` given copy count; hypergeometric). Reads centrality,
  symmetry, castability from Feature A.
- **Owned-only** via `data/collection/inventory.json`.
- **Field-share uncertainty** — propagate the Dirichlet field-share uncertainty already used in
  `advise positioning`; don't over-commit silver bullets to a noisy small-share matchup; flag
  brittle boards over-tuned to the snapshot.
- **Explainable** — every per-card score decomposes into its factors so the pilot can audit it
  (transparency substitutes for the empirical validation we can't do).
- **Honest-degrade gating** — thin/uncovered field cells labeled low-confidence (the Boulder field
  has ~36% of matchups with no data).

<!-- Design input below preserved from the folded backlog idea. -->

## Design input (from idea-field-weighted-sideboard-optimizer)

Score every sideboard candidate on two axes, then run all owned options through the scorer to
optimize the 15:
1. **Field coverage** — the share of the current field a card is *meaningfully relevant* against,
   summing field-shares of the archetypes it impacts (e.g. "Null Rod hits ~26%": Painter + D&T +
   Saga Storm + Eldrazi + Blue Artifacts). A single headline number per card, per field.
2. **Per-opponent impact score** — how hard the card swings each specific matchup it touches.
   Coverage % hides this: Null Rod is a near hard-lock vs Painter (stops Grindstone's activated
   ability) but a marginal mana-tax vs Eldrazi (doesn't touch Chalice, which is static). Impact is
   per-(card, opponent), not flat.

The novel/hard part is the **mechanics-grounded per-opponent IMPACT model** — what the card actually
does to that deck's gameplan — rather than curated swing constants or a presence-correlational proxy.
It reads the card-effect → archetype-plan interaction layer from Feature A (activated ability?
colorless spell? Tomb? a graveyard the deck doesn't have? a linchpin?).

Connects to existing surfaces: extends `advise sideboard` (field-weighting, `--smart` coverage
curve, natural-budget τ, per-card gain in `advisory/sideboard.py`); reuses `report cards --contrast`
as one empirical impact input where n≥30; feeds `feature-sb-slot-roi-punt` (this scores cards, that
allocates slots).

Honesty gates: coverage % is a *relevance* number, not a measured win-rate lift; impact scores are
mechanics-inferred, NOT causal before/after-board measurements (no game-level data in corpus). Every
score carries the caveat and gates by sample tier.

Motivating session (2026-07-03): hand-computed exactly this for Andrew's Dimir Tempo board vs the
107-player Boulder field; surfaced Mystical Dispute (~43%) and Spell Pierce (~54%) as high-coverage
anti-blue cards absent from the current SB.

## Design decisions

Captured via `feature-design --only-questions` (2026-07-03), interactive alignment before autopilot.
These are fixed inputs for the eventual full design pass.

- **Impact-factor combination**: **Multiplicative (hard gates).**
  `impact = centrality × symmetry × castability × draw-prob`, each ∈ [0,1]. Any factor near 0
  zeroes the card — a fully symmetric self-hoser or an uncastable card is worthless regardless of
  coverage. Encodes "a self-hosing SB card is a trap" directly and stays interpretable.
- **Δequity base magnitude**: **Reuse existing swing, modulated by impact.** Base magnitude from the
  curated `_SWING_DEDICATED`/`_SWING_SOFT` constants + the empirical presence-correlational proxy
  where n≥30 (as today), then modulated by the decomposed impact factors. Inherits the honest-degrade
  gating already built; does not discard curated expertise or the empirical proxy.
- **Output surface**: **Replace `advise sideboard`'s scoring core in place.** The decomposed score
  becomes how `advise sideboard` ranks candidates (Feature A already feeds this command); add the
  explainable per-card breakdown to its output. One operator surface, one code path (SSOT); existing
  output/flags preserved, tests re-baselined. No parallel command or dual scoring paths.
- **Draw-probability × ILP**: **Feed per-copy value into the ILP (tapers copies).** Draw-probability
  `P(draw ≥1 in a Bo3)` modulates the marginal value of each successive copy, so the existing
  pulp/CBC solver naturally tapers (3rd copy worth less than 1st). "How many copies" becomes a
  first-class, principled output — the solver change lives here, respecting `max_copies`.

Implication for the full design pass: the objective stays `Σ(field_share × Δequity)`; Dirichlet
field-share uncertainty (from `advise positioning`) annotates confidence and shrinks tiny-share
matchups so the multiplicative score isn't over-committed to noisy cells (resolve exact treatment at
design time — annotate + shrink is the default, full robust optimization is out of scope for v1).

---

## Architectural choice

Considered: (1) a new parallel scorer command; (2) a full rewrite of the coverage/ILP solver; (3) **replace the scoring-core inputs in place** — keep the entire `maximize Σ_e weight_e·g(cov_e)` ILP+greedy+τ+hedge machinery in `sideboard.py`, and change only *how* `weight_e` and the per-copy marginal are computed. Chosen **(3)**, per the locked decision "replace `advise sideboard`'s scoring core in place." The solver, honest-degrade, natural-budget τ, and hedge-fill infrastructure are reused unchanged (SSOT); Feature B redefines two things: the element weight `share × swing` becomes `share × swing × impact`, and the copy-shaping `_redundancy_penalty` becomes draw-probability-driven. A new module `advisory/impact.py` owns the decomposed factors; `_build_coverage_model` consumes it. When impact data is absent the path stays byte-identical to today (honest-degrade + preserves the no-collection contract).

## Implementation Units

### Unit B1: `advisory/impact.py` — the four decomposed factors (trickiest; design first)

**File**: `src/legacy_engine/advisory/impact.py` (new). **Story**: `…-impact`.

```python
_CENTRALITY_BASELINE = 0.5   # non-linchpin coverage still counts, at half a linchpin hit
_SYMMETRY_FLOOR = 0.15       # a fully self-hosing symmetric card isn't quite 0 (you can still time it)
# castability is a hard gate: 0.0 when truly uncastable, else 1.0

@dataclass(frozen=True)
class ImpactBreakdown:
    centrality: float; symmetry: float; castability: float; draw_prob: float
    def score(self) -> float: ...   # multiplicative product (hard gates)

def centrality_factor(hoser, opp_archetype, opp_linchpins) -> float:
    """max centrality among opp linchpins this hoser neutralizes (capability ∩ neutralized_by),
    else _CENTRALITY_BASELINE. Uses hoser_capabilities() [Unit B2]."""

def symmetry_factor(hoser, my_vulnerability_tags) -> float:
    """1.0 if hoser.symmetry == 'asymmetric'; if 'symmetric', penalize toward _SYMMETRY_FLOOR
    when my deck shares the hosed axis (e.g. symmetric graveyard hate AND my deck emits
    graveyard-recursion/fuel), else ~1.0 (symmetric but I'm not self-hit)."""

def castability_factor(hoser, my_colors, opp_archetype, opp_cards=None) -> float:
    """1.0 castable in this matchup; 0.0 if color-uncastable and not castable_any_color;
    cast_requires token gated (e.g. 'opp_controls_plains' → 1.0 only if opp deck controls a Plains)."""

def draw_probability(copies, deck_size=60, cards_seen=_BO3_CARDS_SEEN) -> float:
    """Hypergeometric P(draw >= 1 copy across a Bo3), given copies in a deck_size deck.
    Marginal per-copy value = draw_probability(k) - draw_probability(k-1) (concave → taper)."""

def impact(hoser, opp_archetype, *, opp_linchpins, my_vulnerability_tags, my_colors, copies, opp_cards=None) -> ImpactBreakdown:
    """Combine multiplicatively (hard gates). Returns the breakdown for explainability."""
```

### Unit B2: hoser → capability bridge (the piece deferred from Feature A)

**File**: `src/legacy_engine/advisory/impact.py`. **Story**: `…-impact`.

```python
def hoser_capabilities(hoser: HoserCard) -> frozenset[str]:
    """Map a hoser's attacks + name/oracle to the linchpin `neutralized_by` capability vocabulary
    (artifact-ability-lock, artifact-bounce, artifact-removal, exile-graveyard, counter-on-cast,
    board-sweep, creature-removal, enchantment-removal). Conservative — only assert a capability
    the card's text supports. This is the bridge linchpins.py explicitly left to Feature B."""
```

### Unit B3: wire impact into `_build_coverage_model` element weights

**File**: `src/legacy_engine/advisory/sideboard.py`. **Story**: `…-wiring`.
Element weight becomes `field_share × swing × impact(best hoser for element | my deck, that opp).score()`. Swing base source is unchanged (curated `_SWING_*` + `empirical_swing_proxy` where n≥30) — impact only *modulates* it. Preserve a byte-identical path when impact inputs are unavailable (no linchpins/collection) so the honest-degrade + no-collection contract tests stay green.

### Unit B4: draw-probability per-copy value into the ILP

**File**: `src/legacy_engine/advisory/sideboard.py`. **Story**: `…-wiring`.
Replace the generic `_u_redundancy`/`_redundancy_penalty` per-copy shaping with the draw-probability marginal from B1 (the Nth copy contributes `draw_probability(N) − draw_probability(N−1)`), keeping the concave/LP-representable shape the solver needs and respecting `max_copies`. "How many copies" becomes a principled output.

### Unit B5: explainable output + coverage% diagnostic + field-share uncertainty

**File**: `src/legacy_engine/advisory/sideboard.py` (+ the `advise sideboard` CLI render). **Story**: `…-output`.
Each recommended card surfaces its `ImpactBreakdown` (centrality/symmetry/castability/draw-prob) so the score is auditable. Coverage% surfaced as a labeled DIAGNOSTIC line (not the objective). Dirichlet field-share uncertainty (reuse `advise positioning`'s machinery) shrinks tiny-share matchup weights and annotates recommendations with a confidence tier; thin/uncovered field stays honest-degrade-labeled.

## Implementation Order

1. Story `…-impact` (B1 + B2) — pure, DB-free factor functions + the capability bridge; no deps. The trickiest/most novel; testable in isolation.
2. Story `…-wiring` (B3 + B4) — depends on `…-impact`; replaces the scoring-core inputs + copy-shaping in the solver.
3. Story `…-output` (B5) — depends on `…-wiring`; explainability + coverage% diagnostic + uncertainty.

## Testing

- `tests/test_impact.py` (new): each factor (centrality linchpin-hit vs baseline; symmetry self-hosing penalty vs not; castability hard gate incl. cast_requires; hypergeometric draw-prob monotonic + concave marginal); multiplicative combine + the hard-gate behavior (uncastable/fully-symmetric → ~0).
- `tests/test_sideboard.py`: element weights reflect `× impact`; copy taper follows draw-prob; the no-impact-data path is byte-identical (regression guard).
- `tests/test_recommendation_coverage.py`: deliberate re-baseline for the new weighting; assert the explainable breakdown is present and the coverage% diagnostic renders.
- Reuse pytest factory fixtures; hand-built linchpin/vuln inputs keep impact tests DB-free (objective-search-split).

## Risks

- **Multiplicative over-zeroing** — a mildly symmetric or awkward card could score ~0. *Fallback*: symmetry/centrality are floored (`_SYMMETRY_FLOOR`, `_CENTRALITY_BASELINE`); only true uncastability hard-gates to 0. Floors are named constants, tunable.
- **Core-replacement regression** — changing element weights risks the existing coverage tests. *Fallback*: byte-identical no-impact-data path + deliberate re-baseline; the no-collection contract test is the guard.
- **Draw-prob assumptions** (Bo3 cards-seen, deck size) — modeling choices. *Fallback*: named constants; the taper *shape* matters more than absolute values.
- **Centrality bridge false-matches** — a hoser miscredited with neutralizing a linchpin. *Fallback*: conservative `hoser_capabilities`; non-linchpin coverage still scores at `_CENTRALITY_BASELINE`, so a miss degrades gracefully rather than swinging wildly.

## Implementation summary (2026-07-03)

All three child stories done; feature advanced implementing → review.

- **`…-impact`** (B1+B2) — new `advisory/impact.py`: `ImpactBreakdown` + `centrality/symmetry/castability/draw_probability` factors combined multiplicatively (hard gates), plus the `hoser_capabilities` bridge to the linchpin `neutralized_by` vocabulary. Pure/DB-free. (Also surfaced + fixed the Null Rod catalog-color bug.)
- **`…-wiring`** (B3+B4) — `_build_coverage_model` element weight = `share × swing × impact(best hoser, opp | my deck).score()` (`copies=1` to avoid double-tapering); per-copy redundancy curve replaced with the hypergeometric draw-prob marginal `(1.0, .61, .37, .22)`. Byte-identical no-impact path (gated like `matchup_pressure is None`) — zero re-baselining.
- **`…-output`** (B5) — explainable per-card `CardImpactAnnotation` audit lines, coverage% diagnostic (labeled NOT-the-objective, union at board level), and Dirichlet field-share uncertainty reused from `advise positioning` (closed-form Beta marginal) driving a `brittle` flag + `confidence` tier. Annotate + real computed shrink, NOT live reweighting of the solver (zero blast radius to the reviewed objective).

**Verification**: full suite green — 2419 passed (was 2308 at feature-A start). Smoke-tested end-to-end against the real DB + the live Boulder field.

**Locked decisions honored**: multiplicative hard gates; swing reused-and-modulated; `advise sideboard` core replaced in place (one command, one code path); draw-prob feeds per-copy ILP value. Objective stays `Σ(share × Δequity)`; coverage% is diagnostic-only.
