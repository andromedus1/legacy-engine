---
id: idea-card-count-outlier-advisor
created: 2026-06-13
tags: [advisory, analytics, generation]
---

For a given decklist + archetype + regime, surface **each card's field copy-count DISTRIBUTION** (not
just the modal consensus list) and **flag where the user's list is off-consensus, and by how much.**

This session (2026-06-13) we repeatedly hand-queried distributions to validate counts, and it was the
highest-leverage deck-doctoring move of the whole conversation:
- Orcish Bowmasters: 68% run 3, 23% run 4 → "3 is modal, 4 is a real camp."
- Murktide Regent: 79% run 2, 11% run 0, 9% run 3 → "2 is firmly standard."
- Lands: 73% run 19, 21% run 20, only 5% run 18 → caught a wrong 18-land rec.
- Daze: user at 2, field mode 3 → flagged as the one off-consensus count.

`generate consensus` already produces a modal deck, but it does NOT tell you *"on card X you're an
outlier — here's the field distribution and where your count sits."* That per-card outlier report is
what turns a list into a tuned list. Should be ban-regime-windowed by default
([[idea-ban-regime-everywhere]]) and could pair with variant clustering
([[idea-subarchetype-variants]]) so the distribution is compared within the right build, not the
whole parent archetype.
