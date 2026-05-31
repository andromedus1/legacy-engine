---
id: fix-advisory-peer-review-bugs
kind: feature
stage: done
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

## Design (autopilot, 2026-05-30)
Single-stride: apply each documented finding's specified fix with a focused regression test. No new
architecture. Ordering note: this lands before `improve-positioning` (which builds on the #2 tie fix) and
`improve-sideboard` (which builds on the #6 Surgical/Faerie color fix). Finding #7 applies to the
just-reworked `whattoplay.best_deck_vs_best_call`.

## Implementation notes

**Files touched:**
- `src/legacy_engine/advisory/positioning.py` — fixes 1, 2, 3
- `src/legacy_engine/advisory/sideboard.py` — fixes 4, 5, 6
- `src/legacy_engine/advisory/whattoplay.py` — fix 7
- `src/legacy_engine/advisory/field.py` — fix 8
- `tests/test_positioning.py` — 3 regression tests (fixes 1, 2, 3)
- `tests/test_sideboard.py` — 3 regression tests (fixes 4, 5, 6); 5 existing tests updated for schema change
- `tests/test_whattoplay.py` — 2 regression tests (fix 7)
- `tests/test_field_model.py` — 4 regression tests (fix 8)

**Test count:** 611 before → 623 after (12 new regression tests). All green.

**Per-finding status:**

1. **Done.** Concentration-only params `a=max(_NODATA_STRENGTH*center, eps)`, `b=max(_NODATA_STRENGTH*(1-c), eps)` so E[Beta]=center. Tested: known-mean-0.8 row imputes ≈0.8 (±0.05).
2. **Done.** Replaced `np.argmax` with row-max boolean mask + tie-fractional credit. Pairwise also updated to half-credit ties. Tested: two identical candidates → P(best)≈0.5 each.
3. **Done.** Detect all-zero row_sums after mirror zeroing; return `np.full(n_draws, 0.5)` with `log.warning`. Tested: mirror-only field + include_mirror=False → S=0.5, not 0.0.
4. **Done.** Replaced flat-archetype element keys with `"archetype|tag"` pairs so each hoser captures only the weight of the specific tags it attacks. 5 existing tests updated for new key scheme.
5. **Done.** Replaced near-total-field-share weight with interactive-field-share (archetypes not tagged `low-interaction`) × `_SWING_SOFT`. Tested: half-low-interaction field → hate weight ≈ half field share × swing.
6. **Done.** Added `castable_any_color: bool = False` field to `HoserCard`; set `True` for Surgical Extraction (Phyrexian mana) and Faerie Macabre (free activation). Color pre-filter bypassed when `castable_any_color=True`. Tested: all-white deck includes both cards.
7. **Done.** Added `cell.display` guard (n≥30) before including a cell in `best_deck_vs_best_call` classification. Low-n cells are counted but skipped with `log.debug`. Tested: row with only n=10 cells → "neither", row with n=100 → classifies correctly.
8. **Done.** Added `math.isfinite(share)` check before the `<0` check in `_normalize_shares`. Tested: nan, +inf, -inf each raise `ValueError` with "non-finite".

## Review (2026-05-30, autopilot)
**Verdict**: Approve. All 8 findings fixed with a regression test each (623 green, +12). Host-verified:
imputation now centers correctly (known-0.8 row → S=0.799, was de-centering ~0.70); `castable_any_color`
True for Surgical/Faerie, False for normal-cost Leyline; rank_decks ties split evenly; `_normalize_shares`
rejects NaN/inf; sideboard coverage keys are now `(archetype, tag)`-specific; `_hate` weight tied to
interactive field-share; best_deck_vs_best_call gated to n>=30. Provides the tie fix (#2) and catalog
color fix (#6) that improve-positioning and improve-sideboard build on.
