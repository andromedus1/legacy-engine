# Closed-Vocabulary Fail-Fast Token Validation

A small closed set of allowed string tokens lives in a module-level `frozenset`; every load/parse
of that token validates membership and raises a `ValueError` naming the offending token and the
sorted allowed set.

## Rationale

Curated/vendored inputs use string tokens for enum-like fields (symmetry, cast conditions,
condition types). A typo silently changes behavior unless membership is checked. Centralizing the
vocabulary in one `frozenset` and failing loud at load turns author errors into immediate,
self-describing exceptions. Refines `curated-json-resource-loader`'s generic per-entry validation
into a specific reusable shape; applies beyond loaders (the archetype matcher).

## Examples

### Example 1: hoser symmetry
**File**: `src/legacy_engine/advisory/sideboard.py:904` (validation `:1005`)
```python
_VALID_SYMMETRY = frozenset({"asymmetric", "symmetric"})
...
if symmetry not in _VALID_SYMMETRY:
    raise ValueError(
        f"load_hoser_catalog: {name!r} 'symmetry' {symmetry!r} must be one of {sorted(_VALID_SYMMETRY)}"
    )
```

### Example 2: hoser cast_requires
**File**: `src/legacy_engine/advisory/sideboard.py:909` (validation `:1012`)
`_VALID_CAST_REQUIRES = frozenset({"opp_controls_plains"})`, same raise shape.

### Example 3: archetype condition types (reused across two validators)
**File**: `src/legacy_engine/archetype/rules.py:37` (validation `:75`)
`KNOWN_CONDITION_TYPES` (12 tokens) → `UnknownConditionTypeError(ValueError)`; the same frozenset
is reused by `src/legacy_engine/archetype/variants.py:45`.

## When to Use
- Any enum-like string field on curated/vendored input with a small fixed set of legal values.

## When NOT to Use
- Open-ended free-text fields.
- Large/externally-governed vocabularies that change often (validate against a generated source).

## Common Violations
- Accepting the token as any string with no membership check (see `linchpins.py` `neutralized_by`
  — tracked as a refactor story from the v0.2.0 patterns gate).
- Inlining the allowed set at the check site instead of a named module-level `frozenset`.
- Raising without naming the offending value or the allowed set.
