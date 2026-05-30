---
description: How to define a shared data model in legacy-engine — subclass LegacyEngineModel. Read before adding any model class.
type: pattern
kind: planning
updated: 2026-05-29
summary: |
  All shared models subclass LegacyEngineModel (Pydantic v2) with extra="ignore" so external JSON
  (Scryfall cards, fbettega cache) drops unmodeled fields instead of failing. The project is
  Pydantic-uniform — no dataclasses for shared models.
decisions:
  - "Every shared model subclasses legacy_engine.models.base.LegacyEngineModel (not bare BaseModel, not dataclass)."
  - "Base config is model_config = ConfigDict(extra=\"ignore\", populate_by_name=True)."
  - "Pydantic v2 everywhere — a deliberate divergence from edh-engine's dataclass/Pydantic mix."
---

# Pattern: Pydantic Base Model (`LegacyEngineModel`)

All shared data models subclass `LegacyEngineModel`.

## Rationale
External JSON carries far more fields than we model (a Scryfall card object has dozens of keys; the
fbettega `CacheItem` is PascalCase and nested). `extra="ignore"` lets us declare only what we use and
drop the rest rather than fail validation. `populate_by_name=True` lets a field accept either its
Python name or an alias — useful for the PascalCase fbettega schema. Standardizing on Pydantic (not
edh-engine's dataclass/Pydantic mix) keeps one idiom across the project.

## Example (canonical)
**File**: `src/legacy_engine/models/base.py`
```python
class LegacyEngineModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
```
Usage — declare fields, unknown input keys are dropped:
```python
class _Sample(LegacyEngineModel):
    name: str
    count: int = 0
# _Sample(name="Brainstorm", count=4, oracle_text="...", foo="bar") -> keeps name/count, drops the rest
```
`ConfidenceMetadata` (`src/legacy_engine/confidence.py`) is a sibling model that subclasses `BaseModel`
directly only because it predates the base import order; new models use `LegacyEngineModel`.

## When to use
- Any model representing external data (cards, decklists, tournament records, rules) or internal results.

## When NOT to use
- Pure value enums / Literals (use `Literal[...]`), or hot-loop structs where Pydantic overhead matters
  (rare; measure first).

## Common violations
- Using a `@dataclass` for a shared model (breaks the uniform idiom).
- Subclassing `BaseModel` directly (loses the shared `extra="ignore"` config → fails on Scryfall extras).
