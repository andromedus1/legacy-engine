---
id: epic-advisory-output-honesty-transparency
kind: feature
stage: implementing
tags: [analytics, advisory, generation]
parent: epic-advisory-output-honesty
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Output Transparency Labeling

## Brief

Three surfaces print numbers without the context needed to trust them — three applications of the one
"Source transparency / no unlabeled headline numbers" NFR. (1) No report surfaces data currency, so a
stale DB yields confident-looking outdated output. (2) Card-inclusion percentages are reported without
foregrounding sample size — a 7-week-old current-regime Dimir Tempo (n=11) read "100%". (3)
`generate tune` reports Value/Coverage numbers with no sense of scale and no per-swap rationale, so the
user can't tell whether 0.0633 is large or whether a swap is justified.

Covers: a "data current as of <max event date>" + corpus-size header on reports (warn when newest
event is older than N days); foregrounding sample size on card-inclusion reads (gate/annotate small-n
inclusion %); adding scale-anchoring + per-swap rationale to `generate tune` output.

Does NOT cover: positioning coverage (separate feature); the underlying tune swap logic (this is about
making its output legible, not changing what it swaps).

## Epic context
- Parent epic: `epic-advisory-output-honesty`
- Position in epic: independent capability — parallelizable. Spans report/metashare/generation
  surfaces but is one coherent "label the output with its own confidence" capability.

## Inherited design decisions
- These three are unified by the source-transparency NFR; design them as one labeling pass applied to
  three output surfaces, not three unrelated changes.

## Foundation references
- `docs/SPEC.md` — NFR "Source transparency — every figure labeled with source, window, basis"; NFR "Reproducibility — deterministic given inputs + seed; no network at analysis time"
- `src/legacy_engine/analytics/metashare.py` (corpus query), `confidence.py` (`tier_for_sample`), `generation/consensus.py` (`sample_n`), `generation/tuning.py` (`TunedDeck.swaps`), `cli.py` report + generate commands

## Design decisions
- **Data-freshness**: print `// data as of <max event date> (<N> decks)` (deterministic, from the
  corpus) on every `report` subcommand, PLUS a clock-based staleness warning line (`⚠ newest event is
  X days old`) when the newest event is older than `_STALE_DAYS` (30). The header/analysis stay
  deterministic; only the advisory warning line reads the wall clock — acceptable (it's a warning, not
  analysis output, and never changes any computed figure).
- **Tune transparency**: render the existing `TunedDeck.swaps` as `cut X → add Y` lines + the headline
  Δvalue (after−before) + a one-line scale/interpretation note (per-card lifts are
  presence-correlational, typically small). No restructuring of the tune result.
- **Inclusion small-sample**: the consensus output already prints `sample_n`; add the confidence tier
  (`tier_for_sample`) next to it and a loud thin-sample warning when speculative (n<30), so a 100%
  inclusion off n=11 reads as speculative.

## Architectural choice

Three independent display/transparency surfaces, each reusing an existing domain primitive (Phase 5a:
(A) a shared `corpus_freshness` query helper in analytics + presentation owns the clock + reuse
`tier_for_sample`/`TunedDeck.swaps`; (B) inline each query/format at its call site; (C) a generic
"report header" framework). **Chosen: A.** The freshness *query* lives in the domain
(`analytics/metashare.corpus_freshness`, deterministic), while the *clock-based staleness check* lives
in the CLI presentation helper (`_echo_data_freshness`) — honoring Ports & Adapters (domain free of
wall-clock, reproducible) and the reproducibility NFR. Tune + inclusion reuse data already on the
result objects (`swaps`, `sample_n`) — pure render additions. B scatters the corpus query; C is
over-engineering for three call sites.

## Implementation Units

### Unit 1: data-freshness header + staleness warning
**Files**: `src/legacy_engine/analytics/metashare.py` (query), `src/legacy_engine/cli.py` (presentation)

```python
# metashare.py — deterministic, no wall-clock
def corpus_freshness(con, *, provenance: str | None = None) -> tuple[str | None, int]:
    """Return (max_event_date ISO 'YYYY-MM-DD' or None, labeled_deck_count) for the corpus."""

# cli.py — presentation owns the clock
_STALE_DAYS = 30
def _echo_data_freshness(con) -> None:
    """Echo '// data as of <max date> (<N> decks)' + a clock-based staleness warning when stale."""
```

