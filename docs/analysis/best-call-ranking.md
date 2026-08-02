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
  strata, the cross-camp P(best) column, and the exploratory three-level family view;
  the page itself carries the authoritative definitional prose.
decisions:
  - "Agency % = min(adjusted field WR, worst grounded matchup) x 100 — the page's single ranking number; theory under test: maximum agency = most fun."
  - "Measured cells only: a matchup counts at n>=8; era-windowed cells preferred; the fallback pools matches since the last ban that affected either deck (BA label, archetype_valid_since) — full-corpus FC only when neither deck was ever ban-affected. The Nadu rule: a banned engine's matches never inflate a row (Nadu Cephalid inflated agency 40.5 vs honest 31.1, 2026-07-28)."
  - "A thin cell must prove its hole: the floor is set only by cells with n>=20 or a 95% CI upper bound below 50% — otherwise min() is won by noise and better-covered decks mechanically show lower floors. Blowouts classify on the shrunk estimate, not raw."
  - "Grounded row = top-8 field opponents all measured AND >=80% of field share-mass covered; ungrounded rows are labeled leans (agency shown as an upper bound), and sorting never intermixes strata."
  - "Field basis = the current ban-regime window; --field-since defaults to the latest confirmed ban event so regime changes auto-track; its confidence tier is computed from window size, never hardcoded."
  - "Camp sweep = ONE multi-split pass (build_multi_split_adaptive + one uniform multi-split matrix per distinct ban-fallback date) — numerically identical to per-parent split builds (parity-tested at engine and script level, ~25x cheaper), keeping the per-pair max(subj_ban, opp_ban) Nadu-rule fallback windows."
  - "Cross-camp P(best) = ONE shared-field rank_decks MC (fixed seed) over all camps + unsplit field archetypes on the page-used cells; candidacy is gated at the same coverage threshold that suppresses display (<5% measured coverage -> n/a + reason) because zero-coverage candidates otherwise absorb the whole argmax as imputation noise; S* labels full-field values below 85% coverage."
  - "Superarchetypes remain an additive, explicitly non-authoritative page layer: page-unmeasured ledgers may carry stricter-gated family leans that never enter archetype/camp decision metrics, while the serving registry produces an exploratory family → archetype → camp navigator, S×S family heatmap, and camps×parent-opponents map. Archetype Best Call remains authoritative until a future-only benchmark passes; no registry/--no-superarchetypes explicitly degrades the family surface and preserves the baseline."
  - "The output page is gitignored and disposable; the template + refresh script are the tracked artifacts — regenerate, don't hand-edit (data changes go in the script, presentation changes in the template)."
  - "Refresh THIS page last in the data cycle: its matrices read eras + variants, so it inherits whatever labeling state exists when it runs."
---

# Best Deck / Best Call agency ranking — refresh runbook

The page: [decks/best-deck-best-call-ranking.html](../../decks/best-deck-best-call-ranking.html)
(gitignored, self-contained offline HTML). Tables are click-sortable per column
(default: agency % descending); sorting stays within honesty strata. Rows expand
to the full per-opponent matchup ledger.

## Refresh (one command, after a data cycle)

The page reads eras + variants, so run it **last**, after the standard cycle:

