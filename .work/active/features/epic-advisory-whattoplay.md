---
id: epic-advisory-whattoplay
kind: feature
stage: implementing
tags: [advisory]
parent: epic-advisory
depends_on: [epic-advisory-field-model]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# What-to-Play Advisor (proactivity · vulnerability · hate-equity)

## Brief
The strategic read. Derive a continuous **proactivity score [0,1]** from card composition
(`proactive_mass = fast_mana + ritual + tutor + low_curve_score + compact_combo`;
`reactive_mass = counters + removal + stax + card_advantage + protection`;
`PROACTIVITY = proactive / (proactive + reactive)`) — auditable from card counts, not the archetype tag —
and **surface disagreement** between the computed score and the archetype's fair/unfair tag as a finding.
Tag archetypes with **vulnerability classes** (graveyard-reliant, combo, low-curve, greedy-manabase,
creature-based, low-interaction, storm-reliant) from oracle-text roles + metagame data. Compute
**hate-equity = the field share each hate category attacks** (`Σ field_share(a) for a carrying the tag`),
using **coverage, not a naive sum** for a package — this vector is exactly the sideboard recommender's
weighting input. Classify **best-deck vs best-call** from the **variance of a deck's matchup spread**
(low spread + high mean = robust BEST DECK; high spread + high field-specific mean = BEST CALL gamble).
Emit transparent **plan-clash WHY strings** (a readable rule table layered over the empirical matchup
numbers, never replacing them).

Consumes `field-model` (field shares for hate-equity) and the done `matchup-matrix` (spread variance) +
`Card` model (composition/oracle-text roles). 

Does NOT solve the sideboard ILP (`sideboard` consumes the hate-equity/vulnerability output), compute the
positioning score (`positioning`), or render the combined report (`report`).

## Epic context
- Parent epic: `epic-advisory`
- Position in epic: consumer of `field-model` + done `matchup-matrix`/`Card`; **producer of the
  vulnerability tags + hate-equity vector that `sideboard` depends on**. Parallel to `positioning`.

## Inherited design decisions
- **Proactivity is composition-derived** (auditable from card counts), not the archetype tag; surface
  computed-vs-tag disagreement as a finding.
- **Hate-equity uses coverage, not naive sum** (a deck carries multiple tags); it is the sideboard
  weighting input.
- **best-deck vs best-call = matchup-spread variance** classification (independent of `positioning`'s S
  ranking — the two combine only in `report`).
- **Plan-clash heuristics are a readable rule table → WHY strings layered over empirical numbers**, never
  replacing them; flag heuristic-vs-data disagreement.

## Research briefs
- `docs/briefs/advisory-methods.md` — §4 (proactivity formula + calibration, vulnerability-tag table,
  hate-equity coverage, plan-clash rule table, best-deck/best-call).
- `docs/briefs/legacy-metagame.md` §6-7 — hosers-by-target, current strategic read (tag-derivation inputs).

## Foundation references
- `docs/ARCHITECTURE.md` — `advisory/whattoplay.py`; `models/Card` role tags; `analytics/matchup.py`.
- `docs/PRINCIPLES.md` — #7 confidence-gate; heuristic-vs-data-driven labeling.

## Design decisions
(Resolved under autopilot delegation — Phase 4.5. Parent-epic + advisory-methods §4 decisions inherited.
No strategic 50/50s.)

- **A shared oracle-text role classifier (`_card_roles`) is the substrate** for proactivity and vulnerability,
  layered over the existing `card_tags` (`is_free_spell`, `staple_role`, `mana_base_tags`). It maps a `Card` to a
  set of analytical roles (`counter`, `removal`, `stax`, `card_advantage`, `protection`, `ritual`, `tutor`,
  `compact_combo`, `graveyard_recursion`, `storm`, …) via curated regexes over `oracle_text` + `type_line` +
  `staple_role`. This is whattoplay's own analytical layer — `card_tags` stays the curated-staple SSOT and is
  reused, not duplicated.
