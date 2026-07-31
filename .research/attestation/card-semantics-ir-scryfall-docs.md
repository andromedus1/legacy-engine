---
source_handle: card-semantics-ir-scryfall-docs
fetched: 2026-07-31
source_url: https://scryfall.com/docs/api/cards
provenance: source-direct
source_class: standard
---

# Scryfall API documentation — Card Objects

## Summary

Scryfall's official card-object reference. The fields relevant to a semantics IR: `keywords`
(an array of keyword names the card uses), `oracle_text` (nullable string, "The Oracle text
for this card, if any"), `layout` (a code for the card's layout, which governs whether the
card's rules text lives at top level or inside `card_faces`), `oracle_id` (a UUID stable
across reprints — the natural per-card key for derived semantics), `type_line`, and
`produced_mana`. `card_faces` is an array describing the distinct faces of multi-face cards.
The documentation confirms that `keywords` is populated from the game's keyword vocabulary
(examples given are "Flying" and "Cumulative upkeep"), i.e. it mirrors CR keyword
abilities/actions rather than arbitrary functional tags.

## Key passages

> keywords — Array — An array of keywords that this card uses, such as 'Flying' and
> 'Cumulative upkeep'. — § Core Card Fields (field table)

> oracle_text — String — Nullable — The Oracle text for this card, if any. — § Card Fields

> layout — String — A code for this card's layout. — § Core Card Fields

> oracle_id — UUID — Nullable — A unique ID for this card's oracle identity. This value is
> consistent across reprinted card editions, and unique among different cards with the same
> name (tokens, Unstable variants, etc). — § Core Card Fields

> produced_mana — Colors — Nullable — Colors of mana that this card could produce.
> — § Card Fields

## Structural metadata

HTML docs page (fetched 2026-07-31 with a browser user agent; the page returns 403 to generic
fetchers). Field tables grouped as Core Card Fields / Gameplay Fields / Print Fields;
multi-face card handling documented under "Card Face Objects".
