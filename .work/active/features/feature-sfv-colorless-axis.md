---
id: feature-sfv-colorless-axis
kind: feature
stage: done
tags: [advisory]
parent: epic-scorer-flexibility-valuation
depends_on: [feature-sfv-attachments]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Colorless/trigger vulnerability axis — close the Consign acceptance criterion

## Brief

Promoted from backlog during the epic's completion review because **Consign to Memory is named in
the epic's acceptance oracle** ("FoN / Consign move from winners-only into overlap") and remains
winners-only at **95.7%** adoption in 258 local-field-relevant top-finisher boards. Mechanism
(confirmed): Consign's catalog `attacks = {combo, storm-reliant}` is a strict subset of Force of
Negation's, so under correct submodular marginal-gain FoN dominates and Consign's marginal is ~0 —
tag-subset dominance, not a solver bug. Winners run BOTH because Consign answers an axis FoN cannot.

**Oracle (DB-verified 2026-07-03):** `{U}`, "Replicate {1}" + **"Counter target triggered ability or
colorless spell."** Colorless spells and TRIGGERED ABILITIES only — not a general counterspell.
Premier vs Saga chapter triggers (Black Saga Storm / Blue Artifacts), storm-count triggers, Chalice
triggers, Eldrazi/colorless spells; replicate {1} scales to multiple triggers in one turn.

## Design (inline — story-sized)

Add a mechanics-derived vulnerability axis so trigger/colorless-answering cards attach to the
archetypes whose plan runs through colorless spells or key triggered abilities:

- **`colorless-reliant`** in `whattoplay.py`'s `VulnerabilityTag` vocabulary: derived in
  `_vulnerability_from_composition` from colorless-nonland-spell density (a card with empty
  `colors` and a castable spell type) ≥ a named threshold constant (pick by inspecting real
  archetypes: Eldrazi, Blue Artifacts/Affinity, Saga Storm should fire; Dimir/Izzet should not —
  verify against the corpus and document the threshold choice). Judgment call allowed on whether a
  separate `trigger-reliant` axis is derivable purely from composition (Saga density etc.) — if it
  isn't cleanly mechanics-derivable, ship `colorless-reliant` only and note why.
