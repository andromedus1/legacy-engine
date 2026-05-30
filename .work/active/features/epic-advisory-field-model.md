---
id: epic-advisory-field-model
kind: feature
stage: review
tags: [advisory]
parent: epic-advisory
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Field Distribution Model (global + custom field)

## Brief
The shared SSOT for "what is the field" that the positioning score, sideboard recommender, and
what-to-play advisor all consume. Build a `FieldDistribution` (archetype→expected-share map) two ways:
**global** — derived from `metashare`'s `compute_metashare` over the labeled corpus (carrying the backing
per-archetype counts so positioning can form a Dirichlet posterior) — and **custom** — a user-supplied
`archetype→share` map (the "best metagame call for MY room" headline). Custom-field handling: auto-normalize
(warn if shares don't sum to 1), warn + impute on archetypes with no/low matchup data, keep **Other/rogue
as an explicit archetype** with imputed wide-uncertainty, include the **mirror at its field share**, and
stamp a `field_source: global | custom | local` label on every distribution.

Extracted as a foundation feature (not in the architecture's 4-file advisory table) because all three
advisory consumers need the same field semantics; owning it once is the SSOT that avoids three
re-implementations of custom-field normalization / Other-handling / Dirichlet-count carrying — the same
rationale that extracted `match-results` ahead of `metashare`/`matchup-matrix` in `epic-meta-analytics`.

Does NOT compute the positioning score, sideboard, or what-to-play signals (those consume this); does NOT
recompute meta-share (reads `compute_metashare`).

## Epic context
- Parent epic: `epic-advisory`
- Position in epic: **foundation feature** — `positioning`, `whattoplay`, and `sideboard` depend on its
  `FieldDistribution` type. Consumes the done `epic-meta-analytics` (`compute_metashare`).

## Inherited design decisions
- **Custom field included in MVP** (archetype→share map; auto-normalize; warn on no-data archetypes) — the
  "best metagame call for MY room" headline, not just global-meta scoring.
- **Other/rogue is an explicit archetype** with imputed wide-uncertainty; **mirror included at field share**
  (p=0.5, zero variance) for headline scoring (per advisory-methods §2 conventions).
- **`field_source` label** (`global | custom | local`) on every distribution — never an unlabeled field.

## Research briefs
- `docs/briefs/advisory-methods.md` — §2 conventions (normalize w to 1; Other/rogue explicit; mirror at
  share; Dirichlet `counts+γ`); custom-field semantics (normalize/warn/impute, `field_source`).

## Foundation references
- `docs/ARCHITECTURE.md` — `advisory/` module; `analytics/metashare.py` (`compute_metashare`/`MetaShareReport`).
- `docs/PRINCIPLES.md` — #6 never an unlabeled meta-% (field is labeled by source); #7 confidence-gate.

## Design decisions
(Resolved under autopilot delegation — Phase 4.5. Parent-epic + advisory-methods decisions inherited as
fixed. No strategic 50/50s.)

- **`FieldDistribution` is a plain `@dataclass`** in `advisory/field.py` — consistent with the analytics
  computed records (`MetaShareReport`/`MatchupMatrix`/`TrendSeries` are all dataclasses). The project's
  Pydantic `LegacyEngineModel` base is for types parsed from external JSON; a derived distribution isn't one.
- **Global field is backed by `compute_metashare(definition="raw")`** (configurable): raw entry counts
  *are* the natural Dirichlet `counts`, and "what people brought" is the field you actually face. `group_other=False`
  so every archetype is an explicit field element (positioning/sideboard want per-archetype granularity; the
  downstream n<30 matchup gate handles thin cells). `provenance` defaults `None` (all), parametrizable.
- **`Unknown` / `Conflict(...)` excluded from the field** (reusing `metashare._is_never_other`): they're
  unclassified decks, not archetypes you can position against. Exclude, **renormalize** the remaining shares to
  sum 1, and **warn** with the excluded (unclassified) share fraction — never silently dropped.
- **Custom field carries `counts=None`** (share-only). Pure custom shares have no count-backing, so positioning
  can't form a Dirichlet posterior over them → it uses point shares (no share-uncertainty in the MC). `field.py`
  emits a warning stating this; it does NOT synthesize pseudo-counts (that's positioning's call if it wants a
  concentration param). Per advisory-methods §2 ("swaps w and the Dirichlet counts in count-backed mode").
- **No-data archetypes**: `build_custom_field` accepts an optional `known_archetypes` set; archetypes the user
  names that aren't in it are kept in the field (their share matters) but flagged in `no_data` + a warning, for
  wide-uncertainty winrate imputation **downstream in positioning** (which owns the matchup matrix). `field.py`
  does not impute winrates — it only flags.
- **Normalization is always applied** at build time: custom shares are normalized to sum 1 (warn if the input
  sum deviates beyond a tolerance). Empty map, negative shares, or all-zero → `ValueError` (fail-fast).
- **`field_source` (`global | custom | local`) is always set** — never an unlabeled field (PRINCIPLES #6 spirit).
- **Single-stride, no child stories** — one cohesive `advisory/field.py` module (a type + two builders + a
  normalize helper); tightly coupled.

## Architectural choice

**A `FieldDistribution` dataclass + two explicit builders (`build_global_field`, `build_custom_field`) sharing
one `_normalize_shares` helper.** Options weighed: (A) two named builders + shared normalize (chosen — the
global and custom paths have genuinely different inputs and warnings, so two entry points read clearer than one
branching function); (B) a single `build_field(con, custom=None)` that branches internally (rejected — muddies
two distinct contracts); (C) make `FieldDistribution` a Pydantic `LegacyEngineModel` (rejected — it's a derived
record like the analytics dataclasses, not an external-JSON boundary type). The distribution carries optional
`counts` (present for global/count-backed, `None` for custom) so positioning can decide between Dirichlet
share-uncertainty and point shares without re-deriving the field.

## Implementation Units

### Unit 1: `_normalize_shares` (trickiest — designed first)

**File**: `src/legacy_engine/advisory/field.py`

```python
from __future__ import annotations

import logging

import duckdb

log = logging.getLogger(__name__)

_SUM_TOLERANCE = 1e-6


def _normalize_shares(raw: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    """Validate and normalize a raw archetype→share map to sum 1.0.

    Returns (normalized_shares, warnings). Fail-fast (ValueError) on an empty map,
    any negative share, or an all-zero/zero-sum map. If the input sum deviates from
    1.0 beyond ``_SUM_TOLERANCE``, normalize and emit a warning naming the original sum.
    """
```

**Implementation Notes**:
- `ValueError` (fail-fast, per project convention) for: empty `raw`; any `share < 0`; `sum(raw.values()) <= 0`.
- Otherwise divide each share by the total; if `abs(total - 1.0) > _SUM_TOLERANCE`, append a warning
  `f"custom field shares summed to {total:.4f}; normalized to 1.0"`.

**Acceptance Criteria**:
- [ ] `{"A": 0.6, "B": 0.4}` → unchanged shares, no warning.
- [ ] `{"A": 0.6, "B": 0.3}` (sum 0.9) → `{"A": 0.667, "B": 0.333}` + one warning.
- [ ] `{}` raises `ValueError`; `{"A": -0.1, "B": 1.1}` raises `ValueError`; `{"A": 0.0}` raises `ValueError`.

---

### Unit 2: `FieldDistribution` + `FieldSource`

**File**: `src/legacy_engine/advisory/field.py`

```python
from dataclasses import dataclass
from typing import Literal

FieldSource = Literal["global", "custom", "local"]


@dataclass
class FieldDistribution:
    """The expected field a deck is positioned against — the advisory SSOT for 'what is the field'.

    ``shares`` sums to ~1.0 over positionable archetypes (Unknown/Conflict excluded).
    ``counts`` is the per-archetype backing sample for a Dirichlet posterior, or ``None`` for a
    share-only custom field (positioning then uses point shares). ``field_source`` is ALWAYS set.
    ``no_data`` are field archetypes lacking backing data (wide-uncertainty imputation downstream).
    """

    shares: dict[str, float]
    field_source: FieldSource
    counts: dict[str, int] | None
    no_data: frozenset[str]
    warnings: tuple[str, ...]
```

**Acceptance Criteria**:
- [ ] A `FieldDistribution` always carries a non-null `field_source`.
- [ ] `counts` is a dict for global fields and `None` for pure-custom fields.

---

### Unit 3: `build_global_field`

**File**: `src/legacy_engine/advisory/field.py`

```python
from legacy_engine.analytics.metashare import _is_never_other, compute_metashare


def build_global_field(
    con: duckdb.DuckDBPyConnection,
    *,
    definition: str = "raw",
    provenance: str | None = None,
    min_share: float = 0.0,
) -> FieldDistribution:
    """Build the global field from the labeled corpus via ``compute_metashare``.

    Uses ``group_other=False`` so every archetype is an explicit element. Excludes
    Unknown/Conflict labels (renormalizing + warning with the excluded share). Carries
    the per-archetype deck counts as the Dirichlet ``counts``. ``field_source='global'``.
    """
```

**Implementation Notes**:
- Call `compute_metashare(con, definition=definition, provenance=provenance, min_share=min_share, group_other=False)`.
- Drop entries where `_is_never_other(entry.archetype)`; track their summed share; renormalize the rest via
  `_normalize_shares`; if any were dropped, warn `f"excluded {excluded_share:.1%} unclassified (Unknown/Conflict) from the field"`.
- `counts = {archetype: entry.n}` over the kept entries; `no_data = frozenset()` (global is data-backed).

**Acceptance Criteria**:
- [ ] Over a labeled corpus, `shares` sum to ~1.0 and `counts[a] == entry.n` for each kept archetype.
- [ ] An `Unknown`/`Conflict(...)` labeled deck is excluded from `shares` and triggers an exclusion warning.
- [ ] `provenance="paper"` restricts the field to paper events.
- [ ] `field_source == "global"` and `counts is not None`.

---

### Unit 4: `build_custom_field`

**File**: `src/legacy_engine/advisory/field.py`

```python
def build_custom_field(
    shares: dict[str, float],
    *,
    known_archetypes: frozenset[str] | None = None,
) -> FieldDistribution:
    """Build a user-supplied custom field (the 'best call for MY room' headline).

    Normalizes via ``_normalize_shares`` (warn on sum!=1). If ``known_archetypes`` is given,
    archetypes absent from it are flagged in ``no_data`` + warned (kept in the field for
    downstream wide-uncertainty imputation). ``counts=None`` (share-only) → positioning uses
    point shares; emits a warning to that effect. ``field_source='custom'``.
    """
```

**Implementation Notes**:
- `normalized, warnings = _normalize_shares(shares)`.
- `no_data = frozenset(a for a in normalized if known_archetypes is not None and a not in known_archetypes)`;
  if non-empty, warn naming them.
- Always append the point-shares warning: `"custom field is share-only (counts=None); positioning will use point shares (no field-share uncertainty)"`.

**Acceptance Criteria**:
- [ ] `{"Delver": 0.5, "Lands": 0.5}` → `field_source="custom"`, `counts is None`, shares unchanged, point-shares warning present.
- [ ] An archetype not in `known_archetypes` lands in `no_data` with a warning, and is still in `shares`.
- [ ] Input summing to 0.8 is normalized to 1.0 with a normalization warning.

---

### Unit 5: Module exports

**File**: `src/legacy_engine/advisory/__init__.py` — export `FieldDistribution`, `FieldSource`,
`build_global_field`, `build_custom_field` (add `__all__`).

## Implementation Order

1. **Unit 1** (`_normalize_shares`) — the validation core everything else calls; trickiest edge cases.
2. **Unit 2** (`FieldDistribution` + `FieldSource`) — the type.
3. **Unit 3** (`build_global_field`) — consumes `compute_metashare`.
4. **Unit 4** (`build_custom_field`) — the custom path.
5. **Unit 5** (exports).

## Testing

### Unit tests: `tests/test_field_model.py`
House style (raw dicts → `parse_cache_item` → `store.load_tournament` into `:memory:`; `UPDATE decks SET
archetype`; `TestX` classes). Build the global field from a real labeled corpus (proves the `metashare` seam).

- `TestNormalizeShares` — unchanged/normalized/warning paths; empty/negative/zero → `ValueError`.
- `TestBuildGlobalField` — shares sum ~1, `counts == entry.n`, Unknown/Conflict excluded + warned, provenance filter, `field_source="global"`.
- `TestBuildCustomField` — normalize + warn, `no_data` flag for unknown archetype (with `known_archetypes`), `counts is None` + point-shares warning, `field_source="custom"`.
- `TestFieldDistribution` — `field_source` always present; `counts` dict (global) vs `None` (custom).

### Integration points
- Seam with `metashare`: `build_global_field` consumes `compute_metashare(...).entries` (`share`, `n`) — a test
  loads a corpus, labels decks (incl. one `Unknown`), and confirms the field excludes Unknown and renormalizes.
- Seam with downstream positioning: `counts` is the Dirichlet input positioning will consume; `no_data` is the
  set positioning imputes — assert both are populated as specified (the consuming behavior is positioning's test).

## Risks

- **Custom field with no count-backing weakens positioning's uncertainty** (point shares, no Dirichlet draw).
  **Mitigation**: explicit warning on every custom field; positioning documents that custom → field-share
  variance is zero. **Fallback**: a future `concentration` param could synthesize pseudo-counts — additive, out
  of scope here.
- **Excluding Unknown/Conflict shifts shares**: renormalizing after dropping unclassified decks inflates the
  remaining shares. **Mitigation**: the exclusion warning names the dropped fraction so the distortion is
  visible; this is correct (you position against known archetypes, not the unclassified bucket).
- **`min_share=0.0` includes a long tail** of sub-1% archetypes with thin matchup data. **Mitigation**: this is
  intentional (the field is real); the n<30 matchup display gate downstream keeps thin cells honest. Callers
  wanting a headline field can raise `min_share`.

## Implementation notes

### Files created/modified
- `src/legacy_engine/advisory/field.py` — new module: `_normalize_shares`, `FieldSource`, `FieldDistribution`, `build_global_field`, `build_custom_field`
- `src/legacy_engine/advisory/__init__.py` — exports: `FieldDistribution`, `FieldSource`, `build_global_field`, `build_custom_field` + `__all__`
- `tests/test_field_model.py` — 43 new tests across `TestNormalizeShares`, `TestBuildGlobalField`, `TestBuildCustomField`, `TestFieldDistribution`

### Test count
- Before: 344 passing
- After: 387 passing (+43)

### Deviations from spec
- **Extra normalization warning in `build_global_field`**: When Unknown/Conflict entries are excluded, the
  remaining shares do not sum to 1.0, so `_normalize_shares` emits an additional "custom field shares summed to…"
  warning. This warning is technically accurate (the raw shares were 0.75 in a 3/4 example) but the message
  wording says "custom field" in a global-field context. Rationale: the spec says `_normalize_shares` always
  warns on sum deviation — this is a helper with a single contract. The exclusion warning already names the
  excluded fraction. The extra normalization warning is correct but could be confusing; noted for a future
  cleanup (e.g., suppress the norm warning in `build_global_field` when the deviation is entirely attributable
  to Known/Conflict exclusion). No behaviour change made — left as-is to follow spec precisely.

### Adjacent issues parked
- None found. `compute_metashare` and `_is_never_other` work exactly as expected for this consumer.