- **Proactivity operates on a supplied decklist** (`maindeck: dict[str,int]`); cards resolved via
  `store.fetch_card`. **Vulnerability tags are per-archetype**, derived from the corpus aggregate of decks
  labeled that archetype (most-common cards via a `deck_cards`⋈`decks` query) — with a deck-level variant for a
  user's specific list. Rationale: proactivity tracks a *specific* list (the brief's point); vulnerability is a
  field-level property of an archetype.
- **Proactivity formula** (advisory-methods §4): `proactive_mass = fast_mana + ritual + tutor + low_curve_score
  + compact_combo`, `reactive_mass = counters + removal + stax + card_advantage + protection`, `PROACTIVITY =
  proactive/(proactive+reactive)` (0.5 when both zero). `low_curve_score` = sigmoid centered ~MV 2.0 over
  nonland average MV. Calibration is a **relative-ordering** target (combo > tempo > control), asserted as
  orderings in tests — not exact magic numbers.
- **Computed-vs-tag disagreement is surfaced as a finding** (not silently reconciled): when a deck's archetype
  carries a fair/unfair expectation that the computed proactivity contradicts, emit a `findings` note.
- **Hate-equity = coverage, not naive sum**: `hate_equity(field, archetype_tags)` returns, per vulnerability
  tag, `Σ field_share(a) for a whose tag-set includes it`. For a *package* of hate spanning multiple tags, the
  combined equity is the **coverage** (union of field share attacked), not the sum (a deck carrying two attacked
  tags is counted once toward the package). This vector is the sideboard recommender's weighting input.
- **best-deck vs best-call** = the **variance of an archetype's matchup spread** across the field: low spread +
  high mean → `BEST_DECK` (robust); high spread + high field-weighted mean → `BEST_CALL` (field-specific gamble).
  Computed from the matchup-matrix row (known cells), independent of `positioning`'s `S`.
- **Plan-clash is a readable rule table → WHY strings layered over the empirical matchup numbers, never
  replacing them**; when heuristic and the empirical cell disagree (e.g. heuristic favors A but the cell shows
  A losing), emit a disagreement note (possible pilot-skill/low-n confound).
- **Single-stride, no child stories** — one cohesive `advisory/whattoplay.py` built around the shared
  `_card_roles` core; splitting would fragment that core.

## Architectural choice

**One `advisory/whattoplay.py` with a shared `_card_roles` classifier feeding four analytical surfaces**
(proactivity, vulnerability tags, hate-equity, best-deck/best-call) plus plan-clash WHY strings. Options
weighed: (A) shared role classifier + surface functions in one module (chosen — the role classification is the
common substrate and stays in one place); (B) push role classification into `card_tags` (rejected — `card_tags`
is the curated-staple SSOT; analytical role heuristics are advisory-specific and would bloat it); (C) split
composition-signals vs matchup-stats into two modules (rejected — best-deck/best-call is small and the module is
cohesive). Heuristics are transparent rule tables / curated regexes (never a learned weight matrix), keeping
every output auditable per the confidence-gating + heuristic-vs-data-label principle.

## Implementation Units

### Unit 1: `_card_roles` oracle-text role classifier (trickiest — designed first)

**File**: `src/legacy_engine/advisory/whattoplay.py`

```python
from __future__ import annotations

import logging
from dataclasses import dataclass

import duckdb

from legacy_engine.card_tags import is_free_spell, mana_base_tags, staple_role
from legacy_engine.models.card import Card

log = logging.getLogger(__name__)

# Analytical roles (a card may carry several)
Role = str  # "counter" | "removal" | "stax" | "card_advantage" | "protection"
            # | "fast_mana" | "ritual" | "tutor" | "compact_combo" | "graveyard_recursion" | "storm"


def _card_roles(card: Card) -> set[str]:
    """Classify a Card into analytical roles via oracle-text regexes + card_tags + type_line.

    Reuses ``staple_role``/``is_free_spell``/``mana_base_tags``; adds regex detection for counter,
    removal, stax/taxing, card-advantage, protection, ritual, tutor, storm, graveyard-recursion.
    Pure function — auditable from card text.
    """
```

