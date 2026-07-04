---
id: epic-sb-config-evaluation-matchup-slot-test
kind: feature
stage: done
tags: [analytics]
parent: epic-sb-config-evaluation
depends_on: []
release_binding: v0.2.0
gate_origin: null
created: 2026-06-29
updated: 2026-06-29
---

# Matchup-conditioned sideboard-slot test

## Brief

Let the operator test a candidate sideboard card against a specific target matchup: for a
given archetype, compare win-rate **WITH** the card (in `board=side`) vs **WITHOUT** it,
*within the same archetype and the same opponent matchup*. This is the
within-archetype/within-matchup, with-vs-without contrast — the empirical answer to "does this
slot actually pull weight vs this deck?"

**Why it's net-new.** Two adjacent capabilities exist but answer different questions:
- `report cards --vs Y --board side` (via `card_value_matchup`) returns *lift vs the card's
  own prior* — the wrong baseline for this question, and it nearly misled us (see below).
- `report subgroup` splits an archetype on a signature card but is **not** conditioned on an
  opponent or on `board=side`.

This feature is most naturally the intersection: extend `analytics/subgroup.py` /
`report subgroup` to accept `--vs OPPONENT` + `--board {main,side}` (vs. a new `report` leaf —
exact surface is a `feature-design` call).

## Hard requirement (surfaced during investigation — do NOT skip)

The output **must** ship with statistical honesty or it will mislead:
- **Wilson CIs on each side** (WITH and WITHOUT).
- **A two-proportion significance test on the diff** (z-test / Fisher), with the p-value and an
  explicit "not significant" flag.
- **A loud presence-correlational + thin-n banner** (honest-degrade marker pattern).

