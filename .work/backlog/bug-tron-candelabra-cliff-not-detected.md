---
id: bug-tron-candelabra-cliff-not-detected
created: 2026-08-04
tags: [bug, eras, analysis]
---

**Tron's post-Candelabra collapse produced no era boundary, so every "current regime"
Tron number the engine emits blends a 9.5%-share deck with a 2.0%-share deck.** The
ban was aimed at Tron specifically; the entity it targeted is the one entity that did
not get the boundary.

Measured 2026-08-04 (corpus through 2026-07-30, `eras run` last at 2026-07-31):

| window | Tron decks / total | share |
|---|---|---|
| current regime pre-ban (2026-05-18 → 06-29) | 282 / 2971 | **9.49%** |
| post-Candelabra (2026-06-29 → 08-01) | 38 / 1876 | **2.03%** |

A 79% drop. Monthly deck counts: Apr 169, May 158, Jun 196, **Jul 38**. Zero copies of
Candelabra of Tawnos remain in the corpus post-ban, so the composition break is total,
not partial.

`entity_eras` for Tron:

```
stable_since = 2026-05-11   (accepted)
  2025-03-17  p=0.06     bh_accepted=false  ban: Sowing Mycospawn
  2025-12-22  p=0.135    bh_accepted=false  unattributed
  2026-05-11  p=1.7e-31  bh_accepted=TRUE   ban: Undercity Informer
                          signal: presence-adopt "Faerie Macabre 0%->33%"
```

There is **no 2026-06-29 candidate at all** for Tron, while the same `eras run` did
detect that boundary for Blue Artifacts, Doomsday, and Izzet Delver (visible in the
positioning audit header). Note this is a regression against the 2026-07-12 state
recorded in project memory, where Tron's `valid_since` *was* 2026-06-29 — the newer run
moved the boundary earlier and lost the ban.

Likely mechanism: the 2026-05-11 Faerie-Macabre presence-adopt signal is astronomically
strong (p=1.7e-31) and, once accepted as `stable_since`, the later share cliff sits
inside the accepted era where the share signal is comparatively weak (the 2026-05-11
row's own share signal is p=0.505). A single-boundary `stable_since` cannot express
"composition stabilised in May, then population collapsed in June."

Two things to consider, probably separable:

1. **Detect share cliffs independently of composition boundaries.** A −79% population
   drop with a confirmed same-week ban should always produce a boundary regardless of
   what the composition signal says. The BAN_EVENTS ledger already knows Candelabra was
   confirmed on 2026-06-29 (it was confirmed via `eras confirm` in a prior session) —
   a registered ban should be able to force a candidate for every entity whose share
   moves through it, not only those whose flex band moves.
2. **Surface population collapse in field composition.** `report meta` /
   field-composition currently reports Tron at 6.60% of the current regime, which is
   true of the window and false of the format. Candidate honest-degrade: when an
   entity's trailing-4-week share diverges from its window share by more than some
   factor, label the row (`// share 6.6% window / 2.0% trailing 4wk — collapsing`).

This is the concrete instance of the caveat already logged as "detection lags fast
rebuilds". Related: `idea-eras-alarm-stale-after-registration`,
`roadmap-young-regime-data-strategy`.

Practical consequence hit this session: building
`decks/tron-blue-karn-moxfield.txt` required hand-windowing to `>= 2026-06-29`, because
every engine-default read blended the pre-ban and post-ban decks.
