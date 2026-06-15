---
id: gate-cruft-import-inventory-merge-param
kind: story
stage: done
tags: [cleanup]
parent: null
depends_on: []
release_binding: null
gate_origin: cruft
created: 2026-06-14
updated: 2026-06-15
---

# `merge` parameter on `import_inventory` is documentary-only — never read

## Confidence
Low

## Category
unused argument (param that only documents intent)

## Location
`collection/inventory.py:24`

## Evidence
```python
def import_inventory(text: str, *, owner: str = LOCAL_OWNER, merge: bool = True) -> Inventory:
    # body never reads `merge`; always returns a fresh Inventory
```

## Removal
The merge/replace decision is the caller's (via `merge_inventory`). Either remove `merge` and
fold its guidance into the docstring as caller advice, or honor it. Verify callers before touching
(may be a deliberate documented affordance).

## Resolution (2026-06-15)
Removed. The sole caller (`cli.py:4993`) never passed `merge` — it does merge/replace itself via the
CLI `--merge` flag → `merge_inventory`/`replace_inventory`. Param dropped from `import_inventory`;
docstring now states the merge-vs-replace decision is the caller's. No behavior change.
