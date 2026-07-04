---
id: feature-sb-field-weighted-scorer-impact
kind: story
stage: done
tags: [advisory]
parent: feature-sb-field-weighted-scorer
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Impact factors + hoser→linchpin capability bridge

## Brief

New `src/legacy_engine/advisory/impact.py`: the four decomposed impact factors (centrality,
symmetry, castability, draw-probability) combined multiplicatively with hard gates, plus the
`hoser_capabilities()` bridge (deferred from Feature A) mapping a hoser to the linchpin
`neutralized_by` capability vocabulary. Pure / DB-free (objective-search-split) — takes resolved
inputs (opp linchpins, my vulnerability tags, my colors, copies), returns an `ImpactBreakdown`.

## Implementation

Covers parent feature **Units B1 + B2** — see `feature-sb-field-weighted-scorer` § Implementation
Units for exact signatures, constants (`_CENTRALITY_BASELINE`, `_SYMMETRY_FLOOR`), and the locked
Design decisions (multiplicative hard gates). Consumes `advisory/linchpins.py` + the `HoserCard`
`symmetry`/`cast_requires`/`functional_group` fields + the `plays-<color>`/`graveyard-*` vocab from
Feature A. Tests: new `tests/test_impact.py`.

## Implementation notes (2026-07-03)

**Files**: new `src/legacy_engine/advisory/impact.py`; new `tests/test_impact.py`; added
`make_hoser`/`make_linchpin` factory fixtures to `tests/conftest.py` (project's established
`_make_X(**kwargs)` idiom). No changes to `sideboard.py` or `cli.py` — confirmed via `git
status` before commit; those are the B3/B4/B5 wiring stories.

**API surface**: `ImpactBreakdown` (frozen dataclass: `centrality, symmetry, castability,
draw_prob: float`, `.score()` = product), `centrality_factor`, `symmetry_factor`,
`castability_factor`, `draw_probability`, `hoser_capabilities`, `impact` (orchestrator).
`HoserCard` is imported only under `TYPE_CHECKING` (string-quoted type hints) so this module
never creates a runtime circular import once B3 makes `sideboard.py` import from here.

**`_BO3_CARDS_SEEN = 24`**: 2 "live" games (you sideboard after game 1; you always get game 2,
game 3 only if the set goes the distance — modeled as ~2 live games) × ~12 cards seen per game
(7-card opening hand + ~5 draw steps, reasoning that Legacy games commonly resolve by turn
8-10 given the format's low curves / free spells). The taper *shape* (monotonic + concave
marginal) is what matters for B4's future ILP wiring, not the exact constant — documented as
tunable in the module.

**`hoser_capabilities` mapping**: a curated `_CAPABILITY_BY_NAME` dict (name, case-insensitive
→ capability tokens), grounded by reading each of the 34 catalog cards' `oracle_text` in
`data/legacy.duckdb` (read-only, at authoring time — the function itself never opens the DB).
Mirrors the existing hard-coded-map precedent in `sideboard.is_anti_synergistic` rather than a
new JSON resource. Key rules (full rationale + per-card notes in the module):
- Literal exile-from-graveyard effects → `exile-graveyard`, EXTENDED to non-literal-exile
  effects that equally deny a graveyard-recursion linchpin's access (Endurance's
  bottom-of-library reset, Containment Priest's cast-trigger exile, Grafdigger's Cage's
  cast/enter lock) — closest available token in the fixed 8-token vocabulary.
- Stack-timed counters/exiles (incl. Chalice of the Void's static counter-on-cast-shaped
  ability) → `counter-on-cast`.
- Destroy/exile artifact|enchantment → the matching `*-removal` token(s); a sweeper hitting
  multiple permanent types also earns `board-sweep`.
- Artifact-ability-lock effects (Null Rod, Pithing Needle) → `artifact-ability-lock` only
  (doesn't remove the permanent).
- Deliberately NO capability credit for: hand disruption (Thoughtseize/Duress — no vocab
  token), protection/taxes/mana-denial-without-removal (Veil of Summer, Defense Grid, Blood
  Moon, Back to Basics, Harbinger of the Seas, Carpet of Flowers, Damping Sphere), land
  destruction (Wasteland — no land-removal token), and **edict effects** (Sheoldred's Edict —
  the opponent chooses the sacrifice, so it can't reliably be credited with answering one
  specific named linchpin). Unmapped/uncataloged cards return an empty frozenset — an honest
  "unknown" (mirrors `linchpins._infer_neutralized_by`'s own convention), which
  `centrality_factor` degrades gracefully to `_CENTRALITY_BASELINE`, not a wrong zero.

**Symmetry intersection logic**: `hoser.attacks` and the vulnerability-tag vocabulary
(`whattoplay.VulnerabilityTag`) are the SAME tag space (graveyard-recursion, graveyard-fuel,
plays-<color>, combo, low-curve, greedy-manabase, creature-based, low-interaction,
storm-reliant, ramp) — verified by reading both vocabularies side by side. "My deck shares the
hosed axis" is literally `hoser.attacks & my_vulnerability_tags` being non-empty. Implemented
as a flat two-value function (1.0 vs `_SYMMETRY_FLOOR`), not a graded interpolation — matches
the parent feature's framing ("penalize toward the floor... a self-hosing symmetric card isn't
quite 0").

**Castability / `cast_requires` judgment call**: `cast_requires == "opp_controls_plains"` is
treated the same way `castable_any_color` already is in `HoserCard`'s own docstring — an
ALTERNATIVE cast path that supersedes the ordinary color-subset check, not a constraint layered
on top of it (so an off-color deck can still "cast" a `cast_requires`-gated card once its
condition fires, mirroring how a pitch spell bypasses colors). When the condition doesn't hold
(or `opp_cards` isn't supplied), the factor hard-gates to `0.0`, not a low nonzero value — this
is the same multiplicative hard-gate philosophy the parent feature locked in, and it's the one
place I resolved genuine ambiguity in the story text ("0.0 or a low value") by judgment. Plains
detection (`_opp_controls_plains`) is a conservative literal-name check (`"Plains"` /
`"Snow-Covered Plains"`) over an opponent-cards container (frozenset/list/dict-keys) — no
Plains-fetching duals/fetchlands credited, since resolving that needs type_line data this pure
module doesn't have.

**Deviations / escape hatch**: none hit. Feature A's API (`Linchpin`, `HoserCard`,
`vulnerability_tags_for_deck`'s vocabulary) provided everything B1/B2 needed; no design gap
found.

**Bug found, parked (not fixed here — out of scope)**: `bug-null-rod-catalog-color` —
`src/legacy_engine/data/hosers/legacy.json`'s Null Rod entry has `"colors": ["G"]`, but Null
Rod is colorless (`{1}`, no color pips per its own oracle_text). Left untouched per this
story's pure-module-only scope; will incorrectly hard-gate Null Rod's castability for
non-green decks until the catalog is fixed.

**Test results**: `tests/test_impact.py` — 37 new tests, all passing. Full suite:
`.venv/bin/python -m pytest -q` → 2386 passed (2349 existing + 37 new), 0 failures.
