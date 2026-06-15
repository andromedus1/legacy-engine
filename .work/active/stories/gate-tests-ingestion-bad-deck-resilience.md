---
id: gate-tests-ingestion-bad-deck-resilience
kind: story
stage: implementing
tags: [testing, ingestion, bug]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: tests
created: 2026-06-14
updated: 2026-06-14
---

# Ingestion does not tolerate one bad deck/event (resilience NFR unhonored + untested)

## Priority
Critical

## Spec reference
Item: `epic-tournament-ingestion-cache-parser` (NFR owned across `epic-tournament-ingestion`)
Acceptance criterion: SPEC.md NFR "Resilience — ingestion tolerates a single bad deck/event
(catch, log, continue); the community cache is fragile / single-maintainer."
ARCHITECTURE.md Conventions/Error handling: "ingestion tolerates one bad deck/event (catch,
log, continue)."

## Gap type
Missing test for error case — and the test surfaces a real production bug (the spec'd
behavior is absent, not merely untested).

## Bug
`parse_cache_item` (`src/legacy_engine/ingestion/cache.py:70`) builds
`decks=[Deck.model_validate(d) for d in raw.get("Decks", [])]` with **no per-deck try/except** —
one deck dict that fails Pydantic validation (card row missing `CardName`, non-coercible `Count`,
malformed `Standing`/`RoundMatch`) raises `ValidationError` and aborts the entire event.
`ingest_cache` (`cache.py:141-143`) calls `json.loads(...)` + `parse_cache_item(...)` +
`store.load_tournament(...)` **outside any try/continue**, so one bad event aborts the whole
batch. Only the discovery loop (`cache.py:123-127`) catches `JSONDecodeError`/`OSError`.

## Fix scope
1. Per-deck: wrap the deck-validation in a try/except in `parse_cache_item`; on `ValidationError`,
   log (warn) with the event + deck index and `continue` (drop the deck, keep the event).
2. Per-event: wrap the parse+load body in `ingest_cache` in try/except; on failure log + continue
   to the next event. Return the count of successfully-ingested events.
3. Decide the honest-degrade surface: a warn-level log line is the floor; consider a summary count
   ("N events ingested, M skipped") echoed via the audit-comment-line convention.

## Suggested test
```python
# tests/test_cache_parser.py
def test_one_bad_deck_does_not_drop_the_event(caplog):
    raw = {"Tournament": {"Name": "x", "Date": "2026-05-25", "Formats": "Legacy"},
           "Decks": [VALID_DECK, MALFORMED_DECK, VALID_DECK], "Rounds": [], "Standings": []}
    result = parse_cache_item(raw, "MTGO")
    assert len(result.decks) == 2          # bad deck dropped, not the whole event
    assert "skip" in caplog.text.lower()   # logged, not silent

# tests/test_cache_mirror.py (or test_store_tournaments.py)
def test_one_bad_event_does_not_abort_the_batch(con, tmp_path, caplog):
    # cache dir: [good_event.json, malformed_event.json, good_event.json]
    n = ingest_cache(con, cache_dir=tmp_path)
    assert n == 2                          # batch continues past the bad event
    assert "skip" in caplog.text.lower()
```

## Test location (suggested)
`tests/test_cache_parser.py` (deck-level) and `tests/test_cache_mirror.py` (batch-level).
