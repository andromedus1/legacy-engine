---
id: epic-sb-advisor-correctness-fourof-guard
kind: story
stage: done
tags: [advisory, bug]
parent: epic-sb-advisor-correctness
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-31
---

# Combined main+SB 4-of legality guard in recommend/considering paths


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

## Implementation notes

**Single chokepoint.** All three consumers of a candidate's copy limit — `_greedy_solve`,
`_ilp_solve`, and `_rank_considering_pool` — read `model.candidate_meta[name].max_copies`.
Capping at `candidate_meta` assembly inside `_build_coverage_model` therefore fixes the
solver path AND the considering/refill path with one rule, rather than patching the two
construction sites the story named (promoted `min(freq_map, 4)` and catalog `max_copies`)
separately and leaving a third path to drift.

**Mechanism.**
- `_maindeck_copy_caps(main_cards, get_card) -> {name: 4 - copies}` — pure, floored at 0,
  basics omitted entirely. Built once in `recommend_sideboard` from the already-resolved
  `deck_card_objects` (objective-search-split — the existing `maindeck_coverage` call right
  above it uses the same `_card_by_name.get` lookup, so no extra DB round-trip).
- `_build_coverage_model` gains a `maindeck_copy_caps` kwarg. Candidates are rewritten via
  `dataclasses.replace(hoser, max_copies=cap)`; a candidate with cap <= 0 is dropped outright.
  Applied at BOTH the catalog and promoted-candidate assembly points.
- Gated-additive: `maindeck_copy_caps` None/`{}` -> no-op -> byte-identical, matching the
  `maindeck_coverage` / `promoted_candidates` gating precedents in the same function.

**Element weights deliberately untouched.** The cap changes only which candidates exist and
how many copies each may contribute — not `element_weight`. How valuable answering a tag is
does not depend on how many copies THIS deck may still legally add. Capping weights too would
have silently changed the objective.

**Basics exemption** keys on the `Basic` supertype in `type_line`, not a hardcoded name list,
so snow-covered basics and Wastes are covered. An unresolvable card (`None` from the lookup)
is explicitly NOT treated as basic — a card missing from the DB must not silently bypass the
legality cap.

**Post-check backstop.** `_fourof_legality_warnings` re-checks the ASSEMBLED package and emits
`// ILLEGAL: <card> N main + M SB = T copies (max 4)` per offender into the existing
`SideboardPackage.warnings` tuple, which the CLI already renders as `[warn] ...`
(cli.py ~3269). Prefix style matches the sibling `// maindeck-aware:` audit lines
(audit-echo-comment-lines pattern). The candidate cap should make this unreachable; it exists
so that if any future path bypasses the cap, the user is told the board is illegal instead of
shipping a silently illegal list. Two `// 4-of guard: dropped/capped ...` audit lines report
when the cap actually binds.

**Tests** (18 new, in `TestMaindeckCopyCaps` / `TestFourOfLegalityPostCheck` /
`TestFourOfGuardIntegration`): 4-of maindeck card yields no 5th (board AND considering pool);
2-of capped at 2 more; 0-of unconstrained (control — proves the guard is not a blanket
suppressor); basics + snow basics exempt; nonbasic land not exempt; unresolvable card not
exempt; >4 maindeck floors at 0; post-check fires on a crafted illegal package, stays silent
at exactly 4 combined, exempts basics, reports multiple offenders; and a 0..4 sweep asserting
no maindeck count ever produces a combined-illegal recommendation.

Verified load-bearing by mutation: neutralizing the cap fails 4 of the 5 integration tests
(the 5th is the zero-maindeck control, which correctly still passes).

**Test re-pin.** `TestMaindeckAwareCoverageIntegration::
test_recommend_sideboard_wires_maindeck_coverage_end_to_end` used a deck running 4 maindeck
Reanimate while Reanimate was also a catalog candidate — the guard now correctly drops it, so
the run differed from its baseline by both the discount and the dropped candidate, and the
exact `covered_weight * (1 - _MAINDECK_DISCOUNT)` equality no longer held. The baseline call
now uses the same effective candidate set (`{Surgical Extraction}`), which isolates the
discount the test is actually about, plus a new assertion that no 5th Reanimate is offered.

**Not addressed (pre-existing, separate path):** `_matchup_plan`'s swap legality uses
`_max_copies_for(card) = max(catalog[card].max_copies, 4)` (sideboard.py ~2502), which bounds
post-board copies for the OUT/IN swap planner. That path already enforces a per-card post-board
ceiling and was not among the two reported illegal-board instances, so it is left alone rather
than folded into this guard.
