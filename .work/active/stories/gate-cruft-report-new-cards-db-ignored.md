---
id: gate-cruft-report-new-cards-db-ignored
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

# `report new-cards --db` is silently ignored

## Confidence
Medium

## Category
dead CLI option / unused argument

## Location
`cli.py:1867` (param `db`), option at `cli.py:1860-1865`

## Evidence
```python
@click.option("--db", type=click.Path(exists=True, dir_okay=False), default=None, ...)
def report_new_cards(limit: int, db: str | None, verbose: bool) -> None:
    diff = store.load_ingest_diff()   # uses default path; `db` never read
```

## Removal
`report new-cards` reads only the persisted ingest diff (no DB connection), so `--db` is
meaningless. Remove the `--db` option and the `db` param. (Also a hermetic-test trap: a no-op
`--db` is a green-local/red-CI hazard if a test passes it expecting isolation.)
