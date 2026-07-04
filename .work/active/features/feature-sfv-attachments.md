---
id: feature-sfv-attachments
kind: feature
stage: review
tags: [advisory]
parent: epic-scorer-flexibility-valuation
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Attachments: plays-<color> as opponent vulnerability + broad-interaction attribution + missing counters

## Brief

Make flexible cards actually *attach* to the field needs they answer — coverage credit requires connection. Fix `_color_contingent_tags` (advisory/whattoplay.py) so `plays-<color>` fires as an **opponent** vulnerability (a blue opponent is vulnerable to `plays-blue` interaction), not only for the deck's own protection. Add a **broad-interaction attribution** so free/flexible counters attach to the whole combo/control plurality they answer rather than a couple of tiny `combo` elements. Add the missing catalog entries (Force of Negation, Spell Pierce, Mystical Dispute) to `data/hosers/legacy.json` with correct attribution against the new axis. Foundation for the breadth-objective feature — without correct attachments, submodular marginal-gain has nothing to aggregate.

## Epic context

- Parent epic: `epic-scorer-flexibility-valuation`
- Position: foundation — no deps; prerequisite for breadth-objective

## Inherited design decisions

- **Pure mechanics; NO empirical prior in scores** — value flexibility from first principles; the backtest is a divergence diagnostic + acceptance gate, never a score input.
- **Breadth mechanism = reformulate the coverage objective to true submodular marginal-gain** (a card credited by its total marginal coverage across every element it answers; inherits the 1−1/e greedy guarantee).
- **Make protective cards coverable** (`_hate:` self-protection becomes real coverage, not uncoverable crowding).


## Research briefs

- [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md) — the design foundation (submodular breadth = marginal gain; CVaR option value under the Dirichlet field; the three distortions; pure-mechanics guardrail). Addresses root causes #1 (missing attribution) and #2 (plays-blue never fires as opponent vuln). Folds idea-hoser-catalog-missing-blue-and-fon.

## Acceptance (epic-wide oracle)

Validated via field/window-scoped `advise backtest` on the Dimir Tempo deck + Boulder field: the recommended board's overlap with top-finisher boards improves **via first-principles flexibility value, not an empirical prior**. Residual model-vs-consensus divergence is surfaced, not scored away.

## Design (single-stride — story layer skipped)

Sized for direct implementation: three narrowly-scoped changes confined to attachment/attribution + catalog data, no ILP/objective math. Implemented inline in this feature rather than spawning child stories.

### Implementation discovery: item 1 (`plays-<color>` as opponent vulnerability) was already fixed

Before touching code, I verified the brief's D3 claim empirically against the live corpus (`data/legacy.duckdb`, read-only copy). `_color_contingent_tags` (whattoplay.py) already iterates `_COLOR_NAMES = {W,U,B,R,G}` symmetrically — there is no red-only special case. `_vulnerability_from_composition` unions its output into **both** `vulnerability_tags_for_deck` (a deck's own composition) and `vulnerability_tags`/`field_vulnerability_tags` (a corpus archetype's aggregate composition — i.e. the OPPONENT-facing path `sideboard.py` feeds into `archetype_tags`). Running `vulnerability_tags(con, archetype)` over all 707 corpus archetypes gives:

```
plays-blue: 415   plays-red: 270   plays-black: 456   plays-white: 347   plays-green: 418
```

`plays-blue` already fires for MORE opponent archetypes than `plays-red`. Git history shows this was fixed by `feature-sb-effect-tagging-model-vocab-catalog` (part of `epic-sideboard-scoring-model`, commit `3e19b8c`), which landed the same day as this epic's brief — the brief's D3 observation was accurate at the time it was written but the code had already moved past it by the time this feature started. This is a genuine (small) design-input discrepancy, not a bug to fix: **no code change was made for item 1.** Per the escape-hatch guidance this doesn't rise to re-opening drafting (nothing is broken; the acceptance criterion is already met) — instead I locked in the correct behavior with regression tests (`TestColorContingentTags.test_fires_symmetrically_for_every_wubrg_color`, `TestPlaysColorOpponentVulnerability` — parametrized over all five colors, DB-backed via `vulnerability_tags(con, archetype)` so the *opponent* code path is what's actually exercised, not just the pure helper) and added a docstring note on `_color_contingent_tags` citing the corpus counts, so a future reader doesn't waste time re-litigating this.

### Architectural choice: broad-interaction attribution (item 2)