- **Catalog:** add the new tag to Consign's `attacks` (keeping `combo, storm-reliant`). Check
  whether other catalog cards genuinely attack the axis (e.g. Stifle-likes if present; do NOT
  stretch cards that don't).
- **Pure mechanics** — no empirical prior; the 95.7% signal motivates the investigation, the tag
  derivation must stand on composition alone.

## Acceptance

Field-scoped `advise backtest` (Dimir Tempo + the local meta): **Consign moves winners-only → overlap**
(recommended by the engine) with FoN still in overlap and the suite green (2546 floor + new tests).

## Implementation notes

**`colorless-reliant` derivation** (`whattoplay._vulnerability_from_composition`): tallies
colorless-nonland-spell copies (`card.colors == []` and not a land) during the existing
composition walk, then fires `colorless-reliant` when that count / total maindeck copies
≥ `_COLORLESS_RELIANT_DENSITY = 0.15`. Denominator matches `_CREATURE_DENSITY` /
`_NONCREATURE_RELIANT_MAX` (total maindeck copies), for consistency with the other
composition-share tags in this function; `>=` semantics match creature-based/storm-reliant/
gy-recursion (fires AT the boundary), not the strict-`<` complement style `noncreature-reliant`
uses.

**Calibration (2026-07-03, `_archetype_composition` aggregates against `data/legacy.duckdb`):**

| Archetype | total_cards | colorless copies | density (÷ total_cards) |
|---|---|---|---|
| Eldrazi | 162,524 | 91,308 | **0.562** (fires) |
| Mystic Forge Combo | 119,035 | 75,613 | **0.635** (fires) |
| Blue Artifacts | 89,855 | 32,779 | **0.365** (fires) |
| Black Saga Storm | 6,422 | 1,823 | **0.284** (fires — lowest must-fire) |
| Painter | 112,872 | 30,537 | 0.271 (fires — not required, but genuinely artifact/colorless-heavy: Grindstone, Painter's Servant, Mishra's Bauble) |
| Show and Tell | 167,922 | 19,647 | 0.117 (checked, does not fire — closest non-firer) |
| Death & Taxes | 126,464 | 10,107 | **0.080** (must NOT fire — highest must-not-fire) |
| Izzet Delver | 119,957 | 8,262 | **0.069** (must NOT fire) |
| Dimir Tempo | 179,330 | 3,814 | **0.021** (must NOT fire) |

Threshold **0.15** sits in the wide gap between the highest must-not-fire archetype
(Death & Taxes 0.080; next-closest checked non-firer Show and Tell 0.117) and the lowest
must-fire archetype (Black Saga Storm 0.284) — comfortable margin on both sides.

**`trigger-reliant` axis: declined.** Consign's oracle text also answers "triggered ability"
(Saga chapters, storm-count triggers, Chalice-style ETB/cast triggers) — mechanically
heterogeneous with no single composition signature analogous to `colors == []`. A narrow
proxy (e.g. Saga-permanent density) would silently drop storm-count/Chalice triggers and
misrepresent what Consign answers; a broad triggered-ability keyword scan fires on nearly
every deck (almost any creature has an ETB/attack trigger) and has no discriminating power
as a density threshold. The storm-count slice is already covered by `storm-reliant`.
Shipped `colorless-reliant` only, per the design's explicit escape hatch — documented in
`whattoplay.VulnerabilityTag`'s docstring and the `_COLORLESS_RELIANT_DENSITY` constant.

**Catalog attachment:** added `colorless-reliant` to Consign to Memory's `attacks` in
`data/hosers/legacy.json` (now `["combo", "storm-reliant", "colorless-reliant"]`). Audited
all other 36 catalog entries' oracle text against `cards.oracle_text` (DB-verified) — none
genuinely restrict to colorless spells/permanents. In particular: Chalice of the Void
("counter that spell" when mana spent == charge counters) and Engineered Explosives
("destroy each nonland permanent with mana value equal to...") are CMC-gated, not
color-gated; Null Rod ("Artifacts lose all activated abilities") restricts by permanent
TYPE (artifact), not color — none stretched onto this axis. `_derive_attacks_for_promoted`
(sideboard.py) gained a symmetric rule 1c (`_RE_COUNTER_COLORLESS`: "counter target ...
colorless spell") so a future empirically-promoted colorless-counter (verified against the
DB: Ceremonious Rejection, "Counter target colorless spell.", exists in `cards` but is not
yet catalog-adopted) would attach correctly without a catalog edit.

**Backtest before/after** (`advise backtest --archetype "Dimir Tempo" --field
decks/local-field-current.txt --field-scope`, 258 top-finisher decks, field-scope ON):

| | Before | After |
|---|---|---|
| Consign to Memory | winners-only, 95.7% | **overlap/recommended, 95.7%** |
| Force of Negation | overlap, 99.2% | overlap, 99.2% (unchanged) |
| Scorer-only false positives | 3 (Damping Sphere 2.7%, Defense Grid 0.0%, Nihil Spellbomb 17.8%) | **2** (Damping Sphere 2.7%, Defense Grid 0.0%) |
| Agreement | 6/9 (67%) | 7/9 (78%) |

Consign's marginal gain from `colorless-reliant` (an axis FoN's attack set does not carry)
was enough on its own to outscore Nihil Spellbomb for the 9th recommended slot — Nihil
Spellbomb drops out of the top-9 entirely (net improvement, not a new false positive: it
was already scorer-only before this change). No new scorer-only false positives were
introduced; the count went down, and the two that remain (Defense Grid, Damping Sphere) are
the pre-existing tracked ones named in the epic's acceptance oracle.

**Tests:** 10 new (5 in `tests/test_whattoplay.py`: corpus-verified firing pattern
Eldrazi-fires/Dimir-doesn't as hermetic fixtures, boundary-at-threshold, boundary-just-below,
independence from creature-density; 5 in `tests/test_sideboard.py`: Consign's real oracle
text → colorless-reliant, Ceremonious-Rejection-style generic template, negative case
(generic "counter target spell"), negative case (noncreature-restricted counter does NOT
also get colorless-reliant), plus a Consign-vs-FoN complement test asserting neither
catalog entry's `attacks` is a subset of the other's — the mechanism fix for the
tag-subset-dominance the epic's acceptance oracle identified). Full suite: 2556 passed
(2546 floor + 10 new), no regressions.

Escape hatch: not needed — the honest threshold reached the acceptance target on its own.


## Determinism caveat (Phase-8 review, 2026-07-03)

The backtest agreement recorded above reads **6/9 or 7/9 run-to-run** due to a pre-existing,
untracked ILP tie in slot 9 (Snuff Out 30.2% observed vs Long Goodbye 1.2% —
`idea-ilp-tiebreak-nondeterminism`). This feature's acceptance facts are stable across both
optima: Consign in overlap (95.7%), FoN in overlap (99.2%), Damping Sphere + Defense Grid the
scorer-only pair.
