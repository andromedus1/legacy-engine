---
id: epic-gap-discovery-archetype-gaps
kind: feature
stage: implementing
tags: [generation, discovery]
parent: epic-gap-discovery
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Archetype-Gap Finder (`report gaps`)

## Brief

Surfaces **under-explored archetypes** — shells with high positioning `S` (well-positioned
versus the current field, per `advisory/positioning`) but low meta-share (per
`analytics/metashare`). These are the strategies the field is sleeping on: strong matchup
math, little adoption. Ranks archetypes by a gap score of the shape `S − g(share)` (reward
strong position, penalize already-popular), confidence-gated so a shell whose `S` rests on
thin matchup data does not surface.

Delivers a new `report gaps` CLI command in the existing `report` family
(`report meta|matchups|tiers|trends|cards`), following that group's established output
conventions and disclaimer wording. This is the **archetype-gap half** of deck-generation
mode 3 — mechanical, composing two already-shipped surfaces; the brief flags it as needing
no external research.

Does NOT cover card-level discovery (the adjacent swap-in half — see the sibling features).
It only ranks whole archetypes, not cards within a deck.

## Epic context

- Parent epic: `epic-gap-discovery`
- Position in epic: independent capability — no shared types with the card-discovery half;
  fully parallelizable with `epic-gap-discovery-adjacency`.

## Inherited design decisions

- **Archetype-gap surface = new `report gaps` command** — fits the existing `report` family
  pattern rather than folding an under-explored column into `report tiers` (keeps the two
  distinct reads uncoupled).
- Gate the gap ranking by the **existing `ConfidenceMetadata` tiers** — never surface an
  archetype whose `S` is computed from thin matchup data.
- The exact gap-score shape (`g(share)`) and display threshold are this feature's own
  design-pass calls.

## Research briefs

