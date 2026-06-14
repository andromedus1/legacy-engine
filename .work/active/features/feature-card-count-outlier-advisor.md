---
id: feature-card-count-outlier-advisor
kind: feature
stage: done
tags: [advisory, analytics, generation]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

For a given decklist + archetype + regime, surface **each card's field copy-count DISTRIBUTION** (not
just the modal consensus list) and **flag where the user's list is off-consensus, and by how much.**

This session (2026-06-13) we repeatedly hand-queried distributions to validate counts, and it was the
highest-leverage deck-doctoring move of the whole conversation:
- Orcish Bowmasters: 68% run 3, 23% run 4 → "3 is modal, 4 is a real camp."
- Murktide Regent: 79% run 2, 11% run 0, 9% run 3 → "2 is firmly standard."
- Lands: 73% run 19, 21% run 20, only 5% run 18 → caught a wrong 18-land rec.
- Daze: user at 2, field mode 3 → flagged as the one off-consensus count.

`generate consensus` already produces a modal deck, but it does NOT tell you *"on card X you're an
outlier — here's the field distribution and where your count sits."* That per-card outlier report is
what turns a list into a tuned list. Should be ban-regime-windowed by default
([[idea-ban-regime-everywhere]]) and could pair with variant clustering
([[idea-subarchetype-variants]]) so the distribution is compared within the right build, not the
whole parent archetype.

---

## Design

### Summary
A per-card **copy-count outlier advisor**: given a user decklist + archetype + window, it surfaces
each card's **field copy-count distribution** (the share of archetype decks running 0/1/2/3/4… copies)
and flags where the user's count sits off the field's modal count, with a magnitude. This is the
distribution layer underneath the existing modal-only `card_frequencies` primitive — `generate
consensus` answers "what's the modal list"; this answers "on card X you're an outlier — here's the
spread and where you sit."

### Architectural choice (2-3 options weighed)

**Option A — extend `card_frequencies` to also return the full distribution.** Reject. The consensus
fill/reconciliation path consumes `CardFreq` (modal_count only) and adding a `distribution` field
would either bloat every consensus query or force two query shapes through one function. The
`card_frequencies` query already computes per-count `freq` in its `card_counts` CTE and then collapses
to modal — the distribution is *thrown away* there. We want a sibling query that **keeps** it.

**Option B (chosen) — new pure-analysis module `generation/card_distribution.py`** with (1) a thin
DB primitive `card_count_distributions(...)` that returns the full per-count distribution dict, and
(2) a pure `diff_deck_vs_field(...)` that compares a parsed decklist's counts against that dict and
emits per-card `CardCountDelta` records (no DB). This follows the **objective-search-split** pattern
(heavy DB query once → plain dict → pure, hand-testable comparison loop) and keeps consensus.py
untouched (its tests stay green — **gated-additive** spirit: zero change to the shipped modal path).

**Option C — fold it into `report cards` / `advise report`.** Reject. `report cards` is
win-rate-correlational per-card value (a different axis), and `advise report` is the heavyweight
field-read. Copy-count tuning is a deck-construction concern, so it belongs in the `generate` group
alongside `consensus`/`tune` (deck generation = "build/tune a list").

**CLI command: `generate doctor`** (new leaf in the existing `generate` group). Justification: it takes
a `--deck <file>` like `generate tune`, resolves the archetype (override or classify), windows to the
ban regime by default, and emits a tuning-oriented per-card report — it "doctors" the user's list
against field consensus. Name is consistent with the `@generate.command(...)` nested-group pattern and
reads naturally next to `consensus` and `tune`. (Rejected `report list-deltas`: `report` is the
meta/performance descriptive group, not deck-input-driven; this surface is deck-in/advice-out.)

### Windowing decision
Default to the **latest ban regime**, reusing the same path `consensus`/`report cards` already use:
`from legacy_engine.generation.consensus import _latest_regime_window`. This is a **deck-based**
surface (it counts archetype decks, not rounds), so it does NOT use the rounds-thinness degrade in
`resolve_advisory_window` — matching the precedent set by `generate consensus` and `report cards`,
which both window via `_latest_regime_window()` directly and convey thinness via confidence tiers, not
the rounds banner. `--since/--until` override; `--all-time` uses the full corpus. (We deliberately do
NOT wire the full `--regime`/adaptive `_window_opts` stack: `card_count_distributions` queries a single
archetype's deck pool over one window — the per-cell adaptive matrix machinery is matchup-matrix-only
and irrelevant here. Plain `--since/--until/--all-time` options mirror `generate consensus`.)

