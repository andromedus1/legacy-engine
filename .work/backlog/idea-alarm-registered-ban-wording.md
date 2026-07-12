---
id: idea-alarm-registered-ban-wording
created: 2026-07-12
tags: [analytics, honesty]
---

**Drift-alarm wording after a ban is registered but the era boundary is still held.** Post
`eras confirm` (Candelabra), the Tron alarm still reads "possible unregistered B&R change" —
technically stale: the ban IS registered; the era boundary is merely held below acceptance
(confirmation asymmetry, thin post-ban sample). The alarm's suppression/wording check should
also consult BAN_EVENTS directly: a registered ban date inside the recent window should render
"disturbance consistent with registered ban: <card> (<date>); era windows truncate via the ban
horizon until the new era accumulates sample" instead of the unregistered-B&R hint. Same for
the Grixis Reanimator [Shallow Grave] camp alarm if a parent-level attribution covers it.