```bash
.venv/bin/legacy-engine refresh all          # mirror + ingest new events
.venv/bin/legacy-engine label                # full-corpus archetype relabel
# re-apply every staged camp split (variant labels are wiped by label):
.venv/bin/legacy-engine discover list | grep 'status: candidate' | sed 's/  \[status.*//' | \
  while IFS= read -r a; do .venv/bin/legacy-engine discover apply --archetype "$a"; done
.venv/bin/legacy-engine eras run             # re-detect era boundaries + drift alarms
# re-derive cores over each archetype's own stable era (the page's family fallback
# reads the DuckDB derived cache; horizon provenance is echoed in the audit header):
.venv/bin/legacy-engine superarchetype run
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

**Three-level strategy-family view (exploratory).** The same serving registry
also produces an additive top-level `families` payload beside `arch` and `camps`.
Each family record carries its stable id, display/full labels, curated flag,
current-field member archetypes with provenance, presentation-only family
metrics, a deterministic two-sentence description naming its derived/curated origin, leading
positive-share current-field members, and field footprint, and typed family-opponent cells. The template renders this as an
**family-expandable, visually nested family → archetype → camp** hierarchy: family rows open onto
their current-field archetypes with each archetype's staged camp rows nested beneath it. Long derived labels composed with ` + ` are shortened for display after
the first two components (`... + N more`), while `full_label` retains the exact
registry label for hover/title disclosure.

The family metrics (agency, adjusted WR, floor, coverage, field share) are an
**exploratory navigation summary, not a recommendation surface**. A family cell
is a current-field-share-weighted summary of accepted member-archetype pooled
cells; refused and below-display-gate pools never become numbers. Each numeric cell carries its
accepted subject field-share support; coverage and adjusted WR are weighted by that support, top
opponents need at least the page coverage threshold in subject support to ground a row, and partial
refusals remain inspectable in the tooltip. Ungrounded family metrics are visibly labeled as leans
(and agency as an upper bound), matching the page's muting discipline. The family
floor excludes the intra-family cell. These values do not feed archetype Best
Call, camp P(best), or either view's grounding strata. The archetype table remains
the decision-authoritative Best Call surface until the family layer passes a
future-only predictive/decision benchmark.

Two maps expose the evidence without inventing a camp-by-camp cube:

- The **S×S strategy-family heatmap** has subject families on rows and opponent
  families on columns. Numeric cells use only accepted typed pooled outputs;
  hatched `refuse` cells retain the typed refusal or insufficient-`n_eff` reason
  in a keyboard-focusable tooltip/accessible label, along with effective n, subject support,
  current-regime evidence share, and source windows; outlined diagonal cells are labeled intra-family.
- The **camps×parent opponents map** is rectangular: staged camps are subjects
  and the existing parent-archetype opponents are columns. Measured cells show
  the shrunk rate; thin/unavailable cells stay explicit (`n=<count>` or an
  unavailable marker). It performs no speculative camp x camp pooling.

If the serving registry is absent, empty, or disabled with
`--no-superarchetypes`, `families` is an empty list. The page then says that the
strategy-family view is unavailable, hides both family maps, and leaves the
authoritative archetype and camp views unaffected; this is an explicit honest
degrade, not an unlabeled missing section.

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
- **Blowouts** count measured current-field matchups at shrunk WR <40% (full) /
  40–45% (half) — classified on the shrunk estimate so thin-cell noise doesn't
  count; "% meta that blows you out" weights them by field share and is a lower
  bound (unmeasured opponents can't be counted).
- **Floors are evidence-gated** — a cell sets the floor only at n>=20, or
  thinner when its 95% CI upper bound is still below 50% (an 0-8 qualifies —
  Eldrazi vs Red Stompy, CI 0–26%; a 2-6 is ambiguity and cannot). Still check
  the expanded ledger (CIs shown per cell) before acting on a single-cell verdict.
- **Fallback windows are ban-scoped** — a deck whose engine was banned (Nadu
  Cephalid, Candelabra Forge) keeps none of its banned-era matches in any cell
  that touches it; coverage drops honestly instead (Forge 95%→17% grounding was
  Candelabra-era data).
- Camp rows carry staged-candidate provenance (speculative overlay, never
  promoted taxonomy).
- **Family rows are exploratory navigation** — their agency/adj/floor/coverage
  summarize typed pooled family evidence and must not be read as a ranked Best
  Call recommendation. Follow the nested row to the archetype's `Best Call`
  metrics for the authoritative decision surface; family authority requires the
  future-only benchmark first.
- **Heatmap refusals are data** — a hatched family cell is a typed refusal (or
  insufficient effective evidence), not a blank to interpolate. Outlined cells
  are intra-family; the camps map remains camps×parent opponents by design.
- **Family leans are leans** — an `imputed`/`pooled` value in the ledger is
  superarchetype-sourced, never a measured cell, and passing the heterogeneity
  gate never promotes it: I² is one-sided evidence (a low value is not a
  certificate of exchangeability). A `family range` line is a refusal rendered
  honestly — read the member split, not a blended number. Check the audit header
  for the registry window (a stale-taxonomy warning there means re-run
  `superarchetype run`; use `--since <date>` only for a labeled uniform-window diagnostic).
- **Cross-camp P(best) is a shared-budget number** — all camps and unsplit
  archetypes compete in ONE argmax, so the values are comparable across parents
  and can never sum past 1. n/a means the row failed the 5% measured-coverage
  candidacy gate (its score would be pure imputation); S* means the supporting
  field WR is a full-field estimate leaning on imputation for unmeasured share,
  which always includes the camp's own parent (that cell is absent by
  construction).
