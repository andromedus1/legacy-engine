---
id: idea-winners-only-triage-creature-interaction
created: 2026-07-03
tags: [advisory, sideboard]
---

# Triage the remaining winners-only divergences — creature-interaction cluster looks systematic

The field-scoped backtest (Dimir Tempo + Boulder, 2026-07-03) shows 9 winners-only cards at ≥20%
adoption; only Consign was investigated. The un-recommended creature-interaction cluster —
Sheoldred's Edict (50.4%), Toxic Deluge, Snuff Out (each ~virtually always in real boards) — being
absent from recommendations is a candidate SYSTEMATIC gap (is creature-based coverage under-weighted
for this field? is removal's swing under-credited vs hosers?), not per-card noise. Also un-triaged:
Barrowgoyf (83.7%), Feed the Cycle, Grafdigger's Cage, Harbinger (partially recommended), Surgical
(graveyard-meta pollution candidate even field-scoped). Investigate cluster-by-cluster with the
divergence-as-diagnostic discipline: each is either a missing mechanic (fix) or an engine edge
(document why the engine dissents).

## Sweep confirmation (2026-07-04, validated harness)

The generalizing sweep (feature-archetype-sweep-backtest) reproduces this as a first-class
cluster: winners-only `creature-based` across 7 archetypes — Sheoldred's Edict / Long
Goodbye / Fatal Push (3 each: Dimir family + Doomsday), Toxic Deluge (Dimir Tempo 86%),
Snuff Out — honestly labeled THIN (speculative winner samples). Copy-count note from the
study: winners run reactive fixers ~60% as 1-ofs, so the gap is WHICH cards get credited,
not their copy counts.
