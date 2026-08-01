---
id: epic-sb-advisor-correctness-acquire-color-filter
kind: story
stage: review
tags: [advisory, bug]
parent: epic-sb-advisor-correctness
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-27
updated: 2026-08-01
---

# Color-identity filter for advise acquire + sideboard candidate pool


**`advise acquire` (and the `advise sideboard` candidate pool) suggests off-color
cards the deck cannot cast — no color-identity filter.**

Found dogfooding Dimir Tempo (UB) on 2026-06-27. The acquire buy-list for a UB deck
recommended:
- Blood Moon, Pyroblast  (RED — uncastable in UB)
- Veil of Summer, Carpet of Flowers, Force of Vigor  (GREEN — uncastable in UB)
- Back to Basics  (castable, but actively anti-synergistic for a 2-basic Dimir
  manabase — it would hose the pilot's own nonbasics; arguably needs a
  hurts-my-own-manabase guard too)

A buy-list meant to optimize *my* sideboard must restrict candidates to the deck's
color identity (plus truly colorless/artifact cards like Null Rod, Damping Sphere,
Pithing Needle, Engineered Explosives). Off-color suggestions are noise at best and
misleading at worst.

Fix: derive the deck's color identity from the maindeck (or accept a `--colors`
override) and filter acquire/sideboard candidates to {deck colors} ∪ {colorless}.
Consider a secondary flag for cards whose downside scales with the pilot's own
nonbasic count (Back to Basics, Blood Moon mirror-hate).

Related: [[idea-archetype-conditioned-card-winrate]] (other advisory-honesty gap
found the same session).

## Implementation notes

**Where the bug actually lived.** `recommend_sideboard`'s own candidate pool was
already correct: `_build_coverage_model` color-prefilters HOSER_CATALOG (and
promoted) candidates against `deck_colors` (`hoser.colors <= deck_colors`, bypassed
by `castable_any_color`). The bug was in `advisory/acquire.py`'s `acquire_plan`
Step A: its candidate-universe assembly unconditionally added **every**
HOSER_CATALOG entry to the buy-ranking universe (the old comment even claimed
"filtered by color ... inside recommend_sideboard", which was false for THIS
code path — `acquire_plan` never routes catalog cards through
`_build_coverage_model` at all). Fix landed in the assembly step itself
(`acquire_plan`, not `_rank_acquisitions` — keeps the pure core DB/domain-free per
`objective-search-split`).

**Deck color derivation** reuses `legacy_engine.colors.compute_deck_colors`
(`lands.produced_mana ∩ nonlands.colors`) unchanged — no second rule invented.
Resolution order in `acquire_plan`'s new Step A2: explicit `colors=`/`--colors`
override > the supplied `deck` (via `_load_deck_cards`) > the target archetype's
own modal maindeck consensus (`card_frequencies(..., board="main")`) > undetermined
(honest-degrade: no filter, labeled in `warnings`, never a silent narrow-to-nothing
when a real deck could exist and we simply lack a hook to it). `--colors` wired
through the CLI (`advise acquire --colors UB`).

**Hybrid/Phyrexian decision**: HOSER_CATALOG already carries a curated
`castable_any_color` field for exactly this case (Surgical Extraction's `{B/P}`
Phyrexian mana; Faerie Macabre's zero-mana discard activation) — reused as-is, the
same convention `_build_coverage_model` already uses. Verified against
`data/legacy.duckdb` (`cards.mana_cost`): Surgical Extraction = `{B/P}`, Faerie
Macabre = `{1}{B}{B}` (its bypass is the alt-cost activation, not Phyrexian mana —
both fields under the same `castable_any_color` flag). No shipped catalog entry
uses genuine hybrid mana (`{G/W}`-style OR-cost) today; if one is ever added, the
subset-check (`colors <= deck_colors`, an AND semantics) would wrongly require
BOTH colors — the curator should mark it `castable_any_color=True` (conservative:
always passes) until/unless the hybrid case earns its own OR-semantics field.

**Non-vacuity**: added 6 tests in `tests/test_collection_aware_engine.py`
(`TestAcquirePlanColorFilter` + one CLI test) — UB-deck exclusion of Blood Moon /
Pyroblast / Veil of Summer / Carpet of Flowers / Force of Vigor with Null Rod /
Pithing Needle / Engineered Explosives still included; `--colors` override working
standalone (no deck/DB cards needed); invalid `--colors` raising `ValueError`;
Surgical Extraction + Faerie Macabre surviving a mono-R filter via
`castable_any_color` while Veil of Summer (no bypass) is still excluded in the
same test; and archetype-consensus-derived colors when no `--deck` is given.
Verified non-vacuous directly: stashed the `acquire.py`/`cli.py` changes (fix
reverted, tests kept) and reran — all 6 new tests failed (4 on `TypeError:
unexpected keyword argument 'colors'`, 1 on the real assertion — Blood Moon
present in the archetype-consensus-derived buy list — 1 CLI test also failed);
restored the fix and all 6 pass again. Full existing suite for the touched module
(`tests/test_collection_aware_engine.py`, 46 tests) stays green, including the two
pre-existing `deck=None, archetype=None` smoke tests (undetermined-colors path,
unfiltered — unchanged behavior).

**Follow-up (explicitly out of scope here)**: Back to Basics is castable-but-
anti-synergistic for a nonbasic-heavy Dimir manabase — it would hose the pilot's
own nonbasics. This story only filters by *castability*, not by *self-cost*. The
clean seam for a "hurts-my-own-manabase" guard is `acquire_plan`'s Step A2/HOSER
loop reusing `compute_deck_anti_synergy_signals` +
`is_anti_synergistic`/`_ANTI_SYNERGY_MAP` (already built for
`recommend_sideboard` in `advisory/sideboard.py`) the same way the color filter
now reuses `compute_deck_colors` — but that semantics belongs to the epic's
`hate-self-cost` feature, not this story.
