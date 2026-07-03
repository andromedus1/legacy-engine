---
id: feature-sb-effect-tagging-model-vocab-catalog
kind: story
stage: review
tags: [advisory]
parent: feature-sb-effect-tagging-model
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Vocabulary replace + HoserCard model + catalog rewrite + wire into current tool

## Brief

The atomic vocabulary migration + the shippable quick-fix. Replace the monolithic
`graveyard-reliant` tag with `graveyard-recursion` / `graveyard-fuel`, add color-contingent
`plays-<color>` tags, extend `HoserCard` with `symmetry` / `cast_requires` / `functional_group`,
rewrite the hoser catalog (re-tag graveyard cards, fix the mis-tagged Hydroblast/Pyroblast blasts,
add Blue/Red Elemental Blast, add symmetry, mark functional groups), and wire the fixes + a
`functional_group` de-dup into the current `advise sideboard` matcher. These MUST ship together —
a half-migrated vocabulary breaks matching on main.

## Implementation

Covers parent feature units **1, 2, 3, 5** — see
`feature-sb-effect-tagging-model` § Implementation Units for exact signatures, files, and
acceptance criteria. Files: `advisory/whattoplay.py`, `advisory/sideboard.py`,
`data/hosers/legacy.json`; tests in `tests/test_whattoplay.py`, `tests/test_sideboard.py`,
`tests/test_recommendation_coverage.py`.

## Implementation notes (2026-07-03)

Delivered as one atomic change; full suite green throughout (`python -m pytest -q` —
2308 passed; note: run with `python -m pytest`, not the `pytest` binary directly, or three
pre-existing/unrelated `test_viz_*` collection errors appear — confirmed present on `main`
before this story, a `tests` package import-path quirk, out of scope here).

**Unit 1 — `advisory/whattoplay.py` (archetype vulnerability vocab)**
- Split `graveyard-reliant` into `graveyard-recursion` (existing `graveyard_recursion`
  role/density, unchanged threshold `_GY_RECURSION_DENSITY=0.08`) and `graveyard-fuel` (new
  `graveyard_fuel` role: delve/delirium/threshold oracle-text regexes + `*goyf` name-suffix
  match; new `_GY_FUEL_DENSITY=0.10`).
- Added `_color_contingent_tags(cards_with_counts)` and `_COLOR_SPELL_MIN=6`; unioned into
  `_vulnerability_from_composition`'s output from the same walked composition (added a
  `cards_with_counts` accumulator inside the existing loop — no second DB pass).
- `combo`'s "broken signal" gate now reads `gy_recursion_slots` (previously the monolithic
  `gy_slots`) — recursion, not fuel, is the "engine" signal for reanimator-style combo;
  fuel decks (delve/goyf fair strategies) are not combo by this heuristic and shouldn't be.
- `VulnerabilityTag` docstring rewritten with the full new vocabulary.

**Unit 2 — `advisory/sideboard.py` (`HoserCard` + `load_hoser_catalog`)**
- Added `symmetry: str = "asymmetric"`, `cast_requires: str | None = None`,
  `functional_group: str | None = None` to the frozen dataclass.
- Loader validates `symmetry ∈ {"asymmetric","symmetric"}`, `cast_requires ∈ {None,
  "opp_controls_plains"}`, `functional_group` is `str | None` — each raises `ValueError`
  naming the card and the offending field, matching the existing Fail-Fast error style.
- Massacre note: Massacre is empirically promoted (not a curated catalog entry), so no
  shipped JSON entry uses `cast_requires: "opp_controls_plains"` yet — the loader supports
  the token per spec; a future curated Massacre entry (or Feature B) can use it directly.

**Unit 3 — `data/hosers/legacy.json` (catalog rewrite, 32 → 34 entries)**
- Re-tagged the 8 former `graveyard-reliant` entries by **oracle-text-grounded judgment**
  (queried `cards.oracle_text` in `data/legacy.duckdb`, not memory), not a flat "all→recursion"
  mapping: cards that **fully exile a graveyard going forward or in one shot** (denying both
  recursion targets and delve/threshold fuel) got both tags — `Leyline of the Void`,
  `Endurance`, `Nihil Spellbomb`, `Dauthi Voidwalker` → `[graveyard-recursion,
  graveyard-fuel]`. Narrow/specific-target or casting-restriction effects that don't reduce
  graveyard *quantity* got recursion only — `Surgical Extraction`, `Faerie Macabre`,
  `Containment Priest`, `Grafdigger's Cage` → `[graveyard-recursion]`. This is a deliberate
  deviation from the parent feature doc's simpler "all 8 → recursion" suggestion, made
  because the doc's mapping wasn't itself oracle-text-verified; documented here per the
  "ground card interactions in oracle text" project convention.
- Fixed the two mis-tagged blasts: `Hydroblast` → `["plays-red"]` (was
  `["greedy-manabase","low-interaction"]`); `Pyroblast` → `["plays-blue"]` (was
  `["combo","low-interaction"]`).
