---
id: idea-card-kingdom-price-source
created: 2026-06-27
tags: [feature, pricing, advisory]
---

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
