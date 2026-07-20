---
id: feature-refresh-keyed-reload
kind: feature
stage: drafting
tags: [ingestion, hygiene]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-12
updated: 2026-07-20
---

# Refresh: keyed reload that preserves labels for unchanged decks

## Brief

Every `refresh all` run — including fully no-op runs where the cache mirror reports
"Already up to date" — silently wipes the label layers: `decks.archetype` drops to ~3
rows and `decks.variant` to 0. Everything downstream (camps, eras consumption,
split-variant reports) silently degrades to fallbacks until a manual recovery of
`label` + 29× `discover apply` + `eras run` (~10 min wall clock). Three documented
recurrences: 2026-07-12, 2026-07-13, 2026-07-20.

Root cause: `ingest_cache` (src/legacy_engine/ingestion/cache.py:148) calls
`load_tournament` (src/legacy_engine/ingestion/store.py:458) for **every** discovered
cache event on every refresh. `load_tournament` is "idempotent" via DELETE + re-insert
of the tournament's child rows, and re-inserts decks with `archetype=NULL,
variant=NULL` — so labels are destroyed even when the underlying cache file is
byte-identical to what was already ingested.

The fix is a keyed (incremental) reload: skip `load_tournament` entirely for cache
events whose content is unchanged since the last ingest, so their deck rows — and the
labels on them — are never touched. Only new or changed events reload (those decks
legitimately need relabeling). Plus honest audit output: refresh must report how many
events were skipped-unchanged vs reloaded, and how many labeled rows were dropped by
the reload, with a loud `// ⚠` checklist line (label + discover apply + eras run)
whenever labeled rows were lost.

## Strategic decisions
- **Fix approach**: option (b) keyed reload preserving labels for unchanged decks,
  plus honest audit output on label loss — pinned by Andrew 2026-07-20. Options (a)
  auto-run recovery and (c) audit-line-only were considered in the backlog note;
  (a) may still fall out cheaply as the `// ⚠` checklist line, but auto-running
  recovery is not in scope.
- **Guarantee to keep**: staged-registry membership persistence (data/variants/
  discovered.json) made every manual recovery lossless — the fix must not regress it.

## Original backlog note (for provenance)

**`refresh all` can silently wipe the label layers.** The 2026-07-12 run did a full
cache reload (65,785 decks reloaded; archetype labels dropped to 3, decks.variant to
0) — everything downstream (camps, eras consumption, split-variant reports) silently
degraded to fallbacks until a manual `label` + per-archetype `discover apply` (29
splits) + `eras run` recovery. Ideas: (a) `refresh all` should detect a labels-wiped
state and either auto-run `label` (+ re-apply staged splits + `eras run`) or print a
loud `// ⚠ labels wiped — run: label && discover apply … && eras run` checklist;
(b) make ingestion preserve labels for unchanged decks (keyed reload instead of full
reload); (c) at minimum an audit line in refresh output stating how many labeled rows
were lost. The staged-registry membership persistence made recovery lossless — keep
that guarantee.

**Recurred 2026-07-13:** the wipe happens even on a NO-OP refresh — cache said
"Already up to date", zero new tournaments (deck count and max date unchanged), yet
the reload still dropped labels to 3 and variants to 0. Manual recovery (label + 29×
discover apply + eras run) worked again but took ~10 min of wall clock. This fires on
every refresh, not just data-bearing ones — raises the priority of option (b) (keyed
reload preserving labels for unchanged decks).

**Recurred 2026-07-20:** third occurrence, again on a fully no-op refresh (upstream
fbettega/MTG_decklistcache stalled since 2026-07-02, so zero new data). Labels
65,785→3, variants 21,484→0; recovered via label + 29× discover apply + eras run.