- `docs/briefs/card-adjacency-and-discovery.md` §4 (the archetype-gap half — "rank archetypes
  by `S − g(share)`; reuses positioning + metashare; no external research required").

## Foundation references

- `src/legacy_engine/advisory/positioning.py` — `positioning_score` / `PositioningResult`
  (`S` is the well-positioned-vs-field score).
- `src/legacy_engine/analytics/metashare.py` — `compute_metashare` / `MetaShareReport`
  (meta-share per archetype).
- `src/legacy_engine/cli.py` — `report` command group (`@report.command(...)`, ~line 148+).

## Design decisions

Resolved with judgment during feature-design (autopilot delegation); mechanical choices, not
strategic forks (the surface = `report gaps` was locked at the epic):

- **Module placement = `advisory/gaps.py`** — it composes `advisory.positioning.rank_decks` AND
  `analytics.metashare`; since `advisory/` already sits downstream of `analytics/`, this home
  imports both without a dependency cycle (an `analytics/gaps.py` would create a back-edge).
- **Position term = MC `rank_decks`** — reuse the shared-field Monte-Carlo positioning, which
  already yields `s_mean`, the risk-adjusted lower-quantile `s_quantile`, `data_coverage`, and
  `low_coverage`. No new scoring.
- **Gap score = `s_mean − share_weight · share`** (g = linear, `share_weight` default 1.0) —
  interpretable: rewards high positioning, penalizes already-popular. `share_weight` is a CLI lever.
- **Confidence gate = `rank_decks(min_coverage=…)`** (default 0.5): archetypes whose
  `data_coverage < min_coverage` (S computed from thin matchup data) are EXCLUDED from the ranked
  gaps and reported as an excluded-count (no silent cap — the "no silent caps" pattern). The
  metashare/`tier_for_sample` tier is shown per row for transparency.
- **Un-windowed (no `since/until`)** — `build_matrix` / `rank_decks` / `build_global_field` are
  themselves un-windowed (match-results isn't windowed); gaps stays consistent with positioning.
- **Candidate set = the global field's real archetypes** (`build_global_field` already excludes
  Unknown/Conflict and renormalizes); bounded by `--min-share`.
- **Provenance** = single basis (`online`/`paper`/`all`→None); one ranking, no per-basis loop.

## Architectural choice

`report gaps` is a thin composition, so the only real choice was the score shape + gate. Two were
weighed: (A) **rank by raw `s_mean` among decks below a share threshold** (a hard popularity cut) —
rejected: a cliff at the threshold and no graded reward for under-exploration; (B) **a continuous
`gap_score = s_mean − share_weight·share`** (chosen) — graded, interpretable, and a single
`share_weight` knob spans "pure positioning" (0.0) to "strongly penalize popularity" (>1.0). The
honesty gate is delegated to `rank_decks`'s existing `min_coverage`/`low_coverage` mechanism rather
than reinvented, so "don't surface S from thin matchup data" reuses a tested path.

## Implementation Units

### Unit 1: result records

**File**: `src/legacy_engine/advisory/gaps.py` (new module)

```python
@dataclass(frozen=True)
class ArchetypeGap:
    archetype: str
    s_mean: float
    s_quantile: float       # risk-adjusted lower quantile (from rank_decks)
    share: float            # meta-share within the global field (0..1)
    gap_score: float        # s_mean − share_weight · share
    data_coverage: float    # fraction of field share-mass with a measured cell
    tier: ConfidenceLevel   # tier_for_sample(deck count) — display/transparency

@dataclass(frozen=True)
class GapReport:
    gaps: list[ArchetypeGap]          # sorted gap_score DESC (tie: share ASC, then name)
    excluded_low_coverage: list[str]  # dropped for thin matchup data (reported, not silent)
    field_source: str
    risk_quantile: float
    share_weight: float
    min_coverage: float
```

**Acceptance Criteria**:
- [ ] Frozen dataclasses; `GapReport.gaps` sorted by `gap_score` DESC.

---

### Unit 2 (trickiest): `compute_archetype_gaps`

**File**: `src/legacy_engine/advisory/gaps.py`

```python
def compute_archetype_gaps(
    con: duckdb.DuckDBPyConnection,
    *,
    definition: str = "raw",
    provenance: str | None = None,
    share_weight: float = 1.0,
    min_coverage: float = 0.5,
    risk_quantile: float = 0.25,
    min_share: float = 0.0,
    seed: int | None = None,
) -> GapReport:
    """Rank archetypes by under-exploration: high positioning S, low meta-share.

    field = build_global_field(...); candidates = list(field.shares);
    matrix = build_matrix(con, provenance=provenance);
    ranking = rank_decks(matrix, field, candidates, min_coverage=min_coverage,
                         risk_quantile=risk_quantile, seed=seed).
    For each candidate NOT in ranking.low_coverage: gap_score = s_mean − share_weight·share.
    Those in low_coverage → excluded_low_coverage (reported). Sort gap_score DESC,
    tie-break share ASC then name ASC.
    """
```

**Implementation Notes**:
- `share = field.shares[arch]`; `tier = tier_for_sample(int(field.counts[arch]))` when counts
  present, else `tier_for_sample(0)`.
- Empty field (no positionable archetypes) → `GapReport([], [], field.field_source, …)`.
- `provenance` threads identically into `build_global_field` and `build_matrix`.
- Determinism: pass `seed` to `rank_decks`; stable tie-break.

**Acceptance Criteria**:
- [ ] A high-S / low-share archetype ranks above a high-S / high-share one (popularity penalty).
- [ ] `gap_score == s_mean − share_weight·share` for each surfaced archetype.
- [ ] An archetype with `data_coverage < min_coverage` is absent from `gaps` and present in
      `excluded_low_coverage` (no silent drop).
- [ ] Two calls with the same `seed` produce identical ordering.
- [ ] Empty/te field → empty `GapReport`, no crash.

---

### Unit 3: `report gaps` CLI command

**File**: `src/legacy_engine/cli.py` (`@report.command("gaps")`, beside `report tiers`)

```python
@report.command("gaps")
# --definition / --provenance / --share-weight / --min-coverage
# --risk-quantile / --min-share / --seed / --db / --verbose
def report_gaps(...) -> None:
    """Under-explored archetypes: high positioning S, low meta-share."""
```

**Implementation Notes**:
- Mirror `report_tiers`' option/`store.connect(db)`/`try/finally` shape.
- `--provenance` Choice(online/paper/all); `all`→None.
- Call `compute_archetype_gaps`, render via `_print_gap_report`; echo the excluded-for-thin-data
  count explicitly (no silent cap).

**Acceptance Criteria**:
- [ ] `report gaps --help` lists the options.
- [ ] On a seeded corpus the command prints a ranked table + the excluded count; exit 0.

---

### Unit 4: `_print_gap_report` renderer

**File**: `src/legacy_engine/cli.py`

```python
def _print_gap_report(report: GapReport) -> None:
    """Labeled text table: archetype, S, Sq, share, gap, coverage, tier; then excluded count."""
```

**Acceptance Criteria**:
- [ ] Prints header + one row per gap with gap_score, S, share, coverage, tier.
- [ ] Prints `excluded_low_coverage` count/names when non-empty.

## Implementation Order

1. **Unit 1** records — the typed surface.
2. **Unit 2** `compute_archetype_gaps` — trickiest; the MC + metashare composition + gate.
3. **Unit 4** `_print_gap_report` then **Unit 3** the command — display + wiring.

## Testing

### Unit tests: `tests/test_gaps.py`
- Build a small corpus (tournaments/decks/rounds labeled across ≥2 archetypes) so `build_matrix`
  + `build_global_field` + `rank_decks` produce real S/coverage; mirror the `test_positioning`
  fixture style.
- `compute_archetype_gaps`: popularity-penalty ordering (high-S/low-share first); `gap_score`
  arithmetic; `min_coverage` exclusion lands in `excluded_low_coverage` (not silently dropped);
  `seed` determinism; empty-field no-crash.
- CLI: `CliRunner` smoke test of `report gaps` against an in-memory `--db` (exit 0, table + excluded line).

### Integration
- End-to-end on the seeded fixture: ranking is stable across two seeded calls; an obviously
  under-explored archetype (strong matchups, tiny share) tops the list.

## Risks

- **MC nondeterminism without a seed** — tests pin `seed`; the CLI exposes `--seed`. **Fallback**:
  none needed; rank_decks already supports `seed`.
- **`share_weight` default scaling** — share (0..~0.3) vs S (~0.5); weight 1.0 gives a modest
  penalty. **Fallback**: `--share-weight` lets the user dial popularity penalty up; documented lever.
- **Thin-coverage gate too aggressive** (min_coverage 0.5 could exclude most archetypes on a sparse
  DB). **Fallback**: `--min-coverage` is tunable; excluded archetypes are reported, never hidden.
