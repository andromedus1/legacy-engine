---
id: fix-tuner-core-protection
kind: story
stage: implementing
tags: [generation, quality]
parent: null
depends_on: []
release_binding: null
gate_origin: tests
created: 2026-06-13
updated: 2026-06-13
---

# Tuner over-cuts high-inclusion core cards

## Finding (gate-tests, High)
`generation/tuning.py` field-tuner protects cards only via the ≥65%-inclusion lock in `partition_flex`.
A card that is the field MODE but sits below 65% inclusion (e.g. Nethergoyf at 3 copies, ~50-64%) is
classified flex and can be cut to 0 on ANY positive lift — there is no minimum-lift threshold and no
inclusion-weighted cut penalty. Test-drive: `advise refresh` cut all 3 Nethergoyf for Marsh Flats on
epsilon presence-correlational lift, then the same report's outlier check flagged the result as
off-consensus. Self-contradictory output.

## Fix
Decide + encode the intended policy: add a minimum-lift-to-cut gate (don't swap on sub-threshold lift)
and/or an inclusion-weighted penalty so high-mode cards resist cuts. Encode as a failing-then-passing
test: a mode-3 flex card at ~0.6 inclusion vs a pool card exceeding it by epsilon → tuner does NOT cut
the core card to 0. Supersedes part of idea-test-drive-findings #2.

