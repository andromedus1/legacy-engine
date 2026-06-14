---
id: feature-custom-field-counts-normalization
kind: feature
stage: review
tags: [advisory]
parent: epic-local-meta-support
depends_on: [feature-advise-provenance-flag]
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Custom fields carry counts + tightened normalization

## Brief
A custom `--field` file is share-only (`counts=None`), so positioning can't model field-share confidence
(Dirichlet backing) for a user-supplied local field — it falls back to point shares. Let custom fields
optionally carry counts (or a confidence proxy / effective-N), feeding the Dirichlet posterior so a
hand-built Boulder field can express uncertainty. Also tighten the custom-field normalization edge cases
(zero-sum, renormalization warnings, Unknown/Conflict handling). Gated-additive: share-only fields keep
working exactly as today.

## Design

### Extended field file format (backward-compatible)

Three supported forms, all backward-compatible:

**Share-only (existing — counts=None, byte-identical behavior):**
```
0.35 Delver
0.25 Lands
0.20 Reanimator
```

**Per-line counts (new — optional 3rd token, positive integer):**
```
0.35 Delver 42
0.25 Lands 30
0.20 Reanimator 24
```

**Global effective-N header (new — proportional distribution):**
```
# effective_n: 120
0.35 Delver
0.25 Lands
0.20 Reanimator
```

Rules:
- Per-line counts and `# effective_n` are mutually exclusive; per-line counts win (log warning, header ignored)
- An archetype without a per-line count in a mixed file gets count=1 (weakest Dirichlet prior)
- `effective_n` distributes N proportionally by share; last archetype gets the remainder to prevent rounding drift; every archetype gets ≥ 1
- Comment lines (`#`) without the `effective_n:` directive are ignored (as before)
- Multi-word archetype names work in all formats

### How counts feed positioning

`_load_field` in `report.py` parses the counts and passes them to `build_custom_field(shares, counts=...)`. `build_custom_field` validates the counts dict (same keyset as shares, positive integers) and stores them on `FieldDistribution.counts`.

In `_sample_S` / `rank_decks`:
- `field.counts is not None` → `W ~ Dirichlet(counts + γ)` per draw (share-uncertainty propagation)
- `field.counts is None` → `W = tiled(point_shares)` (zero weight-variance; existing behavior)

The Dirichlet path introduces per-draw weight variance, widening the S CI compared to point shares. This is the honest uncertainty signal for a hand-built field.

### Normalization tightening

`_normalize_shares` already handled: empty map, negative shares, non-finite (NaN/±inf), zero-sum. No gaps found that needed code changes — the existing guards are complete. Tests added explicitly document these cases.

`build_custom_field` validates counts when provided:
- Missing keys in counts (relative to shares) → `ValueError: counts missing keys`
- Extra keys in counts → `ValueError: counts has extra keys`
- Non-positive or non-integer counts → `ValueError: must be a positive integer`

### Gated-additive contract

- `build_custom_field(shares)` (no `counts` kwarg) → identical to pre-feature behavior: `counts=None`, same warning text, same `FieldDistribution` values
- `_load_field` with share-only lines → `counts=None` path unchanged
- New behavior activates only when 3rd token or `# effective_n:` is present in the file

## Implementation notes

**Files changed:**
- `src/legacy_engine/advisory/field.py` — `build_custom_field` gains optional `counts: dict[str, int] | None = None` parameter with validation; emits `"Dirichlet-backed"` warning when counts present vs `"point shares"` when not
- `src/legacy_engine/advisory/report.py` — `_load_field` extended to parse per-line count tokens and `# effective_n: N` header; produces `resolved_counts` dict for `build_custom_field`

**Tests added (49 new, 2116 total, all passing):**
- `tests/test_advise_report.py`: `TestLoadFieldCounts` (15 tests — parse format, backward-compat, error cases), `TestBuildCustomFieldCounts` (10 tests — counts parameter validation, warnings), `TestCustomFieldCountsPositioning` (4 tests — Dirichlet wider CI than point shares, determinism, S mean proximity)
- `tests/test_field_model.py`: `TestBuildCustomFieldCountsFieldModel` (13 tests — field model unit tests), `TestNormalizeSharesEdgeCases` (8 tests — zero-sum message, renorm warning format, non-finite, many archetypes)

**Suite:** 2116 passed (was 2067; +49). ruff clean.
