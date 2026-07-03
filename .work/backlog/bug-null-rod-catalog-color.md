---
id: bug-null-rod-catalog-color
created: 2026-07-03
tags: [data, advisory]
---

`src/legacy_engine/data/hosers/legacy.json`'s "Null Rod" entry has `"colors": ["G"]`, but Null
Rod is actually a colorless artifact (mana cost `{1}`, no color pips) — confirmed via
`cards.oracle_text`/`type_line` in `data/legacy.duckdb` (`type_line="Artifact"`; oracle text
"Activated abilities of artifacts can't be activated." has no color identity). Likely a
copy-paste/adjacency slip from a nearby green-colored catalog entry (Force of Vigor / Krosan
Grip are both `["G"]`).

Impact: any color-subset castability check against this catalog entry (e.g.
`advisory/impact.py`'s `castability_factor`, added in `feature-sb-field-weighted-scorer-impact`)
will incorrectly hard-gate Null Rod to uncastable for any deck without green, when it should
always be castable (colorless).

Fix: change `"colors": ["G"]` to `"colors": []` for the Null Rod entry.

Found while grounding Null Rod's oracle text for the `hoser_capabilities()` mapping table in
`advisory/impact.py`; out of scope for that story (pure module, no catalog edits).
