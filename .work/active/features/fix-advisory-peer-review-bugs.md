---
id: fix-advisory-peer-review-bugs
kind: feature
stage: drafting
tags: [advisory, bug]
parent: epic-advisory-hardening
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Advisory correctness bugs (cross-model peer review, Codex xhigh)

## Brief
A cross-model deep peer review (`agile-workflow:review --deep` → peeragent → Codex xhigh) of the advisory
pillar (`src/legacy_engine/advisory/*.py`) on 2026-05-30 surfaced concrete correctness bugs that the
same-model in-session reviews missed. No blockers; all verified against the code. Verdict: Approve with
comments. The peer confirmed the core methods are otherwise sound (observed-cell Beta params, Dirichlet
share sampling, mirror=0.5, normal exclude-mirror renormalization, ILP budget/copy bounds).

## Findings (verified, with fixes)

### Positioning (`positioning.py`)
1. **No-data imputation is NOT centered on the intended mean** (`positioning.py:163-164`). `a = 2·center +
   0.5`, `b = 2·(1−center) + 0.5` → posterior mean `(2c+0.5)/3`, so a known-mean-0.8 row imputes ~0.70, not
   0.80 (the Jeffreys +0.5 pulls toward 0.5). The comment claims "centred on `center`" — it isn't. **Fix:**
   concentration-only params (`a = strength·center`, `b = strength·(1−center)`, with an epsilon guard for
   center∈{0,1}), or document the extra shrink explicitly.
2. **`rank_decks` tie handling biases the first candidate** (`positioning.py:448`). `np.argmax(all_S, axis=1)`
   awards every tied-max draw to the lowest index → identical/empty-field candidates get `P(best)=1.0` vs
   `0.0`. **Fix:** split tied-max credit evenly across the tied set; consider half-credit ties in pairwise
   `P(a>b)` (`positioning.py:467`). *(Compounds [[improve-positioning-pbest-uneven-sample]].)*
3. **`include_mirror=False` returns `S=0.0` on a mirror-only field** (`positioning.py:182`). The renormalize
   zeroes the only column and `safe_sums` makes `S=0` — an undefined view reported as a 0% matchup. **Fix:**
   return 0.5 with a warning, or raise a clear `ValueError`.

### Sideboard (`sideboard.py`)
4. **Best-swing weight leaks dedicated-hate value to soft hosers** (`sideboard.py:321` weight, `:384`
   coverage). An archetype's element weight uses the best swing across all its tags, but any hoser overlapping
   *any* of its tags captures that full weight. **Fix:** model elements as `(archetype, tag)` or make gains
   card/tag-specific.
5. **`_hate:` pseudo-elements don't match the documented model** (`sideboard.py:347`). Created for every deck
   vulnerability tag at near-total field-share weight, and every `_hate` card covers every such tag — not
   `h_k = Σ share·P(opp sideboards hate k)`. Over-recommends Veil/Defense Grid/Carpet. **Fix:** tie
   pseudo-elements to actual field hate + specific counter-hoser coverage. *(Extends
   [[improve-sideboard-realdata-quality]].)*
6. **Catalog color gating is wrong for free/Phyrexian hosers** (`sideboard.py:85,92,374`). Surgical Extraction
   (Phyrexian black — castable for 2 life in any deck) and Faerie Macabre (free discard activation) are marked
   black-only, so non-black decks can't receive them. **Fix:** a castability flag / model alternate+free costs
   separately from color identity.

### What-to-play (`whattoplay.py`)
7. **`best_deck_vs_best_call` uses n<30 cells while the report claims "data-driven"** (`whattoplay.py:622`).
   Classification includes all `n>0` cells (incl. speculative), but `report` only checks that ≥1 cell is
   `n≥30` — so low-n cells can drive the label under a data-driven audit banner. **Fix:** filter to
   `cell.display`/`n≥30` for the classification, or report exactly which cells were used.

### Field (`field.py`)
8. **`_normalize_shares` doesn't reject NaN/inf** (`field.py:43`) — `float()` accepts `nan`/`inf` and they
   propagate into normalized shares. **Fix:** add `math.isfinite(share)` validation (nit).

## How to apply
Route through `/agile-workflow:fix` per bug (1, 2, 3, 6, 8 are small, clear fixes with regression tests);
4 and 5 are design refinements that fold into [[improve-sideboard-realdata-quality]]; 7 folds into the
report/whattoplay honesty work. All are accuracy fixes to the shipped advisory pillar — none block the
pillar's existing (test-green) behavior.

## Notes
Reviewer: peeragent → Codex (agent_session 019e7b60), effort xhigh, in-repo. Codex could not run pytest in
its sandbox (a local `pydantic_core` import mismatch — environment-specific, NOT a project issue; our `.venv`
suite is 581 green). Findings stand on code reading + line references, re-verified by the host.
