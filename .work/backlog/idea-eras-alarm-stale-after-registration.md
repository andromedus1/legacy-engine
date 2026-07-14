---
id: idea-eras-alarm-stale-after-registration
created: 2026-07-13
tags: [eras]
---

**Drift-alarm message is stale after ban registration.** Candelabra of Tawnos is registered in
`src/legacy_engine/data/banlist/events.json` (via `eras confirm` on 2026-07-12), but today's
`eras run` still emits `// ⚠ Tron: unattributed disturbance (p_change=0.929) — possible
unregistered B&R change` (same for Grixis Reanimator [Shallow Grave]). The alarm should consult
BAN_EVENTS and say something like "registered ban (Candelabra 2026-06-29) awaiting detectable
boundary — post-ban sample too thin" instead of implying no one has registered it.
Repro: `eras run` (2026-07-13), tail of output.
