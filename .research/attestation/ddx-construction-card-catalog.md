---
source_handle: ddx-construction-card-catalog
fetched: 2026-08-20
source_path: data/scryfall/oracle_cards.json
provenance: source-direct
substrate_confidence: source-direct
---

# Local Oracle-card construction fields

The local Oracle-card export supplies the card names, type lines, Oracle text, produced-mana
fields, and card-face records used to identify lands and fetchable colored land sources.

## Key passages

- Every card name in the 14 registered 75s resolves either as a top-level card name or a named
  card face in the export.
- Land cards are identified by `type_line`; basic land types in that field identify fetchable
  duals and basics.
- The seven fetchland names in the registered maindecks have Oracle text naming the two basic land
  types they can search for.
- `produced_mana` supplies the unrestricted color outputs used for colored-source counts.
- Cavern of Souls has conditional colored-mana text, so the experiment reports it separately as a
  restricted rainbow land rather than adding it to unrestricted colored-source totals.

