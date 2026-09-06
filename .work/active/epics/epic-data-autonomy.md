---
id: epic-data-autonomy
kind: epic
stage: implementing
tags: [ingestion, infra, needs-brief]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-11
---

# Data autonomy & currency — own the supply chain, automate freshness

## Brief

The engine's data supply chain has single points of failure and manual-freshness gaps that
dogfooding keeps hitting: the upstream tournament-data source has gone down before (July
2026 outage), data refreshes and B&R/new-release awareness depend on manual runs, prices
only reflect Scryfall/TCGplayer market, and the hand-curated catalogs (hosers, linchpins)
silently fall behind new cards. This epic makes the engine's data layer autonomous:
scheduled refresh + format monitoring, additional price sources, catalog currency guards,
and — the largest arc — recreating and owning the upstream tournament-data generation
process itself.

Tagged needs-brief for the upstream-ownership arc specifically: the brief must
reverse-engineer what the upstream (fbettega cache) pipeline actually does — scraping
sources, normalization, coverage — and assess feasibility/cost of running it ourselves.
Scheduled monitoring and price/catalog work do not need the brief and can be decomposed
first by epic-design.

## Design decisions
<!-- captured 2026-07-31 via epic-design --only-questions; the /brief and feature-design treat these as fixed inputs -->
- **Upstream ownership ambition**: hot-spare pipeline — build and periodically exercise our
  own tournament-data generation pipeline, but keep consuming upstream normally; flip to
  ours when upstream is down. The brief targets this feasibility level (not full
  replication, not archive-only).
- **Scheduling substrate**: local scheduler (launchd) on the maintainer's Mac, running refresh +
  B&R/release monitors against local data/ + DuckDB directly; session-start surfaces
  results. No cloud state to sync.

## Child stories (quick win, stage: implementing)
- epic-data-autonomy-catalog-lint — CI lint cross-checking curated JSON (hosers, linchpins) against the cards table in DuckDB

## Authorized feature slice (2026-08-11)

The operator authorized the local currency/monitoring slice while continuing to defer the
hot-spare upstream recreation and Card Kingdom price arcs. This partial decomposition deliberately
does not activate those larger members:

- `epic-data-autonomy-local-refresh-operations` — schedule the existing composed refresh locally,
  with overlap protection, durable success/failure status, and operator controls.
- `epic-data-autonomy-format-monitoring` — detect B&R and release changes, preserve attribution,
  and require human confirmation before changing format truth.

## Member findings (absorbed from backlog; full text below)

---

### idea-own-upstream-data-generation


Recreate the upstream data generation process we rely on (the tournament data
source) and own/run it ourselves, if possible. Motivation: we should never be
reliant on someone else for data availability — the upstream has gone down
before, and owning the generation process removes that single point of failure.

---

### idea-scheduled-data-and-format-monitoring


# Scheduled deck-data updates + B&R and new-release monitoring

the maintainer (2026-07-04): we need (1) scheduled updates of deck/tournament data, (2) monitoring
of ban & restricted announcements, and (3) monitoring of new card releases — the engine's
data currency and format awareness shouldn't depend on manual refreshes.

---

### idea-card-kingdom-price-source


**Add a Card Kingdom price source so buy-lists can be priced against what the user
actually pays at CK — not just Scryfall/TCGplayer market.**

Found dogfooding (2026-06-27): the engine's price pipeline (`seed prices` /
`refresh --prices`) loads **Scryfall bulk USD = TCGplayer market**. For reserved-list /
spiky cards this diverges hard from Card Kingdom. Concrete miss: I quoted Lion's Eye
Diamond at a stale ~$55 from memory; the maintainer sees **~$800 on Card Kingdom**. Scryfall
provides a CK *purchase link* but not CK *price values*, so the engine literally cannot
report CK prices today.

the maintainer prices and buys at Card Kingdom, so CK is the decision-relevant vendor for his
acquire/buy-list output.

What to build:
- Ingest a **Card Kingdom price feed** (their pricelist endpoint / API, or a sanctioned
  data source) into a CK price table, keyed by card (+ printing where possible).
- Add a **vendor dimension** to the price layer so `advise acquire` / `report prices`
  can report CK alongside (or instead of) Scryfall/TCG — e.g. `--vendor cardkingdom`.
- Consider **buylist vs retail** awareness (CK buylist ≠ sell price), and a "cheapest
  across vendors" mode.
- Honest-degrade: when CK data is missing for a printing, fall back to Scryfall/TCG with
  a labeled source tag — never silently mix vendors in one total.

Caveats / open questions:
- Card Kingdom ToS / rate limits for price scraping; prefer an official feed if one
  exists. (MTGJSON carries CK pricing under some licenses — could be the cleaner source
  than direct scrape.)
- Reserved-list cards are exactly where vendors diverge most and where accuracy matters
  most for build-vs-not decisions.

Process note that prompted this: stop quoting prices from memory entirely — they're
volatile (see [[analysis-statistical-context-gates]] for the same lesson on card text /
regime data). Until a price source is loaded, report prices as "unknown — load the price
DB or check the vendor."

---

### idea-hoser-catalog-new-card-gap


# Hoser-catalog new-card gap — sweep's unclassified cluster is rank-1 (24 archetypes)

Sweep finding (2026-07-04, validation-gated harness, global current-regime field): the
`unclassified` winners-only cluster is the top-ranked divergence — 24 archetypes, led by
cards the catalog/tag derivation can't attribute:

- **Disruptor Flute — winners-only in 10 archetypes** (Eldrazi 100%, Golgari Landfall 100%,
  Lands 87%, Painter 75%, Show and Tell 70%, Blue Artifacts 63%, …) — the exact
  "systematic gap, not per-deck noise" shape the sweep was built to catch.
- Wrath of the Skies (4 archetypes), Dismember (4), Barrowgoyf (5, tag-missed), Meltdown
  (3), Deafening Silence (3), Magus of the Moon, Price of Progress, …

Likely one root cause: recently-printed cards absent from the curated hoser catalog AND
missed by `_derive_attacks_for_promoted`'s text heuristics. Candidate fixes: catalog refresh
sweep for post-cutoff sets (data-driven: mine the sweep JSON's unclassified members by
adoption), plus derivation-rule gaps (e.g. "each opponent" tax effects, X-damage board
sweeps). Related: [[idea-catalog-lint-vs-db]], [[idea-card-semantics-rules-layer]] (the
error map this feeds). The unclassified cluster size is the tracking metric — re-run
`advise sweep` after any fix.