The item floats variant-clustering ([[idea-subarchetype-variants]]) as a future pairing — **out of
scope here**; we compare against the whole parent archetype's pool and note the limitation in the
output footer. Logged as a follow-up consideration, not a child story.

### Interfaces / signatures

**File: `src/legacy_engine/generation/card_distribution.py`** (new)

```python
from dataclasses import dataclass, field as dc_field

@dataclass(frozen=True)
class CardCountDist:
    """Field copy-count distribution for one card in one archetype+board over a window.

    ``dist`` maps copy-count -> fraction of the archetype's decks running EXACTLY that many.
    Counts of 0 (decks that DON'T run the card) ARE included so percentages sum to 1.0 over the
    full archetype pool — this is what makes "11% run 0" (Murktide) expressible.
    ``modal_count`` = the count with the highest share (ties -> higher count, matching CardFreq).
    ``decks_total`` = archetype deck count in the window (the denominator / sample_n).
    """
    name: str
    board: str                     # "main" | "side"
    dist: dict[int, float]         # copy_count -> fraction (sums to ~1.0 incl. the 0 bucket)
    modal_count: int
    decks_total: int

def card_count_distributions(
    con, archetype, *, board, since=None, until=None, provenance=None,
) -> dict[str, CardCountDist]:
    """Heavy DB path (runs ONCE). Per-card full copy-count distribution for an archetype+board.

    Window defaults to the latest ban regime when since AND until are both None (same trigger as
    card_frequencies). The 0-bucket is computed as decks_total - sum(running-deck freqs) so the
    distribution is over the WHOLE archetype pool, not just decks that run the card.
    Returns {} when the archetype has no decks in the window.
    """

@dataclass(frozen=True)
class CardCountDelta:
    """One card's user-count-vs-field comparison."""
    name: str
    board: str
    user_count: int                # copies in the user's list (0 if absent but field runs it)
    field_modal: int               # field's modal count
    field_dist: dict[int, float]   # the full distribution (for rendering "68% at 3 / 23% at 4")
    delta: int                     # user_count - field_modal (signed magnitude)
    user_share: float              # fraction of field running EXACTLY user_count (0.0 if none)
    is_outlier: bool               # user's count is below the outlier-share gate (see policy)
    decks_total: int               # denominator (drives the confidence tier)

@dataclass(frozen=True)
class DeckDoctorReport:
    archetype: str
    window: tuple[str | None, str | None]
    decks_total: int               # sample_n for the whole report
    deltas: list[CardCountDelta]   # sorted: outliers first (by |delta| desc), then on-consensus
    not_in_field: list[str]        # user cards the field never runs in this archetype+board
    board: str

_OUTLIER_SHARE_FLOOR: float = 0.15  # user's count run by < this share of the field -> flagged outlier

def diff_deck_vs_field(
    user_counts: dict[str, int],          # parsed mainboard OR sideboard (name -> copies)
    dists: dict[str, CardCountDist],      # from card_count_distributions (same board)
    *,
    board: str,
    outlier_floor: float = _OUTLIER_SHARE_FLOOR,
) -> tuple[list[CardCountDelta], list[str]]:
    """PURE comparison (no DB). Returns (deltas, not_in_field).

    For every card in EITHER the user's list or the field dists:
      - field_dist/modal/decks_total from dists[name] (or empty if user-only -> not_in_field).
      - user_share = field_dist.get(user_count, 0.0).
      - is_outlier = (name in dists) AND user_share < outlier_floor AND user_count != field_modal.
    A card the user runs that the field never runs in this archetype goes to not_in_field (never an
    'outlier' — there's no distribution to be off of). Deterministic ordering for stable output.
    """

def build_deck_doctor_report(
    con, user_main, user_side, archetype, *,
    since=None, until=None, provenance=None, board="main",
) -> DeckDoctorReport:
    """Orchestrator: runs card_count_distributions ONCE per requested board, wires diff_deck_vs_field,
    assembles the report. Resolves the default window via _latest_regime_window when since/until None."""
```

