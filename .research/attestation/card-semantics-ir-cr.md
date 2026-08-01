---
source_handle: card-semantics-ir-cr
fetched: 2026-07-31
source_url: https://media.wizards.com/2026/downloads/MagicCompRules%2020260619.txt
provenance: source-direct
source_class: standard
version: effective 2026-06-19
---

# Magic: The Gathering Comprehensive Rules (June 19, 2026)

## Summary

The current Comprehensive Rules text file (effective June 19, 2026), downloaded from the
official Wizards media host. Two sections function as closed semantic vocabularies: rule 701
enumerates keyword actions (verbs with defined game meanings — counted mechanically from the
file: 69 numbered subsections 701.1–701.69) and rule 702 enumerates keyword abilities (counted:
194 numbered subsections 702.1–702.194). Rule 118 defines cost semantics: 118.8 defines
additional costs (paid *on top of* the mana cost) and 118.9 defines alternative costs (paid
*instead of* the mana cost) — and 118.9 states the canonical English templates alternative
costs are phrased with, which is exactly the phrasing surface that pitch-spell detection keys
on. The rules also distinguish cost from effect structurally (costs are announced and paid
during casting per 601.2b; effects happen on resolution), which is the rules-level basis for
clause-role segmentation in an IR.

## Key passages

> 701.1. Most actions described in a card's rules text use the standard English definitions of
> the verbs within, but some specialized verbs are used whose meanings may not be clear. These
> "keywords" are game terms; sometimes reminder text summarizes their meanings. — CR 701.1

> 702.1. Most abilities describe exactly what they do in the card's rules text. Some, though,
> are very common or would require too much space to define on the card. In these cases, the
> object lists only the name of the ability as a "keyword"; sometimes reminder text summarizes
> the game rule. — CR 702.1

> 118.8. Some spells and abilities have additional costs. An additional cost is a cost listed
> in a spell's rules text, or applied to a spell or ability from another effect, that its
> controller must pay at the same time they pay the spell's mana cost or the ability's
> activation cost. Note that some additional costs are listed in keywords; see rule 702. — CR 118.8

> 118.9. Some spells have alternative costs. An alternative cost is a cost listed in a spell's
> text, or applied to it from another effect, that its controller may pay rather than paying
> the spell's mana cost. Alternative costs are usually phrased, "You may [action] rather than
> pay [this object's] mana cost," or "You may cast [this object] without paying its mana
> cost." Note that some alternative costs are listed in keywords; see rule 702. — CR 118.9

> 118.9a Only one alternative cost can be applied to any one spell as it's being cast. The
> controller of the spell announces their intentions to pay that cost as described in rule
> 601.2b. — CR 118.9a

## Structural metadata

Plain-text file, 975,632 bytes; header states "effective as of June 19, 2026." Organized as
numbered rules 1–9 plus glossary. Counts of 701.x (69) and 702.x (194) subsections were
extracted mechanically with a regex over rule-number line starts (`\n701\.(\d+)\. ` /
`\n702\.(\d+)\. `); max indices 701.69 and 702.194 with no gaps in the numbering.
