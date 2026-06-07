---
id: epic-local-meta-support
kind: epic
stage: drafting
tags: [advisory, ingestion, analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Local-Meta Support

## Brief

The engine's headline use case — "what's the meta, how do I attack it, how do I tune my deck?" — is
in practice answered for a *global online-derived* field, but the real user (Andrew) preps for a
*local paper* meta near Boulder, CO that diverges sharply from the online data (big-mana-heavy). This
session modeled Boulder by hand-building a custom `--field` file and leaning on `--provenance paper`,
which worked — but the path is undiscoverable and partial: the advise commands don't expose
`--provenance`, the most insightful output (field-vulnerability / hate-equity) is gated behind
supplying a full deck, and custom fields are share-only (can't model field-share confidence). And
there's no native way to filter by region at all.

This epic makes preparing for a *specific local meta* a first-class, supported workflow.

## Strategic decisions
- **How should local-meta prep work?**: Both, phased — v1 makes the curated-field / provenance /
  standalone-field-read path first-class (the workflow that worked this session, no schema change);
  a later phase adds a real geographic/location ingestion dimension so the engine can filter by
  region natively. — v1 ships value fast with no foundation-doc churn; the geo dimension is a bigger
  bet sequenced after the lightweight path proves the workflow.
- **Foundation roll-forward**: deferred to the geo-dimension phase. v1 surfaces existing capabilities
  (no new entity/boundary), so foundation docs stay as-is now; `/epic-design` rolls SPEC/VISION/
  ARCHITECTURE forward when the geo-dimension phase is actually designed (rolling-foundation: docs
  describe present intent, not planned phases).

## Member findings (absorbed from backlog — full text in git history)

### Phase 1 — lightweight curated-field / provenance workflow (no schema change)
- **advise-provenance-flag** [advisory]: `report meta/matchups` expose `--provenance` but the advise
  commands (whattoplay/positioning/report/sideboard) don't — so you can't run advisory against a
  paper-only field. Thread `--provenance` through the advise commands.
- **standalone-field-read** [advisory]: field-vulnerability / hate-equity (the most insightful output)
  is gated behind supplying a deck. Expose a standalone field-read that takes just a field (no deck).
- **custom-field-counts-and-normalization** [advisory]: a custom field is share-only (counts=None) so
  positioning can't model field-share confidence; plus normalization edge cases. Let custom fields
  carry counts (or a confidence proxy) and tighten normalization.

### Phase 2 — native geographic dimension (foundation-doc impact)
- **engine-geo-dimension** [ingestion, analytics]: tournaments carry no geographic/location field, so
  the engine can't natively answer its headline local-meta use case. Add a geo/location dimension to
  ingestion + schema and expose region filtering across reports/advise.
