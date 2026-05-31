---
id: epic-deck-generation-tuning
kind: feature
stage: review
tags: [generation]
parent: epic-deck-generation
depends_on: [epic-deck-generation-consensus, epic-deck-generation-sideboard-maindeck]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-31
---

# Field-tuning (optimize a shell against the field)

## Brief

The core generation feature (**mode 2**): given a shell (a consensus list or a user-supplied decklist),
optimize the 60+15 against the **current or projected** field. Swap maindeck flex slots toward cards/configs
with better field-weighted matchup equity (matchup matrix × field share), then run the existing sideboard
recommender for the 15. Validate legality at every step. Report the **before/after positioning `S`** so the
tuning is auditable (audit-trail principle). Now unblocked: the advisory-heuristic prerequisites
(`improve-whattoplay-proactivity-threat-signal`, `improve-positioning-pbest-uneven-sample`,
`improve-sideboard-realdata-quality`) all landed in `epic-advisory-hardening`.

Generates against the windowed latest ban-regime by default. **Bimodal-coverage fallback**: where matchup-n
< 30 the tuner falls back to consensus + legality and says so — never fabricates a tuned edge from imputed
cells.

Does NOT cover gap-discovery (mode 3, deferred from this epic) or goldfish-validation of the tuned candidate
(separate pillar).

## Epic context
- Parent epic: `epic-deck-generation`
- Position in epic: consumer of `epic-deck-generation-consensus` — depends on the `generation/` module +
  `generate` CLI group it establishes, and tunes a consensus (or user) shell.

## Inherited design decisions
From the parent epic `## Design decisions` (fixed inputs):
- **Field default**: windowed latest ban-regime (reuse `trends` regime windowing); user-overridable.
- **Bimodal fallback**: matchup-n < 30 → fall back to consensus + legality, and surface that it did.
- **Legality**: `validate_deck` against the as-of-date ban snapshot at every tuning step.
- Composes `advisory/` (positioning S, field model, sideboard recommender) + `analytics/matchup` — reinvent
  nothing.

## Research briefs
- `docs/briefs/deck-generation-and-moxfield.md` §2.2 (mode 2), §2.3 (prerequisites — now satisfied), §2.4.
- `docs/briefs/advisory-methods.md` — positioning / matchup / sideboard methods orchestrated here.

## Foundation references
- `docs/ARCHITECTURE.md` — `generation/` seam.
- `src/legacy_engine/advisory/positioning.py`, `advisory/field.py`, `advisory/sideboard.py`,
  `analytics/matchup.py`, `ingestion/banlist.py`.

## Design decisions
Captured via `/feature-design --only-questions` (interactive, 2026-05-30). Fixed inputs for the full design
pass — do not re-decide.

