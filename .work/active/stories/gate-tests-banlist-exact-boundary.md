---
id: gate-tests-banlist-exact-boundary
kind: story
stage: done
tags: [testing, ingestion, documentation]
parent: null
depends_on: []
release_binding: null
gate_origin: tests
created: 2026-06-14
updated: 2026-06-15
---

# As-of-date legality: pin the exact ban-date boundary (legal day-before vs on-the-day)

## Priority
Low

## Spec reference
SPEC.md NFR "Version-stamped legality — every legality check resolves against a dated
BanListSnapshot." PRINCIPLES: "validate against a dated BanListSnapshot with banned_date."

## Gap
`test_banlist.py` covers legal-before/illegal-after but always at dates well clear of the
boundary. The half-open semantics *on* the `banned_date` itself (legal on-the-day or only the
day before?) is the classic off-by-one in dated-snapshot logic and is unpinned. If SPEC is
silent on the on-the-day rule, settle that first (small [documentation] step), then pin it.

## Suggested test
```python
def test_legality_at_exact_ban_date_boundary():
    # Psychic Frog banned 2024-12-16
    assert banlist_as_of(date(2024,12,15)).is_legal("Psychic Frog") is True
    assert banlist_as_of(date(2024,12,16)).is_legal("Psychic Frog") is False  # pin on-the-day rule
```

## Test location (suggested)
`tests/test_banlist.py`

## Resolution (2026-06-15)
SPEC was silent on the boundary, so settled it first: SPEC.md "Version-stamped legality" NFR now
states a ban takes effect *on* its `banned_date` (`banned_date <= as_of` ⇒ banned), matching the
existing `banlist_as_of` implementation. Added `test_legality_at_exact_ban_date_boundary` pinning
Psychic Frog legal 2024-12-15 / banned 2024-12-16.