**File: `src/legacy_engine/cli.py`** — new `@generate.command("doctor")` leaf:
```
generate doctor --deck <file> [--archetype NAME] [--board main|side|both]
                [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--all-time]
                [--min-tier speculative|evolving|established] [--db PATH] [-v]
```
Body (mirrors `generate tune`'s plumbing): `_parse_decklist(Path(deck).read_text())` →
resolve archetype (use `--archetype` else `_classify_deck(con, main, side)` and echo the classified
label, exactly as `advise positioning`/`whattoplay` do) → `build_deck_doctor_report(...)` per board →
`_render_deck_doctor(report)`. Reuse `_echo_data_freshness(con)` for the currency header and
`tier_for_sample(report.decks_total)` for the sample tier + thin-sample warning banner (copy the
speculative-warning pattern from `generate_consensus`). Lazy imports inside the command per the CLI
pattern.

### Rendering (`_render_deck_doctor` in cli.py, pure-ish text)
Per the validated hand outputs:
```
=== Deck Doctor: Izzet Delver  [regime 2026-05-18 → current]  sample_n=212 [established] ===

OUTLIERS (your count is off the field consensus):
  Daze              you run 2   field mode 3  (3: 61%, 2: 18%, 4: 12%)   Δ-1  [only 18% run 2]
  lands             you run 18  field mode 19 (19: 73%, 20: 21%, 18: 5%) Δ-1  [only 5% run 18 — outlier]

ON CONSENSUS:
  Orcish Bowmasters you run 4   field mode 3  (3: 68%, 4: 23%)           Δ+1  [23% run 4 — a real camp]
  Murktide Regent   you run 2   field mode 2  (2: 79%, 0: 11%, 3: 9%)    Δ 0

NOT RUN BY THE FIELD (this archetype, main): Chrome Mox, Lava Spike
// distribution compared against the whole 'Izzet Delver' pool (no sub-archetype/variant split yet)
```
Distribution string shows counts ordered by share desc, top ~3 buckets. The "real camp" / "outlier"
annotations derive purely from `user_share` vs `outlier_floor`. Reuse `--min-tier` to suppress the
whole report (with a note) when `tier_for_sample(decks_total)` is below the gate, matching
`report cards`' suppression-with-note honesty contract.

### Units (build order — trickiest first)
1. **U1 `card_count_distributions` (DB primitive).** Trickiest: the **0-bucket**. The query gets
   per-count `freq` (like `card_frequencies`' `card_counts` CTE) and `decks_total`; the 0-share is
   `decks_total - Σ freq` over running decks, divided by `decks_total`. Half-open `[since, until)`
   window + provenance filter + `_latest_regime_window()` default — copy the exact WHERE/CTE shape
   from `card_frequencies` so windowing semantics match consensus byte-for-byte. Returns `{}` on
   empty archetype.
2. **U2 `diff_deck_vs_field` + `CardCountDelta`/`DeckDoctorReport` (pure).** No DB. The outlier gate,
   the `not_in_field` split, deterministic ordering. This is where the hand-validated examples become
   unit tests.
3. **U3 `build_deck_doctor_report` (orchestrator).** Window resolution, per-board query, wiring.
4. **U4 CLI `generate doctor` + `_render_deck_doctor`.** Plumbing + rendering + tier/freshness banners.

Single feature, no child stories — four tightly-coupled units in one module + one CLI leaf, well
under the spawn threshold. Implement inline-orchestrated.

### Test plan
**`tests/test_card_distribution.py`** (house style: in-memory store + `parse_cache_item`, `TestX`
classes, deterministic; extend the existing Delver fixture from `test_generation_consensus.py` —
Murktide at 8/10 @ 2 already gives a 0-bucket of 0.2):
- `TestCardCountDistributions` (DB): inclusion/0-bucket math — Murktide → `{2: 0.8, 0: 0.2}` (8/10 run
  it @ 2, 2/10 don't); a mixed-count card (build a fixture where 6 decks run 3 and 4 run 4 → `{3: 0.6,
  4: 0.4}`); modal tie → higher count; window default = latest regime; `{}` on unknown archetype.
- `TestDiffDeckVsField` (PURE, hand-built dists — the core): replay all four validated examples —
  Bowmasters user 4 vs `{3:.68,4:.23}` → on-consensus (23% ≥ 15% floor, Δ+1); lands user 18 vs
  `{19:.73,20:.21,18:.05}` → outlier (5% < floor); Daze user 2 vs `{3:.61,2:.18,4:.12}` → 18% ≥ floor
  so NOT flagged at default floor (document this — tune floor or note it's the borderline case the item
  called "off-consensus"; pick floor so the item's intent holds: **set `_OUTLIER_SHARE_FLOOR` so Daze
  @ 18% is borderline — verify against the item's "flagged as the one off-consensus count" and adjust
  floor to ~0.20 if needed, logging the rationale**); Murktide user 2 → Δ0 on-consensus; a user card
  absent from dists → `not_in_field`; user runs 0 of a field staple → outlier with `user_count=0`.
- `TestBuildReport` (orchestrator, DB): end-to-end on the Delver fixture; ordering (outliers first by
  |Δ|); `decks_total` populated.
- `tests/test_cli.py`: add a `generate doctor` smoke test (CliRunner over the in-memory fixture DB via
  `--db`) asserting an outlier line and the sample-tier banner render; assert `--archetype` override
  path and the classify-and-echo path.
- **Regression:** no change to `consensus.py`, so `test_generation_consensus.py` stays green untouched
  (the gated-additive contract).

### Risks / pre-mortem
- **Outlier-floor calibration.** A single 15% floor may mis-call borderline cards (Daze @ 18%). Mitigation:
  make it a named constant + CLI-overridable later; pin the default by replaying the item's four
  hand-validated calls as tests and choosing the floor that reproduces the human verdict; log the
  chosen value's rationale in the test.
- **0-bucket correctness.** If a deck runs a card across split entries (rare in this corpus —
  `deck_cards` is pre-aggregated per name) the per-deck count could double-count. Mitigation: the
  existing `card_frequencies` query already groups by `(name, count)` per deck-row and the corpus
  stores one row per (deck, card); mirror its exact CTE so behavior is identical. Add a fixture deck
  with a card at an unusual count to prove the bucket.
- **Sideboard semantics.** Sideboard "0-bucket" is noisier (15-card boards vary a lot). Mitigation:
  `--board` defaults to `main`; `both` runs the side report under a clear sub-header; tiers convey the
  thinness.
- **Variant blindness.** Comparing against the whole parent archetype can wash out a legitimate
  sub-build's counts (the item's [[idea-subarchetype-variants]] pairing). Mitigation: out of scope;
  the footer states the comparison pool explicitly so the user isn't misled. Follow-up, not a blocker.
- **Window mismatch with consensus.** If `generate doctor` and `generate consensus` resolved different
  default windows the advice would contradict. Mitigation: both call the SAME `_latest_regime_window()`
  — single source of truth, asserted by a test that the two surfaces report the same window for one
  archetype.

---

## Implementation notes

**Files created:**
- `src/legacy_engine/generation/card_distribution.py` — `CardCountDist`, `CardCountDelta`,
  `DeckDoctorReport` dataclasses; `card_count_distributions` DB primitive;
  `diff_deck_vs_field` pure comparison; `build_deck_doctor_report` orchestrator.
- `tests/test_card_distribution.py` — 38 tests (U1-U4 + CLI smoke tests).

**Files modified:**
- `src/legacy_engine/cli.py` — `generate doctor` CLI leaf + `_render_deck_doctor` renderer.
  Added additively after `generate_tune` without restructuring the file.

**`_OUTLIER_SHARE_FLOOR` = 0.20** — chosen to satisfy all four hand-validated examples:
- Bowmasters @ 4: 23% of field → NOT outlier (23% ≥ 20%). "A real camp." ✓
- Murktide @ 2: 79% of field → NOT outlier. ✓
- Lands @ 18: 5% of field → outlier (5% < 20%). ✓
- Daze @ 2: 18% of field → outlier (18% < 20%). ✓ (With 0.15, Daze would NOT be flagged —
  contradicting the design's "flagged as the one off-consensus count" verdict.)

**Window SSOT:** CLI resolves the window before calling `build_deck_doctor_report`
(mirrors `report_cards` at cli.py:874). The `--all-time` flag passes `apply_default_window=False`
to prevent the orchestrator from re-applying `_latest_regime_window()`. The window SSOT test
(`TestBuildReport.test_window_ssot_matches_consensus`) asserts both surfaces resolve to the
same `_latest_regime_window()` values.

**Deviations from design:**
- `apply_default_window` parameter added to `card_count_distributions` and
  `build_deck_doctor_report` to distinguish "use default" from "explicit full corpus (--all-time)".
  Required because Python has no null-sentinel distinct from None. The design spec didn't need to
  address this since it described the CLI surface, not the internal calling convention.
- `_tier_order` dict kept local inside `_render_deck_doctor` (a local variable, not module-level)
  to stay additive; `report_cards` keeps its own local `_TIER_ORDER` unchanged.

**gated-additive contract:** `consensus.py` untouched — `test_generation_consensus.py` green.
