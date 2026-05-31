---
id: epic-deck-generation-export
kind: feature
stage: implementing
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

## Architectural choice

A pure formatter module + a CLI leaf. **Zero network, no new deps.** The exporter is the inverse of the
existing decklist-text *parser* used by `advise --deck` (a `<qty> <name>` reader — find it in `cli.py` or a
parsing helper and mirror its grammar so round-trip parse↔export is exact). One formatter handles all
targets because Moxfield / Archidekt / MTGGoldfish / `.dec` share the `<qty> <name>` + `Sideboard`-header
shape; per-target differences are limited to optional set/collector annotations and the section header, so
the format is a thin enum, not separate code paths. Single-stride feature — no child stories. Independent of
consensus/tuning: it formats any `dict[str,int]` board pair (or a `GeneratedDeck`/`Deck`).

## Implementation Units

### Unit 1: Decklist text formatter
**File**: `src/legacy_engine/generation/export.py`
```python
ExportFormat = Literal["moxfield", "archidekt", "mtggoldfish", "text", "dec"]

def format_decklist(maindeck: dict[str, int], sideboard: dict[str, int] | None = None,
                    *, fmt: ExportFormat = "moxfield") -> str:
    # "<count> <Card Name>" per line, maindeck block, blank line, "Sideboard" header, side block.
    # ".dec" uses "SB: <count> <name>" for sideboard (the .dec convention); others use the header.
```
**Notes**: deterministic ordering (by count desc then name) so output is stable/testable. **AC**: a 60+15
deck round-trips through the existing parser back to the same board maps; `dec` uses the `SB:` convention;
empty sideboard omits the header.

### Unit 2: Moxfield convenience (deep link / copy block)
**File**: `src/legacy_engine/generation/export.py`
```python
def moxfield_import_block(maindeck, sideboard=None) -> str:
    # the importable text wrapped with a one-line "paste into Moxfield → New Deck → Import" hint.
```
**AC**: returns the standard text plus the hint; no network call.

### Unit 3: `export deck` CLI leaf + `--export` on generate output
**File**: `src/legacy_engine/cli.py`
```python
@main.group()
def export() -> None: ...
@export.command("deck")
@click.option("--deck", type=click.Path(exists=True), required=True)   # a decklist file
@click.option("--format", "fmt", type=click.Choice([...]), default="moxfield")
@click.option("--out", type=click.Path(), default=None)  # write to file or stdout
# Also add an --export/--format flag path so `generate consensus --export moxfield` emits import text.
```
**AC**: `export deck --deck list.txt --format archidekt` prints valid import text; `--out` writes a `.txt`;
piping a generated list through export produces Moxfield-importable text.

## Implementation Order
1. Unit 1 formatter (+ confirm the existing parser grammar for round-trip).
2. Units 2-3.

## Testing
- `tests/test_generation_export.py` — round-trip (parse(format(d)) == d) for each format; `.dec` SB
  convention; empty-sideboard header omission; deterministic ordering; deep-link block has no network.
- `tests/test_cli.py` — `export deck` to stdout + `--out` file.

## Risks
- **Parser grammar drift**: if export and the `advise --deck` parser disagree on annotations, round-trip
  breaks. **Fallback**: the round-trip test is the guard; mirror the parser exactly, keep set/collector
  annotations optional.
