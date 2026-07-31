---
id: feature-era-alarm-hygiene
kind: feature
stage: drafting
tags: [analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Era-alarm hygiene — registered-ban awareness + same-date multi-ban attribution

## Brief

Three related eras-surface findings: (1)+(2) the drift alarm's wording goes stale after a
ban is registered — post `eras confirm` (Candelabra), `eras run` still emits "possible
unregistered B&R change" even though the ban IS registered and the boundary is merely held
below acceptance; the alarm should consult the registered-events ledger and say so (two
parks merged — same defect). (3) Era-boundary attribution on a same-date double ban names
only the first matching card and can miss the load-bearing one (named Entomb, missed Nadu
— 91% of pre-ban Cephalid decks mained Nadu); attribution should consider all same-date
events and rank by entity relevance. Full member texts below.

## Member findings (absorbed from backlog)

---

### idea-alarm-registered-ban-wording


**Drift-alarm wording after a ban is registered but the era boundary is still held.** Post
`eras confirm` (Candelabra), the Tron alarm still reads "possible unregistered B&R change" —
technically stale: the ban IS registered; the era boundary is merely held below acceptance
(confirmation asymmetry, thin post-ban sample). The alarm's suppression/wording check should
also consult BAN_EVENTS directly: a registered ban date inside the recent window should render
"disturbance consistent with registered ban: <card> (<date>); era windows truncate via the ban
horizon until the new era accumulates sample" instead of the unregistered-B&R hint. Same for
the Grixis Reanimator [Shallow Grave] camp alarm if a parent-level attribution covers it.

---

### idea-eras-alarm-stale-after-registration


**Drift-alarm message is stale after ban registration.** Candelabra of Tawnos is registered in
`src/legacy_engine/data/banlist/events.json` (via `eras confirm` on 2026-07-12), but today's
`eras run` still emits `// ⚠ Tron: unattributed disturbance (p_change=0.929) — possible
unregistered B&R change` (same for Grixis Reanimator [Shallow Grave]). The alarm should consult
BAN_EVENTS and say something like "registered ban (Candelabra 2026-06-29) awaiting detectable
boundary — post-ban sample too thin" instead of implying no one has registered it.
Repro: `eras run` (2026-07-13), tail of output.

---

### bug-era-attribution-same-date-ban


Era-boundary attribution named Entomb and missed Nadu on the 2025-11-10 double ban for
Cephalid breakfast — its trigger reads "ban: Entomb (2025-11-10) — inclusion unverified
(not in this entity's flex band)" even though 91% of pre-ban Cephalid decks mained Nadu.
The attribution inclusion check only scans the entity's flex band, so it verified the
wrong same-date ban; `analytics.affectedness.archetype_valid_since` (any-card >=25%
pre-ban inclusion, either board) got it right. Align the attribution check: on
multi-card ban dates, verify inclusion per banned card across the full deck, and name
the card that actually hits.
