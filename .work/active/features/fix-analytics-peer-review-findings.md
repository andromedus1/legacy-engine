---
id: fix-analytics-peer-review-findings
kind: feature
stage: implementing
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

## Design decisions
Captured via `/feature-design --only-questions` (interactive, 2026-05-30). Fixed inputs for the full design +
implement pass — autopilot inherits them and should not re-decide.

- **Finding #1 (cardinality-safe join) → Skip the confusing ones.** Join rounds↔decks only where the
  normalized player name (`lower(trim(...))`) is **unique within the tournament**: build a per-tournament
  unique-normalized-player CTE and join through it; pairings whose name is ambiguous drop out of the matchup
  data and are counted in coverage (e.g. `ambiguous_player_names` / surfaced count). No mis-attribution; n's
  fall slightly where collisions occur (~13% of events). Apply the **same fix to the top-cut player join**.
- **Finding #2 (mirror row inclusion) → Count mirrors on both sides.** Make the inclusion denominator
  `2 * (decisive_matched + mirror_matches)` so the numerator (which already includes each archetype's mirror
  credits in `.n`) and the denominator both count mirror involvement. Aligns with the existing design that
  credits mirrors to `.n` for honest marginal win-rate. Mirror-only corpus no longer yields an included row
  with `total_matches=0`.
- **Finding #3 (top-cut NULL-archetype) → fold in (no fork).** Add a top-cut-specific unlabeled count over
  the same standings/rank/window join, instead of forcing `unlabeled=0` (`metashare.py:359`).
- **Finding #4 (`_assemble` ignores `display_total`) → fold in (no fork).** Honor `display_total` in the
  `group_other=False` return path (`metashare.py:259`).
- **Finding #5 (WRW drops zero-match archetypes silently) → fold in.** Surface the excluded share as
  coverage metadata (`excluded_no_match_data`) consistent with the bimodal-coverage contract, rather than
  only a debug log (`metashare.py:149`).
- **Finding #6 (`blend_shares`) → Keep 'Other' in the mix.** Preserve the 'Other' bucket in the share vector
  and renormalize including it, so named shares aren't inflated (`metashare.py:459`). **Also** guard
  weight-sum `> 0` to fix the divide-by-zero (`metashare.py:451`). Caller contract unchanged.
- **Finding #7 (byes miscategorized) → fold in (no fork).** Classify blank-opponent byes
  (`player2="", result="2-0"`) as `dropped_byes_draws` before the join-failure/unmatched coverage branch
  (`match_results.py:224`). Follows [[fix-roundmatch-null-player2]].
- **Finding #8 (top-cut trends zero-denominator) → fold in (no fork).** For topcut trends, skip regimes whose
  report `total_decks == 0` (`trends.py:213`).
- **Scope → All 8 findings, split into child stories.** Group as **data-integrity** (1), **correctness/contract**
  (2-7), **nit** (8), with `depends_on` only where real. Trickiest unit = **#1** (unique-player CTE + threading
  it through both the rounds join and the top-cut join) — design it first in the full pass.

## Architectural choice

