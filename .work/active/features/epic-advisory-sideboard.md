---
id: epic-advisory-sideboard
kind: feature
stage: implementing
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

## Design decisions
(Resolved under autopilot delegation — Phase 4.5. Parent-epic + advisory-methods §3 decisions inherited.
No strategic 50/50s.)

- **Curated `HOSER_CATALOG` seeded from legacy-metagame §6** (the brief's explicit "hosers by target" edge
  list): each entry maps a card → `{attacks: frozenset[vulnerability-tag | "_hate"], colors, max_copies,
  swing}`. Seed: Surgical Extraction / Faerie Macabre / Leyline of the Void / Endurance / Containment Priest /
  Grafdigger's Cage → `graveyard-reliant`; Force of Will / Flusterstorm / Mindbreak Trap / Thoughtseize / Duress
  → `combo`,`storm-reliant`; Blood Moon / Back to Basics / Wasteland → `greedy-manabase`; Force of Vigor /
  Krosan Grip → `greedy-manabase`/artifact-hate; Veil of Summer / Defense Grid / Carpet of Flowers → `_hate`
  (counter-hosers, attack hate pseudo-elements). A curated catalog is the SSOT for candidate cards, mirroring
  `card_tags`' curated staples.
- **`swing` (Δ) is a curated heuristic constant per hoser, NOT empirically derived** — there is no
  before/after-sideboard data to estimate it from. Every package output is **labeled heuristic-not-data-driven**
  for the swing component (audit-trail principle). Default swing by category (e.g. dedicated GY hate vs
  graveyard-reliant ≈ 0.20; soft hate ≈ 0.10), documented as module constants. This is the honest MVP: the
  *structure* (weighted max-coverage + ILP/greedy) is the deliverable; the magnitudes are flagged estimates.
- **Weighted MAXIMUM-COVERAGE with binary coverage** (textbook Nemhauser formulation the brief cites): element =
  field archetype `a` (+ hate pseudo-elements); `value(a) = field_share(a) × swing_a` where `swing_a` is the best
  swing among catalog hosers that attack a tag `a` carries (from `whattoplay.vulnerability_tags`). Objective:
  maximize `Σ value(a)·y_a` with `y_a` binary (covered ≥ once). Binary coverage IS the n=1 saturating case
  (`g(1)`); the multi-answer saturating `g(n)=1−(1−p)^n` redundancy refinement is **documented as a future
  additive extension** (keeps the MVP ILP tractable and honest). Redundancy still emerges across the field
  because the budget spreads over many archetypes.
- **ILP (PuLP/CBC) primary + greedy always computed for the trace.** PuLP/CBC solves exact max-coverage
  (`msg=0`, trivial scale). The greedy (1−1/e) marginal-gain trace is **always produced** as the explainable
  "why each card" rationale, even when the ILP solution is used for the final 15. A `solver="ilp"|"greedy"`
  toggle lets the caller force greedy (e.g. if CBC is unavailable).
- **Color pre-filter before the solver**: drop catalog hosers not castable in the deck's colors
  (`colors.compute_deck_colors` over the deck; hoser colors from the catalog; colorless always allowed).
- **Anti-hate pseudo-elements in one unified pass**: the deck's own vulnerability tags →
  expected-opposing-hate `h_k = Σ_a field_share(a)·P(a brings hate k vs you)`, where `P` is heuristic
  (an archetype is assumed to bring hate category `k` if it has access to it and the deck is vulnerable to it).
  Significant `h_k` become pseudo-elements added to the same element set with their weights; counter-hosers
  (`_hate`) cover them. The optimizer then trades a hoser slot for a counter-hoser when the field's hate is the
  bigger threat — one unified coverage solve, no second pass.
- **`reserved` slots** held out of the 15 (default 0) for flex/maindeck-overlap; budget = `15 − reserved`.
- **Bounded-integer copies** per hoser (catalog `max_copies`, default 1; e.g. Surgical 1–2).
- **`SideboardPackage` is a `@dataclass` in `advisory/sideboard.py`** (not `models/`) — computed record, same
  sanctioned deviation as `PositioningResult`/analytics records; logged.
