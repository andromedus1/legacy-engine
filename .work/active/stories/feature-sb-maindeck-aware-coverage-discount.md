---
id: feature-sb-maindeck-aware-coverage-discount
kind: story
stage: done
tags: [advisory]
parent: feature-sb-maindeck-aware-coverage
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Maindeck-coverage discount on SB element weights

## Brief

Detect which vulnerability tags the maindeck already answers and discount the SB coverage-model
element weights for those tags, so the recommender stops padding cards redundant with the maindeck
(the "SB'd Ghost Quarter while running 4 Wasteland" bug). Gated-additive: no maindeck answers ⇒
byte-identical.

## Implementation

Covers parent feature **Units C1 + C2** — see `feature-sb-maindeck-aware-coverage` § Implementation
Units for the `_maindeck_answer_coverage` helper, the `_MAINDECK_DISCOUNT`/`_MAINDECK_SATURATION`
constants, the `_build_coverage_model` discount + `recommend_sideboard` wiring, and acceptance
criteria. File: `src/legacy_engine/advisory/sideboard.py`; tests in `tests/test_sideboard.py`.

## Implementation notes

**C1 — `_maindeck_answer_coverage(main_cards, get_card, *, catalog=None)`** (placed right before
`_build_coverage_model`, after `_build_promoted_candidates`). Attribution is catalog-first,
oracle-text-derivation-fallback:

1. If the maindeck card name is itself a `HOSER_CATALOG` entry (e.g. Wasteland ->
   `attacks={"greedy-manabase"}`), its curated `attacks` are used directly.
2. Otherwise, `get_card(name)` (an injected `name -> Card | None` lookup, objective-search-split:
   the caller resolves once via `_load_deck_cards` and passes a plain dict `.get`) resolves the
   card, and `_derive_attacks_for_promoted` (the same heuristic `_build_promoted_candidates`
   already uses) derives tags from `oracle_text`/`type_line`.

Copies accumulate per tag and saturate at `_MAINDECK_SATURATION=4` (`min(1.0, copies/4)`).
`"_hate"` is excluded from the returned coverage (not a real vulnerability tag).

**Judgment call — the catalog-first branch is load-bearing, not cosmetic.** I verified against the
real card corpus (`legacy.duckdb`) that Wasteland's and Ghost Quarter's oracle text is literally
"{T}, Sacrifice ...: Destroy target land." — `_derive_attacks_for_promoted`'s removal rule
(`"destroy target" in text_lower`) matches that substring and would mislabel both as
`creature-based`, not `greedy-manabase`/`ramp`. Reusing the derivation *unconditionally* (as a
literal reading of "reuse the existing oracle→attacks derivation" might suggest) would have
silently failed the feature's own motivating example. Wasteland is already a curated
`HOSER_CATALOG` entry (`attacks=["greedy-manabase"]`), so checking the catalog first before falling
back to derivation both (a) reuses real, already-reviewed curation for the common case and (b)
produces the exact tag the feature spec's example names. I did **not** touch
`_derive_attacks_for_promoted`'s land-destruction mislabeling itself — that's a pre-existing latent
gap in a different, already-shipped unit, out of this story's scope. Parking it: real promoted (not
curated) land-destruction hosers like Ghost Quarter, when NOT pre-seeded into a catalog, will still
mis-attribute to `creature-based` via the empirical-pool promotion path — worth a follow-up to add a
land-destruction rule to `_derive_attacks_for_promoted` ahead of the "destroy target" removal check.

**Judgment call — fallback exclusion.** `_derive_attacks_for_promoted` never returns an empty set;
unmatched text falls back to `_FALLBACK_ATTACKS={"combo"}`. Crediting that indiscriminately to
every maindeck card with no concrete signal (most of a 60-card deck) would spuriously discount the
`combo` axis for literally every deck. `_maindeck_answer_coverage` detects `attacks ==
_FALLBACK_ATTACKS` and treats it as "answers nothing" (`combo` only ever arises for real signal
in combination with `storm-reliant`, from the counter-magic/free-interaction rules — a bare
`{"combo"}` result is unambiguously the fallback).

