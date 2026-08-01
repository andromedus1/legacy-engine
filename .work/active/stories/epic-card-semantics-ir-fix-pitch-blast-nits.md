---
id: epic-card-semantics-ir-fix-pitch-blast-nits
kind: story
stage: implementing
tags: [advisory, bug]
parent: epic-card-semantics-ir
depends_on: []
release_binding: null
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
