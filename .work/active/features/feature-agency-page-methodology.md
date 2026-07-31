---
id: feature-agency-page-methodology
kind: feature
stage: drafting
tags: [analytics, advisory]
parent: null
depends_on: [feature-multi-split-matrix]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Agency-page methodology v2 — lean view, path-to-grounding, verdict stability, floor fix

## Brief

Four methodology improvements to the best-deck/best-call agency ranking page (generator:
scripts/refresh_best_call_ranking.py; runbook: docs/analysis/best-call-ranking.md), all from
the 2026-07-28 session retro: (1) a soft-weighted "lean view" beside the gated view — every
cell contributes in proportion to its precision, agency becomes a posterior, no n>=8 /
coverage-80% cliffs (gated view stays the headline); (2) every ungrounded row shows its
path to grounding — which 2-3 cells need how many more matches to enter the grounded
stratum, converting discarded coverage into a data-acquisition agenda; (3) a per-row rank
STABILITY column computed across the page's own methodological variants (raw / CI-gated /
ban-scoped / era-only) — robustness-across-estimators beat any single metric's #1;
(4) the agency (worst-matchup floor) methodology fix. Full member texts below.

Depends on feature-multi-split-matrix: camp-level ranking currently needs ~29 separate
per-parent split-matrix builds and P(best) is incomparable across them; the stability
column and lean view multiply that cost without the one-pass multi-split matrix.

## Member findings (absorbed from backlog)

---

### idea-lean-view-toggle


Add a soft-weighted "lean view" beside the agency page's gated view: no n>=8 /
coverage-80% cliffs — every cell contributes in proportion to its precision, agency
becomes a posterior rather than a hard min. The gated view stays the headline
(auditable, legible); the lean view recovers the graded middle the binary gates
discard (live stratum fell 24 -> 13 rows after the Nadu rule — much of the format now
lives between "proven" and "unknown"). Divergence between the two views is itself
diagnostic, per the divergence-as-diagnostic house pattern. Andrew's framing: "we're
quite rigorous, but we sacrifice a lot of ability to view into the data."

---

### idea-path-to-grounding


Every ungrounded row on the agency page should show its path to grounding: which 2-3
cells need how many more matches (to reach n>=8 measured / top-8 coverage) for the row
to enter the grounded stratum. Converts discarded coverage into a concrete
data-acquisition agenda — "Cephalid needs X more matches vs Y" — and tells the user
what to watch as upstream data flows.

---

### idea-verdict-stability-column


Compute the agency ranking under all of the page's own methodological variants (raw /
CI-gated / ban-scoped / era-only) and surface per-row rank stability as a first-class
column. From the 2026-07-28 session: robustness-across-estimators beat any single
metric's #1 — Doomsday stayed #6-8 across every perturbation while Eldrazi, Cephalid,
and Mystic Forge each collapsed under one (n=8 noise, Nadu contamination, Candelabra
coverage). A deck that's #6 under every estimator beats a deck that's #1 under one.

---

### idea-agency-floor-methodology-fix


Patch the unsuppressed best-deck-best-call report's "agency" (worst-matchup floor)
methodology. Report: `decks/best-deck-best-call-ranking.html` (gitignored); generators
`rank_all.py` + `gen_best_call_html.py` were session-scratchpad (2026-07-21 session —
rebuild from the project-state memory description if lost).

**Context.** Andrew caught two real holes in the floor analysis after it named Cephalid
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