**C2 — `_build_coverage_model(..., maindeck_coverage: dict[str, float] | None = None)`.** New Step
3c (right after the existing Step 3b `matchup_pressure` pass, same `"|" not in key` skip to exempt
`_hate:` pseudo-elements): for each live `<archetype>|<tag>` element, multiply its weight by
`(1 - _MAINDECK_DISCOUNT * maindeck_coverage.get(tag, 0.0))`. One `// maindeck-aware: discounted
<tag> by <pct>% (deck already answers it)` line is appended to `warnings` per tag actually
discounted (deduped across archetypes sharing a tag, sorted for determinism). `maindeck_coverage`
falsy (`None` or `{}`) short-circuits the whole step — byte-identical to pre-change, verified both
by an explicit `element_weight`/`candidate_covers`/`warnings` equality test and by the fact the new
kwarg defaults to `None` so every pre-existing call site is unaffected.

**Judgment call — where the audit line lives.** The spec asked for a `// maindeck-aware: ...`
audit-echo line. Rather than adding a new `SideboardPackage` field + bespoke `cli.py` wiring (the
pattern used for genuinely new *rendered* surfaces like `natural_budget_count`/`marginal_curve`),
I appended it to `CoverageModel.warnings`, which `recommend_sideboard` already merges into
`pkg.warnings` — the exact mechanism every other `_build_coverage_model` construction-time note
uses (empirical-pool promotion warnings, no-hoser-for-tag warnings, etc.). This keeps the change
scoped to `sideboard.py` per the story's stated file, is fully exercised by
`tests/test_sideboard.py` alone, and is consistent with the "audit-echo comment lines" pattern
(text starts with `// `) even though the CLI's generic warnings loop wraps it in `[warn] ...` —
identical to how every other model-level warning is surfaced today. If a dedicated, unprefixed CLI
line is wanted later, that's a small follow-up to `cli.py`, not a design change here.

**Wiring.** `recommend_sideboard` builds `_card_by_name = {card.name: card for card in
deck_card_objects}` from the Step-1 `_load_deck_cards` resolution (no extra DB round-trip) and
calls `_maindeck_answer_coverage(deck_maindeck, _card_by_name.get, catalog=catalog)` right before
building the coverage model, passing the result as `maindeck_coverage=`.

**Byte-identical gating confirmed**: `TestBuildCoverageModelMaindeckDiscount
.test_maindeck_coverage_none_is_byte_identical` compares `element_weight`, `candidate_covers`, and
`warnings` across an omitted kwarg, an explicit `None`, and an explicit `{}` — all three equal.

**Tests** (`tests/test_sideboard.py`, 14 new, all passing):
- `TestMaindeckAnswerCoverage` (7): Wasteland catalog short-circuit, copy-count saturation
  (2/4 copies -> 0.5, 4 -> 1.0, 5 -> still 1.0), oracle-text derivation for non-catalog cards,
  fallback-attacks exclusion, unresolved-card skip, `_hate` exclusion, zero-copy defensive case.
- `TestBuildCoverageModelMaindeckDiscount` (5): byte-identical guard, exact-discount-factor check
  (with the audit line's exact text asserted), partial-coverage proportional discount, unrelated-tag
  no-op, `_hate:` pseudo-element exemption.
- `TestMaindeckAwareCoverageIntegration` (2): a `_build_coverage_model` + `_greedy_solve` test that
  reproduces the motivating bug directly — a Ghost-Quarter-style `greedy-manabase`-only candidate
  wins a 1-slot budget pre-discount, and loses that same slot to a still-undiscounted
  `storm-reliant` candidate once the maindeck already answers `greedy-manabase`; and a full
  `recommend_sideboard` DB-backed end-to-end wiring test (reusing `TestRedundancyDecay
  ._gy_field_corpus`) confirming the audit line appears only when maindeck answers are present and
  `covered_weight` scales by exactly `(1 - _MAINDECK_DISCOUNT)`.

**Verification**: `.venv/bin/python -m pytest -q` — 2433 passed (2419 pre-existing + 14 new), no
regressions, run time ~99s.

**Escape hatch**: not used — no genuine design gap in this story's own scope. The
`_derive_attacks_for_promoted` land-destruction mislabeling noted above is a pre-existing,
out-of-scope bug in an already-shipped unit; it doesn't block C1/C2's acceptance criteria (the
catalog-first branch sidesteps it for the literal Wasteland example) and has been called out here
rather than silently worked around.