- Added `Blue Elemental Blast` (colors `["U"]`, attacks `["plays-red"]`,
  `functional_group:"red-blast"`, max_copies 2, swing "soft") and `Red Elemental Blast`
  (colors `["R"]`, attacks `["plays-blue"]`, `functional_group:"blue-blast"`, max_copies 2,
  swing "soft"); tagged `Hydroblast`/`Pyroblast` with the matching `functional_group`.
- **`symmetry` judgment call — broader than the single Cage example in the spec.** Verified
  every entry's oracle text and applied one rule consistently: an effect with **no owner
  restriction** in its own text ("each", "all", "a player", unqualified "nonbasic lands") is
  `symmetric`; an effect that **targets** or explicitly says "opponent"/"opponent's" is
  `asymmetric` (the caster's rational choice always targets the opponent, so no self-harm
  in practice). Beyond `Grafdigger's Cage`, this rule marks `Blood Moon`, `Back to Basics`,
  `Harbinger of the Seas`, `Chalice of the Void`, `Defense Grid`, `Damping Sphere`,
  `Null Rod`, `Pithing Needle`, `Engineered Explosives`, `Toxic Deluge`, and
  `Containment Priest` as `symmetric` — each independently corroborated by the existing
  anti-synergy filter already treating several of them (Chalice, Back to Basics,
  Defense Grid) as self-harm risks. This gives Feature B (the linchpin/scorer) an
  accurate, oracle-grounded symmetry signal from day one rather than a one-card stub.

**Unit 5 — `advisory/sideboard.py` (wiring into `advise sideboard`)**
- `_derive_attacks_for_promoted`: graveyard branch now emits `graveyard-recursion`; added
  `_RE_BLAST_RED`/`_RE_BLAST_BLUE` (matches "target red/blue spell/permanent" and "if it's
  red/blue") → `plays-red`/`plays-blue`. The color-blast check runs *before* the generic
  "destroy target" → `creature-based` rule and short-circuits it for a detected blast
  (blasts phrase their permanent-kill mode as "destroy target red permanent", which would
  otherwise false-positive into `creature-based`).
- `_build_coverage_model`: added a `functional_group` de-dup pass (Step 5, just before
  constructing `CoverageModel`) — for each group with ≥2 surviving candidates, keeps only
  the highest-swing one (ties broken by name for determinism) and drops the rest from both
  `candidate_covers` and `candidate_meta`. Ownership is deliberately **not** a tiebreaker:
  the coverage model must stay collection-blind (the byte-identical no-collection contract
  tested in `test_collection_aware_engine.py`), so "owned copy" from the spec's phrasing is
  implemented as swing-only + deterministic tie-break, not ownership-aware.

**Test re-baseline**
- `tests/test_recommendation_coverage.py` needed no changes — it tests `acquire_plan`
  overpriced-printing flags and `interaction_facts` evidence content, neither of which
  touches the vulnerability-tag vocabulary. Confirmed still green.
- `tests/test_whattoplay.py` / `tests/test_sideboard.py`: renamed real-derivation and
  real-catalog assertions from `graveyard-reliant` to `graveyard-recursion` (all 8 retagged
  catalog cards keep the recursion tag, so this is a pure rename with no logic drift), added
  new coverage for `graveyard_fuel` role detection, `_color_contingent_tags` (pure-function
  + DB-integration, at/below/above `_COLOR_SPELL_MIN`), the 3 new `HoserCard` fields (happy
  + fail-fast paths), `functional_group` de-dup (unit + against the real shipped catalog),
  and blast→`plays-<color>` mapping in `_derive_attacks_for_promoted`.
- Left `graveyard-reliant` untouched (out of story scope) in `tests/test_interaction_facts.py`
  (stale prose docstrings only, no assertions on the literal string),
  `tests/test_collection_aware_engine.py`, and `tests/test_generation_tuning.py` (both use
  the string only as an arbitrary synthetic label for testing tag-agnostic generic
  mechanisms — `build_custom_field`'s share math and a hand-built `CoverageModel` — never
  as input to real vocab-producing code, so they don't need to change and remain green
  unmodified). `src/` is fully grep-clean per the acceptance criterion.
- Also fixed `src/legacy_engine/advisory/report.py`'s `_interaction_annotation` — it
  checked `"graveyard-reliant" not in hoser.attacks` against the real `HOSER_CATALOG` and
  would have silently stopped annotating every graveyard hoser once the catalog was
  retagged (a genuine "half-migrated vocab breaks matching" case the story explicitly
  warns about, even though `report.py` isn't one of the four Unit files). Now checks
  `{"graveyard-recursion","graveyard-fuel"} & hoser.attacks`.

**Docs drift (not fixed here, flagged for a follow-up doc pass)**: `docs/ARCHITECTURE.md`
and `docs/briefs/advisory-methods.md` still describe the retired `graveyard-reliant` tag.
Left alone to keep this story's diff scoped to the four spec'd files; a documentation gate
(`/agile-workflow:gate-docs` or `/update-documentation`) should pick this up before release.
