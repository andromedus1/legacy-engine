---
id: gate-docs-readme-test-count
kind: story
stage: implementing
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: docs
created: 2026-07-04
updated: 2026-07-04
---

# README test count stale (2464 -> current)

## Drift category
readme-staleness

## Location
Doc: README.md:34 + README.md:259

## Current doc text
> '2464 passing tests' (both occurrences)

## Reality
Suite is 2556 green pre-gate-drain and will grow as gate-tests items add tests.

## Required edit
Update both occurrences to the verified green count AT SHIP TIME (run pytest --collect-only after the gate drain; do this item LAST among doc items).
