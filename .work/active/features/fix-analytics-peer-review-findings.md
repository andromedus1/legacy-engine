---
id: fix-analytics-peer-review-findings
kind: feature
stage: drafting
tags: [analytics, bug]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Analytics correctness findings (cross-model peer review, Codex xhigh)

## Brief
Cross-model deep peer review (peeragent → Codex xhigh, ran the suite: 219 passed) of the analytics pillar
on 2026-05-30. No blockers; all verified against code (and several host-re-verified for data impact).
Sound areas confirmed: Wilson/Jeffreys selection, Beta-Binomial shrinkage, n=0 + n<30 gate, half-open ISO
date windowing (incl. full timestamps), chart low-n masking + empty-input handling.

## Findings

### Data-integrity (highest priority)
1. **Rounds↔decks join is not cardinality-safe** (`match_results.py:190`). Duplicate *normalized* player
   names within a tournament multiply one pairing into multiple match rows (Codex repro: one round →
   `total_pairings=2`, two wins). **Host-verified impact: 330/2449 tournaments (13%) have duplicate
   normalized player names (444 extra decks)** — so reported matchup-n's are mildly inflated where dups
   occur (qualitative conclusions hold; exact n's run slightly high). **Fix:** join via a per-tournament
   unique-normalized-player CTE; surface ambiguous names in coverage. Apply the same to the top-cut player join.

### Correctness / contract
2. **Mirror matches inflate row-inclusion inconsistently** (`matchup.py:181`). Mirrors are in
   `mr.archetypes[a].n` but excluded from `total_matches`, so `build_matrix` row inclusion uses a
   numerator/denominator mismatch (mirror-only corpus → `total_matches=0` yet archetype still included).
   **Fix:** either include `mirror_matches` in the denominator/headline or exclude mirror marginals from
   row inclusion.
3. **Top-cut silently hides NULL-archetype decks** (`metashare.py:359`). `_TOPCUT_SQL` excludes NULLs then
   the branch forces `unlabeled=0` (repro: 1 labeled + 1 NULL top-cut deck → `total=1, unlabeled=0`).
   **Fix:** a top-cut-specific unlabeled count over the same standings/rank/window join.
4. **`_assemble(group_other=False)` ignores `display_total`** (`metashare.py:259`). `compute_metashare(
   definition="wrw", group_other=False)` reports `total_decks=1` instead of matchup-n. **Fix:** honor
   `display_total` in the non-grouped return path. *(Note: `advisory.build_global_field` uses raw+group_other
   =False, not wrw, so the field model is unaffected today.)*
5. **WRW drops zero-match archetypes with only a debug log** (`metashare.py:149`), then renormalizes —
   the excluded share isn't surfaced (bimodal-coverage contract). **Fix:** surface `excluded_no_match_data`
   or explicit zero-match entries.
6. **`blend_shares` discards "Other" before renormalizing** (`metashare.py:459`) → inflates named archetypes
   (A=80%/Other=20% → A=100%); also **division-by-zero when all weights are zero** (`metashare.py:451`).
   **Fix:** preserve "Other" (or require ungrouped inputs + re-bucket after) and validate weight-sum > 0.
7. **Byes miscategorized as `unmatched`** (`match_results.py:224`). After the null-Player2 fix, a bye
   (`player2="", result="2-0"`) is counted `unmatched=1` rather than `dropped_byes_draws`. **Fix:** classify
   blank-opponent byes before join-failure coverage. *(Follows from [[fix-roundmatch-null-player2]].)*

### Nit
8. **Top-cut trends keep zero-denominator regimes** (`trends.py:213`) — `_window_event_stats` counts all
   tournaments before `compute_metashare`, so a regime with events but no top-cut decks survives. **Fix:**
   for topcut, skip regimes where the report `total_decks == 0` (or stat over standings-bearing events).

## How to apply
1 (cardinality) and 2 (mirror inclusion) first — they affect the matchup data's accuracy. Route concrete
bugs (1,2,3,4,6,7) through `/agile-workflow:fix` with regression tests; 5 + 8 are coverage/edge refinements.

## Notes
Reviewer: peeragent → Codex (session 019e7b6d-79f6), effort xhigh, in-repo; ran the analytics test subset
(219 passed). Companion: [[fix-spine-peer-review-findings]], [[fix-advisory-peer-review-bugs]].
