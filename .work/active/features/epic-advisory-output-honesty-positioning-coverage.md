---
id: epic-advisory-output-honesty-positioning-coverage
kind: feature
stage: implementing
tags: [advisory, analytics, correctness]
parent: epic-advisory-output-honesty
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Positioning Coverage & Confidence

## Brief

Make the positioning score honest about how much of the field it can actually see. Today, against a
broad field the matchup matrix covers only ~15 archetypes, so the vast majority of opponents are
imputed and `S` collapses to the ~0.50 imputation prior — yet S prints with full authority, and in
`--candidates` ranking zero-data decks (cov=0.00) surface spuriously high raw P(best) from the same
imputation. This feature introduces a share-weighted **field-coverage ratio** (the % of field mass
with real matchup data) as a first-class concept, auto-restricts the headline S to the covered
sub-field, and suppresses/flags low-support derived numbers.

Covers: surfacing the coverage ratio next to S; computing S over the covered sub-field with the
excluded share reported; suppressing/flagging P(best) and wide imputed CIs when coverage ≈ 0. This is
the foundation feature of the epic — the coverage concept it establishes is consumed by
whattoplay-honesty (which surfaces the coverage-aware S).

Does NOT cover: list-level granularity (deferred — see backlog `idea-list-granular-positioning`);
the "what to play" output surface (see `epic-advisory-output-honesty-whattoplay-honesty`).

## Epic context
- Parent epic: `epic-advisory-output-honesty`
- Position in epic: foundation feature — `whattoplay-honesty` depends on the coverage-aware S it produces.

## Inherited design decisions
- **Low-coverage behavior**: **auto-restrict + note** — compute S over the covered sub-field
  automatically, print it alongside the field-coverage ratio and the excluded share. No flag required;
  the honest result is the default. Preserve the existing full-field path byte-identical when coverage
  is already high, and leave explicit `--field` / `--all-time` invocations behaving predictably.
- **P(best) at zero coverage**: suppress or visually flag raw P(best) (and the wide imputed CIs) when
  a candidate's coverage ≈ 0, so imputation-driven values don't read as real.

## Foundation references
- `docs/SPEC.md` — NFRs "Confidence-gated stats" + "Source transparency / no unlabeled headline numbers"
- `src/legacy_engine/advisory/positioning.py`, `advisory/field.py`, `advisory/gaps.py`
- Pattern: confidence-metadata (`tier_for_sample(n)`), gated-additive-augmentation (no-op path byte-identical to baseline)

## Design decisions
- **Restrict trigger**: only when `data_coverage < _COVERAGE_RESTRICT_THRESHOLD` (≈0.85). A
  near-fully-covered field (trivial uncovered tail) stays byte-identical — avoids churning S on a
  0.3% missing deck. One tunable constant.
- **Replace, don't dual-report**: when restricted, the headline S becomes the covered-field S; print
  the coverage ratio + "X% of field has no matchup data (excluded): [list]". Do NOT print the
  imputation-prior full-field S — it's the misleading number we're removing.
- **Zero coverage → refuse**: when no non-mirror opponent has a displayed cell, set
  `s_computable=False` and report "S not computable (no covered matchups)" rather than auto-restricting
  to a mirror-only 0.5. (Design call, consistent with the honesty theme.)