- **Single-stride, no child stories** — one cohesive `advisory/sideboard.py` (catalog + coverage model + two
  solvers + orchestrator); the ILP and greedy share the coverage model, so splitting fragments it.

## Architectural choice

**A shared coverage-model builder feeding both a PuLP/CBC ILP and a greedy solver, orchestrated by
`recommend_sideboard`.** Options weighed: (A) build the element/weight/candidate coverage model once, then solve
it two ways — ILP for the optimal 15, greedy for the explainable marginal-gain trace (chosen — DRY, and the
brief explicitly wants both: exact + explainable); (B) ILP-only (rejected — loses the legible per-card "why");
(C) greedy-only (rejected — the brief makes ILP primary, exact at this scale). The coverage model is a plain
data structure (`elements: {id → weight}`, `candidates: {card → covered element ids}`), so both solvers operate
on the same abstraction and the anti-hate pseudo-elements fold in as just more elements.

## Implementation Units

### Unit 1: `HOSER_CATALOG` + `HoserCard`

**File**: `src/legacy_engine/advisory/sideboard.py`

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field

from legacy_engine.advisory.field import FieldDistribution

log = logging.getLogger(__name__)

# Heuristic swing constants (NOT empirical — labeled in output)
_SWING_DEDICATED = 0.20   # dedicated hate vs its target tag
_SWING_SOFT = 0.10        # soft / partial answers
_HATE_ELEMENT = "_hate"   # pseudo-element key prefix for anti-hate


@dataclass(frozen=True)
class HoserCard:
    name: str
    attacks: frozenset[str]   # vulnerability tags (or "_hate" for counter-hosers)
    colors: frozenset[str]    # WUBRG cast colors ("" = colorless)
    max_copies: int
    swing: float

# Seeded from legacy-metagame §6 "hosers by target"
HOSER_CATALOG: dict[str, HoserCard] = { ... }   # ~20-30 curated entries
```

**Acceptance Criteria**:
- [ ] Catalog includes the §6 seeds (Surgical→graveyard-reliant; FoW→combo; Veil of Summer→`_hate`; Blood Moon/Wasteland→greedy-manabase; Force of Vigor present).
- [ ] Every entry has non-empty `attacks`, a `max_copies ≥ 1`, and a `swing` in (0, 1).

---

### Unit 2: Coverage-model builder (trickiest — designed first)

**File**: `src/legacy_engine/advisory/sideboard.py`

```python
@dataclass
class CoverageModel:
    element_weight: dict[str, float]          # element id (archetype | "_hate:<k>") → weight
    candidate_covers: dict[str, frozenset[str]]  # card → element ids it covers
    candidate_meta: dict[str, HoserCard]
    warnings: tuple[str, ...]


def _build_coverage_model(
    field: FieldDistribution,
    archetype_tags: dict[str, frozenset[str]],   # from whattoplay.field_vulnerability_tags
    deck_colors: frozenset[str],
    deck_tags: frozenset[str],                   # the user deck's own vulnerability tags
    *,
    catalog: dict[str, HoserCard] = None,
) -> CoverageModel:
    """Build elements (field archetypes + anti-hate pseudo-elements) with weights, and the
    color-prefiltered candidate hosers with the element sets they cover."""
