---
id: bug-mtgo-event-url-alias-duplicates
created: 2026-09-05
updated: 2026-09-05
tags: [ingestion, analytics]
---

# Identical MTGO event ingested under two date URLs

The live corpus has the same Legacy Showcase Challenge (MTGO event 12852808,
event date 2026-08-23) under both `legacy-showcase-challenge-2026-07-2212852808`
and `legacy-showcase-challenge-2026-08-2312852808` on www.mtgo.com/decklist/.
All 32 decks, 991 deck-card rows, 32 standings and 7 rounds are byte-equivalent
after sorting and excluding tournament_id. The current Deck Rankings field
inherits both publications; current Dimir Doomsday standings gain a duplicate
12–4 from Munchlax446 and 2plus2isfive unless the event alias is removed.

Found during the Doomsday variant report's live-corpus validation. That report
will exclude verified event aliases locally; ingestion/global field correction
remains separate. Preserve distinct same-day events and daily League publications:
League URL numeric suffixes are not unique event identifiers. Broader identity and
cache replay behavior need review before changing shared ingestion/history.
