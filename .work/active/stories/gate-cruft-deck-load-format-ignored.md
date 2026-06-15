---
id: gate-cruft-deck-load-format-ignored
kind: story
stage: done
tags: [cleanup]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: cruft
created: 2026-06-14
updated: 2026-06-14
---

# `deck load --format` is fully ignored — advertises 5 formats, delivers one

## Confidence
Medium

## Category
dead CLI option / unused argument

## Location
`cli.py:5242` (param `fmt`), option at `cli.py:5229-5238`

## Evidence
```python
@click.option("--format", "fmt", type=click.Choice(["moxfield","archidekt","mtggoldfish","text","dec"], ...), default="moxfield")
def deck_load(deck_name, version_num, fmt: str, out, verbose) -> None:
    text = export_deck_text(deck, version_num)   # fmt never passed
```
`export_deck_text(deck, version_num=None)` takes no format arg; every `--format` choice produces
identical output.

## Removal
Cruft-correct default: remove the `--format` option + `fmt` param + the `--format dec` example
at cli.py:5251. (Wiring `fmt` through `export_deck_text`/`format_decklist` is a feature decision,
not cleanup — if desired, file separately.) Removal is the surgical choice for this gate.
