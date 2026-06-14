---
id: idea-held-features-followups
created: 2026-06-13
tags: [advisory, ingestion, generation, documentation]
---

Non-blocking findings from the deep reviews of the 4 held foundation features (all approved → done;
suite green at 1842). Queue for a polish pass / docs gate.

new-set-ingestion-and-speculation:
- (Low) `report new-cards` and `report speculate --new` don't read a persisted ingest diff — `new-cards`
  prints DB total + a hint; `--new` speculates on "10 most recently inserted cards" as a proxy. The
  Part-1→Part-2 persisted-diff hand-off the design promised is under-delivered. Wire the IngestDiff
  through so `--new` operates on the actual new-cards set.
- (Low) `store.py` `total_after` comment says "only full-name rows (not face aliases)" but the SQL is
  `count(*)` (includes alias rows). Fix the comment (new_names is accurate; cosmetic).
- (Low) `report speculate` forecast column label "0=low,1=high" is loosely interpretable (fuses a [0,1]
  intrinsic score with a lift recentred at 0.5). Always-speculative banner mitigates.

collection-aware-engine:
- (Low) `acquire.py` per-printing loop (~331-354) is dead (`pass` body; real check is orchestrator-level).
  Remove; comment suffices. Cruft-gate candidate.
- (Low) Overpriced-printing flag firing path (the orchestrator $33-vs-$2 Dismember DB lookup) is only
  asserted negatively (no false-positive); add a positive test that fires it.

personal-inventory-and-decks:
- (Low) `--my-deck NAME` flag (on 7 leaves) not documented in ARCHITECTURE.md Conventions CLI list / docs.
- (Low) `export deck` wraps `_resolve_deck_boards` in `except ValueError` but that helper raises
  ClickException; harmless but misleading vs other leaves.

curated-price-source:
- (Trivial) download progress counter counts `b'{"id"'` per 64KB chunk — a token split across a chunk
  boundary is undercounted. Log-only estimate, never used for correctness.

(Combine with idea-build-group-doc-drift-and-polish at the next quality-checkpoint / release-deploy.)
