---
description: Read before refreshing or interpreting the Best Deck / Best Call agency ranking page — the one-command refresh runbook, the metric definitions, and the honesty gates baked into the page.
type: design
kind: planning
status: active
updated: 2026-08-02
summary: |
  Runbook + method spec for decks/best-deck-best-call-ranking.html (gitignored, fully
  regenerable). One tracked script recomputes the page from the DuckDB corpus through a
  tracked HTML template: scripts/refresh_best_call_ranking.py +
  scripts/best_call_ranking_template.html. Defines Agency %, the grounded/current
  strata, the cross-camp P(best) column, and the five-plan strategic taxonomy;
  the page itself carries the authoritative definitional prose.
decisions:
  - "Agency % = min(adjusted field WR, worst measured matchup) x 100 — the page's single ranking number; theory under test: maximum agency = most fun."
  - "Measured cells only: a matchup counts at n>=8; era-windowed cells preferred; the fallback pools matches since the last ban that affected either deck (BA label, archetype_valid_since) — full-corpus FC only when neither deck was ever ban-affected. The Nadu rule: a banned engine's matches never inflate a row (Nadu Cephalid inflated agency 40.5 vs honest 31.1, 2026-07-28)."
  - "Every measured cell (n>=8 by default) can set the floor using its shrunk estimate; this exposes apparent holes sooner. Because better-covered decks have more chances to reveal a low matchup, ungrounded agency remains an explicit upper bound and must be read with measured coverage. Blowouts classify on the raw observed rate after the same measured-cell gate."
  - "Grounded row = top-8 field opponents all measured AND >=80% of field share-mass covered; ungrounded rows are labeled leans (agency shown as an upper bound), and sorting never intermixes strata."
  - "Field basis = the current ban-regime window; --field-since defaults to the latest confirmed ban event so regime changes auto-track; its confidence tier is computed from window size, never hardcoded."
  - "Camp sweep = ONE multi-split pass (build_multi_split_adaptive + one uniform multi-split matrix per distinct ban-fallback date) — numerically identical to per-parent split builds (parity-tested at engine and script level, ~25x cheaper), keeping the per-pair max(subj_ban, opp_ban) Nadu-rule fallback windows."
  - "Cross-camp P(best) = ONE shared-field rank_decks MC (fixed seed) over all camps + unsplit field archetypes on the page-used cells; candidacy is gated at the same coverage threshold that suppresses display (<5% measured coverage -> n/a + reason) because zero-coverage candidates otherwise absorb the whole argmax as imputation noise; S* labels full-field values below 85% coverage."
  - "Strategic plans are a curated, independent five-plan taxonomy: every current-field archetype has exactly one primary plan for mutually exclusive match-level aggregation and may carry secondary labels for hybrid explanation only. Plan cells pool decisive matches directly rather than averaging archetype rates."
  - "Strategic-plan same-plan play is structural 50% context: it contributes to adjusted field WR but is never measured, never sets the floor, and is excluded from the external-coverage denominator. External plan cells use the page's n>=8 measured gate; grounding requires the top external plans measured and >=80% external field-share coverage."
  - "Superarchetypes remain only as stricter-gated fallback evidence in otherwise unmeasured archetype/camp ledger cells. They never enter strategic-plan, archetype, or camp metrics; --no-superarchetypes removes those ledger leans without changing the ranking surfaces."
  - "The output page is gitignored and disposable; the template + refresh script are the tracked artifacts — regenerate, don't hand-edit (data changes go in the script, presentation changes in the template)."
  - "Refresh THIS page last in the data cycle: its matrices read eras + variants, so it inherits whatever labeling state exists when it runs."
---

# Best Deck / Best Call agency ranking — refresh runbook

The page: [decks/best-deck-best-call-ranking.html](../../decks/best-deck-best-call-ranking.html)
(gitignored, self-contained offline HTML). Tables are click-sortable per column
(default: agency % descending); sorting stays within honesty strata. Coverage
filters and column sorting apply to the strategic-plan, archetype, and camp peer
tables. Rows expand to accessible per-opponent matchup ledgers.

## Refresh (one command, after a data cycle)

The page reads eras + variants, so run it **last**, after the standard cycle:

