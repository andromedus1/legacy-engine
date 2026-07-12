---
id: epic-stable-era-windows-detection
kind: feature
stage: drafting
tags: [analytics, methodology]
parent: epic-stable-era-windows
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Per-entity disturbance detection engine

## Brief

The pure-analytics core: given the corpus, derive each entity's (parent archetype, and camp where
sample permits) detected era boundaries. Builds per-entity weekly (or pooled-bucket) series — share
of field, flex-band composition vectors, per-card inclusion — and runs the brief's signal-typed
detector ensemble: S1 presence rules for ban cliffs / release ramps (threshold crossings with
consecutive-bucket confirmation), S2 kernel/energy change-point detection on composition vectors
(PELT + RBF/cosine cost, or E-Divisive with permutation p-values), S3 share-shift and S4 win-rate
corroboration via exact Beta-Binomial likelihoods (in-project conjugate BOCPD recursion — no
existing Python package covers count/proportion likelihoods). Candidate boundaries merge across
signals (±1-2 week tolerance), pass fleet-level false-positive control (Benjamini-Hochberg FDR over
per-boundary p-values + a minimum-segment floor expressed in DECKS, tied to the evolving-tier
floor of 30), and yield `stable_since(entity)` = the last accepted boundary. Adds the `ruptures`
dependency. Per-entity adaptivity: bucket width and signal subset scale with weekly density
(camps below the density floor inherit their parent's boundaries).

This feature does NOT persist anything, attribute triggers, or touch any consumer — output is
pure data structures. Calibration IS in scope: the penalty/threshold operating point is chosen by
sweeping against the labeled disturbance ledger (12 BAN_EVENTS × affectedness cases, the
Candelabra/Tron cliff, the Flow State three-archetype adoption step, and known stable non-event
stretches) and the chosen operating point ships as a pinned test fixture. Never trust CPD
defaults — the brief's benchmark evidence says defaults lose to a zero-detector.

## Epic context

- Parent epic: `epic-stable-era-windows`
- Position in epic: foundation feature — everything else depends on its detected boundaries.

## Inherited design decisions

- Self-heal gate — auto-truncate, labeled: the detector's accepted boundaries are authoritative
  even when unattributed; design the acceptance bar (FDR + floors) knowing its output truncates
  windows without human review.
- Known ban/release dates are labels/priors, never the source of truth (epic Brief).

## Research briefs

- `docs/briefs/change-point-detection.md` (load-bearing; attested) — §1 data shapes + ground
  truths, §2 signal taxonomy, §3 method selection, §4 FP control, §5 calibration ledger, §6
  small-sample playbook.
- `docs/briefs/subarchetype-discovery.md` — the flex-band representation reused for composition
  vectors.

## Foundation references

- `docs/ARCHITECTURE.md` — analytics/ module map (affectedness.py is the mechanism being
  generalized; discovery.py owns the flex-band builders).
- Patterns: objective-search-split (heavy DB scan once → pure detector loop, unit-testable
  without DB); confidence-metadata (tier floors); closed-vocabulary fail-fast (signal/trigger
  enums).
