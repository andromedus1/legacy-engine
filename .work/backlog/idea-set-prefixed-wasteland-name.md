---
id: idea-set-prefixed-wasteland-name
created: 2026-08-12
updated: 2026-08-12
tags: [ingestion, cards, benchmark]
---

The raw MTGmelee cache contains one sideboard row named `[TMP] Wasteland` (four copies) in paper
event `https://melee.gg/Tournament/View/212627`, dated 2025-04-06, deck 5 (`Lons99`). The set-prefix
spelling has no exact card-dimension row and blocks the cutoff-safe snapshot at fold
`2025-04-28--2025-05-26` with `snapshot has 1 deck-card rows without observed card metadata`.
Raw provenance is
`data/cache/Tournaments/MTGmelee/2025/04/06/8-tappa-tigullio-legacy-league-by-kryptalegacy-212627-2025-04-06.json`.

Observed during the unchanged protocol
`6416fe6141d3f572c5c8f68a52021147a63639a6e2b2eba3482c2a1d0a2ac561` after the historical Goblin
repair allowed six folds to run. Canonical partial-run summary artifact
`c51ca0acdd12f20d97ad90ce77d6885b7c7df6557112911bae10d3838098702e` is `not-evaluable`: five
evaluable descriptive folds, one support-censored fold, then this fail-closed prerequisite. Preserve
provider/raw authority; do not strip arbitrary bracket prefixes generically or mutate the locked
source corpus/protocol without a separately reviewed exact reconciliation rule.
