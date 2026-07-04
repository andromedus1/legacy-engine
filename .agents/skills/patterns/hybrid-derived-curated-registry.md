# Hybrid Derived + Curated Registry

Auto-derive a mapping from corpus data, then merge hand-curated entries over the derived ones with
an explicit precedence rule (curated wins by key; derived entries fill the gaps).

## Rationale

Some registries need both breadth (whatever the data throws up) and correctness (expert overrides
for the cases the heuristic gets wrong). Deriving alone is noisy; curating alone doesn't scale. The
pattern lets the derived layer cover the long tail while a small curated layer authoritatively pins
the entries that matter, with a single, testable merge function that names who wins. Distinct from
`curated-json-resource-loader` (the *load* half) — this is the *merge* semantics on top of a loaded
curated source plus a data-derived source.

## Examples

### Example 1: linchpin overrides
**File**: `src/legacy_engine/advisory/linchpins.py:352` (wired at `:377`)
```python
def _merge_linchpins(derived, curated):
    """Merge curated overrides over derived candidates: curated WINS by name
    (case-insensitive); unmatched derived entries are kept as-is."""
    curated_names_lower = {lp.name.lower() for lp in curated}
    merged = list(curated)
    merged.extend(d for d in derived if d.name.lower() not in curated_names_lower)
    ...
# linchpins_for_archetype:
derived = derive_linchpins(archetype, cards_with_counts, inclusion_pct)
curated = LINCHPIN_OVERRIDES.get(archetype, [])
return _merge_linchpins(derived, curated)
```

### Example 2: empirical hoser promotion vs curated catalog
**File**: `src/legacy_engine/advisory/sideboard.py:1371` (`_build_promoted_candidates`; merged in
`_build_coverage_model` Step 4/4b at `:1864`/`:1923`)
```python
pool_not_in_catalog = empirical_pool - frozenset(catalog.keys())
if not pool_not_in_catalog:
    return {}, []
```
Curated `HOSER_CATALOG` cards are added in Step 4; empirically-promoted cards (derived via
oracle-text heuristics) fill only the set-difference — curated wins by construction.

### Example 3: maindeck answer-coverage attribution
**File**: `src/legacy_engine/advisory/sideboard.py:1486` (`_maindeck_answer_coverage`, precedence at `:1530`)
```python
hoser = catalog.get(name)
if hoser is not None:
    attacks = hoser.attacks                       # curated: authoritative
else:
    card = get_card(name)
    if card is None:
        continue
    attacks = _derive_attacks_for_promoted(name, card.oracle_text, card.type_line)  # fallback: derive
    if attacks == _FALLBACK_ATTACKS:
        continue
```

## When to Use
- A lookup benefits from both a data-derived long tail and a small authoritative curated override
  set, and you can state a clean per-key precedence rule.

## When NOT to Use
- Purely-curated registries with no derived signal (e.g. `archetype/variants.py::resolve_variant`).
- When derivation should always win (then it isn't an override merge).

## Common Violations
- Merging inline at the call site instead of a named pure `_merge_*` function (precedence becomes
  untestable and the winner ambiguous).
- Letting derived silently overwrite curated (inverts the intended authority).
- Duplicating the derive engine instead of reusing it across sites.
