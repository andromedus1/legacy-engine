---
id: feature-regime-windowing-consistency
kind: feature
stage: drafting
tags: [analytics, advisory, methodology]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

**Methodology principle, not just a per-command behavior:** every analytical surface must analyze
data correctly with respect to ban regimes, so tuning reflects the **current** meta and not a stale
pre-ban field.

The engine already has pieces of this:
- `epic-regime-aware-advisory` — `--regime`, adaptive per-cell matchup windows, thin-regime degrade
  banners on advise/report surfaces.
- `idea-consensus-window-consistency` — narrow: consensus's default window (latest ban-regime) vs the
  matchup engine's adaptive window can disagree, so a generated list and its matchup numbers come from
  different slices.

**Broaden into a project-wide principle + checklist:** EVERY surface (`report meta/trends/matchups/
cards/gaps/tiers`, `generate consensus/tune`, all `advise` commands) should (a) default to
ban-regime-aware windowing, (b) use consistent window-resolution semantics across commands, and
(c) loudly state its window + thinness in output. Document it as a methodology principle (a doc /
PRINCIPLES entry), and audit each surface against the checklist — don't just trust per-command code.

**Live example motivating this:** on 2026-06-13 the current regime "after Undercity Informer
(2026-05-18)" is only ~22 days old / 61 events / ~56 Dimir Tempo decks. A naive all-corpus read
would badly misrepresent today's meta (e.g. Dimir Tempo shows 9.0% in the prior regime vs 4.0% now;
Tron 2.2% → 9.1%). Also note: the strongest reference decklists in the corpus (Mengucci, BoshNRoll)
are all from the PRIOR regime — so "copy a pro list" silently imports stale-regime tuning unless the
regime gap is surfaced.

**Specific item found this session:** the `advise sideboard` per-matchup OUT/IN plans were stuck at
"speculative, n≥0" for nearly every opponent in the thin current regime — because those plans do NOT
use the adaptive ban-aware window that the matchup *matrix* already uses (per-cell `valid_since`).
Extend the adaptive window to the sideboard matchup plans so they borrow prior-regime depth the same
way the matrix does, instead of going dark in a fresh regime. Until then, sideboard in/out guidance is
reasoning-based, not data-derived — which should be stated honestly.

Related: [[idea-consensus-window-consistency]].
