---
description: How to load a curated, human-editable JSON resource shipped inside the package. Read before adding a new hand-authored data file (catalog, registry, alias/lookup map) that ships as a package resource and is read at import or call time.
type: pattern
kind: planning
updated: 2026-06-15
summary: |
  Curated, hand-authored JSON files that ship as package resources (under PACKAGE_DATA_DIR, path
  named in config.py as a *_PATH constant) are read by a standalone, path-taking loader
  load_X(path) -> validated structure that validates per-entry and raises ValueError citing the
  offending path/index, paired with a module-level default loader that resolves the config path
  and degrades to an empty structure on any error. Distinct from json-ssot-rebuildable-duckdb-table:
  these are READ-ONLY curated lookups (no DuckDB cache, no rebuild), not a mirrored data domain.
decisions:
  - "Curated JSON ships INSIDE the package (PACKAGE_DATA_DIR/<domain>/legacy.json), not under data/ — it is code-adjacent expert knowledge, versioned with the source, not a rebuildable cache."
  - "The shipped path is a constant in config.py (HOSERS_REGISTRY_PATH, VARIANTS_REGISTRY_PATH, ALIASES_PATH) so tests can monkeypatch it and the loader stays path-injectable."
  - "load_X(path) is standalone and takes an explicit path (Ports & Adapters): it never reaches into config itself, so it is hand-testable with a tmp file and reused by the default loader."
  - "Validation is per-entry and FAILS FAST citing the offending path + key/index — a malformed curated file is an author error, surfaced loudly at load time, never silently half-loaded."
  - "A module-level _load_default_*() (or a default path arg) resolves the config path and degrades to an EMPTY structure on error, so a missing/broken curated file never crashes import — the feature just no-ops (gated-additive)."
  - "The default result is bound once at import (HOSER_CATALOG = _load_default_hoser_catalog()) — the curated lookup is effectively a constant after module load, no per-call disk reads on the hot path."
---

# Pattern: Curated JSON Resource Loader

Hand-authored expert data (the sideboard hoser catalog, the archetype-variant registry, the
player-alias map) ships as a **JSON resource inside the package** and is read by a small,
uniform loader shape. This is the read-only curated-lookup cousin of
[json-ssot-rebuildable-duckdb-table.md](json-ssot-rebuildable-duckdb-table.md): there is no
DuckDB cache and no `rebuild_*` — the JSON *is* the in-memory structure, loaded once.

## The shape

```
src/legacy_engine/data/<domain>/legacy.json   ← curated, hand-editable, versioned with source
config.py:  <DOMAIN>_PATH = PACKAGE_DATA_DIR / "<domain>" / "legacy.json"
```

```python
# 1. Standalone, path-taking, validating loader (no config import — hand-testable).
def load_X(path: Path | str) -> ValidatedStructure:
    """Load + validate from a JSON file. Raises ValueError citing the offending entry."""
    path = Path(path)
    raw = json.loads(path.read_text())          # or a lenient parser for trailing commas
    result = {}
    for key, entry in raw.get("...").items():
        if not _entry_is_valid(entry):
            raise ValueError(f"load_X: {key!r} ... in {path}")   # fail fast, cite path+key
        result[key] = _build(entry)
    return result

# 2. Module-level default loader: resolve config path, degrade to empty on error.
def _load_default_X() -> ValidatedStructure:
    try:
        from legacy_engine.config import X_PATH
        return load_X(X_PATH)
    except Exception as exc:
        log.error("X: failed to load from data file — returning empty: %s", exc)
        return {}            # gated-additive: missing/broken curated file → feature no-ops

# 3. Bind once at import — the curated lookup is a constant thereafter.
X_REGISTRY = _load_default_X()
```

## The three occurrences

| Loader | File | Curated file / config path | Validation + failure | Default / degrade |
|---|---|---|---|---|
| `load_hoser_catalog` | `advisory/sideboard.py:912` | `data/hosers/legacy.json` / `HOSERS_REGISTRY_PATH` | per-hoser schema (swing alias, non-empty attacks, colors, `max_copies≥1`, dup names) → `ValueError`/`FileNotFoundError` | `_load_default_hoser_catalog()` @1044 → `{}`; bound to `HOSER_CATALOG` @1056 |
| `load_variant_registry` | `archetype/variants.py:25` | `data/variants/legacy.json` / `VARIANTS_REGISTRY_PATH` | Pydantic `model_validate` + fail-fast on unknown `Condition.Type` → `UnknownConditionTypeError`/`ValueError` citing `parent/name` + source | resolved via config path; missing → empty registry behaviour |
| `load_alias_map` | `analytics/players/identity.py:51` | `data/players/aliases.json` / `ALIASES_PATH` | normalizes each handle via `normalize_player`; tolerant | `path=ALIASES_PATH` default arg; absent file → `{}` (no-alias no-op) |

## When to use

Adding a new piece of **curated, hand-authored** reference data (a catalog, a registry, a
lookup/alias map) that:
- is small, expert-edited, and belongs *with the code* (not a mirrored/ingested data source);
- should be loaded once and treated as a constant;
- must fail loudly when an author mis-edits it, but never crash import when it is simply absent.

## When NOT to use

- A large, externally-sourced, or mirrored dataset that needs a queryable cache → use
  [json-ssot-rebuildable-duckdb-table.md](json-ssot-rebuildable-duckdb-table.md) instead.
- Constants with no file backing → put them in `config.py`
  ([constants-only-config.md](constants-only-config.md)).
