---
id: feature-hoser-catalog-expansion
kind: feature
stage: done
tags: [advisory, generation]
parent: epic-bigmana-coverage-sideboard-fidelity
depends_on: [feature-bigmana-ramp-tag]
release_binding: v0.1.0
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Expand HOSER_CATALOG + move to an editable data file

## Brief
`HOSER_CATALOG` (~25 hand-curated cards in `advisory/sideboard.py`) is blind to most real sideboard tech
(Null Rod, Pithing Needle, Consign to Memory, Engineered Explosives, Sheoldred's Edict, Toxic Deluge,
Dauthi Voidwalker, Harbinger of the Seas, Damping Sphere). PARTIALLY SUPERSEDED: `fix-sideboard-surface-
field-staples` already made the empirical pool ADDITIVE (promotes high-adoption staples into the candidate
universe from `card_frequencies(board=side)`). Remaining work: (a) move the curated catalog to an editable
data file (`data/` JSON, like the variants registry) so coverage/attack mappings are maintainable; (b)
add the named staples with proper hoser→tag attribution (esp. the big-mana answers for feature-bigmana-
ramp-tag); (c) reconcile the curated catalog with the empirical-promotion path so they compose. Data-driven
where possible (`report cards --board side`).

## Design

**Data file format**: `src/legacy_engine/data/hosers/legacy.json` — version-stamped JSON with a `hosers`
array. Each entry: `name` (str), `attacks` (non-empty list of tag strings), `colors` (WUBRG list; empty =
colorless), `max_copies` (int ≥ 1), `swing` ("dedicated" → 0.20 / "soft" → 0.10 / raw float), optional
`castable_any_color` (bool). Mirrors the variants registry (`data/variants/legacy.json`) pattern.

**Loader**: `load_hoser_catalog(path)` in `advisory/sideboard.py`. Validates all fields; rejects duplicates
and bad swing aliases at load time. `HOSER_CATALOG` is populated by `_load_default_hoser_catalog()` called
at module import. Config constant `HOSERS_REGISTRY_PATH` added to `config.py` (mirrors `VARIANTS_REGISTRY_PATH`).

**New staples added** (32 total entries, up from 27):
- Dauthi Voidwalker (B, graveyard-reliant, dedicated)
- Consign to Memory (U, combo + storm-reliant, dedicated)
- Engineered Explosives (colorless, combo + greedy-manabase + creature-based, soft)
- Sheoldred's Edict (B, creature-based, dedicated)
- Toxic Deluge (B, creature-based, dedicated)

Pre-existing ramp hosers (Harbinger, Damping Sphere, Pithing Needle, Null Rod) from feature-bigmana-ramp-tag
are present in the JSON with correct tags — no duplication.

**Catalog + empirical composition**: `_build_promoted_candidates` gates promotion via
`pool_not_in_catalog = empirical_pool - frozenset(catalog.keys())`. Moving catalog to JSON preserves
identical in-memory keys, so Consign to Memory (now a catalog card) is excluded from promotion; Force of
Negation (absent from catalog) continues to be promoted. The compose invariant is structural — no runtime
logic change required.

## Implementation notes

- `src/legacy_engine/data/hosers/legacy.json` — 32-entry JSON catalog (new file).
- `src/legacy_engine/config.py` — added `HOSERS_DIR` and `HOSERS_REGISTRY_PATH` constants.
- `src/legacy_engine/advisory/sideboard.py` — added `json`/`Path` imports; added `_SWING_ALIAS`,
  `_VALID_COLORS`, `load_hoser_catalog()`, `_load_default_hoser_catalog()`; replaced the inline
  `HOSER_CATALOG` dict literal with a module-level call to `_load_default_hoser_catalog()`.
- `tests/test_sideboard.py` — updated 3 existing tests whose Consign-to-Memory assertions were
  written against the old (not-in-catalog) state; added `TestHoserCatalogExpansion` (20 new tests).
- Suite: 2136 passing (2116 pre-existing + 20 new); ruff clean.