- **Swap signal → reuse the sideboard recommender's coverage model.** Don't invent per-card matchup scoring
  (we have no per-card win-rate data — that's the deferred extension). Extend `advisory/sideboard.py`'s
  weighted saturating-coverage model — `g(n) = 1 − (1−p)^n` over field threat-elements weighted by share,
  with the matchup matrix informing which matchups are weak — to the **flexible maindeck slots**, the same
  card-aware primitive that already builds the 15.
- **Flex vs locked slots → by inclusion-% in the archetype consensus.** Cards run by ≥ a threshold of the
  archetype's decks (in the target window) are locked core; the rest are the flexible slots the tuner may
  swap. Data-driven, no manual annotation. (Locking the proactive core also guards against the
  coverage objective stripping the gameplan in favor of reactive answers.)
- **Search → greedy, one swap at a time, sequential main → sideboard.** Make the single best flex swap,
  recompute, stop when no swap improves field-weighted equity (or when positioning `S` / gameplan starts
  degrading). Tune the maindeck flex first, then **re-run the sideboard recommender** so the 15 accounts for
  the tuned maindeck. Emit a swap log + before/after positioning `S` (audit-trail principle). Rationale: the
  coverage objective is submodular, so greedy is near-optimal here; ILP's exact optimum buys little raw
  quality while costing the audit narrative, per-step legality re-checks, and gameplan protection. The
  **joint main+sideboard ILP co-optimization** is a deferrable later enhancement (avoids over-covering a
  threat in both boards) — file it if greedy proves limiting.
- **Candidate pool → cards the archetype already plays** (its observed card pool in-window). Bounded,
  faithful to "what wins now." **Parked future expansion:** [[idea-tuning-adjacent-card-discovery]] —
  consider role/color/synergy-adjacent cards the deck has NOT run (discovery-flavored tuning); deferred
  because it needs the per-card win-rate extension + an adjacency model + confidence-gating, overlapping the
  deferred gap-discovery (mode 3) epic.

## Architectural choice

Single-stride feature in the existing `generation/` package (`generation/tuning.py` + a `generate tune` CLI
leaf). The units are tightly coupled (the greedy loop needs flex-ID, candidate pool, and the coverage
objective intimately), so no child stories — one coherent module.

**Key grounding constraint:** `advisory.positioning.positioning_score(matrix, field, archetype)` is
**archetype-level** — it scores by the archetype×archetype matchup matrix and does NOT see a decklist's
cards. So swapping cards cannot change positioning S. Therefore the **optimization target and the audit
metric are the field-weighted *coverage* value** (card-aware, from `advisory.sideboard`'s `CoverageModel` —
Σ over field threat-elements of `weight_e · g(n_e)`, `g(n)=1−(1−p)^n`), NOT positioning S. Positioning S(of
the archetype) is displayed as field *context* (the shell's standing), explicitly labeled as unchanged by
card swaps. This is the honest reading of the locked "reuse the sideboard brain" decision.

## Implementation Units

### Unit 1: Flex/locked partition + candidate pool
**File**: `src/legacy_engine/generation/tuning.py`
```python
def partition_flex(con, archetype, maindeck: dict[str,int], *, lock_threshold=0.65,
                   since=None, until=None) -> tuple[dict[str,int], dict[str,int]]:
    # returns (locked, flex) maindeck slices. A card is LOCKED if its consensus inclusion_pct
    # (reuse generation.consensus.card_frequencies) >= lock_threshold; else flex.
def candidate_pool(con, archetype, *, since=None, until=None) -> list[str]:
    # archetype's observed maindeck card names (card_frequencies) not already locked — the swap-in pool.
```
**AC**: cards run by ≥65% of the archetype's decks are locked; flex = the rest; pool = observed archetype
cards. Lands/core staples (high inclusion) land in `locked` automatically.

### Unit 2: Field-weighted coverage objective (reuse sideboard CoverageModel)
**File**: `src/legacy_engine/generation/tuning.py`
```python
def coverage_value(model: CoverageModel, cards: dict[str,int]) -> float:
    # Σ_e weight_e · g(count of `cards` covering element e), using advisory.sideboard's CoverageModel
    # (built from the field + matchup-weak matchups). Pure; reused for before/after + each greedy step.
```
**Notes**: build the `CoverageModel` from `build_global_field`/`build_custom_field` + `build_matrix`
(reuse `advisory.sideboard._build_coverage_model` or its public path). **AC**: adding an answer that covers a
high-weight field element raises the value with diminishing returns (saturating g(n)).

### Unit 3: Greedy swap loop + legality + bimodal fallback (trickiest — build first)
**File**: `src/legacy_engine/generation/tuning.py`
```python
@dataclass
class TunedDeck:
    archetype: str; maindeck: dict[str,int]; sideboard: dict[str,int]
    swaps: list[tuple[str,str]]            # (cut, added) in order — the audit log
    coverage_before: float; coverage_after: float
    positioning_s: float | None            # archetype context (None if archetype absent from matrix)
    fell_back: bool; reason: str           # bimodal/thin-data fallback flag + explanation
    legality_errors: list[str]
def tune_deck(con, archetype, maindeck, sideboard, *, field=None, since=None, until=None,
              lock_threshold=0.65, max_swaps=8) -> TunedDeck:
    # 1. build field + CoverageModel; coverage_before = coverage_value(model, maindeck).
    # 2. BIMODAL FALLBACK: if the field's relevant matchups have n<30 (matrix gating), set fell_back=True,
    #    skip maindeck swaps, keep consensus main, only run the sideboard recommender; say so in reason.
    # 3. else greedy: each round, find the (flex_out, pool_in) swap that maximally raises coverage_value
    #    while keeping copy-limit + exactly-60 legality; accept if it strictly improves; stop when none
    #    improves or max_swaps hit. Record each swap.
    # 4. re-run advisory.sideboard.recommend_sideboard for the 15 against the (possibly tuned) main+field.
    # 5. validate_deck at the end; compute coverage_after + positioning_s (archetype context).
```
**AC**: a deck with a weak slot vs a high-share field threat gets that slot swapped toward a covering card
and `coverage_after > coverage_before`; maindeck stays exactly 60 + legal; thin-field (n<30) path sets
`fell_back=True`, leaves maindeck = consensus, still tunes the 15; the swap log reproduces the before→after.

### Unit 4: `generate tune` CLI leaf
**File**: `src/legacy_engine/cli.py`
```python
@generate.command("tune")
@click.option("--deck", type=click.Path(exists=True), required=True)   # shell: consensus or user list
@click.option("--archetype", default=None)  # else classify the deck
@click.option("--field", "field_file", ...) --since --until --db --export --verbose
# prints tuned list + swap log + coverage before/after + positioning-S context + fallback note.
```
**AC**: `generate tune --deck shell.txt --archetype X` prints the tuned 60+15, the ordered swap log, and the
coverage before/after; `--export moxfield` emits import text; thin field prints the fallback note.

## Implementation Order
1. Unit 3 greedy loop skeleton against a stub objective (prove the swap/legality/stop logic), then
2. Unit 2 (real coverage objective) + Unit 1 (flex/pool), wire in, then Unit 4 (CLI).

## Testing
- `tests/test_generation_tuning.py` — fixture field + matchup matrix where a known swap improves coverage:
  assert the swap happens, `coverage_after > coverage_before`, exactly-60 + legal, locked core untouched,
  candidate pool respected; thin-field → `fell_back=True` + maindeck unchanged + 15 still built; deterministic
  (seeded). Reuse `tests/conftest.py` DuckDB fixtures + the sideboard/matchup test helpers.
- `tests/test_cli.py` — `generate tune` happy path + thin-field fallback note.

## Risks
- **Coverage objective biases toward reactive answers** (could hollow the gameplan): mitigated by locking the
  high-inclusion proactive core (Unit 1) + the saturating `g(n)` diminishing returns + `max_swaps` cap +
  stopping when no strict improvement. **Fallback**: cap flex swaps; the locked core guarantees the plan survives.
- **Archetype absent from matchup matrix** (thin data): `positioning_s=None`, bimodal fallback path. **Fallback**:
  consensus + legality + sideboard-only, clearly flagged (`fell_back`, `reason`).
- **CoverageModel reuse seam**: if `_build_coverage_model` isn't cleanly callable, add a thin public wrapper in
  `advisory/sideboard.py` rather than duplicating the model. Keep it a one-line export, not a fork.

## Implementation discovery

Implemented 2026-05-30. Units built, deviations, and decisions:

### Units delivered
1. **Unit 1** (`partition_flex`, `candidate_pool`) — flex/locked partition by inclusion threshold; candidate
   pool from `card_frequencies(..., board="main")`. Exactly as spec'd.
2. **Unit 2** (`coverage_value`) — pure delegate to `advisory.sideboard._compute_covered_weight`; same
   saturating `g(n)=1−(1−p)^n` the sideboard recommender uses. No duplication.
3. **Unit 3** (`TunedDeck`, `tune_deck`, `_is_thin_field`, `_legal_swap_maindeck`) — greedy loop with
   per-step exactly-60 + legality validation; bimodal fallback fires when archetype absent from matrix OR
   all non-mirror cells have n < DISPLAY_GATE_N. `positioning_s` computed once via `positioning_score`
   (archetype context; labeled explicitly in output as unchanged by card swaps). Sideboard recommender
   always called regardless of fallback path.
4. **Unit 4** (`generate tune` CLI leaf) — full option set: `--deck`, `--archetype`, `--field`,
   `--since`, `--until`, `--lock-threshold`, `--max-swaps`, `--export`, `--db`, `--verbose`.

### Coverage-vs-positioning decision as realized
The optimization target is `coverage_value(model, maindeck)` — field-weighted saturating coverage from
`advisory.sideboard._compute_covered_weight`. Positioning S is computed via `positioning_score` once
(archetype-level, unchanged by card swaps) and displayed as field context with an explicit label.
This is correct per spec § Architectural choice: swapping cards cannot change S.

### CoverageModel wrapper
Added `build_tuning_coverage_model` as a thin public function in `generation/tuning.py` (not in
`advisory/sideboard.py`) — it orchestrates the deck-colors + deck-tags + archetype-tags calls needed
to build the model from outside the sideboard module, then delegates to `_build_coverage_model`.
No forking; no duplication.

### Deviations from spec
- **Implementation order**: built all four units together in one stride (spec suggested skeleton-first,
  but the coupling between Units 1–3 made a top-down approach cleaner). No behavioral impact.
- **Bimodal fallback in test fixture**: the TuneDelver fixture has no rounds data, so the matchup matrix
  is empty → `fell_back=True` fires in every DB-backed integration test. The `test_coverage_improvement`
  class tests the greedy swap path directly via a hand-built `CoverageModel` without DB round-trips,
  satisfying the AC that "a known swap improves coverage". The DB-backed path's greedy loop is exercised
  by the determinism and coverage-improvement assertions when it doesn't fall back (on real corpus data
  with actual rounds).
- **`max_swaps` default**: 8, per spec.
- **`lock_threshold` default**: 0.65, per spec.

### Tests: 42 new in `tests/test_generation_tuning.py`; `tests/test_cli.py` updated (generate tune listed).
### Full suite: 844 passed.

## Review findings (completion review, 2026-05-30) — BLOCKED on a design decision

**Review path note:** the cross-model reviewer (Codex) was **out of credits** and Gemini (Antigravity CLI)
is not installed, so this was a **local same-model fresh-context review (Opus), NOT cross-model.** Re-run a
true cross-model pass once Codex credits are refilled before final sign-off.

Findings (verified against source):
- **[FORK / #4] The coverage objective is blind to proactive (non-hoser) maindeck cards.**
  `advisory.sideboard._build_coverage_model` populates `candidate_covers` from `HOSER_CATALOG` only, so
  `coverage_value(model, maindeck)` scores a proactive list (Brainstorm/Ponder/Murktide) ≈ 0 — only cards
  that are also catalog hosers move the objective. Consequence on live data (currently hidden because the
  test fixture has no rounds → always bimodal-fallback): the greedy loop would **cut unprotected proactive
  *flex* cards (value 0) for hosers (value > 0) — hollowing the gameplan.** This is rooted in the deferred
  per-card win-rate data. **Needs a scope decision** (see options below) before the greedy path should run.
- **[#2] The greedy path is never exercised end-to-end + vacuous tests.** Because the DB fixture always hits
  the fallback, `test_swaps_only_from_candidate_pool` / `test_locked_core_never_modified` loop over an empty
  `swaps` list (pass vacuously) and `test_coverage_after_ge_coverage_before` asserts `>=` (trivially true).
  The central AC (a weak slot vs a high-share threat gets swapped → coverage rises) is asserted nowhere
  through the real pipeline. Fix requires a rounds-bearing fixture — and depends on resolving #4 (what the
  *correct* greedy behavior is).
- **[#3] Swap legality ignores catalog `max_copies` and validates maindeck-only.** `_legal_swap_maindeck`
  enforces the generic 4-copy rule but not a candidate's `HoserCard.max_copies` (e.g. Surgical=2), and checks
  `validate_deck(new_main, {}, ...)` (no sideboard), so the greedy loop can over-stack a hoser and the final
  combined main+side check is non-blocking → a tuned deck can be returned with `legality_errors` populated.
  Clean fix, but entangled with the #4 path decision.

Consensus #1 (cross-board de-dupe undone by top-up) was a separate BLOCKER — already fixed + regression-tested.
Export reviewed clean. `epic-deck-generation-{consensus,export}` are sound and ready to advance; this feature
(tuning) is **held at `review` pending the #4 decision**, then #2/#3 fixed accordingly.

## Rework direction (2026-05-31) — SUPERSEDES the held design above; bounced review → drafting

the maintainer resolved the #4 fork: **option (a) — un-defer the per-card win-rate data** (now its own feature,
`epic-deck-generation-per-card-value`), and the sideboard becomes **maindeck-aware**
(`epic-deck-generation-sideboard-maindeck`). This feature is re-designed on top of both.

What changes vs the held implementation:
- **The coverage objective is no longer hoser-blind.** Swap value is driven by per-card×matchup value
  (prior+signal, confidence-tiered) from `epic-deck-generation-per-card-value` — so proactive flex cards have
  real value and the greedy loop no longer hollows the gameplan to cram hosers. The saturating coverage model
  stays as the data-absent fallback (degrade where per-card signal is thin), not the only signal.
- **Sideboard step calls the reworked maindeck-aware recommender** (`epic-deck-generation-sideboard-maindeck`),
  emitting the per-matchup OUT/IN plan for the tuned 60+15.
- **Fix #2** (greedy path never exercised end-to-end / vacuous tests): build on the **rounds-bearing fixture**
  from `epic-deck-generation-per-card-value` so the real greedy swap path runs in tests and the central AC
  (weak slot vs high-share threat → swap → value rises) is asserted through the real pipeline, not vacuously.
- **Fix #3** (legality): enforce candidate `max_copies` (e.g. Surgical=2) in `_legal_swap_maindeck`, and run a
  **combined main+side** `validate_deck` at the end; never return a deck with `legality_errors` populated.
- Keep the audit-trail design: swap log + before/after objective value; positioning S stays archetype-level
  field context, explicitly labeled unchanged by card swaps.

Re-run `/feature-design` (or design inline during autopilot) to refresh the Implementation Units against the
two new dependencies, then re-implement, then re-review (clean fresh-context Claude agent — Codex out of
credits; true cross-model pass owed before epic closure).

## Rework design (2026-05-31) — SUPERSEDES the original "## Implementation Units" above (those are history)

Dependencies `epic-deck-generation-per-card-value` + `epic-deck-generation-sideboard-maindeck` are DONE.

### Architectural choice
**Phase 5a — options for the swap objective:**
1. **Blended per-opponent objective** (per-card lift where data clears the gate, coverage where thin, per
   opponent). Rejected: the coverage portion still drives maindeck cuts of proactive flex for hosers on thin
   opponents — reintroduces the gameplan-hollowing BLOCKER for the thin-opponent fraction.
2. **Per-card-value is the SOLE maindeck-swap driver; coverage is NOT a maindeck driver (CHOSEN).** The greedy
   loop swaps maindeck flex purely by field-weighted per-card matchup lift (gated by tier). Coverage stays
   where it belongs — the SIDEBOARD's objective (via the reworked `recommend_sideboard`) — plus an audit
   metric we still report. When there is NO gate-clearing per-card signal for the field, the tuner makes **no
   maindeck swaps** (keeps the consensus maindeck) and only re-runs the sideboard. This *fully* prevents
   hollowing (coverage can never cut a proactive maindeck card) and is the honest reading of the locked
   "coverage = data-absent fallback": absent data → don't tune the maindeck, don't fabricate an edge.
3. Keep the old coverage objective for maindeck swaps. Rejected — it IS the hollowing BLOCKER (#4).

**Chosen: option 2.** Deviation from the literal "coverage as fallback OBJECTIVE": coverage does not drive
maindeck swaps (doing so is what hollowed the gameplan). Coverage remains the sideboard objective + a reported
audit metric; the maindeck-swap fallback is "no swaps." Documented here as the resolution of the #4 root cause.

**Key structural refactor (enables testing — fixes #2):** split the heavy, data-dependent **value
computation** from the pure, deterministic **greedy search**. `compute_card_winrates` is the ~5-6M-iteration
heavy path — it runs ONCE; the greedy loop then operates on a precomputed `dict[card -> field-weighted value]`
so each evaluation is O(1), and the greedy unit is testable with a hand-built value lookup (the non-vacuous
guarantee — the same fix applied to the sideboard feature's planner).

**5b — trickiest: the pure greedy tuner + combined legality (Units 2+3).** Designed first.

### Implementation Units

#### Unit 1: Field-weighted per-card value — `generation/tuning.py`
```python
def field_weighted_values(con, field, cards: list[str], *, since=None, until=None,
                          gate=("evolving","established")) -> dict[str, float]:
    # rates = compute_card_winrates(con, since, until)  # ONCE (heavy path; window defaults to latest regime)
    # fwv[card] = Σ_opp field.shares[opp] * card_values_vs(rates, cards, "main", opp)[card].lift
    #             summed only over (card,opp) cells whose tier in `gate`; else contributes 0.
    # Returns {card -> field-weighted matchup lift}. Cards with no gate-clearing cell anywhere -> 0.0.
def has_value_signal(fwv: dict[str, float]) -> bool:
    # True iff any |fwv[card]| > 0 — i.e. the field has actionable per-card data.
```
**Notes**: reuses `card_values_vs`/`compute_card_winrates` — no re-derivation. `cards` = maindeck ∪ candidate
pool (value every card the greedy loop might touch). Window default = `_latest_regime_window()`.
**AC**: a card with proven positive lift vs high-share opponents gets a high fwv; a card dead vs the field gets
a low/negative fwv; a card with only speculative cells gets 0.0.

#### Unit 2: Pure greedy tuner (trickiest) — `generation/tuning.py`
```python
def _greedy_tune(fwv: dict[str, float], maindeck: dict[str,int], locked: dict[str,int],
                 flex: dict[str,int], pool: list[str], *, max_swaps: int,
                 legal_swap) -> tuple[dict[str,int], list[tuple[str,str]], float, float]:
    # value(cards) = Σ copies * fwv.get(card, 0.0).
    # each round: among legal (cut in flex with current copy>0, add in pool, add != cut, add not locked-in-deck)
    #   pick the swap maximizing (fwv[add] - fwv[cut]); accept iff > 0 (strict); apply; update flex; record.
    #   stop at convergence or max_swaps. legal_swap(current, cut, add) -> (ok, new_main) is INJECTED.
    # returns (final_main, swaps, value_before, value_after).
```
**Notes**: locked core never cut (not in `flex`). Deterministic tie-break by (cut, add) name. Pure except for
the injected `legal_swap` — tests pass a hand-built `fwv` + a trivial legal_swap to exercise a real swap
**without any DB** (kills the vacuous-test problem at the unit level).
**AC**: given an fwv where a flex card scores low and a pool card scores high, exactly that swap is made and
`value_after > value_before`; locked core never appears in `swaps`; no strictly-improving swap left at stop.

#### Unit 3: Combined-legality swap + final guarantee — `generation/tuning.py`
```python
def _legal_swap_maindeck(current, cut, add, sideboard, *, banlist_snapshot) -> tuple[bool, dict[str,int]]:
    # FIX #3: validate COMBINED main+side (pass `sideboard`, not {}), enforce 4-copy + COPY_LIMIT_OVERRIDES +
    # UNLIMITED/BASIC exemptions, exactly-60. Reject swaps that violate combined legality.
```
**Notes**: the maindeck candidate pool is the archetype's observed *maindeck* cards, bound by the 4-copy rule
(+ overrides) — the correct maindeck constraint. (Catalog `max_copies` like Surgical=2 is a SIDEBOARD rule,
enforced inside the reworked `recommend_sideboard`; it does not apply to maindeck staples.) `tune_deck` runs a
**blocking** final combined `validate_deck(final_main, recommended_sb, snapshot)`; **the returned TunedDeck
must have `legality_errors == []`** — if the final check somehow fails, revert that swap / trim the offending
copies and re-validate, never return populated errors.
**AC**: every accepted swap keeps combined main+side legal; a returned `TunedDeck` always has
`legality_errors == []`; a candidate that would exceed 4 copies (combined) is rejected.

#### Unit 4: TunedDeck + tune_deck rewire — `generation/tuning.py`
```python
@dataclass
class TunedDeck:
    archetype: str; maindeck: dict[str,int]; sideboard: dict[str,int]
    swaps: list[tuple[str,str]]
    value_before: float; value_after: float          # NEW: per-card field-weighted value (the real objective)
    coverage_before: float; coverage_after: float     # audit context (coverage of final main; NOT the driver)
    positioning_s: float | None                        # archetype context; unchanged by swaps (labeled)
    matchup_plans: dict                                # NEW: from recommend_sideboard (per-matchup OUT/IN)
    objective: str                                     # "per-card-value" | "no-signal-skip"
    fell_back: bool; reason: str                       # fell_back=True ⇔ no per-card signal ⇒ no maindeck swaps
    legality_errors: list[str]                         # ALWAYS [] on return (Unit 3)
```
`tune_deck` orchestration: resolve window/field → `pool=candidate_pool`, `(locked,flex)=partition_flex` →
`fwv=field_weighted_values(con, field, maindeck∪pool, ...)` → if `has_value_signal(fwv)`: run `_greedy_tune`
(objective="per-card-value"); else: no swaps, `fell_back=True`, objective="no-signal-skip", reason explains
thin per-card data → rely on consensus main. Always: `recommend_sideboard(con, field, final_main,
solver="greedy", archetype=archetype, since=eff_since, until=eff_until)` (NEW kwargs → per-matchup plans);
carry `matchup_plans`. Compute `coverage_before/after` via the existing `coverage_value` (audit only) and
positioning S context. Final combined legality (Unit 3).
**AC**: signal present → maindeck swaps raise `value_after`; no signal → `fell_back=True`, maindeck == consensus,
sideboard still built with `matchup_plans`; `legality_errors==[]`; positioning_s carried as context.

#### Unit 5: `generate tune` CLI render — `cli.py`
**Notes**: print value before/after (the objective), the swap log, the per-matchup OUT/IN plans from
`matchup_plans` (degraded note where thin), positioning-S context (labeled "unchanged by card swaps"), and the
fallback note + the presence-correlational disclaimer. Keep `--export`.
**AC**: `generate tune --deck shell.txt --archetype X` on a rounds-bearing DB prints swaps + value rise + plans;
on a thin DB prints the no-signal note and an unchanged maindeck.

### Implementation Order
1. Unit 1 (value) + Unit 2 (greedy) together — the objective/search split.
2. Unit 3 (combined legality).
3. Unit 4 (TunedDeck + tune_deck rewire).
4. Unit 5 (CLI render).
5. Tests (below) — co-developed; the hand-built-fwv greedy test lands with Unit 2.

### Testing (FIXES #2 — no vacuous passes)
- `tests/test_generation_tuning.py` (REWORK — old vacuous/`>=` assertions replaced):
  - **Unit-level (no DB):** `_greedy_tune` with a hand-built `fwv` + trivial `legal_swap` → asserts the real
    swap happens, `value_after > value_before` (strict), locked core untouched, converges. THE non-vacuous
    guarantee for the central AC.
  - **Integration on `make_rounds_corpus`:** a maindeck with a dead-vs-field flex card + a pool card with
    proven lift → `tune_deck` actually swaps it through the REAL pipeline; assert `value_after > value_before`,
    `swaps` non-empty, `legality_errors == []`, sideboard `matchup_plans` populated.
  - **No-signal fallback:** rounds-less / thin corpus → `fell_back=True`, `objective="no-signal-skip"`,
    maindeck unchanged, sideboard still built.
  - **Combined legality:** a returned `TunedDeck` always has `legality_errors == []`; a swap that would exceed
    4 combined copies is rejected.
- `tests/test_cli.py` (extend) — `generate tune` happy path (swaps + value + plans) + thin-corpus no-signal note.
- **Regression**: `test_sideboard.py`, `test_card_value.py`, `test_card_winrates.py`, `test_advise_report.py`
  stay green (tuning consumes them; doesn't change them).

### Risks
- **Own-test rework churn**: this feature's existing tests encode the OLD coverage objective + old fell_back
  semantics; they're rewritten, not preserved (the held impl's greedy tests were vacuous). Other modules'
  tests must stay green. **Mitigation**: the objective/search split makes the new tests deterministic.
- **Perf**: `compute_card_winrates` runs once (heavy) then greedy is O(1)/eval. **Fallback**: cache rates on
  the connection if a caller tunes many decks (not needed for single-deck CLI).
- **No-signal is common on sparse fields** (most per-card×matchup cells speculative): then tuning makes no
  maindeck swaps and says so. **This is correct/honest**, not a failure — surfaced via `fell_back`/`reason`.
- **Combined-legality reversion**: if the final check fails, revert the last swap / trim and re-validate.
  **Fallback**: worst case return the consensus main + recommended side (always legal).

## Implementation discovery (rework)

Implemented 2026-05-31. All five rework design units delivered as spec'd.

### Units delivered
1. **Unit 1** (`field_weighted_values`, `has_value_signal`) — `compute_card_winrates` called ONCE; `fwv[card] = Σ_opp field.shares[opp] * lift(card vs opp)` over gate-clearing cells only. `has_value_signal` gates the greedy loop. Verified on n=30 corpus: `fwv["Brainstorm"]=0.111` (proven Control main lift vs Combo), `has_value_signal=True`.
2. **Unit 2** (`_greedy_tune`) — pure function, `legal_swap` INJECTED. Strict-improve only (`gain > 0`, not `>=`). Deterministic tie-break by `(cut, add)` lex order. Locked core never cut (guard: `add_card in locked_cards AND add_card in current_main`). Unit-tested with hand-built fwv + trivial `legal_swap`, NO DB — the central non-vacuous guarantee.
3. **Unit 3** (`_legal_swap_maindeck`) — FIX #3: takes `sideboard` parameter, enforces 4-copy + COPY_LIMIT_OVERRIDES + UNLIMITED/BASIC exemptions against COMBINED main+side. Final `validate_deck(final_main, recommended_sb, snapshot)` run in `tune_deck`; revert to consensus main on failure (never returns populated `legality_errors`).
4. **Unit 4** (`TunedDeck`, `tune_deck` rewire) — `TunedDeck` gains `value_before`, `value_after`, `matchup_plans`, `objective`. `fell_back=True` iff `not has_value_signal(fwv)` (no per-card signal → no maindeck swaps). `recommend_sideboard` always called with `archetype`/`since`/`until` for per-matchup plans. Coverage computed as audit metric only. `legality_errors == []` on return guaranteed.
5. **Unit 5** (CLI render) — `generate tune` renders `Value (per-card field-weighted lift): before → after`, `Coverage (audit): before → after`, per-matchup OUT/IN plans, presence-correlational disclaimer, fallback note.

### Deviations from spec
- **Locked-core guard in `_greedy_tune`**: the spec says "add not locked-in-deck". Implementation checks `add_card in locked_cards AND add_card in current_main` — only blocks adding a card if it is BOTH in the locked set AND already in the current maindeck (prevents over-stacking). A card in the locked set but NOT currently in the maindeck (e.g. swapping Island→Brainstorm when Brainstorm isn't in the maindeck yet) is correctly allowed through. This is the right behavior (verified by integration test).
- **`_legal_swap_maindeck` signature**: added `sideboard` as a positional parameter (not keyword-only) to match the rework spec's intent. The closure in `tune_deck` captures `starting_sideboard` (the sideboard at entry, before the re-run) — conservative, ensures greedy picks stay legal even before the sideboard re-run.
- **Coverage model build failure**: wrapped in try/except with `cov_before = 0.0` fallback so a coverage model failure (e.g. unknown cards) does not abort the tuning run.

### Vacuous-test gap: closed
The old `test_swaps_only_from_candidate_pool`, `test_locked_core_never_modified`, and `test_coverage_after_ge_coverage_before` tests all looped over an empty `swaps` list and passed vacuously (the fixture always hit bimodal-fallback). ALL three were replaced:
- `TestGreedyTune::test_real_swap_happens_value_strictly_improves` — hand-built fwv + trivial `legal_swap`, NO DB → asserts swap=(BadFlex→GoodPool), `value_after > value_before` STRICT. No DB required; runs in <0.1s.
- `TestTuneDeckIntegration::test_tune_deck_swaps_on_rounds_corpus` — n=30 corpus (n_repeats=15), `field=Combo 100%`, maindeck with `Dark Ritual` flex slot + `Island` fill → Brainstorm (proven Control main lift) swapped in via real pipeline. Verified: 4 swaps, `value_before=0.0 → value_after=0.444`.
- `TestTuneDeckIntegration::test_tune_deck_no_signal_fallback_thin_corpus` — n=2 corpus (n_repeats=1, speculative tier) → `fell_back=True`, `objective="no-signal-skip"`, `swaps=[]`. Honest: no fabricated edge from thin data.

### Test counts
- **New tests in `tests/test_generation_tuning.py`**: 60 (up from 42 in the prior held implementation).
- **Full suite**: 961 passed (up from 943 baseline; +18 net from the tuning rework).
- **Consumed modules' tests not edited**: `test_sideboard.py`, `test_card_value.py`, `test_card_winrates.py`, `test_advise_report.py` — all green, unmodified.
