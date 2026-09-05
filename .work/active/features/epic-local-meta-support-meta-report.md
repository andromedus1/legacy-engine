---
id: epic-local-meta-support-meta-report
kind: feature
stage: drafting
tags: [analytics, advisory]
parent: epic-local-meta-support
depends_on: [feature-decision-unit-taxonomy]
release_binding: null
created: 2026-06-29
updated: 2026-09-05
---

# Generate Deck Rankings for an expected local field

## Brief
Apply the same served posterior model and independent performance/floor priorities to a supplied expected field. Reuse the existing field-file parser (shares and optional counts), render a private local report with an explicit scenario label, and compare it with the global view. Keep scheduled default publication pointed at the global report.

## Outcome boundary
One CLI invocation generates the local report with the same cards, map, tables, camps, tooltips and evidence filters. Reweight complete matchup posteriors for the supplied opponents; unknown opponents remain explicitly prior-backed rather than disappearing. Custom field composition does not define which playable candidate decks may be recommended. Floor covers positive-share non-mirror scenario opponents. Counts represent supplied evidence only; shares alone do not imply observations. Invalid input fails before replacing any output. No public hosting or geo ingestion.

## Simplification
Extend Deck Rankings and the existing build_custom_field parser; retire this item's separate bespoke local comparison-report design.

## Authorized direction
Andrew approved the four-part sequence on 2026-09-05 and asked to execute it: improve historical borrowing and evaluate the exact current model; explain refresh changes concisely; examine pilotable archetype units; apply both independent priorities to custom fields. Keep estimates visible throughout. Existing data integrity and incompatible-era boundaries remain in force. Current report styling and interactions are the approved reference. No new audience, hosted product, or geographic ingestion is in scope.

## Execution
Standard feature review (default): one independent pass followed by verification of accepted fixes. Features run in the approved order. Reuse existing implementation and research before adding abstractions; preserve unrelated Hogaak files and uv.lock changes. Design records concrete interfaces before implementation.
