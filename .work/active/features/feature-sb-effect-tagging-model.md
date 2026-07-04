---
id: feature-sb-effect-tagging-model
kind: feature
stage: done
tags: [advisory]
parent: epic-sideboard-scoring-model
depends_on: []
release_binding: v0.2.0
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Effect-tagging + hoser catalog: linchpin, symmetry, color-contingent, castability

## Brief

Foundation feature (A) of `epic-sideboard-scoring-model`. The scorer (Feature B) is only as
good as the card→effect model it reads, and that model — `data/hosers/legacy.json` + the
vulnerability-tag system — is coarse and has known errors. This feature fixes and deepens it.
It folds two backlog ideas (`idea-sb-color-contingent-hate`, `idea-granular-effect-tagging`)
and adds the two new factors the epic's impact decomposition needs: **centrality (linchpin)**
and **castability**.

Scope:
- **Quick data fixes** (low-risk, independently useful): correct Hydroblast's tag (it targets
  *red*, not manabases); add Blue Elemental Blast + Red Elemental Blast to the catalog with
  correct attribution; dedupe functionally-identical hosers so they aren't counted as distinct
  coverage.
- **Color-contingent hate** — a model concept for "anti-red / anti-blue" rather than shoehorning
  color blasts into archetype tags.
- **Symmetry flag** — asymmetric (opponent-only) vs symmetric (affects me too), so the scorer can
  catch self-hosing (Grafdigger's Cage vs the deck's own graveyard).
- **Finer graveyard tags** — replace monolithic "graveyard hate" with tags that capture how a card
  interacts with the graveyard (synergy/anti-synergy).