```bash
.venv/bin/legacy-engine refresh all          # mirror + ingest new events
.venv/bin/legacy-engine label                # full-corpus archetype relabel
# re-apply every staged camp split (variant labels are wiped by label):
.venv/bin/legacy-engine discover list | grep 'status: candidate' | sed 's/  \[status.*//' | \
  while IFS= read -r a; do .venv/bin/legacy-engine discover apply --archetype "$a"; done
.venv/bin/legacy-engine eras run             # re-detect era boundaries + drift alarms
# Preview a candidate over each archetype's own stable era. Review its membership,
# churn, and quality output; this does not replace the serving family registry:
.venv/bin/legacy-engine superarchetype run --compare-since 2026-06-29
# Only after explicitly approving that candidate, promote it to the serving registry:
# .venv/bin/legacy-engine superarchetype run --promote
.venv/bin/python scripts/refresh_best_call_ranking.py
```

Optionally re-run discovery first (`discover run --archetype <parent> --since 2024-12-16`
per parent) when the corpus has grown materially — staged splits carry frozen
membership, so **new decks get camp labels only after a re-staged PASS + apply**.
A gate-A FAIL keeps the old frozen split; treat that parent's camp rows as stale.

Knobs (defaults are the page's published method): `--field-since` (defaults to the
latest confirmed ban event date), `--ground-n 8`, `--top-k 8`, `--cover-min 0.8`,
`--min-row-share 0.001`, `--no-superarchetypes` (baseline/audit regeneration without
the family-fallback overlay), `--db`, `--out`.

## What the script does

`scripts/refresh_best_call_ranking.py` computes the embedded data blob —
archetype rows from one `build_adaptive_matrix` + one `build_matrix` per distinct
ban-affectedness fallback date; camp rows from ONE `build_multi_split_adaptive`
pass over every staged discovery parent (`staged_split_parents()`) plus one
`build_multi_split_matrix` per distinct ban-scoped fallback date serving all
parents at once; field shares and camp fractions from the ban-regime window —
and splices it into `scripts/best_call_ranking_template.html` at the
`__D_BLOB__` placeholder. Camp cells are field-for-field identical to per-parent
`split_variant` builds — the engine parity suite plus the script-level parity
test (`tests/test_refresh_best_call_ranking.py`, old path reconstructed in-test
and diffed row-for-row) enforce it — and the one-pass sweep keeps the per-pair
`max(subj_ban, opp_ban)` Nadu-rule fallback windows.

The camp table's **P(best) column** comes from one shared-field `rank_decks` MC
(fixed seed `RANK_SEED`, parameters in the blob's `meta.rank` + audit lines):
every camp and every unsplit field archetype is scored against the same sampled
parent-level Dirichlet field, on the page-used cells (era preferred, ban-scoped
fallback), so values are comparable across camps of different parents.
Candidacy is gated at the display-suppression coverage threshold — a candidate
below 5% measured coverage shows n/a with its coverage instead of an
imputation-noise score.

**Strategic-plan view.** The page adds a `plans` peer table above the archetype
table. Its registry defines five curated plans (`Disrupt + Pressure`, `Go Off`,
`Go Over`, `Go Wide`, and `Lock + Outlast`) independently of composition-derived
superarchetypes. Every current-field archetype must have exactly one primary
assignment; optional secondary assignments describe hybrids in the expanded
portrait but do not duplicate their matches or field share across rows.

Plan cells are rebuilt from decisive match records mapped through those primary
assignments. They are therefore match-level aggregates, not averages of rendered
archetype percentages. External plan matchups use the same `n>=8` measured gate
as the page. Same-plan matches are shown as structural 50% context: 50% contributes
to adjusted field WR at that plan's field share, but the diagonal is never marked
measured, never sets the floor, and never enters external coverage. The floor is
the worst measured external plan. Coverage is measured external opponent share
divided by all external opponent share; grounding requires every top external
opponent (up to `--top-k`) measured plus `--cover-min` external coverage. Thus an
incomplete plan agency remains an explicit upper bound.

The peer table is sortable within grounded/ungrounded honesty strata and has a
minimum-floor-coverage filter. Each plan name is a real keyboard-focusable
disclosure button with `aria-expanded`/`aria-controls`; opening it yields a
responsive portrait (description, field footprint, decisive-match count, agency,
member archetypes, and secondary-plan chips) beside the exact plan-versus-plan
ledger. The ledger distinguishes measured shrunk/raw records, below-gate or empty
external cells, and the structural same-plan diagonal in text rather than color
alone.

**Superarchetype family fallback (ledger-only).** `main()` reads the serving
taxonomy from the SAME `--db` (`read_superarchetype_members` — the derived cache
`superarchetype run` rebuilds; absent tables = layer off, byte-identical) and
passes it into the one-pass build. Page-unmeasured cells then carry an additive
`sa` payload resolved by the engine's display ladder — `imputed` (licensed family
siblings' record vs that exact opponent, tau-widened CI), `pooled` (the deck vs
every member of the opponent's family, `intra-family` share flagged), or `range`
(refused/unlicensed/vetoed: the member split with the named refusal — `dominated
by <member>`, heterogeneous pool, local veto, comparability desert — and no point
estimate). The expanded ledger renders them as dashed-border leans with
provenance chips; pools with <50% current-regime evidence carry an amber
`◦mostly pre-regime` marker. **Isolation contract:** leans never enter agency,
adj, floor, coverage, strata, or the P(best) MC — enforced by
`TestSuperarchetypeIsolation` (blob equality modulo additive `sa` keys + audit
lines). Split parents' archetype rows carry no fallback (the multi-split subject
set is camps + unsplit archetypes); their camp rows do.

