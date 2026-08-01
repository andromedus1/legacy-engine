---
id: epic-card-semantics-ir-fix-graveyard-regex
kind: story
stage: review
tags: [advisory, bug]
parent: epic-card-semantics-ir
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-31
---

# Fix _RE_GRAVEYARD to match the "their graveyard" oracle template (Exhume)


# `_RE_GRAVEYARD` misses the "their graveyard" oracle template (Exhume gets no graveyard role)

Surfaced by gate-tests drain v0.2.0 (batch B): restoring a dropped assertion revealed
`whattoplay._RE_GRAVEYARD` doesn't match "their graveyard" — Exhume's actual symmetric template
("each player puts a creature card from their graveyard onto the battlefield") — so
`_card_roles(Exhume)` returns empty and reanimator composition under-counts recursion density.
Honest state: `tests/test_whattoplay.py` carries a strict xfail with full explanation
(test_exhume_has_graveyard_recursion); Animate Dead split into its own passing test.

Fix: extend the regex to the their/each-player possessive templates; re-check which archetype
densities shift (reanimator shells) and whether any vulnerability-tag thresholds need re-pinning.
Card-semantics incident #11 for [[idea-card-semantics-rules-layer]] — another regex-tier miss of a
standard oracle template, strengthening the semantic-IR case.

## Implementation notes

Grounded Exhume's oracle text from `data/legacy.duckdb`: "Each player puts a creature card
from their graveyard onto the battlefield." (verified exact match to the xfail test's fixture
text). Two bugs, not one:

1. Owner-word gap named by the story: none of `_RE_GRAVEYARD`'s three alternatives accepted
   `their` alongside `your|a|the`/`your|a|the`/`a|any|your`.
2. A second, previously-undiagnosed gap in the same regex: the third alternative required the
   literal imperative `put ` (as in Reanimate's "Put target creature card..."), but each-player
   templates use the third-person verb form `puts` ("each player puts..."). Without `puts?` the
   fix would still have left Exhume unmatched even with `their` added — found by running the
   fixed-but-not-yet-`puts?`-aware regex against the actual xfail test and watching it still fail.

Fixed both: added `their` to all three owner-word alternations, and changed `put ` to `puts? `
in the third alternative. Removed the `strict=True` xfail marker from
`test_exhume_has_graveyard_recursion` (tests/test_whattoplay.py) — it now passes plainly.

**Corpus impact check** (required by the story): ran the old vs. new regex over every
`oracle_text` in `data/legacy.duckdb` (read-only). Newly-matched: 24 cards, e.g. Magister of
Worth, Roar of Reclamation, Fall of the Thran, Crypt Champion, Tasha Unholy Archmage, Visions of
Dread — spot-checked oracle text for every one; all are genuine "return/put a card from
[a/their] graveyard to the battlefield/hand" recursion effects, zero false positives (mill/
discard effects use "into their graveyard", not "from ... graveyard onto/to the battlefield/
hand", so the directional preposition keeps them out).

**Re-pin check**: none of the 24 newly-matched cards (including Exhume itself) appear anywhere
else in `tests/` outside `test_whattoplay.py`, so no reanimator-shell composition-density
fixtures or vulnerability-tag thresholds reference them — nothing else to re-pin. Ran the wider
advisory suite (`test_whattoplay.py`, `test_sideboard.py`, `test_linchpins.py`, `test_impact.py`,
`test_positioning.py`, `test_advise_report.py`, `test_generation_discovery.py`,
`test_generation_tuning.py`) — 844 passed, no ripples.

Files: `src/legacy_engine/advisory/whattoplay.py` (`_RE_GRAVEYARD`),
`tests/test_whattoplay.py` (xfail removed).
