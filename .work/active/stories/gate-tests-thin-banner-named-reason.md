---
id: gate-tests-thin-banner-named-reason
kind: story
stage: done
tags: [testing, analytics]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: tests
created: 2026-06-14
updated: 2026-06-15
---

# Thin-regime banner: assert the named reason (round count + floor), not just substring "THIN"

## Priority
Low

## Spec reference
HONEST-DEGRADE NFR (SPEC.md / ARCHITECTURE.md): "thin/absent signal → labeled banner + named
reason + suppressed magnitude." PRINCIPLES: "a thin window may never silently claim depth it
doesn't have." `advisory/window.py` banner formats `"… is THIN: {n_rounds} rounds < floor
{thin_floor} …"`.

## Gap
`test_advisory_window.py` asserts the banner contains `"THIN"` but not that it carries the
actual round count + floor (the *named reason* the NFR requires). A regression dropping
`{n_rounds}`/`{thin_floor}` stays green while violating the contract. Also no test pins the exact
boundary `n_rounds == floor` (degrade is `< floor`, so exactly-at-floor must NOT degrade).

## Suggested test
```python
def test_thin_banner_states_count_and_floor():
    res = resolve_advisory_window(con, regime="current", thin_floor=500)
    assert res.banner and str(res.n_rounds) in res.banner and "500" in res.banner

def test_exactly_floor_rounds_does_not_degrade():
    res = resolve_advisory_window(con, regime="current", thin_floor=500)  # corpus tuned to exactly 500
    assert res.banner is None
```

## Test location (suggested)
`tests/test_advisory_window.py`

## Resolution (2026-06-15)
`WindowResolution` exposes no `n_rounds` field, so pinned the banner string directly:
`test_thin_banner_states_count_and_floor` asserts the regex `\d+ rounds < floor 500` (named reason =
actual count + floor, not just "THIN"). `test_exactly_floor_rounds_does_not_degrade` reads the
in-window count via `_count_rounds` then sets `thin_floor == n`, pinning that `n_rounds == floor`
does NOT degrade (degrade is strictly `< floor`).
