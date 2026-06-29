---
id: epic-sb-config-evaluation-matchup-slot-test
kind: feature
stage: drafting
tags: [analytics]
parent: epic-sb-config-evaluation
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-29
updated: 2026-06-29
---

# Matchup-conditioned sideboard-slot test

## Brief

Let the operator test a candidate sideboard card against a specific target matchup: for a
given archetype, compare win-rate **WITH** the card (in `board=side`) vs **WITHOUT** it,
*within the same archetype and the same opponent matchup*. This is the
within-archetype/within-matchup, with-vs-without contrast — the empirical answer to "does this
slot actually pull weight vs this deck?"

**Why it's net-new.** Two adjacent capabilities exist but answer different questions:
- `report cards --vs Y --board side` (via `card_value_matchup`) returns *lift vs the card's
  own prior* — the wrong baseline for this question, and it nearly misled us (see below).
- `report subgroup` splits an archetype on a signature card but is **not** conditioned on an
  opponent or on `board=side`.

This feature is most naturally the intersection: extend `analytics/subgroup.py` /
`report subgroup` to accept `--vs OPPONENT` + `--board {main,side}` (vs. a new `report` leaf —
exact surface is a `feature-design` call).

## Hard requirement (surfaced during investigation — do NOT skip)

The output **must** ship with statistical honesty or it will mislead:
- **Wilson CIs on each side** (WITH and WITHOUT).
- **A two-proportion significance test on the diff** (z-test / Fisher), with the p-value and an
  explicit "not significant" flag.
- **A loud presence-correlational + thin-n banner** (honest-degrade marker pattern).

Motivation: in session analysis, Null Rod vs Blue Artifacts showed WITH 38.0% (n=71) vs
WITHOUT 46.3% (n=67), a −8.2pt point estimate that *looked* like the premier anti-artifact
card was counterproductive. A two-proportion test gave **z=−0.98, p=0.33 — not significant**;
the CIs ([28,50] vs [35,58]) overlap almost entirely. Without the significance gate the raw
−8.2 reads as a real (and wrong, against first principles) finding. The contrast also revealed
the confound directly: "Blue Artifacts" wins through artifact *creatures* (Kappa Cannoneer,
Patchwork Automaton, Emry, Urza's Saga constructs) that attack through a Null Rod, so the
winning non-Null-Rod lists leaned on creature removal + free counters — exactly first
principles, not "Null Rod is bad."

## Validated prototype (reference for the spec)

A by-hand prototype already produces the target output (within-archetype, `board=side`,
with-vs-without, per opponent). Representative Dimir Tempo results:

| SB card | vs | WITH | WITHOUT | diff | significant? |
|---|---|--|--|--:|--|
| Toxic Deluge | Death & Taxes | 40.6% (n=69) | 29.9% (n=87) | +10.7 | borderline (the one positive signal) |
| Null Rod | Blue Artifacts | 38.0% (n=71) | 46.3% (n=67) | −8.2 | no (p=0.33) |

Note Null Rod is essentially side-only in this archetype (side=1597, main=1), so the
side-based contrast isn't corrupted by maindeck copies — but the spec should still classify
"owns the card" cleanly (consider main+side) to avoid that bug class in other cards.

## Scope notes
- Reuses `compute_card_winrates`' engine dedup (the `dup`/`uniq_decks` CTEs) — do NOT hand-roll
  a `rounds`↔`decks` join (a naive join fans out on the 432 duplicate `(tournament, player)`
  deck rows and inflates n ~3×).
- Honors the data ceiling recorded on the parent epic (presence ≠ played; thin per-matchup
  samples).
- Output feeds the config comparator (the next feature) as its measured per-matchup SB-lift
  input.
