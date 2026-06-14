---
id: feature-hoser-catalog-expansion
kind: feature
stage: drafting
tags: [advisory, generation]
parent: epic-bigmana-coverage-sideboard-fidelity
depends_on: [feature-bigmana-ramp-tag]
release_binding: null
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