**Fix-in-place, contract-faithful, split by disjoint file-group into 3 independently-implementable stories.**
Like the spine findings, these are localized corrections to existing analytics functions. The decisions in
`## Design decisions` lock the three forks (#1 skip-confusing, #2 mirrors-both-sides, #6 keep-Other); the
rest are unambiguous fixes. File ownership is disjoint, so all three stories carry `depends_on: []`:

- **data-integrity** (#1 rounds-join + #7 byes) → `analytics/match_results.py` (+ `MatchCoverage`, same file)
- **metashare-correctness** (#1 topcut-join, #3, #4, #5, #6) → `analytics/metashare.py` (+ `MetaShareReport`, same file)
- **matchup+trends** (#2, #8) → `analytics/matchup.py` + `analytics/trends.py`

Rejected alternative: split by concern (data-integrity vs correctness vs nit). Rejected because #1 spans two
files (the rounds join in `match_results.py` and the top-cut join in `metashare.py`) — splitting by file
keeps each story's edits in one module with one test file, enabling parallel implementation with zero merge
risk. #2 (matchup) only reads existing `MatchCoverage` fields, so it does not depend on the #1 work.

## Implementation Units

### Unit 1: Cardinality-safe rounds join + ambiguous coverage (finding 1, rounds half)

**File**: `src/legacy_engine/analytics/match_results.py`
**Story**: `fix-analytics-peer-review-findings-data-integrity`

```python
# MatchCoverage: add a counter (invariant becomes total_pairings == decisive_matched + unmatched
#                + dropped_byes_draws + mirror_matches + ambiguous_player_names)
ambiguous_player_names: int = 0   # pairing excluded: a player's normalized name is non-unique in its tournament

# _JOIN_SQL: flag whether each player's normalized name is ambiguous (appears >1x) within the tournament.
_JOIN_SQL = """
WITH dup AS (
    SELECT tournament_id, lower(trim(player)) AS norm
    FROM decks
    GROUP BY tournament_id, lower(trim(player))
    HAVING count(*) > 1
)
SELECT t.provenance, r.player1, r.player2, r.result,
       d1.archetype AS arch1, d2.archetype AS arch2,
       (du1.norm IS NOT NULL) AS amb1, (du2.norm IS NOT NULL) AS amb2
FROM rounds r
JOIN tournaments t ON t.id = r.tournament_id
LEFT JOIN decks d1 ON d1.tournament_id = r.tournament_id AND lower(trim(d1.player)) = lower(trim(r.player1))
LEFT JOIN decks d2 ON d2.tournament_id = r.tournament_id AND lower(trim(d2.player)) = lower(trim(r.player2))
LEFT JOIN dup du1 ON du1.tournament_id = r.tournament_id AND du1.norm = lower(trim(r.player1))
LEFT JOIN dup du2 ON du2.tournament_id = r.tournament_id AND du2.norm = lower(trim(r.player2))
WHERE (? IS NULL OR t.provenance = ?)
"""
```

```python
# Accumulator loop — classify byes (#7) and ambiguous names (#1) before the unmatched/match logic.
for _prov, p1, p2, result, arch1, arch2, amb1, amb2 in rows:
    cov.total_pairings += 1
    if not (p2 and str(p2).strip()):          # #7: blank-opponent bye is not a real pairing
        cov.dropped_byes_draws += 1
        continue
    if amb1 or amb2:                           # #1: ambiguous normalized name → cannot attribute deck
        cov.ambiguous_player_names += 1
        continue
    if arch1 is None or arch2 is None:
        cov.unmatched += 1
        continue
    ...                                        # existing decisive / mirror logic unchanged
```

**Implementation Notes**:
- Ambiguous-name check comes before the `arch1/arch2 is None` check so a collision is reported as
  `ambiguous_player_names`, not `unmatched`. Bye check comes first of all (a bye has no real opponent).
- Update the `MatchCoverage` docstring invariant and any test asserting the counter sum.

**Acceptance Criteria**:
- [ ] A tournament with two players sharing a normalized name no longer double-counts the pairing; those rows land in `ambiguous_player_names`.
- [ ] `total_pairings == decisive_matched + unmatched + dropped_byes_draws + mirror_matches + ambiguous_player_names`.
- [ ] A bye (`player2=""`, `result="2-0"`) is counted `dropped_byes_draws`, not `unmatched`.

### Unit 2: Cardinality-safe top-cut join + coverage fixes (findings 1 top-cut half, 3, 4, 5, 6)

**File**: `src/legacy_engine/analytics/metashare.py`
**Story**: `fix-analytics-peer-review-findings-metashare`

```python
# #1 (top-cut half): exclude ambiguous normalized names from the decks↔standings join, same dup-CTE shape.
_TOPCUT_SQL = """
WITH dup AS (SELECT tournament_id, lower(trim(player)) AS norm FROM decks
             GROUP BY tournament_id, lower(trim(player)) HAVING count(*) > 1)
SELECT d.archetype AS archetype, count(*) AS n
FROM decks d
JOIN tournaments t ON t.id = d.tournament_id
JOIN standings s ON s.tournament_id = d.tournament_id AND lower(trim(s.player)) = lower(trim(d.player))
LEFT JOIN dup du ON du.tournament_id = d.tournament_id AND du.norm = lower(trim(d.player))
WHERE d.archetype IS NOT NULL AND du.norm IS NULL          -- drop ambiguous names
  AND s.rank <= ? AND (? IS NULL OR t.provenance = ?) AND (? IS NULL OR t.date >= ?) AND (? IS NULL OR t.date < ?)
GROUP BY d.archetype
"""

# #3: top-cut-specific unlabeled count over the same join (archetype IS NULL, same dup-exclusion + window).
def _topcut_unlabeled(con, *, provenance, cut_size, since, until) -> int: ...
# topcut branch: unlabeled=_topcut_unlabeled(...) instead of hardcoded 0.

# #4: non-grouped return path honors display_total (parity with the grouped path / line 292).
if not group_other:
    return MetaShareReport(..., total_decks=display_total if display_total is not None else total, ...)

# #5: surface archetypes with deck-count-but-no-match-data on the report.
#   MetaShareReport gains: excluded_no_match_data: list[str] = field(default_factory=list)
#   _wrw_weights returns the excluded names; the wrw branch passes them through.

# #6: blend_shares — guard zero weight-sum + keep "Other" in the blend.
if weight_sum <= 0:
    raise ValueError(f"blend_shares: weights sum to {weight_sum}; need a positive total")
...
for entry in report.entries:
    all_archetypes.add(entry.archetype)          # was: if entry.archetype != "Other"  → keep Other
```

**Implementation Notes**:
- `excluded_no_match_data` defaults empty and is only populated for `wrw`; raw/topcut leave it `[]`.
- Keeping "Other" in `all_archetypes` means it blends like any archetype, so named shares are no longer
  inflated by the dropped Other mass. Verify the blended-report assembly treats "Other" as a normal entry.

**Acceptance Criteria**:
- [ ] Top-cut counts no longer inflate from duplicate normalized names; ambiguous names are excluded.
- [ ] A top-cut window with 1 labeled + 1 NULL-archetype deck reports `total_decks=1, unlabeled=1`.
- [ ] `compute_metashare(definition="wrw", group_other=False)` reports `total_decks` = matchup-n, not 1.
- [ ] A wrw archetype with deck count but zero match data appears in `excluded_no_match_data`.
- [ ] `blend_shares` with A=80%/Other=20% keeps Other at ~20% (named shares not inflated to 100%).
- [ ] `blend_shares` with all-zero weights raises `ValueError`, not `ZeroDivisionError`.

### Unit 3: Mirror inclusion + top-cut trends denominator (findings 2, 8)

**File**: `src/legacy_engine/analytics/matchup.py`, `src/legacy_engine/analytics/trends.py`
**Story**: `fix-analytics-peer-review-findings-matchup-trends`

```python
# #2 matchup.py: count mirrors on both sides of the inclusion ratio.
total_matches = mr.coverage.decisive_matched
denom = 2 * (total_matches + mr.coverage.mirror_matches) if (total_matches + mr.coverage.mirror_matches) > 0 else 1
# (numerator mr.archetypes[a].n already includes mirror credits → now consistent.)

# #8 trends.py: for top-cut, skip regimes whose report has no top-cut decks.
#   after computing the per-regime report: if definition == "topcut" and report.total_decks == 0: skip regime.
```

**Implementation Notes**:
- #2: update the matchup row-inclusion docstring to state the denominator now includes mirror matches.
- #8: the skip must use the *report's* `total_decks` (top-cut decks), not `_window_event_stats` event count,
  so a regime with events but no top-cut standings is dropped.

**Acceptance Criteria**:
- [ ] A mirror-only corpus no longer yields an included archetype row with `total_matches=0`.
- [ ] Row inclusion ratio uses `2*(decisive_matched + mirror_matches)` as the denominator.
- [ ] A top-cut trends regime with in-window events but zero top-cut decks is skipped, not kept with a zero denominator.

## Implementation Order

1. **Unit 1 (data-integrity)** — trickiest: the dup-CTE + ambiguous-name flagging and the reordered
   classify loop. Build and test this first; the CTE shape is reused in Unit 2.
2. **Unit 2 (metashare)** — independent file; reuses the dup-CTE pattern from Unit 1.
3. **Unit 3 (matchup+trends)** — independent; reads only existing coverage fields.

## Testing

### Unit tests
- `tests/test_match_results.py` — synthetic rounds/decks with a duplicate normalized name (ambiguous bucket),
  a blank-opponent bye (dropped_byes_draws), and the full coverage-sum invariant.
- `tests/test_metashare.py` — top-cut dup exclusion; topcut unlabeled count; wrw `group_other=False`
  total_decks; wrw `excluded_no_match_data`; `blend_shares` Other-preservation + zero-weight guard.
- `tests/test_matchup.py` — mirror-only corpus inclusion; denominator includes mirror_matches.
- `tests/test_trends.py` — top-cut regime with events but no top-cut decks is skipped.

### Integration points
- `advisory.build_global_field` uses `raw + group_other=False` (not wrw), so the #4 fix does not change the
  field model — confirm via the existing advisory tests staying green.
- The matchup denominator change (#2) shifts which archetypes clear `min_row_share`; verify matrix tests.

## Risks

- **Matchup-n drop from ambiguous exclusion** (#1): excluding ~444 decks across 330 events slightly lowers
  reported matchup-n where collisions occur. **Fallback**: this is the decided correctness-safe behavior;
  the `ambiguous_player_names` counter makes the drop visible rather than silent.
- **Mirror denominator shifts row inclusion** (#2): a few borderline archetypes may drop below
  `min_row_share`. **Fallback**: decided behavior (consistency over inclusion); surface via matrix tests.
- **Shared models in same file**: `MatchCoverage` (Unit 1) and `MetaShareReport` (Unit 2) live in their
  respective analytics modules — disjoint, so the three stories never edit the same file. Orchestrator can
  run them in parallel.

## Notes
Reviewer: peeragent → Codex (session 019e7b6d-79f6), effort xhigh, in-repo; ran the analytics test subset
(219 passed). Companion: [[fix-spine-peer-review-findings]], [[fix-advisory-peer-review-bugs]].
