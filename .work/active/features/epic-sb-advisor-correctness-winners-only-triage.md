---
id: epic-sb-advisor-correctness-winners-only-triage
kind: feature
stage: drafting
tags: [advisory, deferred]
parent: epic-sb-advisor-correctness
depends_on: [epic-sb-advisor-correctness-per-deck-castability]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-11
---

# Winners-only triage — explain-absence diagnostic for blind-spot clusters

## Brief

The backtest and sweep already partition divergence into `overlap` / `scorer_only` / `winners_only`
(`advisory/backtest.py:79-110`, `advisory/sweep.py`), but a `winners_only` entry is currently just
a card name: the engine reports THAT it never recommended Sheoldred's Edict (50.4% adoption), Toxic
Deluge, or Snuff Out, and says nothing about WHY. Every triage pass therefore restarts from
scratch, by hand, in a session. This feature ships the missing half of the diagnostic: an
explain-absence surface that, for each winners-only card, reports which mechanism excluded it —
absent from the catalog and never promoted; dropped by the color pre-filter; dropped by the
anti-synergy filter; a promoted candidate whose derived `attacks` cover no live element; covering
only elements whose weight fell below the natural-budget τ; lost to `functional_group` de-dup; or
capped out by the 4-of guard. Each of those is a distinct, checkable code path in
`_build_coverage_model` / `_rank_considering_pool` (`sideboard.py:2886`, `_considering_label` at
`:2976` are the existing precedent to build on).

On top of the per-card reason, the feature produces the CLUSTER-level triage the epic asked for:
each divergence cluster is classified as a **missing mechanic** (a real engine gap — park a
follow-up item) or an **engine edge** (the engine dissents from the field for a stated, defensible
reason — record the dissent). Confirmed clusters to run it over once `per-deck-castability` has
landed: creature-interaction (Sheoldred's Edict / Long Goodbye / Fatal Push / Toxic Deluge / Snuff
Out — winners-only across 7 archetypes, honestly labeled THIN), plus the un-triaged Barrowgoyf
(83.7%), Feed the Cycle, Grafdigger's Cage, Harbinger of the Seas, and Surgical Extraction. Note
that several of these (Snuff Out, Barrowgoyf, Feed the Cycle) are not in the hoser catalog at all,
so no element-weight fix can ever surface them — that cluster's correct classification is "missing
mechanic, owned by `epic-card-semantics-ir`'s attack-derivation," and this feature parks it rather
than fixing it.

Does NOT cover: changing any score so the scorer matches winners (locked out — this is a diagnosis
feature, not a calibration feature); fixing the mechanisms it classifies (they become new items,
here or in `epic-card-semantics-ir`); the `scorer_only` side (handled by the two mechanism-fix
features); the CI budget (`backtest-ci-gate`).

## Epic context

- Parent epic: `epic-sb-advisor-correctness`
- Position in epic: triages the RESIDUAL after the element-gate fix. Depends on
  `per-deck-castability` because that fix is the leading hypothesis for the creature-interaction
  cluster (the symmetry-floor face of the global-best gate deflates every `creature-based` element
  ~6.7x) — triaging before it lands would triage a known-broken state. Parallel with
  `hate-self-cost`, which attacks the opposite side of the partition.

## Inherited design decisions

- **Calibration philosophy** (epic): mechanism fixes only; observed adoption stays a diagnostic and
  is NEVER blended into scores. This feature is the purest expression of that decision — its entire
  output is the diagnostic, and it is forbidden from feeding adoption back into the objective.
- **Triage output form** (epic `## Design decisions`): an explain-absence surface plus a
  missing-mechanic / engine-edge classification; findings become substrate items, not silent
  score adjustments.
- **Boundary with `epic-card-semantics-ir`**: cards absent from the catalog whose derived `attacks`
  cover nothing are an attack-derivation gap, owned by that epic. Classify and park; do not fix
  here.

## Research briefs

- `docs/briefs/scorer-flexibility-valuation.md` — §2 distortion D3 (broad cards failing to ATTACH
  to the elements they answer) is the single most likely explanation for the non-catalog half of
  the blind-spot list.
- `docs/briefs/card-semantics-ir.md` — the attack-derivation gaps this triage will hand off.
- `docs/briefs/advisory-methods.md` — advisory surface conventions.

## Foundation references

- `docs/ARCHITECTURE.md` — the `backtest.py` and `sweep.py` rows ("divergence-as-diagnostic —
  clusters are engine-error-map input, never auto-calibrated back into scores"); this feature
  extends that surface.
- `docs/SPEC.md` — Pillar 4 "Archetype-sweep backtest" + the HONEST-DEGRADE NFR.
- Patterns: `.agents/skills/patterns/divergence-as-diagnostic-surface.md` (load-bearing — every
  reported gap pairs with a sample-tier annotation and is framed as "investigate", never "error");
  `.agents/skills/patterns/honest-degrade-marker.md` (THIN winner samples must be labeled, and a
  thin cluster must not be classified as a confirmed missing mechanic);
  `.agents/skills/patterns/audit-echo-comment-lines.md` (`// ...` prefix for the reason lines);
  `.agents/skills/patterns/confidence-metadata.md` (tier every cluster).

<!-- The /feature-design pass will fill in interfaces, signatures, and implementation units. -->
