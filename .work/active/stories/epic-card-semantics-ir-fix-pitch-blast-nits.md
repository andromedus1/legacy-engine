---
id: epic-card-semantics-ir-fix-pitch-blast-nits
kind: story
stage: done
tags: [advisory, bug]
parent: epic-card-semantics-ir
depends_on: []
release_binding: v0.4.0
gate_origin: null
created: 2026-07-03
updated: 2026-07-31
---

# Fix _PITCH_SPELL_RE escaped-paren bug + blast-capability nit


# Two small correctness nits from the 2026-07-03 review

1. **`_PITCH_SPELL_RE` escaped-paren bug** (sideboard.py ~196-203): the branch
   `without paying \(its|their\) mana cost` escapes the parens, matching literal "(its" — the
   "their" variant is dead. The comment claims it mirrors `card_tags._FREE_SPELL_RE` (which uses
   unescaped parens and works). Consequence: "without paying their mana cost(s)" cards aren't
   pitch-exempted in `compute_deck_anti_synergy_signals`. Fix the regex; add a their-variant test.
2. **Color-blind blast capabilities** (impact.py `_CAPABILITY_BY_NAME`): Pyroblast/Hydroblast/
   BEB/REB are credited unconditional artifact/creature/enchantment-removal, but each only destroys
   permanents of one color — Hydroblast can never kill Chalice, yet would be credited as
   neutralizing an artifact linchpin. Latent (3 curated linchpin archetypes today); live risk as the
   linchpin set grows. Make capability credit color-conditional.

3. **`_RE_COUNTER_COLORLESS` DOTALL looseness** (sideboard.py ~1275, Phase-8 review nit): the
   `.*` with DOTALL could span unrelated sentences on a future card ("counter target <anything, any
   distance> colorless spell"). Corpus-verified today: exactly 2/39,452 hits, both correct (Consign,
   Ceremonious Rejection). Tighten to a single-sentence bound when touching this file.

## Implementation notes

**(a) `_PITCH_SPELL_RE`** (sideboard.py): confirmed the bug — `without paying \(its|their\)
mana cost` has escaped parens, so the top-level `|`-joined regex actually splits into six
literal alternatives (`...without paying (its` / `their) mana cost...` as separate branches),
neither of which appears in real oracle text; the "its" wording only ever matched via the
separate `without paying its mana cost` branch, and "their" was fully dead. Fixed to
`without paying (?:its|their) mana costs?` (mirrors `card_tags._FREE_SPELL_RE`'s unescaped
group; also added optional trailing `s` since real cards use both "mana cost" and "mana
costs"). Grounded via `data/legacy.duckdb`: Aluren — "Any player may cast creature spells with
mana value 3 or less without paying their mana costs and as though they had flash." (CMC 4,
colors=G) — added `test_their_variant_pitch_spell_excluded_from_low_curve` in
`tests/test_sideboard.py` proving Aluren's CMC is now excluded from the low-curve average
(mirrors the existing Force-of-Will pitch test's shape).

**(b) Color-blind blast capabilities** (impact.py): Pyroblast/Red Elemental Blast hose BLUE
("Counter target spell if it's blue." / "...target blue spell/permanent."); Hydroblast/Blue
Elemental Blast hose RED (mirror) — grounded via `data/legacy.duckdb`. `_CAPABILITY_BY_NAME`
still claims the same unconditional tokens for these four (documented as such), but a new
`hoser_capabilities_for(hoser, linchpin)` gates that claim by `linchpin.colors` via a small
`_BLAST_TARGET_COLOR` map (name -> required target color); `centrality_factor` now calls it
per-linchpin instead of the flat `hoser_capabilities(hoser)`. This required adding a `colors:
frozenset[str] = frozenset()` field to `Linchpin` (backward-compatible default — existing
construction sites unaffected) populated from `card.colors` in `derive_linchpins` and from a
new optional `"colors"` key (closed-vocabulary WUBRG-validated, mirrors
`sideboard._VALID_COLORS`) in `load_linchpin_overrides`. Updated
`src/legacy_engine/data/hosers/../linchpins/legacy.json`'s 3 curated archetypes with grounded
colors (Grindstone/Painter's Servant/Chalice of the Void: colorless, `colors=[]`, verified
`cards.colors=''`; Show and Tell: `colors=["U"]`, verified `cards.colors='U'`) — this also
FIXES the pre-existing over-crediting for Painter's Servant and Chalice (both colorless; all
four blast cards previously got undue creature/artifact-removal credit against them) and for
Show and Tell against Hydroblast/Blue Elemental Blast (blue spell; those two red-hosers
previously got undue counter-on-cast credit). Added `hoser_capabilities_for` and
`centrality_factor` color-gate tests in `tests/test_impact.py`
(`TestHoserCapabilitiesFor`, `TestCentralityFactorColorGate`): Hydroblast gets NO credit vs a
colorless Chalice-of-the-Void-shaped linchpin, keeps full credit vs a red linchpin, and gets
no credit vs a blue linchpin either (it hoses red, not blue); mirrored for Pyroblast; a
non-color-gated hoser (Null Rod) is unaffected by the gate.

**(c) `_RE_COUNTER_COLORLESS`**: tightened `counter target.*colorless spell` (DOTALL) to
`counter target[^.]*colorless spell` (no DOTALL) — a negated character class already spans
newlines without DOTALL, so Consign to Memory's one sentence ("Counter target triggered
ability or\ncolorless spell.") still matches, but the sentence-ending `.` now stops the match
from reaching into a later, unrelated sentence. Corpus check (`data/legacy.duckdb`, all
`oracle_text`): exactly 2 hits before AND after the fix (Consign to Memory, Ceremonious
Rejection) — no regression. Added
`test_counter_colorless_regex_does_not_span_sentences` in `tests/test_sideboard.py`: a crafted
two-sentence card ("Counter target spell. This deals 1 damage to you for each colorless spell
you've cast this game.") no longer gets `colorless-reliant`, while the generic counter-magic
rule still fires.

**Re-pin check**: no existing pinned expectations shifted — `hoser_capabilities()`'s own
return value is unchanged (tests against it still pass unmodified); the color gate only
narrows `centrality_factor`'s per-linchpin matching, and no existing test exercised
Pyroblast/Hydroblast/BEB/REB against the 3 curated linchpins before this story (verified via
grep — none of `tests/test_sideboard.py`/`test_impact.py`/`test_linchpins.py` referenced those
four card names together with a curated linchpin prior to this change), so nothing needed
re-pinning.

**Test evidence**: `tests/test_sideboard.py`, `tests/test_impact.py`, `tests/test_linchpins.py`,
`tests/test_whattoplay.py` — 631 passed. `ruff check` on the touched files shows only
pre-existing UP037 (quoted-annotation style) findings consistent with the rest of each file;
no new categories introduced.

Files: `src/legacy_engine/advisory/sideboard.py` (`_PITCH_SPELL_RE`,
`_RE_COUNTER_COLORLESS`), `src/legacy_engine/advisory/impact.py` (`_BLAST_TARGET_COLOR`,
`hoser_capabilities_for`, `centrality_factor`), `src/legacy_engine/advisory/linchpins.py`
(`Linchpin.colors`, loader validation, `derive_linchpins`),
`src/legacy_engine/data/linchpins/legacy.json`, `tests/test_sideboard.py`,
`tests/test_impact.py`.