**Implementation Notes**:
- Regex table (case-insensitive over `oracle_text`): counter=`r"counter target"`; removal=`r"destroy target|exile target (creature|permanent)|deals? \d+ damage to"`; ritual=`r"add \{[wubrgc]\}.*\{[wubrgc]\}"` on an instant/sorcery (net-positive mana); tutor=`r"search your library for (a|up to)"`; storm=`r"\bstorm\b"`; graveyard_recursion=`r"return.*from your graveyard|from your graveyard to (the battlefield|your hand)"`; protection=`r"hexproof|protection from|can't be countered"`; stax/taxing=`r"costs? \{?\d?\}? more|don't untap|players can't"` or `staple_role==lock_piece`; card_advantage=`r"draw (a card|\w+ cards)"` or `staple_role==cantrip`; fast_mana via `staple_role in {fast_mana}` or `mana_base_tags` fast.
- `compact_combo` is a deck-level signal (see Unit 3), not a single-card role — omit here.
- Lands → mostly empty (rely on `mana_base_tags` for greedy-manabase signal at the deck level).

**Acceptance Criteria**:
- [ ] Force of Will → `{counter, protection?}`-ish includes `counter`; Brainstorm → `card_advantage`; Dark Ritual → `ritual`; Demonic/Vampiric Tutor → `tutor`; Swords to Plowshares → `removal`; Chalice of the Void → `stax`.
- [ ] A vanilla creature → empty or just type-based; pure function, deterministic.

---

### Unit 2: `proactivity_score`

**File**: `src/legacy_engine/advisory/whattoplay.py`

```python
@dataclass
class ProactivityProfile:
    score: float                  # [0,1]
    proactive_mass: float
    reactive_mass: float
    low_curve_score: float
    findings: tuple[str, ...]     # e.g. computed-vs-archetype-tag disagreement


def _load_deck_cards(con: duckdb.DuckDBPyConnection, maindeck: dict[str, int]) -> list[tuple[Card, int]]:
    """Resolve a name→count maindeck to (Card, count) pairs via store.fetch_card (skip+warn unknowns)."""


def proactivity_score(
    con: duckdb.DuckDBPyConnection, maindeck: dict[str, int], *, archetype_tag: str | None = None,
) -> ProactivityProfile:
    """Composition-derived proactivity in [0,1] (advisory-methods §4 formula)."""
```

**Implementation Notes**:
- Weight each card's role contribution by its `count`. `low_curve_score`: sigmoid `1/(1+exp((avg_nonland_mv-2.0)/k))`.
- `score = proactive/(proactive+reactive)`; both zero → 0.5.
- If `archetype_tag` is a known fair/unfair label and the score contradicts it (e.g. "control" but score>0.65), append a finding.

**Acceptance Criteria**:
- [ ] A Storm/combo-style list (rituals + tutors + low curve) scores higher than a counter/removal control list (relative ordering).
- [ ] Both-zero composition → 0.5; score always in [0,1].
- [ ] Unknown card names are skipped with a warning, not a crash.

---

### Unit 3: Vulnerability tags

**File**: `src/legacy_engine/advisory/whattoplay.py`

```python
VulnerabilityTag = str  # graveyard-reliant | combo | low-curve | greedy-manabase
                        # | creature-based | low-interaction | storm-reliant


def _archetype_composition(con: duckdb.DuckDBPyConnection, archetype: str, *, provenance: str | None = None) -> dict[str, int]:
    """Aggregate the most-common cards across corpus decks labeled ``archetype`` (deck_cards⋈decks)."""


def vulnerability_tags(con: duckdb.DuckDBPyConnection, archetype: str) -> frozenset[str]:
    """Derive the archetype's vulnerability classes from its aggregate composition (oracle roles + mana base + curve)."""


def vulnerability_tags_for_deck(con: duckdb.DuckDBPyConnection, maindeck: dict[str, int]) -> frozenset[str]:
    """Same classification over a specific decklist."""
```

