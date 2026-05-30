---
id: epic-foundations-card-data-card-derivations
kind: feature
stage: done
tags: [ingestion]
parent: epic-foundations-card-data
depends_on: [epic-foundations-card-data-card-model-scryfall]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Card Derivations: Deck-Color Helper & Legacy Tags

## Brief

The Legacy-semantic enrichment layered onto resolved cards. Two capabilities: (1) the **deck-color
helper** `compute_deck_colors(decklist) → colors` implementing MTGOArchetypeParser's `GetColors` —
a color is in the deck iff it appears in BOTH a land (`produced_mana`, minus C) AND a nonland
(`colors`); NOT `color_identity`. This is the helper the archetype classifier's color-prefix step
consumes. (2) **Legacy card tags** derived from Scryfall fields: `is_free_spell` (oracle-text
alt-cost patterns), mana-base tags (`is_original_dual`, `is_fetchland`, `is_fast_mana_land`,
`is_denial_land`, etc. from type_line / produced_mana / oracle_text), and `staple_role` from a
curated name→role table seeded by the foundations brief's staples table.

These are pure functions / derived fields over the `Card` model — the analytically valuable
Legacy-specific signals. Does NOT include archetype classification itself (that's the archetype epic);
this only provides the color + tag inputs it will need.

## Epic context
- Parent epic: `epic-foundations-card-data`
- Position in epic: consumer of `card-model-scryfall`; parallelizable with `duckdb-store`. The `compute_deck_colors` helper is a hard dependency of the later archetype classifier.

## Inherited design decisions
- **Card model = typed Pydantic** — tags are derived fields/methods on Card; the color helper operates over a list of Cards.
- Color = lands.produced_mana ∩ nonlands.colors (NOT color_identity) — the single most important derivation correctness point.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md` — GetColors intersection method, the field mapping, is_free_spell / mana-base / staple_role derivation recipes.
- `docs/briefs/legacy-foundations.md` — the staples table (seed for staple_role), is_free_spell definition, mana-base classification tags.

## Foundation references
- `docs/ARCHITECTURE.md` — `archetype/colors.py` (the color helper lives at the card layer per the contract brief), the Legacy card tags on the Card model.

## Architectural choice (autopilot, judgment)
Place the derivations at the **card layer** (top-level modules, not under `archetype/` — that module is
a later epic): `src/legacy_engine/colors.py` (deck-color helper + guild naming) and
`src/legacy_engine/card_tags.py` (per-card Legacy tags). Pure functions over `Card`/`list[Card]` — no
state, deterministic, easy to test. The archetype classifier will import `compute_deck_colors` from here.

## Implementation Units

### Unit 1: `src/legacy_engine/colors.py`
`compute_deck_colors(cards) -> str` implements MTGOArchetypeParser's GetColors: a color is in the deck
iff it appears in some **land's** `produced_mana` AND some **nonland's** `colors`; returns the canonical
WUBRG-ordered string (e.g. `"UB"`). `guild_name(colors) -> str` maps a color string to its
guild/shard/wedge label (e.g. `"UB" → "Dimir"`, `"UBR" → "Grixis"`); mono → color name; `""` → "Colorless".
**Acceptance**: a UB tempo list (Underground Sea + Murktide) → `"UB"`; lands-only or nonlands-only color contributes nothing (intersection); `guild_name("UB")=="Dimir"`.

### Unit 2: `src/legacy_engine/card_tags.py`
- `is_free_spell(card) -> bool` — oracle-text alt-cost patterns ("without paying its mana cost", "rather than pay", "you may exile ... rather than pay", "you may cast ... without paying").
- `mana_base_tags(card) -> set[str]` — for lands: `"fetchland"` ("Search your library for a ... land"), `"dual"` (untapped, produces ≥2 of WUBRG), `"fast_mana_land"` ("Add {C}{C}" / adds two mana), `"denial"` (Wasteland/Rishadan-style: destroys/taps lands). Heuristic over `type_line`/`oracle_text`/`produced_mana`.
- `staple_role(name) -> str | None` — curated name→role table seeded by `legacy-foundations.md`'s staples (Force of Will→free_interaction, Brainstorm→cantrip, Wasteland→land_denial, Ancient Tomb→fast_mana, Underground Sea→dual_land, ...).
**Acceptance**: Force of Will → `is_free_spell` true; Polluted Delta → `{"fetchland"}`; Underground Sea → `{"dual"}`; Brainstorm → `staple_role=="cantrip"`; unknown card → `staple_role None`.

## Testing
- `tests/test_colors.py` — intersection logic, ordering, guild names (TestComputeDeckColors, TestGuildName).
- `tests/test_card_tags.py` — is_free_spell positive/negative; mana_base_tags per land kind; staple_role hits + miss. Build `Card`s via inline construction (small) or the factory idiom.

## Implementation notes
- **Files created**: `src/legacy_engine/colors.py` (`compute_deck_colors`, `guild_name`, WUBRG + full guild/shard/wedge table), `src/legacy_engine/card_tags.py` (`is_free_spell`, `mana_base_tags`, `staple_role` + curated table). Pure functions over `Card`.
- **Tests added**: `tests/test_colors.py`, `tests/test_card_tags.py` — full suite **65 passing in 0.08s**.
- **Discrepancies from design**: none material.
- **Adjacent issues parked**: none.

## Review (2026-05-29)
**Verdict**: Approve. **Blockers/Important**: none.
**Nits**: `mana_base_tags`/`is_free_spell` are heuristic (oracle-text regex) — adequate for tagging; the curated `staple_role` table is the authoritative source for known staples and can be extended as the meta shifts. The fetchland heuristic leans on "land" appearing in fetched type words (e.g. "Island" contains "land") — works, but a future hardening could match basic-land-type names explicitly.
**Notes**: `compute_deck_colors` correctly implements the land∩nonland intersection (NOT color_identity) — the load-bearing input for the archetype classifier's color prefix. 65 tests green. Patterns followed (card-layer pure functions).
