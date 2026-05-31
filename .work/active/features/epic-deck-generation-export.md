---
id: epic-deck-generation-export
kind: feature
stage: drafting
tags: [generation]
parent: epic-deck-generation
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Portable decklist export (Moxfield-as-import + multi-target)

## Brief

Emit a generated (or any) decklist as the standard MTG import text — `<qty> <Card Name>` one per line with a
`Sideboard` section header — that imports cleanly into Moxfield, Archidekt, MTGGoldfish, and `.dec`. One
exporter, many targets (the brief's hedge against Moxfield API uncertainty). Optionally produce a Moxfield
import deep-link / copy block for a one-paste hop. Pure presentation: reuses the existing decklist
representation, makes **zero network calls**, offline-reproducible.

Surfaces as an `export deck --format moxfield|archidekt|text|dec` leaf (and/or a `--moxfield`/`--export`
flag on the `generate`/`advise` output). Independent of the consensus and tuning features — it formats any
decklist object, so it can be built and tested in parallel against existing decklist fixtures.

Does NOT cover native push to Moxfield or sanctioned Moxfield read — both are post-MVP product decisions
explicitly out of scope for this epic (no write API; ToS-gated).

## Epic context
- Parent epic: `epic-deck-generation`
- Position in epic: independent capability — formats any decklist; no code dependency on consensus/tuning.

## Inherited design decisions
From the parent epic `## Design decisions` (fixed inputs):
- **Export breadth**: portable multi-target text (Moxfield/Archidekt/MTGGoldfish/.dec) + optional Moxfield
  deep-link. NO native push, NO sanctioned read in this epic.
- Pure, offline, zero network calls; reuse the existing decklist type.

## Research briefs
- `docs/briefs/deck-generation-and-moxfield.md` §1.2–1.3 (export sink, import format, portability hedge).

## Foundation references
- `docs/ARCHITECTURE.md` — `generation/` seam (export lives next to the advisory `report` surface).
- Existing decklist representation in `src/legacy_engine/models/` + the consensus-list output shape.
