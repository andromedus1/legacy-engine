---
id: idea-agency-floor-methodology-fix
created: 2026-07-21
tags: [analytics, honesty]
---

Patch the unsuppressed best-deck-best-call report's "agency" (worst-matchup floor)
methodology. Report: `decks/best-deck-best-call-ranking.html` (gitignored); generators
`rank_all.py` + `gen_best_call_html.py` were session-scratchpad (2026-07-21 session —
rebuild from the project-state memory description if lost).

**Context.** the maintainer caught two real holes in the floor analysis after it named Cephalid
Breakfast the top "agency" deck (high adjusted WR + high worst matchup):

1. **Coverage hole** — the floor and adjusted-WR columns silently exclude field opponents
   with NO era-windowed cell. Cephalid Breakfast was missing cells vs **26% of field
   share-mass** (incl. Mystic Forge Combo 6.3%, Dimir Midrange 5.1%), so a row's floor can
   look clean simply because its bad matchups are unmeasured.
2. **Prior-riding floor** — opponent-era windowing shrinks cells vs recently-disturbed
   opponents to n=1–2, which sit at their shrinkage prior near 50%, so a maximin/floor
   sort systematically **rewards ignorance**. Cephalid's cells vs Izzet/Azorius/Lands were
   all n=1; Tron's whole row is n≤18. Raw recent slices told the true story (Cephalid vs
   Lands 3/11 = 27% raw). Reinforces the 2026-07-11 shrinkage-floor-mirage lesson.

**Fixes to implement:**

- (a) **Per-row window fallback**: where the era window has no cell, fall back to the
  full-corpus cell LABELED as such (per-cell window provenance) — never silently drop the
  opponent.
- (b) **Coverage counts against the floor**: a floor claim is only as strong as its
  coverage — display "floor undefined over X% of field" or penalize the index.
- (c) **Grounding gate on the ROW, not just the single worst cell**: "grounded floor"
  should require the top-k field shares each measured at n≥threshold (Cephalid had only
  2/19 cells at n≥10 yet got the grounded label because its one worst cell was n=11).
- (d) **Re-rank agency tables under (a)–(c)** — verified outcome: **Eldrazi becomes the
  agency pick** (full-corpus floors: 44.4% vs Mystic Forge n=185, 46.2% vs S&T n=264,
  47.1% vs Izzet n=163; 95% coverage); Cephalid demoted to lean (no measured hole below
  ~44% but current-field form unmeasured); Tron demoted to speculative.

**Generalizes**: any maximin/floor ranking over shrunk cells needs a coverage-aware +
raw-corroborated basis. Candidate absorption target: the report regenerators, and possibly
a first-class `advise agency` floor surface in the engine where these gates live in code
instead of scratchpad scripts.