**Implementation Notes**:
- Tag rules (advisory-methods §4 table) over the composition's roles/curve/manabase:
  graveyard-reliant=`graveyard_recursion` density≥threshold; combo=`compact_combo` (low avg MV + tutor + a known win-con line); low-curve=avg nonland MV<2.0; greedy-manabase=high `mana_base_tags` fast/dual + nonbasic-heavy; creature-based=creature density≥threshold; low-interaction=low (counter+removal) density; storm-reliant=`storm` present.
- Thresholds are module constants, documented.

**Acceptance Criteria**:
- [ ] A Reanimator-style aggregate (graveyard recursion) → includes `graveyard-reliant`.
- [ ] A Death&Taxes-style aggregate (creatures + stax, low free-spell) → `creature-based` and not `combo`.
- [ ] A Storm aggregate → `storm-reliant` + `combo`.

---

### Unit 4: Hate-equity (coverage)

**File**: `src/legacy_engine/advisory/whattoplay.py`

```python
def hate_equity(
    field: FieldDistribution, archetype_tags: dict[str, frozenset[str]],
) -> dict[str, float]:
    """Per vulnerability tag, the field share attacking it: Σ field_share(a) for a carrying the tag.

    Coverage semantics: for a package spanning multiple tags, combined equity is the union of field
    share attacked (computed by the caller via set-union over attacked archetypes), NOT the sum.
    """


def field_vulnerability_tags(
    con: duckdb.DuckDBPyConnection, field: FieldDistribution,
) -> dict[str, frozenset[str]]:
    """Convenience: vulnerability_tags(a) for every archetype in the field."""
```

**Implementation Notes**:
- Per-tag equity is a straight share sum over archetypes carrying that tag. The **coverage** (union) is exposed
  via a helper `covered_share(field, archetypes_attacked: set[str]) -> float` so the sideboard recommender can
  ask "what share does this hoser package attack" without double-counting multi-tag archetypes.

**Acceptance Criteria**:
- [ ] Field {GY-reliant A:0.4, GY-reliant B:0.2, combo C:0.3} → `hate_equity["graveyard-reliant"]==0.6`.
- [ ] `covered_share` over {A,B,C} dedupes overlap (A counted once even if it has 2 tags).

---

### Unit 5: best-deck vs best-call

**File**: `src/legacy_engine/advisory/whattoplay.py`

```python
@dataclass
class BestDeckCall:
    archetype: str
    label: str                 # "BEST_DECK" | "BEST_CALL" | "neither"
    spread_variance: float     # variance of matchup winrates across the field (known cells)
    field_weighted_mean: float # Σ field_share·winrate over known cells
    unweighted_mean: float


def best_deck_vs_best_call(
    matrix: MatchupMatrix, field: FieldDistribution, archetype: str, *,
    spread_hi: float = 0.02, mean_hi: float = 0.52,
) -> BestDeckCall:
    """Classify via matchup-spread variance: low spread+high mean → BEST_DECK; high spread+high field-mean → BEST_CALL."""
```

**Implementation Notes**:
- Use `p_shrunk` of known (n>0, non-mirror) cells in the archetype's row; weight the field-mean by `field.shares`.
- Thresholds configurable; `neither` when neither condition holds. Document the spread metric (variance of winrates).

**Acceptance Criteria**:
- [ ] A flat-0.55-everywhere row → low variance, high mean → `BEST_DECK`.
- [ ] A row that crushes the big-share archetypes but loses to small-share ones → high variance + high field-mean → `BEST_CALL`.

---

### Unit 6: Plan-clash WHY strings

**File**: `src/legacy_engine/advisory/whattoplay.py`