**Implementation Notes**:
- `corpus_freshness` queries `tournaments` for `max(date)` (date-portion only, mixed plain/ISO-timestamp values — slice `[:10]` like `trends.py` does) and the labeled deck count from `decks`/`compute_metashare` denominator.
- `_echo_data_freshness` calls it, prints the header, and `if (date.today() - date.fromisoformat(max_date)).days > _STALE_DAYS:` prints `⚠ newest event is N days old (as of <max>) — data may be stale`.
- Call `_echo_data_freshness(con)` once near the top of each report subcommand: `meta`, `matchups`, `tiers`, `cards`, `gaps`, `trends`.

**Acceptance Criteria**:
- [ ] `corpus_freshness` returns the correct max date (date-portion) + deck count; `(None, 0)` on an empty corpus, no exception.
- [ ] Every `report` subcommand prints the `// data as of …` header.
- [ ] The staleness warning fires iff `max_date` is > 30 days before `date.today()`; the header + all computed figures are unchanged by it (determinism preserved for analysis output).

---

### Unit 2: consensus thin-sample confidence flag
**File**: `src/legacy_engine/cli.py` (`generate_consensus` echo)

**Implementation Notes**:
- Use `from legacy_engine.confidence import tier_for_sample`.
- Change the existing `sample_n={deck.sample_n}` line to include the tier: `sample_n={deck.sample_n} [{tier}]`.
- When `tier == "speculative"` (n<30), echo a warning: `// ⚠ thin sample (n={sample_n}) — modal card choices / inclusion %s are unreliable`.

**Acceptance Criteria**:
- [ ] Consensus output shows the confidence tier next to `sample_n`.
- [ ] A thin (n<30) archetype triggers the unreliable-sample warning; a healthy (n≥100) one does not.

---

### Unit 3: tune swap rationale + scale note
**File**: `src/legacy_engine/cli.py` (`generate_tune` echo)

**Implementation Notes**:
- After the Value line, when `tuned.swaps` is non-empty, render a `// Swaps:` block — one `//   cut {cut} → add {add}` per `(cut, add)` in `tuned.swaps`.
- Show the headline delta: `// Δvalue = {value_after - value_before:+.4f}` with a scale note `// (per-card field-weighted lift is presence-correlational; values are typically small — treat ordering as indicative)`.
- When `tuned.swaps` is empty (no-signal / fell_back), render `// Swaps: none` (already conveyed by the existing reason line; keep consistent).

**Acceptance Criteria**:
- [ ] A tune that made swaps lists each `cut → add` pair and the Δvalue + scale note.
- [ ] A no-swap (fell_back) tune renders cleanly ("none"), no crash.

## Implementation Order
1. **Unit 1** (freshness) — touches the most commands; do first.
2. **Unit 2** (consensus flag) — small, independent.
3. **Unit 3** (tune rationale) — small, independent.

## Testing
- `tests/test_metashare.py` (or analytics) — `corpus_freshness`: correct max-date/count on a built corpus; `(None, 0)` empty.
- `tests/test_cli.py` — `report meta` (DB-backed) prints `// data as of`; a stale-dated corpus triggers the warning, a fresh one does not (control `date.today()` via a built corpus with a recent max date — or assert the header always present and the warning gated by date math at the helper level to avoid clock-coupling in the test). `generate consensus` on a thin archetype shows `[speculative]` + the warning; `generate tune` output lists swaps + Δvalue (use existing tune test fixtures).
- Determinism: `corpus_freshness` has no wall-clock; only `_echo_data_freshness`'s warning line does — test the staleness math at the helper boundary with an injected/comparison date rather than the real clock where possible.

## Risks
- **Clock-coupling in tests** — the staleness warning reads `date.today()`, which is nondeterministic. **Fallback**: keep the date comparison trivially testable by structuring `_echo_data_freshness` so the staleness decision is a pure function of `(max_date, today)` (e.g. an inner `_is_stale(max_date, today, days)` helper) that tests call directly; the wall-clock only enters at the CLI edge.
- **"data as of" on every report adds a line** — minor output-shape change; existing CLI output tests may need the extra header line. **Fallback**: it's additive at the top; update any strict full-output assertions (most tests assert substrings).
