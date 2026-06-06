---
id: idea-hoser-catalog-expansion
created: 2026-06-06
tags: [advisory, generation]
---

The sideboard solver's `HOSER_CATALOG` (src/legacy_engine/advisory/sideboard.py) knows only ~25 cards, and is missing many staples that real Legacy sideboards run — so the solver can't "see" most of a user's actual SB and falls back to recommending only the hosers it knows (Back to Basics, Defense Grid, Chalice). Discovered dogfooding a Dimir Tempo SB: the engine was blind to Null Rod, Pithing Needle, Consign to Memory, Engineered Explosives, Sheoldred's Edict, Toxic Deluge, Dauthi Voidwalker, Harbinger of the Seas — i.e. nearly the whole real sideboard.

Expand the catalog (data-driven where possible — derive candidate hosers from cards that actually appear in winning sideboards per `report cards --board side`), and add the missing tag→answer mappings. Pairs naturally with [[idea-bigmana-ramp-archetype-tag]] (need the tags before the hosers have something to attack). Keep the curated-swing caveat. Consider sourcing the catalog from a data file rather than inline Python so it's editable without a code change.
