---
id: fix-spine-peer-review-findings
kind: feature
stage: drafting
tags: [ingestion, archetype, bug]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Ingestion + archetype-spine findings (cross-model peer review, Codex xhigh)

## Brief
Cross-model deep peer review (peeragent → Codex xhigh, ran the suite: 92 passed) of the ingestion +
archetype spine on 2026-05-30. No blockers; verified against code + the ingestion-archetype-contracts
briefs. Sound areas confirmed: `parse_rounds` flat/nested shapes, null-bye coercion, per-URI
`load_tournament` idempotency, `banlist_as_of` `<=` boundary, fail-fast unknown condition types + lenient
trailing-comma loading, `compute_deck_colors` model.

## Findings

### Classifier faithfulness (affects label accuracy)
1. **Variant `IncludeColorInName=false` overridden by a color-prefixed parent** (`matcher.py:90`) via
   `v.include_color_in_name or arch.include_color_in_name` — mislabels rules like Delver's `Temur Delver`
   variant. **Fix:** use the variant's own flag when a variant matches.
2. **Conflict labels lose color prefixes** (`matcher.py:100`) — built from raw names, sorted+deduped.
   **Fix:** build `Conflict(...)` from each match's final `_label(...)`, preserve matcher order.
3. **Fallback scoring diverges from the Badaro contract** (`matcher.py:117`) — uses maindeck only and divides
   by total maindeck copies; the contract scores main+side and divides by *distinct deck entries*. Can turn
   valid fallback decks into `Unknown`. **Fix:** pass sideboard into `_fallback`; match the documented
   denominator. *(Could reduce the ~4.7% unresolved rate.)*
4. **Condition semantics not fully faithful** (`matcher.py:43`) — `In*`/`DoesNotContain*` use all `Cards`
   while Badaro uses `Cards[0]`; empty `Cards` should be skipped; `TwoOrMoreInMainOrSideboard` should count a
   card in both zones as two hits. Latent (current vendored rules don't exercise the multi-card single-card
   types) but a contract gap. **Fix:** align to the rule-schema brief.

### Reproducibility / completeness
5. **`refresh_rules` doesn't pin to an input SHA** (`rules_vendor.py:30`) — records whatever HEAD was
   cloned/pulled. **Fix:** fetch/checkout a configured SHA and fail if unresolvable (true pinning).
6. **`_coerce_format` on a multi-format list picks the first** (`cache.py:78`) — `["Modern","Legacy"]` →
   `"Modern"`, so discovery skips the event. **Host-verified: zero impact on the current cache (no
   multi-format list entries), so no Legacy events were dropped** — but latent. **Fix:** normalize Formats to
   a collection and test membership for `"Legacy"`.

### Validation
7. **`validate_deck` never enforces `CATEGORY_BANS` and accepts nonpositive counts** (`banlist.py:107`) —
   an ante card not name-listed, or `{"Brainstorm": -1}`, produces no error. **Fix:** validate counts > 0;
   enforce category bans (needs card metadata for category predicates, or name-enumerate).

### Nits
8. **Scryfall name normalization is incomplete** (`scryfall.py:34`) — handles curly apostrophes but not
   Unicode/accents, and index keys aren't normalized; `card_faces[].name` isn't indexed. Risks resolution
   misses for accented names (e.g. "Khazad-dûm", "Æther"). **Fix:** Unicode-normalize keys + lookups; index
   face names.
9. **Fallback `tournament_id` can collide** (`store.py:111`) for no-URI events sharing source/name/date —
   full-refresh deletes then merge events. **Fix:** include file path or a content/player-set hash when URI
   is absent.

## How to apply
Classifier faithfulness (1–4) most affects label quality; route through `/agile-workflow:fix` with rule-based
regression tests grounded in the rule-schema brief. 5 (SHA pinning) and 7 (validate_deck) are correctness;
6/8/9 are latent/edge hardening.

## Design decisions
Captured via `/feature-design --only-questions` (interactive, 2026-05-30). These are fixed inputs for the
full design + implement pass — autopilot inherits them and should not re-decide.

- **Finding #1 (variant color flag)** — no fork; straight contract fix. When a variant matches, use the
  variant's own `include_color_in_name` (replace `v.include_color_in_name or arch.include_color_in_name`
  at `matcher.py:90` with `v.include_color_in_name`). Contract: label is color-prefixed iff the *matched*
  entry's flag is set (matching-algorithm brief line 25).
- **Finding #2 (Conflict label) → Contract-faithful.** Build `Conflict(...)` from each match's final
  color-prefixed `_label(...)`, in matcher (ruleset) order, **no sort, no dedupe** — exactly Badaro's
  `Conflict({String.Join(",", matches.Select(m => GetArchetype(m, color)))})` (brief line 123).
  *Implication:* existing `Conflict(...)` analytics keys change (raw sorted → color-prefixed ruleset-order).
  Acceptable — faithfulness is the feature's purpose. A re-label of stored data picks up the new keys; flag
  in implementation notes that downstream analytics reading old Conflict keys should expect the change.
- **Finding #3 (fallback math) → Full fidelity, including the quirk.** Pass sideboard into `_fallback`;
  weight = sum of *copies* of distinct main+side entries present in a pile's `common_cards`; **denominator =
  number of distinct deck entries (main+side rows), NOT total copies** (brief lines 201-204). This replicates
  Badaro's row-count denominator and shifts the effective 0.10 threshold semantics. `> MIN_FALLBACK_SIMILARITY`
  stays strict `>`.
- **Finding #4 (latent condition semantics) → Fix now, with regression tests.** Align all of
  `evaluate_condition` to the rule-schema brief even though no current vendored rule exercises these:
  single-card types (`InMainboard`/`InSideboard`/`InMainOrSideboard`/`DoesNotContain*`) use `Cards[0]` only;
  empty `Cards` lists are skipped (treated as non-constraining / no match per brief); `TwoOrMoreInMainOrSideboard`
  counts a card present in both zones as **two** hits (sum main-entry count + side-entry count, brief lines
  107-109) rather than `>= 2` over `main | side`. Cover with synthetic-ruleset regression tests grounded in
  the rule-schema brief.
- **Scope → All 9 findings, split into child stories.** Group as: **classifier** (1-4, the label-accuracy
  core), **correctness** (5 SHA-pinning `rules_vendor.py`, 7 `validate_deck` counts>0 + CATEGORY_BANS), and
  **hardening** (6 multi-format `_coerce_format`, 8 Scryfall Unicode/face-name normalization, 9 fallback
  `tournament_id` collision). Declare `depends_on` only where real (likely none cross-group; classifier
  stories may share the matcher edit and should serialize). Trickiest unit = finding #3 (fallback denominator
  + main/side threading) — design it first in the full pass.

## Notes
Reviewer: peeragent → Codex (session 019e7b6d-79db), effort xhigh, in-repo; ran the spine test subset
(92 passed). Companion: [[fix-analytics-peer-review-findings]], [[fix-advisory-peer-review-bugs]].
