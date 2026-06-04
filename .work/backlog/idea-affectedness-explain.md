---
id: idea-affectedness-explain
created: 2026-06-04
tags: [analytics]
---

The per-deck ban-affectedness valid_since (e.g. why Doomsday's window is 2024-12-16) is computed but uninspectable from the CLI — we had to call archetype_valid_since in Python. Add a `report affectedness` / --explain that shows each deck's chosen window and the cards/bans + overlap fractions that drove it, so users can trust the adaptive windowing.