The full refresh runs in ~40s on the current corpus (~11s archetype matrices +
~13s one-pass camp matrices + ~2s shared-field ranking); the script echoes each
phase's wall time.

Metric definitions live in the page's "What is Agency %?" card and in the
frontmatter decisions above — the page prose is authoritative.

## Interpretation guardrails

- **Strata are honesty walls**: grounded+current, grounded-but-not-current
  (<5 decks in the last 4 corpus weeks), ungrounded (thin floor = upper bound).
  Column sorting reorders *within* a stratum only.
- **Blowouts** count measured current-field matchups at raw observed WR <40%
  (full) / 40–45% (half). The `n>=8` measured-cell gate excludes thin cells;
  among those measured cells, classification uses the raw rate rather than the
  shrunk estimate. "% meta that blows you out" weights them by field share and
  is a lower bound (unmeasured opponents can't be counted).
- **Positive ledger highlights** apply only to measured (`n>=8`) cells and use
  raw observed WR: **Edge** at 55–60% inclusive and **Dominant** above 60%.
  They are descriptive ledger bands only; they do not affect any metric,
  grounding decision, or ranking.
- **Floors use every measured cell** — once a matchup reaches the page's
  `n>=8` measured gate, its shrunk estimate can set the floor. This exposes
  holes earlier, while the explicit upper-bound marker and measured-coverage
  column keep incomplete rows from masquerading as fully mapped claims. Still
  check the expanded ledger (raw record and CI shown) before acting on one cell.
- **Fallback windows are ban-scoped** — a deck whose engine was banned (Nadu
  Cephalid, Candelabra Forge) keeps none of its banned-era matches in any cell
  that touches it; coverage drops honestly instead (Forge 95%→17% grounding was
  Candelabra-era data).
- Camp rows carry staged-candidate provenance (speculative overlay, never
  promoted taxonomy).
- **Plan rows are mutually exclusive primary-plan aggregates** — secondary chips
  explain hybrid decks but never count their matches or field share again.
  Same-plan 50% is structural context, not evidence: judge a plan's floor and
  grounding only from its external cells and external-coverage percentage.
- **Family leans are leans** — an `imputed`/`pooled` value in the ledger is
  superarchetype-sourced, never a measured cell, and passing the heterogeneity
  gate never promotes it: I² is one-sided evidence (a low value is not a
  certificate of exchangeability). A `family range` line is a refusal rendered
  honestly — read the member split, not a blended number. Check the audit header
  for the registry window (a stale-taxonomy warning there means preview a candidate with
  `superarchetype run`, review it, then explicitly use `--promote` if approved; use
  `--since <date>` only for a labeled uniform-window diagnostic).
- **Cross-camp P(best) is a shared-budget number** — all camps and unsplit
  archetypes compete in ONE argmax, so the values are comparable across parents
  and can never sum past 1. n/a means the row failed the 5% measured-coverage
  candidacy gate (its score would be pure imputation); S* means the supporting
  field WR is a full-field estimate leaning on imputation for unmeasured share,
  which always includes the camp's own parent (that cell is absent by
  construction).
