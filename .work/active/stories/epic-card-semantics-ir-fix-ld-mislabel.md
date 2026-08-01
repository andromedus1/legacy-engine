---
id: epic-card-semantics-ir-fix-ld-mislabel
kind: story
stage: review
tags: [advisory, bug]
parent: epic-card-semantics-ir
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-31
---

# Fix _derive_attacks_for_promoted land-destruction mislabel (Wasteland/Ghost Quarter)


`_derive_attacks_for_promoted` (src/legacy_engine/advisory/sideboard.py) mislabels
land-destruction spells as `creature-based`.

Found while implementing `feature-sb-maindeck-aware-coverage-discount`: verified against the
real card corpus (`legacy.duckdb`) that Wasteland's and Ghost Quarter's oracle text is literally
"{T}, Sacrifice ...: Destroy target [nonbasic] land." The removal rule in
`_derive_attacks_for_promoted` checks the bare substring `"destroy target"` and tags
`creature-based` before any land-specific check runs, so any promoted (non-catalog)
land-destruction hoser gets mislabeled as `creature-based` instead of `greedy-manabase`/`ramp`.

This doesn't affect Wasteland today because it's a curated `HOSER_CATALOG` entry
(`attacks=["greedy-manabase"]`) that bypasses the derivation entirely, but any land-destruction
card promoted from the empirical sideboard pool WITHOUT a curated catalog entry (e.g. Ghost
Quarter, which is not in `HOSER_CATALOG`) would be silently mis-tagged.

Suggested fix: add a land-destruction detection rule (oracle_text contains `"destroy target"`
AND target phrasing indicates a land, e.g. `"target land"` / `"target nonbasic land"`) ahead of
the generic creature-removal rule in `_derive_attacks_for_promoted`, mapping it to
`greedy-manabase` (and/or `ramp`) instead of `creature-based`.

## Implementation notes

Grounded oracle text (`data/legacy.duckdb`): Wasteland — `"{T}: Add {C}.\n{T}, Sacrifice this
land: Destroy target nonbasic land."`; Ghost Quarter — `"{T}: Add {C}.\n{T}, Sacrifice this
land: Destroy target land. Its controller may search their library for a basic land card, put
it onto the battlefield, then shuffle."` Confirmed Ghost Quarter is NOT in
`src/legacy_engine/data/hosers/legacy.json` (curated `HOSER_CATALOG`), so a promoted Ghost
Quarter really does hit this derivation path.

Added a new rule **3b** (between rule 3 graveyard-exile and rule 4 creature-removal) using a
new `_RE_LAND_DESTRUCTION = re.compile(r"destroy target (?:nonbasic )?land\b", re.IGNORECASE)`
— matches both Ghost Quarter's bare "destroy target land" and Wasteland's "destroy target
nonbasic land". Rule 3b tags `greedy-manabase` and sets an `is_land_destruction` flag; rule 4
now skips (`not is_color_blast and not is_land_destruction`), mirroring the existing
`is_color_blast` skip pattern from rule 2 exactly as directed. Per the parent epic's
sequencing note (Items implemented in order; Item 4 not yet done), this rule emits
`greedy-manabase` for now — **Item 4 revisits this rule** to migrate the tag to
`nonbasic-manabase` once that axis split lands (tracked there, not here).

Updated the docstring's priority list (added "3b. Land destruction") and the stale comment on
`TestMaindeckAnswerCoverage.test_wasteland_maps_to_greedy_manabase_via_catalog_short_circuit`
in `tests/test_sideboard.py`, which previously asserted the derivation "would mislabel"
land destruction — no longer true after this fix, so the comment was rewritten to describe
present behavior (rolling-foundation: no stale bug claims left in test docstrings).

Tests added to `TestDeriveAttacksForPromoted` (`tests/test_sideboard.py`):
`test_ghost_quarter_maps_to_greedy_manabase_not_creature_based` (Ghost Quarter's real oracle
text -> greedy-manabase, NOT creature-based), `test_wasteland_style_nonbasic_land_destruction_maps_to_greedy_manabase`
(the "nonbasic land" phrasing specifically), and
`test_normal_removal_spell_still_maps_to_creature_based` (sanity: ordinary "Destroy target
creature" with no "land" anywhere still tags creature-based — the carve-out doesn't swallow
real removal).

**Re-pin check**: none — grepped for other tests referencing Wasteland/Ghost Quarter/Strip
Mine/Sinkhole-style land destruction going through the oracle-text derivation path; all
existing references either use the curated catalog directly or hand-build `attacks=` on a
`HoserCard` fixture (bypassing derivation), so nothing else exercised the buggy path.

**Test evidence**: `tests/test_sideboard.py` full file — 428 passed (was 424 before; +3 new,
+1 rewritten comment on an existing test). `ruff check` on the touched lines shows no new
findings.

Files: `src/legacy_engine/advisory/sideboard.py` (`_RE_LAND_DESTRUCTION`,
`_derive_attacks_for_promoted` rule 3b + docstring), `tests/test_sideboard.py`.
