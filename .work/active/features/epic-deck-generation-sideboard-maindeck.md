---
id: epic-deck-generation-sideboard-maindeck
kind: feature
stage: implementing
tags: [generation, advisory]
parent: epic-deck-generation
depends_on: [epic-deck-generation-per-card-value]
release_binding: null
gate_origin: null
created: 2026-05-31
updated: 2026-05-31
---

# Maindeck-aware sideboard (per-matchup OUT/IN plan)

## Brief

Rework `advisory/sideboard.py` from a maindeck-blind max-coverage-over-hosers model into a **maindeck-aware**
recommender. the maintainer's framing (2026-05-31): sideboarding is a main↔side **swap per matchup** — you side cards
OUT of the 60 to bring cards IN from the 15 — so the recommendation cannot be computed independently of the
maindeck. The 15 should be chosen to maximize the value of the *post-board* 60s across the weighted field,
given what the maindeck already does.

**Deliverable = hybrid (locked):**
- **Primary — per-matchup OUT/IN plan.** For each top field archetype where the per-card×matchup data clears
  the confidence gate: the cards to side OUT of the 60 (the maindeck's dead/low-value-in-matchup cards, by
  per-card×matchup value) + the cards to side IN from the 15 → the post-board 60. The 15 is selected to serve
  these plans (fill what the maindeck lacks per matchup; don't double-cover what the main already answers).
- **Degrade gracefully — maindeck-aware 15 composition.** Where a matchup is too thin for a credible OUT/IN
  guide, fall back to the 15-composition rationale (gap-fill / no double-cover) WITHOUT inventing an OUT/IN
  list for that cell, and say so. Never fabricate a plan from imputed data.

## SSOT / blast radius (locked)
- **Rework in place** — one model both the `advise sideboard` CLI path and the `generation` tuner consume.
  This **re-opens the done `epic-advisory` sideboard feature**, changes its outputs (the recommendation is no
  longer a standalone 15 — it gains the maindeck input + per-matchup plan), and **will change existing tests**:
  regression-cover them, don't silently break them. Keep the saturating max-coverage primitive
  (`g(n)=1−(1−p)^n`, `max_copies`, weighted field threat-elements) — it stays the fallback objective when
  per-card data is absent; the per-card×matchup value augments it, it does not delete it.
- Consumes `epic-deck-generation-per-card-value` for the per-card×matchup signal (value + confidence tier).

## Foundation references
- `src/legacy_engine/advisory/sideboard.py` — `HoserCard`, `HOSER_CATALOG`, `CoverageModel`,
  `_build_coverage_model`, `_compute_covered_weight`, `recommend_sideboard`, `SideboardPackage`. The current
  contract + the `build_tuning_coverage_model` wrapper in `generation/tuning.py` that depends on it.
- `src/legacy_engine/advisory/field.py` (`build_global_field`/`build_custom_field`), `analytics/matchup.py`
  (`build_matrix`) — field weights + matchup-weak signal feeding the model.
- `docs/briefs/advisory-methods.md` — sideboard method.

## Design decisions (locked 2026-05-31 — do not re-decide)
- **Objective is maindeck-aware + per-card-value-driven**, with the existing coverage model as the
  data-absent fallback (above).
- **Which maindeck cards are siddable-out:** data-driven by per-card×matchup value (low/negative-in-matchup
  cards come out first), bounded by the available IN cards and a sane per-matchup swap cap. Locked-core
  protection (high-inclusion proactive staples never auto-sided-out) carries over from the tuning flex/locked
  partition concept. Exact cap + tie-breaks = feature-design unit choice.
- **`SideboardPackage` gains** the maindeck input + a per-matchup OUT/IN plan structure + per-cell confidence
  tier; the `advise sideboard` CLI prints the plan (degraded note where thin).

## Acceptance (sketch — feature-design fleshes into units + tests)
- `recommend_sideboard` (or its successor) takes the maindeck + field; returns the 15 PLUS per-matchup OUT/IN
  plans for gate-clearing archetypes.
- Post-board 60s are exactly-60 + legal (incl. `max_copies`); the 15 respects catalog `max_copies`.
- Thin matchup → degrades to composition rationale, flagged; no fabricated OUT/IN list.
- Existing `advise sideboard` tests updated/regression-covered, not broken silently.
- Reuses the rounds-bearing fixture from `epic-deck-generation-per-card-value`.

## Architectural choice

**Phase 5a — options:**
1. **Replace the coverage model with a per-card-value model.** Cleanest conceptually but throws away the
   proven `_build_coverage_model`/ILP/greedy machinery + breaks every existing `test_sideboard.py` test (88)
   and the rounds-less `advise sideboard` contract. High blast radius, fragile.
2. **Additive, gated augmentation (CHOSEN).** Keep the coverage model as the structural backbone for choosing
   the 15 AND as the data-absent fallback. ADD: (a) a per-card×matchup value adapter, (b) value-aware element
   re-weighting that only activates where matchup data clears the confidence gate, (c) a NEW per-matchup OUT/IN
   planner layered on top of the chosen 15 + maindeck, (d) additive fields on `SideboardPackage` (defaults, so
   `whattoplay`'s `dummy_sb` and `report.py` keep working). On a rounds-less corpus the per-card data is
   absent → every gate fails → behavior is **byte-identical to today** → existing tests stay green. New
   behavior is exercised only by `make_rounds_corpus`.
3. **New parallel module in generation/.** Rejected by the locked SSOT decision — would create two divergent
   sideboard brains.

**Chosen: option 2.** `recommend_sideboard` already takes `deck_maindeck`; we evolve it additively (new
optional `since`/`until`/`opponents`/`max_swaps` kwargs with safe defaults; the positional signature is
unchanged so `cli.py:905`, `report.py:305`, and `tuning.py:420/528` keep compiling). The maindeck-awareness
that's NEW is the per-matchup OUT/IN plan + value-aware weighting; the color-gating maindeck use stays.

**5b — trickiest unit: the per-matchup OUT/IN planner (Unit 3).** Designed first: it owns legality
(post-board exactly 60, `max_copies`), locked-core protection (never side out high-inclusion proactive
staples), and the hybrid degradation. The rest hangs on its shape.

## Implementation Units

### Unit 1: MatchupPlan + per-card matchup-value adapter
**File**: `src/legacy_engine/advisory/sideboard.py`
```python
@dataclass(frozen=True)
class MatchupPlan:
    opponent: str
    side_out: dict[str, int]      # maindeck cards to remove (card -> copies)
    side_in: dict[str, int]       # sideboard cards to bring in (card -> copies)
    post_board: dict[str, int]    # the resulting 60 (maindeck - out + in)
    n_basis: int                  # min matchup-cell n backing this plan
    tier: str                     # weakest tier among the cells used
    degraded: bool                # True when matchup data below gate — no OUT/IN, rely on 15 composition
    note: str

def _field_matchup_values(
    con, field, deck_maindeck, sideboard_15, *, since=None, until=None, top_k=8, gate=("evolving","established"),
) -> dict[str, "_OppValues"]:
    # Build CardWinRates once (compute_card_winrates, windowed). For each of the top_k field archetypes
    # by share: value the maindeck cards (board="main") and the sideboard_15 (board="side") vs that
    # opponent via card_values_vs. Returns per-opponent: maindeck values, sideboard values, and whether
    # the opponent cleared the gate (any cell tier in `gate`). Pure adapter over analytics.card_value.
```
**Implementation Notes**: window defaults to the latest ban regime (reuse `consensus._latest_regime_window`)
when both `since`/`until` are None — consistent with `report cards`/`report meta`. `top_k` opponents bounds
the plan size. `_OppValues` is a small internal dataclass (maindeck: dict[card,CardValue], side:
dict[card,CardValue], cleared_gate: bool).
**Acceptance Criteria**:
- [ ] For an opponent with established per-card data, returns CardValues with real lift + `cleared_gate=True`.
- [ ] For a thin opponent (all cells speculative), `cleared_gate=False`.
- [ ] Reuses `compute_card_winrates` + `card_values_vs` — no re-derivation of win-rates here.

### Unit 2: Value-aware element re-weighting (augment `_build_coverage_model`)
**File**: `src/legacy_engine/advisory/sideboard.py`
```python
def _build_coverage_model(field, archetype_tags, deck_colors, deck_tags, *, catalog=None,
                          matchup_pressure: dict[str, float] | None = None) -> CoverageModel:
    # NEW optional matchup_pressure: archetype -> multiplier in [1, 1+MAX_PRESSURE], derived from how
    # poorly the maindeck performs vs that archetype per card_value (low maindeck value vs high-share opp
    # => we need sideboard help there => up-weight its elements). When None (no/thin data), weighting is
    # IDENTICAL to today (multiplier 1.0 everywhere).
```
**Implementation Notes**: `matchup_pressure[a] = 1 + MAX_PRESSURE * clamp01(deficit(a))` where `deficit` =
how far the maindeck's mean per-card value vs `a` sits below the baseline, only for gate-clearing opponents;
others get 1.0. `MAX_PRESSURE` a small constant (e.g. 0.5) so the structural coverage still dominates — this
nudges, it doesn't override. Applied to `element_weight[f"{archetype}|{tag}"] *= matchup_pressure.get(arch,1.0)`.
**Acceptance Criteria**:
- [ ] `matchup_pressure=None` → element weights byte-identical to the pre-rework function (regression).
- [ ] A high-share opponent the maindeck does poorly against gets its elements up-weighted (≤ 1+MAX_PRESSURE).

### Unit 3: Per-matchup OUT/IN planner (trickiest — build first)
**File**: `src/legacy_engine/advisory/sideboard.py`
```python
def _plan_matchups(con, deck_maindeck, sideboard_15, opp_values, archetype, *,
                   max_swaps=4, lock_threshold=0.65, since=None, until=None) -> dict[str, MatchupPlan]:
    # For each opponent in opp_values:
    #   if not cleared_gate: MatchupPlan(degraded=True, empty out/in, post_board=maindeck, note="thin data
    #       (n<gate) — no per-matchup plan; rely on the maindeck-aware 15 composition").
    #   else:
    #     locked = maindeck cards run by >= lock_threshold of `archetype`'s decks (card_frequencies main) —
    #       NEVER sided out (proactive-core protection).
    #     OUT candidates = (maindeck \ locked) ranked by ASCENDING matchup value (most dead vs opp first),
    #       only cards whose value tier clears the gate and lift <= 0 (genuinely weak), capped at max_swaps.
    #     IN candidates  = sideboard_15 ranked by DESCENDING matchup lift vs opp, gate-clearing, lift > 0.
    #     pair OUT[i] <-> IN[i] up to min(len, max_swaps, copies); post_board = maindeck - out + in.
    #     enforce legality: post_board sums to exactly 60; per-card copies <= max(catalog max_copies, 4);
    #       if a swap would violate, skip it. tier/n_basis = weakest cell used.
```
**Implementation Notes**: OUT and IN are copy-aware (side out 2x Card, in 2x Card). The swap count is
`min(available_out, available_in, max_swaps)`. Locked-core uses `card_frequencies(con, archetype,
board="main", since, until)` — the SAME flex/lock primitive the tuning feature will use. Post-board legality
reuses `validate_deck` if cheap, else an inline exactly-60 + copy-cap check. Degraded matchups still appear
in the dict (with `degraded=True`) so the renderer can say "thin — no plan".
**Acceptance Criteria**:
- [ ] Established opponent: dead maindeck cards (low/neg lift) are sided OUT for high-lift sideboard cards IN;
  `post_board` sums to exactly 60 and respects copy caps; locked proactive core never appears in `side_out`.
- [ ] Thin opponent: `degraded=True`, empty out/in, `post_board == maindeck`, explanatory note.
- [ ] `side_out` and `side_in` have equal total copies (a swap conserves the 60).

### Unit 4: SideboardPackage additive fields + recommend_sideboard wiring
**File**: `src/legacy_engine/advisory/sideboard.py`
```python
@dataclass
class SideboardPackage:
    # ... all existing fields unchanged ...
    matchup_plans: dict[str, MatchupPlan] = field(default_factory=dict)   # NEW, additive
    value_informed: bool = False                                          # NEW: True if any opp cleared gate
    plan_window: tuple[str | None, str | None] = (None, None)             # NEW: window used for per-card data

def recommend_sideboard(con, field, deck_maindeck, *, reserved=0, solver="ilp", catalog=None,
                        archetype=None, since=None, until=None, opponents=None, max_swaps=4) -> SideboardPackage:
    # 1. (existing) colors, deck_tags, archetype_tags.
    # 2. NEW: opp_values = _field_matchup_values(...); matchup_pressure derived from it (gate-gated).
    # 3. _build_coverage_model(..., matchup_pressure=matchup_pressure).
    # 4. (existing) ILP/greedy solve -> the 15.
    # 5. NEW: matchup_plans = _plan_matchups(con, deck_maindeck, final_cards, opp_values, archetype, ...).
    # 6. populate the 3 new fields (value_informed = any opp cleared gate).
```
**Implementation Notes**: `archetype` (the deck's own archetype) is needed for locked-core; when None, classify
the maindeck via the existing `_classify_deck` path or skip locked-core (treat all flex). All new params have
defaults so `cli.py:905`, `report.py:305`, `tuning.py:420/528`, and `whattoplay`'s `dummy_sb` keep working
unchanged. On a rounds-less DB: `opp_values` all fail the gate → `matchup_pressure=None`-equivalent →
identical 15 + empty/degraded plans → existing tests green.
**Acceptance Criteria**:
- [ ] All existing `test_sideboard.py` assertions pass unchanged (rounds-less fixtures → identical output).
- [ ] On `make_rounds_corpus`, `value_informed=True` and `matchup_plans` contains real OUT/IN for the seeded
  established matchup.
- [ ] `whattoplay` `dummy_sb` construction + `report.py` still compile and run.

### Unit 5: Render the per-matchup plan (`advise sideboard` CLI + report)
**Files**: `src/legacy_engine/cli.py` (`advise_sideboard`, ~906), `src/legacy_engine/advisory/report.py`
(audit + a `_render_sideboard_plans` section)
**Implementation Notes**: after the 15 list, print per-opponent plans: `vs <Opp> [tier, n=..]: OUT 2x A, 1x B
| IN 2x X, 1x Y`; for degraded opponents print `vs <Opp>: thin data — no per-matchup plan (rely on 15)`.
report.py adds the plans to the audit trail + a render section. Keep the existing covered-weight + heuristic
note lines.
**Acceptance Criteria**:
- [ ] `advise sideboard` on a rounds-bearing DB prints OUT/IN per established opponent + a degraded note for
  thin ones; on a rounds-less DB prints the same output as before plus nothing spurious.
- [ ] The presence-correlational nature is surfaced (reuse the card_value disclaimer wording).

## Implementation Order
1. **Unit 1** (MatchupPlan + value adapter) — the data seam everything else needs.
2. **Unit 3** (planner) — trickiest; legality + locked-core + degradation.
3. **Unit 2** (value-aware weighting) — small, regression-gated.
4. **Unit 4** (package + wiring) — composes 1–3 into `recommend_sideboard`.
5. **Unit 5** (rendering) — CLI + report surface.

## Testing

### Unit tests
- `tests/test_sideboard.py` (extend) — **regression**: existing 88 tests stay green (rounds-less → identical).
  NEW (on `make_rounds_corpus`): value adapter gate behavior; planner OUT/IN legality (post-board=60, copy
  caps, locked-core never out, equal in/out copies); degraded path; value-aware weighting nudge bounded by
  MAX_PRESSURE and identity at `matchup_pressure=None`.
- `tests/test_advise_report.py` (extend) — report renders plans; `dummy_sb` defaults intact.
- `tests/test_cli.py` (extend) — `advise sideboard` prints plans on rounds-bearing DB; unchanged on rounds-less.

### Integration points
- Seam to `analytics.card_value` (Unit 1) — values + tiers drive both weighting and the planner.
- Seam to the tuning rework: tuning will call `recommend_sideboard(..., archetype=..., since/until=...)` and
  consume `matchup_plans`. Keep the signature stable for that consumer.

## Risks
- **Existing-test regression from value-aware weighting**: the #1 risk of an in-place rework. **Mitigation**:
  hard gate — `matchup_pressure` is None/identity unless an opponent clears the confidence gate, which never
  happens on the rounds-less fixtures the existing tests use. Verify the full `test_sideboard.py` suite is
  green before/after. **Fallback**: if any existing test shifts, the gating has a leak — fix the gate, don't
  edit the test.
- **SideboardPackage field additions break a positional constructor**: **Mitigation**: append fields with
  defaults; all known constructors use kwargs.
- **Locked-core needs the deck's archetype**: when `archetype=None` and classification is ambiguous, the
  planner treats all maindeck cards as flex (no locked-core protection). **Mitigation**: acceptable degraded
  behavior; surfaced in the note. The tuning consumer always passes `archetype`.
- **Post-board legality with odd copy counts**: a swap that would exceed `max_copies` is skipped, not forced.
  **Fallback**: fewer swaps than `max_swaps` is always legal.
