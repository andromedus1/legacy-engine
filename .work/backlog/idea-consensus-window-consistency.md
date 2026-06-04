---
id: idea-consensus-window-consistency
created: 2026-06-04
tags: [generation]
---

generate consensus defaults to 'latest ban-regime' (often thin: n=32 for current Doomsday, yielding shaky modal counts like 1 Thassa's Oracle), while the matchup engine uses per-deck adaptive valid_since — so a generated decklist and its matchup numbers come from different slices, which is confusing and degrades consensus quality. Align consensus's default window with the adaptive/affectedness window (or warn + fall back to the deeper slice when the regime is thin).
