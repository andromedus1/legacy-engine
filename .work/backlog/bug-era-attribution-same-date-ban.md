---
id: bug-era-attribution-same-date-ban
created: 2026-07-28
tags: [eras]
---

Era-boundary attribution named Entomb and missed Nadu on the 2025-11-10 double ban for
Cephalid breakfast — its trigger reads "ban: Entomb (2025-11-10) — inclusion unverified
(not in this entity's flex band)" even though 91% of pre-ban Cephalid decks mained Nadu.
The attribution inclusion check only scans the entity's flex band, so it verified the
wrong same-date ban; `analytics.affectedness.archetype_valid_since` (any-card >=25%
pre-ban inclusion, either board) got it right. Align the attribution check: on
multi-card ban dates, verify inclusion per banned card across the full deck, and name
the card that actually hits.
