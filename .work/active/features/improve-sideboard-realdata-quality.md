---
id: improve-sideboard-realdata-quality
kind: feature
stage: drafting
tags: [advisory]
parent: epic-advisory-hardening
depends_on: [improve-whattoplay-proactivity-threat-signal]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Sideboard recommender under-delivers on real data (budget under-fill + tag inflation)

## Brief
Running `recommend_sideboard` for Dimir Tempo and Energy against the current real field (174 events)
exposed three compounding issues that make the output non-actionable today:

1. **Budget under-fill.** Binary max-coverage stops once each vulnerability tag is covered once (marginal
   gain → 0), so the ILP returned **2 cards of a 15-slot budget**. With only ~7 vulnerability tags the
   objective saturates immediately. The saturating `g(n)=1-(1-p)^n` redundancy model (deferred in the
   original design) is now clearly *required*, not optional — without it the recommender can't fill a board.
2. **Vulnerability-tag inflation.** `greedy-manabase` hate-equity reads **100%** of the field because the
   presence-threshold tags fire on nearly every archetype aggregate (the same root cause as
   [[improve-whattoplay-proactivity-threat-signal]] — switch presence → density/share threshold).
3. **Coarse catalog + heuristic swings → incoherent picks.** It recommended Wasteland to a deck already
   maindecking 4, and counter-hosers (Defense Grid) that don't fit the deck's plan. The curated
   `HOSER_CATALOG` is small/generic and swings are flat constants.

## How to apply
- Implement the **saturating coverage** objective so additional copies/answers add diminishing-but-positive
  value and the recommender fills the budget (the ILP linearization with incremental `y_a^t`, per
  advisory-methods §3).
- Fix vulnerability tags to **density/share thresholds** (depends-on the whattoplay item) so hate-equity
  stops saturating at 100%.
- Exclude cards already in the deck's maindeck from candidates; expand + de-genericize the catalog;
  consider empirical swing once before/after-board data is modeled.
- Validate against the real corpus: a recommended board should fill ~15 slots with archetype-appropriate,
  field-weighted answers.

## Foundation references
- `docs/briefs/advisory-methods.md` — §3 (saturating value, ILP shape, anti-hate).
- Source: `src/legacy_engine/advisory/sideboard.py`. Related: [[improve-whattoplay-proactivity-threat-signal]],
  [[improve-positioning-pbest-uneven-sample]].

## Notes
Discovered via real-data use 2026-05-30. The shipped pillar's *structure* is sound (meta-share + matchup
matrix are reliable); these are accuracy/usability gaps in the advisory heuristic + coverage layers. Route
through `/feature-design` (greenfield-ish: new saturating objective + threshold changes + recalibration).

## Design decisions (--only-questions, 2026-05-30)
- **Coverage model = full saturating `g(n)=1−(1−p)^n`** (user-directed) — diminishing-but-positive value
  for redundant answers, so the ILP/greedy fills the 15-slot budget principledly (the binary-coverage
  underfill that returned only 2/15 is the n=1 degenerate case). Implement the incremental-`y_a^t`
  linearization for the ILP per advisory-methods §3; greedy uses the same saturating marginal gain.
- Still depends on [[improve-whattoplay-proactivity-threat-signal]] (density-threshold vulnerability tags)
  to fix the `greedy-manabase=100%` tag inflation feeding the weights, and on the catalog color-gating fix
  in [[fix-advisory-peer-review-bugs]] (Surgical/Faerie castable in any deck).
