---
id: feature-regime-windowing-consistency
kind: feature
stage: implementing
tags: [analytics, advisory, methodology]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

**Methodology principle, not just a per-command behavior:** every analytical surface must analyze
data correctly with respect to ban regimes, so tuning reflects the **current** meta and not a stale
pre-ban field.

The engine already has pieces of this:
- `epic-regime-aware-advisory` — `--regime`, adaptive per-cell matchup windows, thin-regime degrade
  banners on advise/report surfaces.
- `idea-consensus-window-consistency` — narrow: consensus's default window (latest ban-regime) vs the
  matchup engine's adaptive window can disagree, so a generated list and its matchup numbers come from
  different slices.

**Broaden into a project-wide principle + checklist:** EVERY surface (`report meta/trends/matchups/
cards/gaps/tiers`, `generate consensus/tune`, all `advise` commands) should (a) default to
ban-regime-aware windowing, (b) use consistent window-resolution semantics across commands, and
(c) loudly state its window + thinness in output. Document it as a methodology principle (a doc /
PRINCIPLES entry), and audit each surface against the checklist — don't just trust per-command code.

**Live example motivating this:** on 2026-06-13 the current regime "after Undercity Informer
(2026-05-18)" is only ~22 days old / 61 events / ~56 Dimir Tempo decks. A naive all-corpus read
would badly misrepresent today's meta (e.g. Dimir Tempo shows 9.0% in the prior regime vs 4.0% now;
Tron 2.2% → 9.1%). Also note: the strongest reference decklists in the corpus (Mengucci, BoshNRoll)
are all from the PRIOR regime — so "copy a pro list" silently imports stale-regime tuning unless the
regime gap is surfaced.

**Specific item found this session:** the `advise sideboard` per-matchup OUT/IN plans were stuck at
"speculative, n≥0" for nearly every opponent in the thin current regime — because those plans do NOT
use the adaptive ban-aware window that the matchup *matrix* already uses (per-cell `valid_since`).
Extend the adaptive window to the sideboard matchup plans so they borrow prior-regime depth the same
way the matrix does, instead of going dark in a fresh regime. Until then, sideboard in/out guidance is
reasoning-based, not data-derived — which should be stated honestly.

Related: [[idea-consensus-window-consistency]].

---

## Design

### Scope & decomposition

Single feature, three implementation units, no child stories. The work is cohesive (one principle +
two small, related code touches) and fits one stride. The audit is a checklist + targeted assertions,
not a sprawling refactor — every surface already routes through `resolve_advisory_window` /
`build_advisory_inputs` or the consensus/sideboard window helpers, so this is about *aligning defaults
and labels*, not rebuilding plumbing.

Decision (logged): I considered splitting the sideboard fix into its own child story (it has the most
code), but it shares the `valid_since`/`mr_by_since` mechanism with the audit's "adaptive everywhere"
principle and the same tests exercise both — splitting would duplicate grounding. Kept as one unit.

### Windowing principle (the SSOT this feature establishes)

**Ban-regime-aware windowing is the default for every analytical surface, and every surface loudly
states its window + thinness.** Three legal window modes, one selection rule:

- **adaptive** (matrix/matchup/positioning/gaps/sideboard-plans): per-cell ban-aware window — each
  archetype pools data back to its `valid_since` (latest materially-affecting ban; full history if
  unaffected), field leg = current regime. Dead decks fall out via ≈0 current share; live matchups
  borrow prior-regime depth instead of going dark. This is `build_adaptive_matrix`'s model, and it is
  now the model the sideboard plans use too.
- **uniform** (`--regime`/`--since`/`--until`): one explicit window on both legs; degrades to full
  corpus + loud banner when thinner than `_THIN_ROUNDS_FLOOR`.
- **full** (`--all-time`, or deck-based descriptive surfaces via `thin_floor=0`): full corpus;
  thinness conveyed by per-row confidence tiers, not a rounds-degrade.

Selection rule: `all_time > regime > since/until > default`. The default is **adaptive** for
matrix-consumers and **full** for deck-based descriptive surfaces (`report meta`), each labeled.

### Surface audit (checklist — assert each, fix drift)

