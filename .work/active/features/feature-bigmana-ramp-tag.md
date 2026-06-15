---
id: feature-bigmana-ramp-tag
kind: feature
stage: done
tags: [advisory, archetype]
parent: epic-bigmana-coverage-sideboard-fidelity
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# `ramp`/`big-mana` vulnerability tag + hoser mappings

## Brief
Colorless big-mana / ramp decks (Urzatron, Cloudpost/Post, Eldrazi) are completely outside the hate
model — there's no `ramp`/`big-mana` composition vulnerability tag, so Tron (current regime #1 at ~9%)
falls between `greedy-manabase` and uncovered, and its dedicated answers (Harbinger of the Seas, Null
Rod, Pithing Needle, Damping Sphere) map to nothing. Add a `ramp`/`big-mana` composition tag (signatures:
Urzatron lands / Cloudpost / Eldrazi temples, high colorless utility-land density, low colored-pip
requirement) in `advisory/whattoplay.py` vulnerability tagging, plus corresponding hoser→tag mappings so
the recommender answers big mana. Gated-additive: existing tags/coverage unchanged.

## Design

### Detection signature

Tag name: `"ramp"`.

Detection in `_vulnerability_from_composition` (same module as all other tags):

```
bigmana_land_count = Σ count for card.name in _BIGMANA_LAND_NAMES
if bigmana_land_count >= _RAMP_BIGMANA_LAND_MIN (4):
    tags.add("ramp")
```

`_BIGMANA_LAND_NAMES` (frozenset of 8 names):
- **Urzatron**: Urza's Tower, Urza's Mine, Urza's Power Plant
- **Cloudpost / Loam-Post**: Cloudpost, Glimmerpost, Vesuva (copies Cloudpost / Urza pieces)
- **Eldrazi accelerants**: Eldrazi Temple, Eye of Ugin

Detection by **card name**, not oracle text — these lands have no common textual pattern.
Threshold is 4 (≥ a playset of any single Urza land, or 4 Cloudpost/Eldrazi Temple pieces).
A real Tron shell has 12 Urzatron pieces (4 of each); Cloudpost/Eldrazi run 4+.

Kept deliberately tight: Ancient Tomb and Cavern of Souls are excluded — Ancient Tomb already seeds
`greedy-manabase` via `fast_mana_cards`; Cavern of Souls is widespread in non-ramp decks (Elves, D&T).

### Integration with vulnerability tagging + hate-equity

The `ramp` tag integrates identically to the 7 existing tags:
- `_vulnerability_from_composition` computes it alongside all other tags; gated-additive (new counter
  `bigmana_land_count` only, no existing counter modified).
- `vulnerability_tags` / `vulnerability_tags_for_deck` / `field_vulnerability_tags` surface it
  unchanged — they call `_vulnerability_from_composition`.
- `hate_equity` sums field shares for archetypes carrying `"ramp"` exactly as for other tags.
- `covered_share` works unchanged — the tag flows through as any string.
- `_build_coverage_model` in `sideboard.py` consumes it automatically: `best_swing_for_tag["ramp"]`
  is seeded by Harbinger / Damping Sphere entries; (archetype, "ramp") element keys are built for any
  archetype that carries the tag.

### Hoser → tag mappings (HOSER_CATALOG additions)

| Card | attacks | colors | max_copies | swing |
|------|---------|--------|------------|-------|
| Harbinger of the Seas | `{"ramp"}` | `{U}` | 4 | `_SWING_DEDICATED` |
| Damping Sphere | `{"ramp", "storm-reliant"}` | `{}` | 4 | `_SWING_DEDICATED` |
| Pithing Needle | `{"ramp"}` | `{}` | 2 | `_SWING_SOFT` |
| Null Rod | `{"ramp", "greedy-manabase"}` | `{G}` | 4 | `_SWING_SOFT` |

Harbinger + Damping Sphere are dedicated (directly disable Tron/Cloudpost mana production).
Pithing Needle is soft (names Eye of Ugin / Eldrazi Temple; flexible answer).
Null Rod is soft (artifact mana shutdown; also covers greedy-manabase artifact fast-mana).
Damping Sphere attacks both `ramp` and `storm-reliant` — correctly dual-purpose.

## Implementation notes

Files changed:
- `src/legacy_engine/advisory/whattoplay.py`:
  - Added `_RAMP_BIGMANA_LAND_MIN = 4` (threshold constant)
  - Added `_BIGMANA_LAND_NAMES` frozenset (8 diagnostic land names)
  - Added `bigmana_land_count` counter in `_vulnerability_from_composition`
  - Added `ramp` tag emission rule (gated-additive, 3 lines)
  - Updated `VulnerabilityTag` type alias comment to include `ramp`
- `src/legacy_engine/advisory/sideboard.py`:
  - Added 4 `HoserCard` entries to `HOSER_CATALOG`: Harbinger of the Seas, Damping Sphere,
    Pithing Needle, Null Rod

Tests added (15 new, all green):
- `tests/test_whattoplay.py` — `TestRampBigManaTag` class (8 tests):
  Tron archetype → tag fires; direct deck → tag fires; below-threshold → no tag;
  Dimir Tempo → no tag; gated-additive (other tags unaffected); hate-equity; covered-share
- `tests/test_sideboard.py` — in `TestHoserCatalog` class (7 tests):
  each hoser present + correct attacks; Damping Sphere colorless; Pithing Needle colorless;
  swing in range; max_copies ≥ 1

Suite: 2039 passed (was 2024, +15). Ruff clean on source files.