Motivation: in session analysis, Null Rod vs Blue Artifacts showed WITH 38.0% (n=71) vs
WITHOUT 46.3% (n=67), a −8.2pt point estimate that *looked* like the premier anti-artifact
card was counterproductive. A two-proportion test gave **z=−0.98, p=0.33 — not significant**;
the CIs ([28,50] vs [35,58]) overlap almost entirely. Without the significance gate the raw
−8.2 reads as a real (and wrong, against first principles) finding. The contrast also revealed
the confound directly: "Blue Artifacts" wins through artifact *creatures* (Kappa Cannoneer,
Patchwork Automaton, Emry, Urza's Saga constructs) that attack through a Null Rod, so the
winning non-Null-Rod lists leaned on creature removal + free counters — exactly first
principles, not "Null Rod is bad."

## Validated prototype (reference for the spec)

A by-hand prototype already produces the target output (within-archetype, `board=side`,
with-vs-without, per opponent). Representative Dimir Tempo results:

| SB card | vs | WITH | WITHOUT | diff | significant? |
|---|---|--|--|--:|--|
| Toxic Deluge | Death & Taxes | 40.6% (n=69) | 29.9% (n=87) | +10.7 | borderline (the one positive signal) |
| Null Rod | Blue Artifacts | 38.0% (n=71) | 46.3% (n=67) | −8.2 | no (p=0.33) |

Note Null Rod is essentially side-only in this archetype (side=1597, main=1), so the
side-based contrast isn't corrupted by maindeck copies — but the spec should still classify
"owns the card" cleanly (consider main+side) to avoid that bug class in other cards.

## Scope notes
- Reuses `compute_card_winrates`' engine dedup (the `dup`/`uniq_decks` CTEs) — do NOT hand-roll
  a `rounds`↔`decks` join (a naive join fans out on the 432 duplicate `(tournament, player)`
  deck rows and inflates n ~3×).
- Honors the data ceiling recorded on the parent epic (presence ≠ played; thin per-matchup
  samples).
- Output feeds the config comparator (the next feature) as its measured per-matchup SB-lift
  input.

## Review record
- **Verdict**: Approve with comments (deep lane, fresh-context reviewer). No blockers.
- **Statistics verified correct**: Fisher 2x2 orientation, Wilson/Jeffreys CI usage, exclusion
  parity with `compute_match_results`, `(tid, hero_norm)` dedup grain (no fan-out),
  `pair_adaptive_since` ≡ `build_adaptive_matrix` windowing, no numpy leakage.
- **Findings — all resolved in-session before advancing** (chose fix-now over follow-up items
  since the test gaps were stated acceptance criteria and #1 was a real bug):
  - *Important #1*: `--contrast` defaulted `--board main`; this is the sideboard test → now
    defaults `side` unless `--board` is explicitly passed (Click `get_parameter_source`).
  - *Important #2*: added CLI tests (`tests/test_cli.py::TestReportCardsContrast`) — fail-fast
    without `--vs`/`--archetype`, both windows print, disclaimer prints, scan-vs-single-card
    multiple-comparisons banner, board default, non-contrast path unchanged.
  - *Important #3*: added dual-window + `pair_adaptive_since` tests (`TestWindowing`).
  - *Important #4*: added thin-tier test (`TestThinTier`) asserting speculative tier + `any_thin`.
  - *Nit #5*: removed the dead `multi_card` param from `_echo_slot_contrast`.
  - *Nit #6*: added a `report cards --contrast` line to `docs/ARCHITECTURE.md` CLI conventions.
  - *Nit #7*: commented the deliberate half-open `[since, until)` alignment in `_RESOLVE_SQL`.
- Full suite green after fixes: **2259 passed**.

## Implementation notes
- **Files changed**: `src/legacy_engine/analytics/slot_test.py` (new — compute + dataclasses +
  `pair_adaptive_since`), `src/legacy_engine/cli.py` (extended `report cards` with `--contrast`
  / `--card`; added `_report_cards_contrast` + `_echo_slot_contrast` render helpers).
- **Tests added**: `tests/analytics/test_slot_test.py` (buckets + exclusions, no-fan-out on
  duplicate player, significant vs near-50/50 Fisher, empty cohort, cards=None scan). Full
  suite green (2248 passed).
- **Validated against the hand-prototype**: full-corpus Toxic Deluge vs Death & Taxes reads
  40.6% (n=69) / 29.9% (n=87), diff +10.7 — exact match. Dual-window pays off immediately:
  Null Rod vs D&T shows +13.8 in the adaptive (regime-current) window vs the full-corpus
  Blue-Artifacts −8.2 — different opponents, different stories, both visible.
- **Discrepancies from design**:
  - Sort refined from pure `abs(diff)` desc to **robust-cohort-first** (cells whose smaller
    cohort has n≥30 sort above thinner ones, then by `abs(diff)`; no-diff cells last). Pure
    `abs(diff)` floated n=1/n=2 noise (+67% on a single deck) to the top and buried the real
    signal. Still shows every cell (honest-degrade) — just demotes the noise. In the design's
    intent ("surface the slots that pull weight"), not a deviation from it.
  - Numpy scalars from `scipy.stats.fisher_exact` coerced to native `float`/`bool` so the
    public dataclass never leaks numpy types.
- **Adjacent issues parked**: none.

## Design decisions
- **CLI surface**: Extend `report cards` with a `--contrast` mode (NOT a new leaf, NOT
  `report subgroup`). — `report cards --archetype X --vs Y --board side` already takes exactly
  the right inputs and iterates the archetype's cards, so the "what in my SB helps vs D&T?"
  scan comes for free and `--card` focuses one card. `--contrast` swaps the lift-vs-prior
  columns for the with/without-in-matchup contrast. subgroup was rejected (composition-diff vs
  win-rate output-shape mismatch).
- **Windowing**: Show BOTH windows in one run — an **adaptive (per-cell ban-aware,
  regime-current)** section AND a **full-corpus (all-time)** section, each with its own
  n / CI / significance, mirroring how `report matchups` prints `[all]`/`[online]`/`[paper]`.
  Adaptive is the ideal-but-thin view; full-corpus is the more-data-but-stale view; the
  operator judges. `--since/--until` still override to a custom single window.

## Architectural choice

Three approaches considered (Phase 5a):
- **(A · chosen)** New focused module `analytics/slot_test.py` computing the win-rate contrast,
  surfaced by extending `report cards --contrast`. Reuses `match_results`' dedup join (the
  `dup`/`uniq_decks` CTEs), `matchup.wilson_or_jeffreys_ci` for CIs, and the
  `affectedness`/`matchup` adaptive-window logic. Clean separation: a new statistic gets a new
  module; the surface is the one the operator already knows.
- **(B · rejected)** Put the compute in `analytics/matchup.py`. Rejected — matchup.py is
  matrix-focused; a card-presence-conditioned contrast is a distinct concern that would bloat it.
- **(C · rejected)** Extend `analytics/subgroup.py` + `report subgroup`. Rejected per the CLI
  decision — subgroup measures composition diffs (avg copies); the slot-test measures matchup
  win-rate. Sharing the "split on card presence" idea isn't worth the output-shape mismatch.

The contrast is fundamentally "split this archetype's *matches vs opponent Y* by whether the
hero deck owns card Z on `board`, then compare the two cohorts' win-rates." The proven
prototype keyed ownership by `(tournament_id, normalized_player)` — the same grain
`match_results` resolves matches to — so no `deck_idx` plumbing is needed.

## Implementation Units

### Unit 1: Win-rate contrast compute (trickiest — design-first)

**File**: `src/legacy_engine/analytics/slot_test.py` (new)

```python
from dataclasses import dataclass
from legacy_engine.confidence import ConfidenceLevel

@dataclass
class SlotContrastCell:
    card: str
    board: str                 # "main" | "side"
    opponent: str
    w_with: int; n_with: int    # hero won / decisive matches, hero OWNS card on board
    w_without: int; n_without: int
    p_with: float | None        # w_with / n_with (None if n_with == 0)
    p_without: float | None
    ci_with: tuple[float, float] | None     # Wilson, via matchup.wilson_or_jeffreys_ci
    ci_without: tuple[float, float] | None
    diff: float | None          # p_with - p_without (None if either side empty)
    p_value: float | None       # Fisher's exact (scipy.stats.fisher_exact), two-sided
    significant: bool           # p_value is not None and p_value < alpha
    tier_with: ConfidenceLevel  # tier_for_sample(n_with)
    tier_without: ConfidenceLevel

@dataclass
class SlotContrastReport:
    archetype: str
    opponent: str
    board: str
    window_label: str           # "adaptive (since YYYY-MM-DD)" | "full-corpus"
    cells: list[SlotContrastCell]   # sorted by abs(diff) desc, None-diff last; tie-break name
    degraded: bool              # True if opponent matchup pool is empty / all cells thin
    note: str | None            # named-reason degrade banner text when degraded

def card_matchup_contrast(
    con, archetype: str, opponent: str, *,
    board: str = "side",
    cards: list[str] | None = None,     # None = all cards archetype runs on `board`
    since: str | None = None,
    until: str | None = None,
    alpha: float = 0.05,
) -> SlotContrastReport: ...
```

**Implementation Notes**:
- **Match resolution**: one query reusing `match_results._DUP_UNIQ_CTE`, returning resolved
  decisive `archetype`-vs-`opponent` rows as `(tournament_id, hero_norm, won)`. Apply the exact
  same guards as `compute_match_results`: drop byes/draws (`parse_match_result(...).winner is
  None`), ambiguous names (`amb1/amb2`), unmatched (`arch is None`), and mirrors. Do NOT
  hand-roll the join — the naive join fans out on the 432 duplicate `(tournament, player)` rows.
- **Ownership**: one query over `deck_cards ⋈ decks` for `archetype` decks → `card →
  set[(tournament_id, hero_norm)]` on `board`. Bucket each resolved match per candidate card by
  `hero in owners[card]`. `cards=None` → the candidate set is every card the archetype runs on
  `board` (so the scan answers "what in my SB helps vs Y?"); `cards=[Z]` focuses.
- **Stats**: `p = w/n`; Wilson CI via `matchup.wilson_or_jeffreys_ci`; significance via
  `scipy.stats.fisher_exact([[w_with, n_with-w_with],[w_without, n_without-w_without]])`
  (two-sided) — Fisher, not z, because per-matchup n is routinely < 100 and the normal-approx
  is unsafe there.
- **Degrade**: if the opponent pool is empty → `degraded=True` + named reason. Per-card: when a
  cohort is empty (card in 0 or all decks) leave that side's `p/ci=None`, `diff=None`.

**Acceptance Criteria**:
- [ ] On a hand-built DB, `(w_with,n_with,w_without,n_without)` match a by-hand count.
- [ ] Ownership keyed by `(tournament_id, hero_norm)` matches `match_results` grain (no fan-out:
      a known-duplicate-player tournament does not inflate n).
- [ ] `significant` is False for a constructed non-significant split (e.g. 38% n=71 vs 46% n=67
      → p≈0.33) and True for a constructed clearly-significant split.
- [ ] Empty cohort → `p/ci/diff = None`, no exception.
- [ ] Mirrors / byes / draws / ambiguous / unmatched are excluded identically to
      `compute_match_results`.

### Unit 2: Dual-window resolution

**File**: `src/legacy_engine/analytics/slot_test.py` (helper in same module)

**Implementation Notes**:
- Adaptive window for the pair = `[max(valid_since(archetype), valid_since(opponent)), None)`,
  using the same ban-affectedness source `report matchups`' adaptive matrix uses
  (`analytics/affectedness` → `analytics/matchup.build_adaptive_matrix`). Produce a
  `window_label` like `"adaptive (since 2024-12-16)"`.
- Full-corpus = `since=until=None`, label `"full-corpus"`.
- When the caller passes explicit `--since/--until`, skip the dual view and run that one
  custom window (label `"custom (… to …)"`).

**Acceptance Criteria**:
- [ ] Default (no since/until) yields exactly two reports: adaptive + full-corpus.
- [ ] Adaptive `since` equals the later of the two archetypes' `valid_since`.
- [ ] Explicit `--since/--until` yields one custom-window report.

### Unit 3: `report cards --contrast` CLI wiring

**File**: `src/legacy_engine/cli.py` (extend the existing `report cards` leaf)

**Implementation Notes**:
- Add `--contrast` flag. **Fail-fast** (Click `ClickException`) when `--contrast` is set without
  both `--archetype` and `--vs` (the contrast needs an archetype scope and an opponent).
- `--board` already exists; defaults `side` makes sense for contrast but honor an explicit value.
- Dispatch: if no explicit `--since/--until`, call `card_matchup_contrast` twice (adaptive +
  full-corpus) and render two sections; else render the single custom-window section.
- Follow the **advisory-window-resolution-block** + **audit-echo comment-lines** patterns
  (`// data as of …`, `// window: …`) and close the connection before rendering.

**Acceptance Criteria**:
- [ ] `--contrast` without `--vs` (or without `--archetype`) raises a clear `ClickException`.
- [ ] Default prints both an adaptive and a full-corpus section, each labeled.
- [ ] Non-contrast `report cards` behavior is byte-identical (gated-additive).

### Unit 4: Contrast rendering + honesty banners

**File**: `src/legacy_engine/cli.py` (render helper alongside the leaf)

**Implementation Notes**:
- Per window, a table: `Card | n_with | WR_with [CI] | n_without | WR_without [CI] | diff | p | sig`.
- Loud banners (honest-degrade-marker pattern): (a) a fixed **presence-correlational, NOT
  causal** disclaimer; (b) a **thin-n** note when a cohort is speculative; (c) a
  **multiple-comparisons** caution when scanning >1 card (per-card p-values are uncorrected, so
  scanning inflates false positives — interpret a lone "significant" with skepticism);
  (d) the degrade banner with named reason when `degraded`.
- `sig` column renders e.g. `yes (p=0.01)` / `no (p=0.33)` / `—` (empty cohort).

**Acceptance Criteria**:
- [ ] Scanning >1 card prints the multiple-comparisons caution; single `--card` does not.
- [ ] A speculative cohort triggers the thin-n banner and the row shows its tier.
- [ ] The presence-correlational disclaimer always prints.

## Implementation Order

1. **Unit 1** (compute) — everything hangs on the bucketing + stats being correct; prototype-proven.
2. **Unit 2** (dual-window) — small; depends on Unit 1's signature.
3. **Unit 3** (CLI wiring) — depends on Units 1-2.
4. **Unit 4** (rendering) — depends on Unit 1's dataclasses; co-developed with Unit 3.

## Testing

### Unit tests: `tests/analytics/test_slot_test.py`
- **File-backed hermetic DB** (per the file-backed-cli-test-db-builder pattern): `_build_slot_db(tmp_path)` stands up tournaments/decks/deck_cards/rounds with a known hero archetype, one opponent, a couple of SB cards, and hand-chosen results so with/without buckets are predictable. Deterministic.
- Cases: clean with/without counts; no-fan-out on a duplicated player; empty cohort (card in 0 / all decks); thin (n<30) → speculative tier + thin flag; significant vs non-significant Fisher outcomes (construct the p≈0.33 case from the Null Rod numbers); mirror/bye/draw/ambiguous exclusion parity with `compute_match_results`.

### Unit tests: window resolution
- Adaptive `since` = later `valid_since`; default → two reports; explicit window → one.

### CLI tests: `tests/test_cli.py` (extend)
- Invoke with `--db <tmp>` (NEVER the default DB — the green-local/red-CI trap): `report cards --contrast --archetype X --vs Y --board side` prints both sections; `--contrast` without `--vs` errors; non-contrast path unchanged.

## Risks

- **Presence ≠ played** (data ceiling): owning a card on a board ≠ boarding it in for the match.
  Inherent to the corpus (no game-level/sideboarding data). **Mitigation**: the
  presence-correlational banner is mandatory, never suppressed — this is the headline honesty
  guard, the one that nearly let the Null Rod −8.2 mislead.
- **Multiple comparisons on the scan**: testing every SB card vs one opponent inflates the
  family-wise false-positive rate; an uncorrected per-card `significant=True` is weak evidence.
  **Mitigation**: the multiple-comparisons caution banner on multi-card scans; do NOT silently
  apply Bonferroni (it'd hide the already-rare real signals) — surface, don't correct.
- **Ownership dedup**: a `(tournament, player)` with >1 deck row is ambiguous. **Mitigation**:
  the same `dup`/`uniq_decks` guard that match resolution uses; ambiguous heroes are dropped,
  not attributed.
- **Adaptive window too thin to be useful**: for post-ban archetypes the adaptive section may be
  all-speculative. **Fallback**: that's *why* the full-corpus section is shown alongside —
  there's always a more-data view, clearly labeled stale.