- **Archetype linchpin model** — per-archetype critical points of failure, so impact can score
  "hits a linchpin" (Painter's Grindstone) vs "hits a redundant piece" (a Mox).
- **Castability attributes** — the conditions/cost to actually cast a hoser in a given matchup
  (color requirements, conditional free-cast like Massacre needing an opponent's Plains).

<!-- Design input below preserved from the folded backlog ideas. -->

## Design input — granular effect tagging (from idea-granular-effect-tagging)

Improve decision-making by making card effect tagging more granular — finer tags give the engine
nuance (especially graveyard interactions) and better advice.

1. **More granular graveyard tagging.** Current tags are too coarse to capture how a card
   interacts with the graveyard and other cards. Finer tags let the engine reason about graveyard
   synergies/anti-synergies instead of treating "graveyard hate" as a monolith.
2. **Symmetry flag for game-wide effects.** Asymmetric (opponent-only) vs symmetric (everyone,
   including the controller) — lets the engine catch self-hosing recommendations.

Motivating example (Flow State / Dimir Tempo dive, 2026-06-22): Grafdigger's Cage was treated as
fine SB for Dimir Tempo, but post-Flow-State the deck leans on its *own* graveyard (Nethergoyf +
Flow State's "instant AND sorcery in graveyard → draw 2"). Cage is symmetric graveyard hate, so it
hoses the deck's own plan. Real data backs it: as Flow State hit ~100%, Cage dropped ~47%→~20% SB
inclusion, shifting to Nihil Spellbomb. Today's tagging lacked the nuance to flag Cage as
self-hosing.

## Design input — color-contingent hate (from idea-sb-color-contingent-hate)

Represent color-contingent hate and de-duplicate functionally-identical hosers. Found in a
test-drive: the engine recommended 3 Hydroblast + 1 Blue Elemental Blast as distinct coverage — but
oracle text confirms both target RED (the anti-*blue* blasts are Red Elemental Blast / Pyroblast,
uncastable in U/B). Root cause is data + modeling:
- `data/hosers/legacy.json`: Hydroblast mis-tagged `attacks: ['greedy-manabase','low-interaction']`
  (it counters/destroys red). Blue/Red Elemental Blast aren't in the catalog at all — BEB only
  appeared via empirical promotion with the generic `'combo'` fallback tag.
- The vulnerability-tag system has no concept of color-contingent hate ("anti-red", "anti-blue"),
  so color blasts get shoehorned into archetype tags and stacked as if distinct.

Fix: (a) add BEB + REB with correct attribution and fix Hydroblast's tag (~one-line catalog edit,
low-risk); (b) give the model a notion of color-contingent hate and/or de-duplicate
functionally-identical hosers.

---

## Design decisions

- **Linchpin model representation**: **Hybrid — derive + curated overrides.** Auto-detect
  candidate linchpins from composition (near-mandatory inclusion × engine/combo role), plus a
  curated override file for expert corrections. Balances the data-driven ethos with archetype-
  specific expert knowledge; explainable both ways.
- **Feature A boundary**: **Ship data/model + wire the quick catalog fixes into the current
  `advise sideboard`.** New model fields (symmetry, linchpin, cast conditions) land but sit
  unused until Feature B consumes them; the catalog fixes (Hydroblast/Pyroblast re-tag, add
  Blue/Red Elemental Blast, dedupe) improve the existing tool immediately.
- **Compatibility strategy**: **Replace + re-tag the tag vocabulary.** Replace the monolithic
  `graveyard-reliant` with finer tags and re-tag all affected hosers + the archetype derivation +
  tests. (New *fields* — symmetry, cast condition, functional_group — are additive by nature;
  "replace" applies to the shared tag vocabulary, not to net-new capability fields.)

## Architectural choice

Considered three shapes for the richer effect model: **(1)** a new standalone `card_effects`
registry that owns all tagging and that sideboard/whattoplay consume; **(2)** a learned/derived
classifier that emits everything from oracle text; **(3)** extend the existing surfaces in place —
`HoserCard` + the `whattoplay.py` composition-derived vulnerability vocabulary — and add exactly
one new curated resource (the linchpin catalog) following the established
`curated-json-resource-loader` pattern.

**Chosen: (3), extend-in-place + one new curated resource.** The codebase already has the two
halves this feature needs — `whattoplay._vulnerability_from_composition` derives archetype tags
from composition via transparent regex/thresholds, and `HoserCard`/`load_hoser_catalog` is a
curated-JSON SSOT. Both are exactly the seams the notes call out. A new parallel registry (1) would
duplicate the SSOT and split the vocabulary; a pure-derived model (3-variant of 2) can't capture
"why Grindstone specifically is the linchpin" (the reason the user chose hybrid). Extending in place
keeps one vocabulary shared between hoser `attacks` and archetype vulnerability tags (the existing
match mechanism: `hoser.attacks ∩ archetype.vulnerability_tags`), and the linchpin catalog mirrors
the variant-registry / hoser-catalog loader pattern already in the project.

## Implementation Units

### Unit 1: Replace graveyard vocabulary + add color-contingent tags (archetype side)

**File**: `src/legacy_engine/advisory/whattoplay.py`
**Story**: `feature-sb-effect-tagging-model-vocab-catalog`

Replace the monolithic `graveyard-reliant` `VulnerabilityTag` with two finer tags and add
color-contingent tags derived from composition:

```python
# VulnerabilityTag vocabulary (docstring update):
#   graveyard-recursion  # deck recurs/casts cards from its graveyard (reanimate, escape, flashback, regrowth)
#   graveyard-fuel       # deck uses graveyard as a QUANTITY resource (delve, delirium, threshold, *goyf size)
#   plays-red | plays-blue | plays-white | plays-black | plays-green  # color-contingent: deck runs blast-worthy density of that color's spells
#   (existing: combo, low-curve, greedy-manabase, creature-based, low-interaction, storm-reliant, ramp)

_GY_RECURSION_DENSITY = 0.08   # (existing) graveyard_recursion slots / maindeck  -> graveyard-recursion
_GY_FUEL_DENSITY       = 0.10  # NEW: delve/delirium/threshold/goyf-size slots / maindeck -> graveyard-fuel
_COLOR_SPELL_MIN       = 6     # NEW: nonland spells of a color >= threshold -> plays-<color>

def _color_contingent_tags(cards_with_counts: list[tuple[Card, int]]) -> set[str]:
    """Emit plays-<color> for each color the deck runs at >= _COLOR_SPELL_MIN nonland spell copies.
    Color from card.colors (WUBRG); lands excluded. Drives color-blast coverage (Hydroblast=plays-red)."""

# _vulnerability_from_composition(...) : split the graveyard branch into recursion vs fuel by role
# density, and union in _color_contingent_tags(...).
```

**Implementation Notes**:
- `graveyard-recursion` from the existing graveyard-recursion role density; `graveyard-fuel` from a
  new role set (delve/delirium/threshold/`*goyf`) — reuse `_card_roles` role detection, add a
  `graveyard_fuel` role if not present.
- Color tags are the substrate for symmetry too: a deck emitting `graveyard-fuel` is what lets
  Feature B flag symmetric graveyard hate as self-hosing.

**Acceptance Criteria**:
- [ ] `graveyard-reliant` no longer appears anywhere in the tag vocabulary (grep-clean).
- [ ] A Reanimator-shaped deck emits `graveyard-recursion`; a delve/goyf deck emits `graveyard-fuel`.
- [ ] A deck with ≥6 red nonland spell copies emits `plays-red`; a mono-blue deck does not emit `plays-red`.

### Unit 2: HoserCard model extension (symmetry, cast condition, functional group)

**File**: `src/legacy_engine/advisory/sideboard.py`
**Story**: `feature-sb-effect-tagging-model-vocab-catalog`

```python
@dataclass(frozen=True)
class HoserCard:
    name: str
    attacks: frozenset[str]
    colors: frozenset[str]
    max_copies: int
    swing: float
    castable_any_color: bool = False
    symmetry: str = "asymmetric"          # NEW: "asymmetric" | "symmetric"
    cast_requires: str | None = None       # NEW: structured cast condition token, e.g. "opp_controls_plains"
    functional_group: str | None = None    # NEW: identical-effect group key, e.g. "red-blast" (Hydroblast≡BEB)

# load_hoser_catalog(path): validate symmetry in {"asymmetric","symmetric"} (default "asymmetric");
# cast_requires in a known token set or None; functional_group any str or None. Fail-fast ValueError
# citing the offending name/field (Fail Fast principle).
```

**Implementation Notes**:
- Keep `castable_any_color` as-is (additive fields only here). `cast_requires` is consumed by
  Feature B's castability factor; validated-but-inert in this feature.
- Known `cast_requires` tokens (initial): `None`, `"opp_controls_plains"` (Massacre free-cast).

**Acceptance Criteria**:
- [ ] Loading a catalog entry with `symmetry: "bogus"` raises `ValueError` naming the card + field.
- [ ] Entries omitting the new fields load with defaults (`asymmetric`, `None`, `None`).

### Unit 3: Catalog rewrite — re-tag, fix blasts, add BEB/REB, symmetry, dedupe (trickiest data)

**File**: `src/legacy_engine/data/hosers/legacy.json`
**Story**: `feature-sb-effect-tagging-model-vocab-catalog`

- Re-tag the 8 `graveyard-reliant` entries to `graveyard-recursion` and/or `graveyard-fuel`
  (Surgical/Leyline/Cage/Endurance/Containment Priest/Dauthi/Faerie Macabre → recursion; Nihil
  Spellbomb → recursion). Mark `Grafdigger's Cage` **`symmetry: "symmetric"`** (stops all players
  casting from gy → self-hoses a graveyard-recursion deck).
- **Fix the blasts**: `Hydroblast` `attacks: ["plays-red"]`; `Pyroblast` `attacks: ["plays-blue"]`
  (currently mis-tagged `combo/low-interaction`).
- **Add** `Blue Elemental Blast` (`attacks: ["plays-red"]`, `functional_group: "red-blast"`, colors
  `["U"]`) and `Red Elemental Blast` (`attacks: ["plays-blue"]`, `functional_group: "blue-blast"`,
  colors `["R"]`); tag `Hydroblast` `functional_group: "red-blast"`, `Pyroblast` `"blue-blast"`.
- Add `symmetry` to all 32 entries (default asymmetric; mark the genuinely symmetric ones).

**Acceptance Criteria**:
- [ ] `load_hoser_catalog(HOSERS_REGISTRY_PATH)` loads clean; every entry has a `symmetry` value.
- [ ] Hydroblast/BEB attack `plays-red`; Pyroblast/REB attack `plays-blue`; no blast attacks a
      manabase/combo tag.
- [ ] Hydroblast and Blue Elemental Blast share `functional_group == "red-blast"`.

### Unit 4: Linchpin hybrid model (derive + curated overrides) — trickiest logic

**File**: `src/legacy_engine/advisory/linchpins.py` (new), `src/legacy_engine/data/linchpins/legacy.json` (new), `src/legacy_engine/config.py`
**Story**: `feature-sb-effect-tagging-model-linchpin`

```python
@dataclass(frozen=True)
class Linchpin:
    archetype: str
    name: str                      # card name or mechanic label
    role: str                      # "combo-engine" | "combo-tutor" | "key-payoff" | ...
    centrality: float              # (0, 1]  — how much removing it breaks the plan
    neutralized_by: frozenset[str] # effect tags that hit it (uses Unit 1/2 vocabulary)

_LINCHPIN_INCLUSION = 0.90         # near-mandatory inclusion to auto-qualify
_DERIVED_CENTRALITY = 0.6          # default weight for a derived (non-curated) linchpin

def load_linchpin_overrides(path: "Path | str") -> "dict[str, list[Linchpin]]":
    """Curated-JSON SSOT loader (mirrors load_hoser_catalog). Fail-fast on bad centrality/schema."""

def derive_linchpins(archetype: str, cards_with_counts, inclusion_pct: "dict[str, float]") -> list[Linchpin]:
    """Auto-detect: card with inclusion >= _LINCHPIN_INCLUSION AND _card_roles ∩ {combo-engine,
    combo-tutor,key-payoff} -> Linchpin(centrality=_DERIVED_CENTRALITY). neutralized_by inferred
    from the card's own effect tags (artifact -> {artifact-ability-lock, artifact-bounce}, etc.)."""

def linchpins_for_archetype(archetype, cards_with_counts, inclusion_pct) -> list[Linchpin]:
    """Merge: curated overrides (by name) win over derived; unmatched derived kept."""
```

Curated JSON schema (`data/linchpins/legacy.json`):
```json
{"version": 1, "linchpins": {
  "Painter": [{"name": "Grindstone", "role": "combo-engine", "centrality": 1.0,
               "neutralized_by": ["artifact-ability-lock", "artifact-bounce"]}]
}}
```
`config.py`: add `LINCHPINS_DIR = PACKAGE_DATA_DIR / "linchpins"` and
`LINCHPINS_REGISTRY_PATH = LINCHPINS_DIR / "legacy.json"`.

**Implementation Notes**:
- `neutralized_by` uses the effect-tag vocabulary from Units 1/2 — this is why the linchpin story
  depends on the vocab/catalog story.
- Consumer is Feature B (centrality factor); this feature builds + tests the model and loader, and
  binds a `_load_default_linchpin_overrides()` at import (degrade to empty dict on error, per the
  curated-json-resource-loader pattern).

**Acceptance Criteria**:
- [ ] `linchpins_for_archetype("Painter", ...)` returns Grindstone with `centrality == 1.0` (curated
      override) even though derivation would default it to 0.6.
- [ ] A derived-only archetype (no curated entry) still returns its near-mandatory engine pieces at
      `centrality == _DERIVED_CENTRALITY`.
- [ ] `load_linchpin_overrides` raises `ValueError` on `centrality` outside `(0, 1]`, naming the entry.

### Unit 5: Wire quick fixes into current `advise sideboard`

**File**: `src/legacy_engine/advisory/sideboard.py`
**Story**: `feature-sb-effect-tagging-model-vocab-catalog`

- Update `_derive_attacks_for_promoted` for the new vocabulary (graveyard-reliant → recursion/fuel;
  recognize red/blue blasts via oracle text → `plays-red`/`plays-blue`).
- Add a `functional_group` de-dup in candidate generation: at most one card per `functional_group`
  contributes coverage (keep the best-swing / owned copy), so Hydroblast + BEB no longer stack as
  distinct coverage.

**Acceptance Criteria**:
- [ ] Against a red-heavy field, Hydroblast surfaces as coverage for `plays-red` (not manabase).
- [ ] A catalog containing both Hydroblast and Blue Elemental Blast yields ONE `red-blast` coverage
      contribution, not two.
- [ ] Existing `advise sideboard` output is unchanged for a field with no color/graveyard axis
      (no accidental regression outside the re-tagged axes).

## Implementation Order

1. **Story `vocab-catalog`** (Units 1→2→3→5, atomic) — the vocabulary replace + model fields +
   catalog rewrite + wiring MUST ship together (a half-migrated vocab breaks matching on main).
2. **Story `linchpin`** (Unit 4) — depends on `vocab-catalog` (uses the effect-tag vocabulary in
   `neutralized_by`); otherwise independent. Consumer is Feature B.

## Testing

### Unit tests: `tests/test_whattoplay.py`
- Finer gy tags fire per role density; `plays-<color>` fires at/above `_COLOR_SPELL_MIN`, not below.
- `graveyard-reliant` fully removed (assert not emitted for a known reanimator fixture).

### Unit tests: `tests/test_sideboard.py`
- `load_hoser_catalog` validation of `symmetry` / `cast_requires` / `functional_group` (happy + fail-fast).
- `functional_group` de-dup: two same-group blasts → one coverage contribution.
- `_derive_attacks_for_promoted` maps a blast oracle text to `plays-<color>`.

### Unit tests: `tests/test_linchpins.py` (new)
- Curated override beats derived centrality; derived-only path; fail-fast on bad centrality.

### Regression: `tests/test_recommendation_coverage.py`
- Re-baseline the coverage assertions affected by the vocab replace; confirm no unintended drift on
  non-re-tagged axes.

### Test data
- Small archetype fixtures (reanimator, delve/goyf, mono-red, Painter) via existing pytest factory
  fixtures in `tests/conftest.py`; a tmp hoser catalog + tmp linchpin JSON for loader tests.

## Risks

- **Vocab-migration coverage regression** — replacing `graveyard-reliant` risks silent match misses
  if any surface still emits/consumes the old tag. **Fallback**: the migration is one atomic story
  with a grep-clean acceptance criterion + the `test_recommendation_coverage` re-baseline as the
  guard; CI must be green on the combined change.
- **Color-contingent over/under-firing** — `_COLOR_SPELL_MIN = 6` is a first guess; a light red
  splash shouldn't read as `plays-red`. **Fallback**: threshold is a single named constant, tunable;
  acceptance tests pin the splash-vs-heavy boundary.
- **Linchpin derivation false positives** — a high-inclusion but non-load-bearing card (e.g. a
  format-staple cantrip) could be mis-derived as a linchpin. **Fallback**: hybrid design — curated
  overrides correct it, and the derived default centrality (0.6) is deliberately below curated 1.0;
  Feature B treats centrality as a multiplier, so a mild false positive is a small error, not a
  blowup.

## Implementation summary (2026-07-03)

Both child stories implemented and verified; feature advanced implementing → review.

- **`…-vocab-catalog`** (units 1,2,3,5) — done. Replaced `graveyard-reliant` → `graveyard-recursion`/`graveyard-fuel`; added `plays-<color>` color-contingent tags; extended `HoserCard` with `symmetry`/`cast_requires`/`functional_group` + fail-fast loader validation; rewrote the catalog (32→34: fixed the mis-tagged Hydroblast **and** Pyroblast, added Blue/Red Elemental Blast, oracle-grounded per-card gy re-tags, broad oracle-based symmetry classification); wired `_derive_attacks_for_promoted` + a `functional_group` de-dup into `advise sideboard`. Caught + fixed an out-of-scope break in `report.py`'s `_interaction_annotation` (referenced the old tag).
- **`…-linchpin`** (unit 4) — done. New `advisory/linchpins.py` (hybrid derive + curated overrides), curated `data/linchpins/legacy.json` (Painter/Grindstone+Servant, Show and Tell, Eldrazi/Chalice), config paths, 41 tests. `neutralized_by` capability vocabulary owned by this model; hoser→capability bridging + centrality scoring explicitly deferred to Feature B.

**Verification**: full suite green — 2349 passed (was 2308 pre-feature). Grep-clean of `graveyard-reliant` in `src/`.

**Deferred (not blockers)**: doc drift in `docs/ARCHITECTURE.md` + `docs/briefs/advisory-methods.md` (new vocabulary) flagged for the docs gate at release; hoser→capability bridging + centrality consumption belong to Feature B.