```

**Implementation Notes**:
- For each field archetype `a` with tags `T_a`: `value(a) = field_share(a) × max(swing of catalog hosers
  attacking any tag in T_a, else 0)`; archetypes no catalog hoser attacks get weight 0 (still listed).
- Anti-hate: for each hate category `k` (a vulnerability tag the *deck* carries, `deck_tags`), pseudo-element
  `"_hate:"+k` with weight `Σ_a field_share(a)·[a can bring hate for k]` (heuristic: `a` brings hate `k` if some
  catalog hoser attacking `k` is castable in `a`'s colors — approx via the catalog). Threshold tiny weights out.
- `candidate_covers[card]`: archetypes whose tags intersect `card.attacks`, plus `"_hate:"+k` when card attacks
  `_hate` (counter-hoser). Color pre-filter: drop cards whose `colors ⊄ deck_colors` (colorless ok).

**Acceptance Criteria**:
- [ ] An archetype tagged graveyard-reliant gets `value = share × 0.20` (Surgical's swing) and is covered by Surgical.
- [ ] A red hoser is dropped from candidates when `deck_colors` lacks R.
- [ ] A deck carrying `combo` produces a `"_hate:combo"` pseudo-element covered by Veil of Summer.

---

### Unit 3: Greedy solver + marginal-gain trace

**File**: `src/legacy_engine/advisory/sideboard.py`

```python
@dataclass
class PickTrace:
    card: str
    marginal_gain: float
    newly_covered: frozenset[str]


def _greedy_solve(model: CoverageModel, *, budget: int) -> tuple[dict[str, int], list[PickTrace]]:
    """Add the max-marginal-gain card (respecting max_copies) until budget slots are full.
    Returns (card→copies, ordered trace). Binary coverage: an element already covered adds no gain,
    so a 2nd copy of the same card only helps if it covers a still-uncovered element."""
```

**Acceptance Criteria**:
- [ ] On a field where graveyard-reliant dominates, greedy's first pick is a graveyard hoser.
- [ ] The trace is ordered by marginal gain; total picks ≤ budget; copies ≤ each card's `max_copies`.

---

### Unit 4: ILP solver (PuLP/CBC)

**File**: `src/legacy_engine/advisory/sideboard.py`

```python
def _ilp_solve(model: CoverageModel, *, budget: int) -> dict[str, int]:
    """Exact weighted max-coverage via PuLP/CBC.

    Vars: x_c ∈ {0..max_copies} integer per candidate; y_e ∈ {0,1} per element.
    max Σ_e weight_e·y_e  s.t.  Σ_c x_c ≤ budget;  y_e ≤ Σ_{c covers e} x_c  ∀e.
    Solve with PULP_CBC_CMD(msg=0). Returns card→copies (x_c>0).
    """
```

**Implementation Notes**:
- Build with `pulp.LpProblem(..., pulp.LpMaximize)`. If CBC is unavailable / solve status not Optimal, log and
  signal the caller to fall back to greedy (don't crash).

**Acceptance Criteria**:
- [ ] ILP total objective ≥ greedy objective on the same model (exact ≥ (1−1/e) approx).
- [ ] Respects budget and `max_copies`; returns only `x_c > 0` cards.
- [ ] Status-not-Optimal → raises a sentinel the orchestrator catches → greedy fallback.

---

### Unit 5: `recommend_sideboard` + `SideboardPackage`

**File**: `src/legacy_engine/advisory/sideboard.py`

```python
@dataclass
class SideboardPackage:
    cards: dict[str, int]            # card → copies (sums to ≤ budget)
    trace: list[PickTrace]           # greedy marginal-gain rationale (always present)
    covered_weight: float            # Σ weight of covered elements
    budget: int
    reserved: int
    solver_used: str                 # "ilp" | "greedy"
    field_source: str
    heuristic_note: str              # swing magnitudes are curated heuristics, not data
    warnings: tuple[str, ...]


def recommend_sideboard(
    con, field: FieldDistribution, deck_maindeck: dict[str, int], *,
    reserved: int = 0, solver: str = "ilp", catalog: dict[str, HoserCard] | None = None,
) -> SideboardPackage:
    """Recommend a 15-card sideboard via weighted max-coverage. Builds the coverage model from the
    field's per-archetype vulnerability tags (whattoplay) + the deck's colors/tags, solves with ILP
    (greedy fallback), and always attaches the greedy trace as the per-card rationale."""
