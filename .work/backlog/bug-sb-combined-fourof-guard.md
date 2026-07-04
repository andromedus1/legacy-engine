---
id: bug-sb-combined-fourof-guard
created: 2026-07-04
tags: [advisory, sideboard]
---

# Sideboard recommend/considering path lacks a combined main+SB 4-of guard

Found by the deck-prep-arc completion review (2026-07-04): two generated meta lists were
format-ILLEGAL — `recommend_sideboard`'s candidate pool + `considering` refill path do not
check combined maindeck+sideboard copies against the 4-of rule. Concrete instances: online
Dimir consensus (4 main Thoughtseize) got a 5th Thoughtseize offered via considering
(gain .0028); Painter consensus (4 main Pyroblast) got a 5th Pyroblast recommended outright.
`generate consensus` enforces legality on ITS output ("Legality: OK"), but the advisory board
path solves per-card `max_copies` from the catalog without subtracting maindeck copies.
Fix shape: cap each candidate's effective max_copies at `4 − maindeck.get(card, 0)`
(basics exempt) in `_build_coverage_model` / promoted-candidate construction, + a legality
post-check warning. Both shipped lists were hand-corrected and note the mechanism.