- **`data_coverage` is reported on the FULL field** (the honest "you have data for X% of the real
  field"), even when S is computed on the restricted sub-field.

## Architectural choice

Three plausible shapes (Phase 5a): (A) restrict inside `positioning_score`; (B) restrict in the
report/CLI presentation layer; (C) a pure reusable restrict helper in the domain layer that
`positioning_score` consumes under a default-on gate, with presentation only displaying the enriched
result. **Chosen: C.** It keeps the "honest S" the *default for every consumer* (CLI positioning, the
advise-report path, and the downstream whattoplay-honesty feature all call `positioning_score`, so
SSOT means we fix it once), while factoring the share-renormalization as a pure `FieldDistribution`
method reusable by sideboard/whattoplay which face the same field. B was rejected (duplicates the
restriction logic across 3+ surfaces, drifts, and leaves programmatic callers with the dishonest S);
plain A was rejected in favor of factoring the renormalization into `field.py` so `positioning.py`
owns only "what's covered" and `field.py` owns "renormalize a field over a subset". Honors Ports &
Adapters (domain decides, presentation displays), SSOT, and gated-additive-augmentation (coverage
≥ threshold → byte-identical).

## Implementation Units

### Unit 1: `FieldDistribution.restrict_to` (pure renormalization)
**File**: `src/legacy_engine/advisory/field.py`

```python
from collections.abc import Collection

def restrict_to(self, keep: Collection[str]) -> tuple["FieldDistribution", float]:
    """Return a copy restricted to `keep` (renormalized to sum 1.0) + the excluded share mass.

    `shares` is filtered to `keep ∩ shares` and renormalized directly (NOT via
    _normalize_shares — intentional restriction is not a data-quality warning). `counts`
    (if not None) is filtered to the kept keys (counts are NOT renormalized — they're
    integer backing). `no_data` is intersected with the kept set. `field_source` and
    `warnings` are preserved. Raises ValueError if the kept set has zero share mass
    (callers guard via the zero-coverage check before calling).
    """
```

**Implementation Notes**:
- `excluded_share = 1.0 - sum(self.shares[a] for a in keep if a in self.shares)` (self.shares already sums ~1.0).
- Renormalize directly: `total = sum(kept.values()); shares = {a: s/total for a, s in kept.items()}`.
- Do NOT route through `_normalize_shares` — it would emit a spurious "summed to X" warning on every restriction.

**Acceptance Criteria**:
- [ ] Restricted shares sum to 1.0 (within `_SUM_TOLERANCE`).
- [ ] `excluded_share` equals the summed share of dropped archetypes.
- [ ] `counts` filtered to kept keys when non-None; stays `None` when `None`.
- [ ] `no_data` is intersected with `keep`; `field_source` preserved.
- [ ] Raises `ValueError` when `keep` has zero overlapping share mass.

---

### Unit 2: covered-cell predicate + `covered_field_archetypes` (trickiest — coverage SSOT)
**File**: `src/legacy_engine/advisory/positioning.py`

```python
def _is_covered_cell(matrix: MatchupMatrix, deck: str, opp: str) -> bool:
    """Opponent has trustworthy matchup data: the mirror (fixed 0.5, never imputed) OR a
    displayed (n≥DISPLAY_GATE_N), non-mirror cell."""

def covered_field_archetypes(matrix: MatchupMatrix, field: FieldDistribution, deck: str) -> frozenset[str]:
    """The keep-set for restriction: field archetypes the deck has covered data against
    (includes the deck's own mirror)."""
```

**Implementation Notes**:
- Refactor `_compute_data_coverage` to call `_is_covered_cell` for the per-opponent test (single source of truth for "covered"). Keep its existing **non-mirror** denominator — the coverage *ratio* still measures non-mirror mass; the keep-*set* includes the mirror so the restricted MC keeps the self-mirror column.
- Trickiest because the mirror must be IN the keep-set (so the restricted field isn't degenerate) but OUT of the coverage-ratio denominator — getting these two roles consistent is the crux.

**Acceptance Criteria**:
- [ ] `_is_covered_cell` → True for the mirror, True for an n≥30 non-mirror cell, False for n<30 or absent.
- [ ] `covered_field_archetypes` includes the deck's archetype (mirror) and every displayed opponent.
- [ ] `_compute_data_coverage` returns the same values as before this refactor (regression).

---

### Unit 3: `positioning_score` restrict wiring + `PositioningResult` fields
**File**: `src/legacy_engine/advisory/positioning.py`

```python
_COVERAGE_RESTRICT_THRESHOLD: float = 0.85   # restrict S to covered sub-field below this

@dataclass
class PositioningResult:
    # ... existing fields ...
    restricted: bool = False                        # was the field restricted to covered?
    excluded_share: float = 0.0                     # share-mass dropped by restriction
    excluded_archetypes: frozenset[str] = frozenset()
    s_computable: bool = True                        # False at zero coverage (S is NaN)

def positioning_score(..., restrict_to_covered: bool = True) -> PositioningResult: ...
```

**Implementation Notes**:
- Compute `data_coverage` on the FULL field first (unchanged).
- Gate: `if restrict_to_covered and data_coverage < _COVERAGE_RESTRICT_THRESHOLD:` → compute `covered = covered_field_archetypes(...)`; if no non-mirror covered opponent → `s_computable=False`, leave `s_mean=float('nan')`, `s_ci=(nan,nan)`, add a warning "S not computable: no covered matchups"; else `scoring_field, excluded_share = field.restrict_to(covered)`, set `restricted=True`, `excluded_archetypes = frozenset(field.shares) - covered`, and run the MC on `scoring_field`.
- When `data_coverage >= threshold` (or `restrict_to_covered=False`): run on the full field exactly as today → **byte-identical** result (new fields take defaults: `restricted=False`, `excluded_share=0.0`).
- `u_bar` and `imputed` continue to describe the full field's known/imputed cells (the best-deck lens is unchanged); only the field-weighted `s_mean` moves to the covered sub-field.

**Acceptance Criteria**:
- [ ] coverage == 1.0 → `restricted=False` and `s_mean`/`s_ci` identical to pre-change output for a fixed seed (byte-identical regression).
- [ ] 0 < coverage < 0.85 → `restricted=True`, `excluded_share > 0`, `excluded_archetypes` correct, `s_mean` computed on the covered sub-field (differs from the full-field imputation value).
- [ ] coverage == 0 → `s_computable=False`, `s_mean` is NaN, warning present, no exception.
- [ ] 0.85 ≤ coverage < 1.0 → NOT restricted (threshold respected).
- [ ] Deterministic for a fixed seed.

---

### Unit 4: surface coverage + suppress P(best) at zero coverage (presentation)
**File**: `src/legacy_engine/cli.py` (advise positioning), `src/legacy_engine/advisory/report.py` (advise report)

```python
_PBEST_SUPPRESS_COVERAGE: float = 0.05   # below this, P(best) is imputation noise → suppress
```

**Implementation Notes**:
- Single-deck positioning output: print `Coverage: {data_coverage:.0%} of field has matchup data`; when `restricted`, print `Restricted to covered field — excluded {excluded_share:.0%}: {sorted(excluded_archetypes)}`; when `not s_computable`, print `S: not computable (no covered matchups)` instead of the numeric S line.
- `advise report` positioning/audit section: mirror the same coverage line + restriction note (it calls `positioning_score`, so the restricted S flows automatically — only the print needs the coverage context).
- Ranking output (`rank_decks` path): for decks with `cov < _PBEST_SUPPRESS_COVERAGE`, print `P(best)=n/a` + a `[cov≈0]` flag instead of the spurious imputed number. `rank_decks` already returns `data_coverage` per deck — no domain change needed.

**Acceptance Criteria**:
- [ ] Positioning output shows the coverage % and (when restricted) the excluded-share note with the archetype list.
- [ ] Zero-coverage deck prints "not computable", not a fabricated S.
- [ ] In ranking, a `cov≈0` deck shows `P(best)=n/a`, not a high spurious value.
- [ ] `advise report` carries the same coverage labeling as `advise positioning`.

## Implementation Order

1. **Unit 1** (`restrict_to`) — pure, no deps; foundation for Unit 3.
2. **Unit 2** (covered predicate) — pure, no deps; foundation for Unit 3. (1 & 2 independent.)
3. **Unit 3** (`positioning_score` wiring) — depends on 1 + 2; the behavioral core.
4. **Unit 4** (presentation) — depends on 3's new result fields.

## Testing

### Unit tests
- `tests/advisory/test_field.py` — `restrict_to`: sum-to-1, excluded_share, counts filtering, no_data intersection, ValueError on empty keep, field_source preserved.
- `tests/advisory/test_positioning.py` — `_is_covered_cell` truth table; `covered_field_archetypes` membership; `_compute_data_coverage` regression (unchanged values); `positioning_score` coverage-band matrix (==1.0 byte-identical / mid restricted / ==0 not-computable / ≥0.85 not-restricted); determinism with seed. Build matrices by hand (no DB) per the objective-search-split / pytest-factory-fixtures patterns.

### Integration
- CLI smoke (`tests/test_cli*.py` style): `advise positioning` against a low-coverage custom field prints the coverage line + excluded note; a high-coverage field does not restrict. `advise report` shows the coverage label.

## Risks

- **Existing positioning tests change** — any test asserting `s_mean` against an imputed broad field below 0.85 coverage will move. **Fallback**: this is the intended fix; update those expectations and ADD an explicit coverage==1.0 byte-identical regression so the no-op guarantee is locked. (Flagged at epic level.)
- **NaN `s_mean` propagation** — downstream `epic-advisory-output-honesty-whattoplay-honesty` (which surfaces this S) must handle `s_computable=False`. **Fallback**: documented here so the dependent feature designs for it; `s_computable` is the explicit guard flag, not a magic NaN check.
- **Threshold value (0.85) is a judgment call** — too high churns; too low hides real imputation. **Fallback**: it's a single named constant, trivially tunable after dogfooding the new output.