```

**Implementation Notes**:
- `deck_colors = compute_deck_colors(...)`; `deck_tags = whattoplay.vulnerability_tags_for_deck(con, deck_maindeck)`;
  `archetype_tags = whattoplay.field_vulnerability_tags(con, field)`.
- `budget = 15 − reserved`. ILP primary; on its sentinel/exception → greedy. Greedy trace always computed.
- `heuristic_note` states swings are curated estimates (audit-trail / heuristic-vs-data label).

**Acceptance Criteria**:
- [ ] On a graveyard-heavy field, the package is dominated by graveyard hate; `solver_used == "ilp"`.
- [ ] `sum(cards.values()) ≤ 15 − reserved`; `reserved=3` → ≤ 12.
- [ ] `solver="greedy"` forces greedy; the package still has a coherent trace.
- [ ] A deck carrying `combo` with a hate-heavy field gets a counter-hoser (Veil/Defense Grid) slot.

---

### Unit 6: Module exports

**File**: `src/legacy_engine/advisory/__init__.py` — export `recommend_sideboard`, `SideboardPackage`,
`HoserCard`, `HOSER_CATALOG`, `PickTrace` (+ `__all__`).

## Implementation Order

1. **Unit 1** (catalog) — the candidate-card SSOT.
2. **Unit 2** (coverage model) — trickiest; elements/weights/anti-hate/color-prefilter.
3. **Unit 3** (greedy + trace) — the explainable solver.
4. **Unit 4** (ILP) — exact solver + fallback sentinel.
5. **Unit 5** (`recommend_sideboard` + `SideboardPackage`) — orchestrator.
6. **Unit 6** (exports).

## Testing

### Unit tests: `tests/test_sideboard.py`
House style; build a `FieldDistribution` directly (or via `build_global_field`) and a small `archetype_tags`
map for deterministic coverage. Most tests construct the coverage model from hand-specified field + tags so the
ILP/greedy arithmetic is exact and seed-free.

- `TestHoserCatalog` — §6 seeds present; well-formed entries.
- `TestCoverageModel` — weight = share×swing; color pre-filter drops off-color hosers; anti-hate pseudo-element created for the deck's tags.
- `TestGreedy` — dominant-tag first pick; trace ordering; budget + copy bounds.
- `TestILP` — objective ≥ greedy; budget/copy respected; reserved reduces budget; status-not-Optimal → fallback.
- `TestRecommendSideboard` — graveyard-heavy field → GY-hate package; counter-hoser appears when deck is combo + field is hate-heavy; `solver="greedy"` path; heuristic_note present.

### Integration points
- Seam with `whattoplay`: `field_vulnerability_tags` / `vulnerability_tags_for_deck` drive coverage — a
  corpus-backed test labels decks, builds the field, and confirms a graveyard archetype is covered by GY hate.
- Seam with `field-model`: consumes `FieldDistribution.shares`.
- Seam with `colors`: `compute_deck_colors` drives the color pre-filter.
- Seam with `pulp`: ILP solves with CBC (`msg=0`); a test asserts CBC availability or skips with a clear marker.

## Risks

- **`swing` magnitudes are heuristic, not data** — the package's *ordering* is only as good as the curated
  swings. **Mitigation**: every package carries `heuristic_note`; swings are coarse category constants; the
  *coverage structure* (which archetypes/tags are answered) is the robust part and is data-driven (field shares +
  vulnerability tags). **Fallback**: when matchup data later supports empirical Δ, swing becomes data-driven
  additively.
- **CBC solver availability** in CI/headless. **Mitigation**: ILP wrapped with a fallback to greedy on
  non-Optimal/exception; `solver="greedy"` always works; a test exercises the greedy path explicitly.
- **Binary coverage under-recommends redundancy** (no 2nd GY-hate card for the same archetype). **Mitigation**:
  documented as the n=1 saturating case; redundancy emerges across the multi-archetype field; the saturating
  `g(n)` refinement is a noted additive extension. **Fallback**: `max_copies` lets a hoser cover multiple
  archetypes via multiple copies where the catalog allows.
- **Catalog coverage gaps** (a field archetype no catalog hoser attacks). **Mitigation**: such archetypes get
  weight 0 and are listed in `warnings` (honest — "no curated answer for X"), never silently ignored.
