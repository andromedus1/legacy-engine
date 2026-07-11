---
id: bug-banlist-regime-gap
created: 2026-07-11
tags: [ingestion, bug]
---

**Engine missed the 2026-06-29 Candelabra of Tawnos ban** (era audit finding 1). The regime table
ends at 2026-05-18: rules repo is pinned at the mid-May MTGOFormatData SHA and `data/banlist/`
doesn't exist locally (path/flow to check — `seed banlist` was never re-run this cycle). Corpus
fingerprint of the ban is unmistakable (Tron 59/wk → 1). Fix: refresh the banlist source + bump the
rules pin cadence; register the 2026-06-29 regime; consider a drift alarm (an archetype's week-over-
week collapse ≥70% should prompt a banlist-currency check — honest-degrade the regime windowing
until confirmed).