| Surface | Window today | Correct? | Action |
|---|---|---|---|
| `report meta` | full (deck-based, `thin_floor=0`) | yes — tiers convey thinness | assert label echoed |
| `report trends` | per-regime partition + thin cap to `evolving` | yes | assert thin banner present |
| `report matchups` | adaptive default via `build_advisory_inputs` | yes | assert `_echo_window` + adaptive audit |
| `report cards` | `_latest_regime_window()` uniform | **inconsistent** — uniform, not adaptive; goes thin in fresh regime | see note below |
| `report gaps` | adaptive default | yes | assert window echo |
| `report tiers` | forces `regime="current"` then uniform | acceptable (intentional current-regime crowning) | assert banner |
| `generate consensus` | `_latest_regime_window()` uniform | **the absorbed `idea-consensus-window-consistency` mismatch** | see fix below |
| `generate tune` | `_latest_regime_window()` uniform, threaded | aligns *internally*, but mismatches the adaptive matrix | label the gap |
| `advise positioning` | adaptive default | yes | assert echo |
| `advise whattoplay` | adaptive default | yes | assert echo |
| `advise sideboard` | no window opts; internal `_latest_regime_window()` → **plans go dark** | **the headline fix** | see fix below |

### Fix A — consensus/matchup window alignment (absorbs idea-consensus-window-consistency)

The mismatch: `build_consensus` / `card_frequencies` default to `_latest_regime_window()` (a single
uniform current-regime slice), while the matchup matrix backing a positioning/sideboard read defaults
to **adaptive** (per-cell ban-aware). A generated list and its matchup numbers then come from different
slices, silently.

Resolution (honest-labeling, not forced-identical): consensus is a *deck-composition* surface — its
correct window IS the current regime (you want the list people are playing **now**), so we keep
`_latest_regime_window()` as the consensus default but **make the divergence explicit**:

- `build_consensus` already records `window=(since, until)` on `GeneratedDeck`. The CLI render for
  `generate consensus` must echo `// window: regime current [since..until], sample_n=N` so the user
  sees the list is current-regime-only and how thin that is. Add the echo in `cli.py` (the `generate`
  command render path) — no signature change to `build_consensus`.
- Where consensus feeds a matchup-backed surface (tune), the report must state that the **list**
  is current-regime while the **matchup math** is adaptive (borrows prior-regime depth). Add this as a
  one-line audit note in `tuning.py`'s report assembly (alongside the existing window echo).

No behavior change to the numbers; the fix is loud labeling of an intentional, defensible divergence.
This closes the absorbed idea: the windows are allowed to differ, but never *silently*.

### Fix B — sideboard adaptive window (the headline fix)

**Problem:** `recommend_sideboard` → `_field_matchup_values` computes `compute_card_winrates` **once**
over a single uniform window (`eff_since/eff_until`, defaulting to `_latest_regime_window()`). In a
thin current regime (61 events / ~22 days) almost every per-card×matchup cell falls below the
`evolving` gate, so `cleared_gate=False` for nearly every opponent and `_plan_matchups` emits a
degraded plan (`speculative, n_basis=0`). The matrix doesn't have this problem because
`build_adaptive_matrix` pools each cell back to `max(valid_since[a], valid_since[b])`.

**Fix:** give the sideboard per-matchup plans the same per-opponent adaptive window. The deck's own
archetype is fixed (it's the user's deck), so the relevant window per opponent is
`max(valid_since[deck_archetype], valid_since[opponent])` — pool that opponent's card-value cells back
to there (full history if neither is ban-affected), exactly mirroring the matrix.