```python
def plan_clash(
    deck_profile: ProactivityProfile, opp_profile: ProactivityProfile, cell, *,
    hate_present: bool = False,
) -> tuple[str, bool]:
    """Return (why_string, heuristic_data_disagreement). Rule table layered over the empirical cell.

    Rules (advisory-methods §4): proactive vs reactive (low hate)→proactive; proactive vs reactive (high
    counters/protection)→reactive; proactive vs proactive→faster clock; reactive vs reactive→more card adv.
    Disagreement flag set when the heuristic favorite contradicts the cell's p_shrunk.
    """
```

**Acceptance Criteria**:
- [ ] Proactive (0.8) vs reactive (0.2) with no hate → WHY favors the proactive deck.
- [ ] When the heuristic favors A but `cell.p_shrunk < 0.5` for A, the disagreement flag is `True`.

---

### Unit 7: Module exports

**File**: `src/legacy_engine/advisory/__init__.py` — export `proactivity_score`, `ProactivityProfile`,
`vulnerability_tags`, `vulnerability_tags_for_deck`, `field_vulnerability_tags`, `hate_equity`,
`covered_share`, `best_deck_vs_best_call`, `BestDeckCall`, `plan_clash` (+ `__all__`).

## Implementation Order

1. **Unit 1** (`_card_roles`) — the shared substrate; trickiest (regex calibration).
2. **Unit 2** (proactivity) — consumes roles + curve.
3. **Unit 3** (vulnerability tags) — consumes roles + composition aggregate.
4. **Unit 4** (hate-equity) — consumes vulnerability tags + field.
5. **Unit 5** (best-deck/best-call) — independent matchup-variance.
6. **Unit 6** (plan-clash) — consumes proactivity profiles.
7. **Unit 7** (exports).

## Testing

### Unit tests: `tests/test_whattoplay.py`
House style (`:memory:` corpus; `store.load_cards` for oracle text; `UPDATE decks SET archetype`; `TestX`
classes). Build `Card`s directly for `_card_roles` unit tests; corpus-backed for vulnerability/composition.

- `TestCardRoles` — per-card role assertions (FoW counter, Brainstorm card_advantage, Dark Ritual ritual, Swords removal, Chalice stax, tutor, storm, graveyard recursion).
- `TestProactivity` — combo>tempo>control ordering; both-zero→0.5; unknown card skipped; computed-vs-tag finding.
- `TestVulnerabilityTags` — Reanimator→graveyard-reliant, D&T→creature-based not combo, Storm→storm-reliant+combo.
- `TestHateEquity` — share-sum per tag; `covered_share` dedupes multi-tag overlap.
- `TestBestDeckCall` — flat row→BEST_DECK; spiky field-preying row→BEST_CALL.
- `TestPlanClash` — rule-table directions; heuristic-vs-data disagreement flag.

### Integration points
- Seam with `card_tags`/`store`: `_card_roles` reuses `is_free_spell`/`staple_role`; `_load_deck_cards`/
  `_archetype_composition` read `cards`/`deck_cards` exactly as `store` writes them.
- Seam with `field-model`: `hate_equity`/`field_vulnerability_tags` consume a `FieldDistribution`.
- Seam with `matchup-matrix`: `best_deck_vs_best_call` reads the archetype's `MatchupCell` row.

## Risks

- **Oracle-text role regexes are heuristic** — false positives/negatives on unusual templating. **Mitigation**:
  curated, tested regexes; roles feed *transparent* scores (auditable), not a black box; computed-vs-tag
  disagreement is surfaced, not hidden. **Fallback**: thresholds/regexes are module constants, easily tuned.
- **Sparse archetype composition**: an archetype with few corpus decks gives a thin aggregate → unstable tags.
  **Mitigation**: tags are coarse (presence thresholds), and the field's thin archetypes are already low-share;
  note when an archetype's composition sample is small.
- **Calibration drift**: exact proactivity magnitudes are uncalibrated. **Mitigation**: tests assert *relative
  ordering* (combo>tempo>control), never exact values; the score is presented with its component masses for audit.