**Problem:** a flexible free/soft counter (Force of Negation, Spell Pierce: "counter target noncreature spell") should attach to the *whole* combo/control plurality it answers. Today it can only reach the narrow `combo` tag (requires tutors + low avg MV + a "broken signal") and `storm-reliant` (requires storm density) — real control archetypes (Azorius Control, Esper Control, Jeskai Control, Miracles — verified against the corpus: creature density 0.03–0.10, zero tutors, no storm) carry **neither** tag and were structurally invisible to these cards.

Options considered:

1. **Widen the existing `combo` tag's definition to also cover control decks.** Rejected — `combo`'s definition (tutors + low MV + broken signal) is a load-bearing, semantically precise signal used elsewhere (e.g. `TestVulnerabilityTags`, `_derive_attacks_for_promoted` rule 5). Diluting it to also mean "any spell-based deck" breaks that precision for every other consumer and risks silently changing existing coverage-model behavior for cards that legitimately only answer combo (Chalice of the Void, Engineered Explosives).
2. **A hoser-level wildcard flag** (e.g. `HoserCard.broad: bool`) that dynamically matches a curated set of tags at solve time, bypassing the normal `attacks ∩ archetype_tags` intersection. Rejected — opaque relative to the existing transparent-heuristic contract (PRINCIPLES #7): a reviewer can't read `attacks` off a card and know what it covers; the "curated set" the wildcard expands to would itself need to live somewhere, duplicating the vocabulary without the auditability benefit. It also risks bypassing the `_archetype_tag_keys`/`candidate_covers` invariant the whole coverage model relies on for `functional_group` de-dup and color filtering.
3. **A new, mechanically-derived `VulnerabilityTag`: `noncreature-reliant`** — the complement of the existing `creature-based` signal (creature-slot density < `_NONCREATURE_RELIANT_MAX = 0.15`, well below `creature-based`'s ≥0.25 floor so the two never overlap for one archetype). Archetypes whose plan lives on the stack (combo enablers, control finishers/wraths/planeswalkers) carry it; free/soft anti-noncreature counters attack it in addition to their existing `combo`/`storm-reliant` tags. **Chosen.** It's a new, independently-legible vocabulary word — same shape as every other tag in the system (a documented threshold over composition, zero empirical input), doesn't touch `combo`'s semantics, and composes with the existing `(archetype, tag)` element model with no changes to `_build_coverage_model`'s math: adding a tag to an archetype's `archetype_tags` set and to a hoser's `attacks` frozenset is purely *data*, and the existing `element_weight`/`candidate_covers` construction (§Step 2/Step 4 of `_build_coverage_model`) already sums a card's marginal value across every element key it covers — the aggregation math this feature explicitly does not touch. This is the "confine to attachment/attribution + catalog" scope statement, taken literally: attach the vocabulary; let the (already correct, per the brief's §1) coverage math pick up the new elements.

Verified against the corpus: `noncreature-reliant` fires for Azorius/Esper/Jeskai/Bant Control, Azorius/Esper Miracle, and most combo/storm archetypes (Ad Nauseam Tendrils, TES, Doomsday variants) while correctly NOT firing for Burn (density 0.197, just above threshold — it's a real creature-adjacent aggro shell) or genuinely creature-heavy decks (Elves, Death and Taxes). Reanimator variants split — Rakdos Reanimator (density 0.25, wants to resolve a big creature) does not get the tag while thinner reanimator shells do; this is a defensible mechanics-only proxy (the payoff sits on the battlefield, not the stack) and is called out here as a known, transparent limitation rather than hidden.

Note: I deliberately did **not** retag existing catalog entries (Force of Will, Flusterstorm, Mindbreak Trap, Consign to Memory) to also carry `noncreature-reliant`, even though Force of Will's "Counter target spell" is arguably broader than Force of Negation's noncreature-restricted text. That retag would be a legitimate, mechanically-justified follow-up, but it changes existing cards' coverage footprint (and therefore ILP/greedy output) beyond what this feature's acceptance criteria (the 3 named new entries) call for — left as a judgment call to keep the diff reviewable and scoped.

### Implementation units

- **`src/legacy_engine/advisory/whattoplay.py`**
  - `_NONCREATURE_RELIANT_MAX = 0.15` (new module constant, alongside `_CREATURE_DENSITY`).
  - `_vulnerability_from_composition`: new branch emitting `"noncreature-reliant"` when `creature_slots / total_cards < _NONCREATURE_RELIANT_MAX`.
  - `VulnerabilityTag` comment block + `_vulnerability_from_composition`/`_color_contingent_tags` docstrings updated to document both the new tag and the already-symmetric `plays-<color>` behavior (with the corpus counts as evidence).
- **`src/legacy_engine/advisory/sideboard.py`**
  - `_RE_COUNTER_NONCREATURE = re.compile(r"counter target noncreature spell", re.IGNORECASE)` (new module constant).
  - `_derive_attacks_for_promoted`: new rule 1b — when the regex matches, add `"noncreature-reliant"` to the returned tag set (additive alongside rule 1's `combo`/`storm-reliant`). Module + function docstrings updated.
- **`src/legacy_engine/data/hosers/legacy.json`** — 3 new entries (schema-validated by the existing `load_hoser_catalog`, no loader changes needed):
  - **Force of Negation** — `attacks: [combo, storm-reliant, noncreature-reliant]`, `colors: [U]`, `max_copies: 4`, `swing: dedicated`, `symmetry: asymmetric`. Mirrors Force of Will's existing catalog shape (free pitch spell, colors=[U], no `castable_any_color` override — hard-casting still needs U).
  - **Spell Pierce** — same `attacks`, `colors: [U]`, `max_copies: 4`, `swing: soft` (taxing, not a hard/free counter — matches the Thoughtseize/Duress soft-swing convention).
  - **Mystical Dispute** — `attacks: [plays-blue]` only (per the task's explicit scoping: it counters *any* spell but is cost-reduced specifically against blue, so it's attributed to the color-blast axis like Pyroblast/Red Elemental Blast, not `noncreature-reliant`), `colors: [U]`, `max_copies: 4`, `swing: soft`, `symmetry: asymmetric`.
  - All three verified against `data/legacy.duckdb` oracle_text before writing attribution (see design notes above for exact wording).
- **`tests/test_whattoplay.py`** — `TestColorContingentTags` extended (parametrized, all 5 colors); new `TestPlaysColorOpponentVulnerability` (DB-backed, parametrized, exercises `vulnerability_tags` — the opponent-facing path); new `TestNoncreatureReliantTag` (fires/does-not-fire/boundary/control-without-combo-signal).
- **`tests/test_sideboard.py`** — `TestDeriveAttacksForPromoted` extended (2 new tests: noncreature-reliant fires on the exact phrase, does not fire on the generic "counter target spell"); new `TestAttachmentsFeature` (3 catalog-entry-shape tests + 2 `_build_coverage_model`-level tests proving Force of Negation attaches to BOTH a combo archetype and a control-only `noncreature-reliant` archetype in the same field, and that Mystical Dispute stays narrowly `plays-blue`-only). Updated 7 pre-existing `TestBuildPromotedCandidates`/`TestEmpiricalPromotion` tests whose fixtures assumed Force of Negation was *absent* from the catalog (true before this feature, false after) — swapped their "promoted, not-in-catalog" example card to `Daze` (also `free_interaction`, still absent from the catalog), which preserves each test's original intent (verifying the promotion-boundary mechanism) without depending on an assumption this feature deliberately invalidates.

### Testing

`.venv/bin/python -m pytest -q` → **2500 passed** (2464 baseline + 36 new tests, 0 skipped, 0 gamed). All new tests are acceptance-derived (color symmetry, tag thresholds, catalog shape, multi-archetype attachment) rather than reverse-engineered from the implementation. The 7 pre-existing tests touched were updated because their fixture premise ("Force of Negation is absent from the catalog") was invalidated by this feature's own in-scope catalog addition — not because they were wrong about anything this feature changes; their assertions about the promotion mechanism itself are unchanged, just re-pointed at `Daze`.

### Risks / follow-ups

- **Gated-additive:** every change is additive vocabulary (new tag word, new regex rule, new catalog rows) — no existing element-weight math, ILP objective, or `_build_coverage_model` signature semantics changed. Archetypes/cards that don't touch the new tag are byte-identical to before.
- **Left for `feature-sfv-breadth-objective`:** this feature only makes the *attachment* possible (more `(archetype, tag)` elements now exist for flexible counters to cover); the D1 concavity/aggregation-shape concern and the D2 weight-deflation concern are explicitly out of scope here and belong to the sibling features per the epic's touches list.
- **Judgment call flagged above:** not retroactively adding `noncreature-reliant` to Force of Will/Flusterstorm/Mindbreak Trap/Consign to Memory. Worth revisiting once the breadth-objective lands and its effect on existing recommendations can be observed via the field-scoped backtest.
- **Environment note:** mid-implementation, a concurrent process (another feature's autopilot wave sharing this working directory) reset the working tree via `git checkout`/`reset`, twice discarding my uncommitted edits before I could commit. Redone from scratch and verified; flagging in case the same shared-working-directory hazard affects sibling `feature-sfv-*` work landing concurrently.