Implementation (reuse the matrix's `mr_by_since` pattern — one scan per distinct window, not per cell):

1. **`advisory/sideboard.py` — `_field_matchup_values`**: add optional `adaptive_windows:
   dict[str, tuple[str|None, str|None]] | None = None` (opponent → its `(since, until)`). When provided,
   build a per-window `CardWinRates` cache: for each distinct window, call `compute_card_winrates(con,
   since=w_since, until=w_until)` once (memoized in a local dict keyed by the window tuple), and value
   each opponent's cells against the aggregate for *that opponent's* window. When `None`, behavior is
   byte-identical to today (single uniform window) — preserves all existing tests and the rounds-less
   no-op path. `card_winrates` (single injected aggregate) stays supported for the `adaptive_windows is
   None` path.

2. **`advisory/sideboard.py` — `recommend_sideboard`**: add `adaptive: bool = True` kwarg. When
   `adaptive` and `archetype` is set, compute `valid_since = archetype_valid_since(con, [archetype,
   *top_opponents], provenance=...)` (the `analytics.affectedness` SSOT — already a clean
   analytics→advisory import per its module docstring), build `adaptive_windows[opp] =
   (max(valid_since[archetype], valid_since[opp]) or None, None)`, and thread it into BOTH
   `_field_matchup_values` passes (pressure pass + final-15 pass) and into `_plan_matchups`. The
   top_opponents set is the top-k field-share archetypes (same selection `_field_matchup_values`
   already uses). Set `plan_window` to a sentinel/representative ("adaptive (per-opponent ban-aware)")
   and add a `plan_windows: dict[str, tuple]` additive field on `SideboardPackage` for the per-opponent
   audit. When `adaptive=False` (or `archetype is None`), fall back to today's single-window path —
   no-op for existing callers.

3. **`_plan_matchups`**: the `locked_core` call to `card_frequencies(con, archetype, ...)` should use
   the deck-archetype's own window (`max(valid_since[archetype], None)` i.e. `valid_since[archetype]`),
   not the opponent windows — already takes `since/until`, so thread the deck-archetype window there.
   `n_basis`/`tier` already derive from the actual cells used, so they will correctly report the
   (larger) adaptive n.

4. **`cli.py` — `advise_sideboard`**: add `@_window_opts` + `_echo_window`, resolve via
   `resolve_advisory_window`, and pass the resolved mode through: adaptive mode → `adaptive=True`;
   uniform/full → `adaptive=False` with the resolved `since/until`. Echo the per-opponent windows used
   (one compact audit line, mirroring `_adaptive_audit`) and keep the existing presence-correlational
   disclaimer. Thread the same through `generate tune`'s `recommend_sideboard` calls (`tuning.py`) so
   tune's plans also stop going dark.

**Honesty invariant:** when an opponent's adaptive window STILL has too few rounds to clear the gate,
the plan stays degraded — but the note now says "even pooling to <valid_since> the matchup is thin
(n=<k>); guidance is reasoning-based, not data-derived" rather than a bare `speculative, n≥0`. This is
the "stated honestly" half of the item: data-derived when the pooled window clears the gate,
explicitly reasoning-based otherwise.

### PRINCIPLES.md addition (note here; the implement step makes the edit)

Add principle **#10. Ban-regime-aware windowing is the default, and the window is always stated** to
`docs/PRINCIPLES.md` (and its `decisions:` frontmatter list; bump `updated:`):

> ### 10. Ban-regime-aware windowing, always labeled
> Every analytical surface defaults to ban-regime-aware windowing so tuning reflects the **current**
> meta, not a stale pre-ban field. Three modes — **adaptive** (per-cell/per-opponent ban-aware, the
> default for matrix-backed surfaces: matchups, positioning, gaps, sideboard plans), **uniform**
> (an explicit `--regime`/`--since` window, degraded to full corpus + banner when thin), and **full**
> (`--all-time`, or deck-based descriptive surfaces whose thinness shows via confidence tiers). A
> surface MUST echo its resolved window and thinness; a thin window may never silently claim depth it
> doesn't have. Where two surfaces legitimately use different windows (a current-regime consensus list
> read alongside an adaptive matchup matrix), the divergence is stated, never silent. New surfaces are
> audited against this checklist before they ship.

### Implementation order (trickiest first)

1. **Fix B unit (1)–(3)** — `_field_matchup_values` per-window cache + `recommend_sideboard` adaptive
   threading + `_plan_matchups` locked-core window. This is the trickiest (per-window aggregate cache,
   gate behavior, no-op preservation) — do it first and prove it with tests before wiring the CLI.
2. **Fix B unit (4)** — CLI/tune wiring + echoes.
3. **Fix A** — consensus/tune window-divergence labels (pure echo additions).
4. **PRINCIPLES.md** — principle #10 + frontmatter.

### Test plan

- `tests/advisory/test_sideboard.py` (extend):
  - **Adaptive lifts a thin-regime opponent out of degraded.** Build a fixture corpus where the current
    regime alone gives a top opponent n<30 (speculative) but pooling to its `valid_since` (full history)
    gives n≥30: assert that with `adaptive=True` the plan is non-degraded and `n_basis` matches the
    pooled cell, while `adaptive=False` (single current-regime window) leaves it degraded. This is the
    core regression for the headline bug.
  - **No-op preservation.** Rounds-less corpus → `adaptive_windows` path still yields
    `matchup_pressure=None` and byte-identical element weights; existing tests stay green untouched.
  - **`adaptive=False` byte-identical to pre-feature** for a single-window call (regression guard on
    the fallback path).
  - **Per-window cache correctness.** Two opponents with different `valid_since` get values from their
    own pooled windows (assert via a fixture where the two windows give different lifts for the same
    card); assert `compute_card_winrates` is invoked once per distinct window, not per opponent (patch +
    call-count).
  - **Honest-degrade note.** An opponent thin even after pooling keeps `degraded=True` and the note
    names the pooled `valid_since` + the (small) n.
- `tests/analytics/test_affectedness.py` — already covers `archetype_valid_since`; add an assertion that
  a deck-archetype + opponent pair resolves to `max(valid_since)` (the window the sideboard uses).
- `tests/test_cli.py` (extend): `advise sideboard --regime current` echoes a window line and the
  per-opponent audit; `--all-time` echoes full-corpus; `generate consensus` echoes its current-regime
  window + sample_n; default `advise sideboard` echoes "adaptive (per-opponent ban-aware)".
- **Audit assertions** (lightweight, in `tests/test_cli.py`): for each surface in the checklist, assert
  the window/thinness line is present in output (a regression net so a future surface can't ship
  window-silent).

### Risks

- **`archetype_valid_since` cost.** It runs one batched query per ban date; called once per
  `recommend_sideboard` for the deck-archetype + top-k opponents. Cheap (≤ #ban-dates queries), and the
  per-window `CardWinRates` cache caps `compute_card_winrates` at ≤ #distinct-windows scans (same bound
  the matrix already accepts). Acceptable.
- **No-op regression risk.** The biggest risk is breaking the byte-identical rounds-less path that
  existing tests depend on. Mitigation: `adaptive` defaults preserve the single-window path whenever
  `archetype is None` or no rounds data, and the no-op test above guards it explicitly.
- **Consensus "fix" is labeling-only.** A reviewer may expect the consensus window forced to match the
  matrix. Rationale (logged): consensus is deck-composition (correctly current-regime); the matrix is
  matchup math (correctly adaptive). Forcing identity would *degrade* the matchup math back to thin.
  The honest resolution is loud divergence labeling, which is what the absorbed idea actually needs.
- **Opponent set drift.** The window-resolution top-k and `_field_matchup_values` top-k must use the
  same selection or windows won't align to opponents. Mitigation: compute the opponent list once in
  `recommend_sideboard` and pass it to both.

## Implementation notes

**Files modified:**
- `src/legacy_engine/advisory/sideboard.py` — Fix B: added `adaptive_windows`/`top_opponents` params
  to `_field_matchup_values` (per-window wr_cache with seed from pre-computed uniform aggregate);
  added `adaptive_windows` to `_plan_matchups` (locked-core uses deck-arch window; honest-degrade
  note names the pooled window); added `adaptive: bool = True` to `recommend_sideboard` with the
  adaptive window resolution block (guarded by `_caller_explicit_window` so existing callers with
  explicit `since=` stay on the single-window path byte-identically); two new additive fields on
  `SideboardPackage` (`plan_window_label`, `plan_windows`).
- `src/legacy_engine/cli.py` — added `@_window_opts`, `--archetype`, and window echo to
  `advise sideboard`; Fix A window-divergence note in `generate tune` header; updated
  `generate consensus` window echo to label as uniform/current-regime.
- `src/legacy_engine/generation/tuning.py` — Fix A: window-divergence audit note appended to
  both `reason` strings (greedy-converged path and no-signal fallback).
- `docs/PRINCIPLES.md` — added principle #10 (ban-regime-aware windowing) + updated `decisions:`
  frontmatter and `updated:` date.

**Tests added (15 new, all green):**
- `tests/test_sideboard.py::TestAdaptiveWindowSideboard` — 6 tests: adaptive=False byte-identical,
  rounds-less no-op, per-window cache called once per distinct window (2 variants), honest-degrade
  note names pooled window, plan_window_label set/unset correctly.
- `tests/test_adaptive_regime.py::TestArchetypeValidSincePooling` — 2 tests: max(valid_since)
  pool semantics, both-None means full-corpus.
- `tests/test_cli.py::TestWindowEchoRegimeConsistency` — 7 tests: consensus echoes window +
  sample_n + uniform label; tune echoes divergence; advise sideboard echoes adaptive/full-corpus/
  regime window lines.

**Key design decision implemented:** adaptive per-opponent windows only activate when the caller
passes no explicit `since/until` (mirrors `resolve_advisory_window`'s default-is-adaptive rule).
When `since` or `until` is set explicitly, the single-window path is used — preserving the
scan-count=1 guarantee the pre-existing `test_tune_deck_computes_card_winrates_exactly_once` test
asserts. Full suite: 1269 passed (was 1254; +15 new tests).


## Review findings (bounce 1)
BLOCKING 1: `generation/tuning.py` sets `eff_since,eff_until=_latest_regime_window()` (both non-None) then calls `recommend_sideboard(...)` WITHOUT `adaptive=`, so `_caller_explicit_window` is True and tune's per-matchup plans never get the adaptive window — yet `cli.py` unconditionally prints a note claiming 'matchup math = adaptive (per-opponent ban-aware)'. That is a FALSE honesty label (the exact dishonesty this feature prevents). FIX: thread adaptive into tune (pass since=None/until=None + adaptive=True when the caller gave no explicit window), OR change the label to state plans use the uniform window. BLOCKING 2: the headline regression test is missing — assert that with adaptive=True a thin-regime opponent's plan is NON-degraded with n_basis matching the pooled cell, while adaptive=False leaves it degraded. (Also: the degrade-note test at tests/test_sideboard.py:~2358 is guarded behind `if plan.degraded` so it can pass vacuously — make it assert.)
