---
description: Read before refreshing or interpreting the Best Deck / Best Call agency ranking page — the one-command refresh runbook, the metric definitions, and the honesty gates baked into the page.
type: design
kind: planning
status: active
updated: 2026-07-28
summary: |
  Runbook + method spec for decks/best-deck-best-call-ranking.html (gitignored, fully
  regenerable). One tracked script recomputes the page from the DuckDB corpus through a
  tracked HTML template: scripts/refresh_best_call_ranking.py +
  scripts/best_call_ranking_template.html. Defines Agency % and the grounded/current
  strata; the page itself carries the authoritative definitional prose.
decisions:
  - "Agency % = min(adjusted field WR, worst grounded matchup) x 100 — the page's single ranking number; theory under test: maximum agency = most fun."
  - "Measured cells only: a matchup counts at n>=8; era-windowed cells preferred, full-corpus fallback labeled FC; a thin era cell is shown thin, never a shrinkage prior masquerading as a floor."
  - "Grounded row = top-8 field opponents all measured AND >=80% of field share-mass covered; ungrounded rows are labeled leans (agency shown as an upper bound), and sorting never intermixes strata."
  - "Field basis = the current ban-regime window; --field-since defaults to the latest confirmed ban event so regime changes auto-track; its confidence tier is computed from window size, never hardcoded."
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
.venv/bin/python scripts/refresh_best_call_ranking.py
```

Optionally re-run discovery first (`discover run --archetype <parent> --since 2024-12-16`
per parent) when the corpus has grown materially — staged splits carry frozen
membership, so **new decks get camp labels only after a re-staged PASS + apply**.
A gate-A FAIL keeps the old frozen split; treat that parent's camp rows as stale.

Knobs (defaults are the page's published method): `--field-since` (defaults to the
latest confirmed ban event date), `--ground-n 8`, `--top-k 8`, `--cover-min 0.8`,
`--min-row-share 0.001`, `--db`, `--out`.

## What the script does

`scripts/refresh_best_call_ranking.py` computes the embedded data blob —
archetype rows from one `build_adaptive_matrix` + `build_matrix` pair, camp rows
from one pair per staged discovery parent (`split_variant`), field shares and
camp fractions from the ban-regime window — and splices it into
`scripts/best_call_ranking_template.html` at the `__D_BLOB__` placeholder.
All rendering (strata, sorting, blowout tallies, scatter) is client-side JS in
the template; the blob carries data only.

Metric definitions live in the page's "What is Agency %?" card and in the
frontmatter decisions above — the page prose is authoritative.

## Interpretation guardrails

- **Strata are honesty walls**: grounded+current, grounded-but-not-current
  (<5 decks in the last 4 corpus weeks), ungrounded (thin floor = upper bound).
  Column sorting reorders *within* a stratum only.
- **Blowouts** count measured current-field matchups at raw WR <40% (full) /
  40–45% (half); "% meta that blows you out" weights them by field share and is
  a lower bound (unmeasured opponents can't be counted).
- **A raw n=8 floor is grounded but fragile** — an 0-8 run reads as a ~21%
  shrunk floor (Eldrazi vs Red Stompy, 2026-07-28). Check the expanded ledger
  before acting on a single-cell verdict.
- Camp rows carry staged-candidate provenance (speculative overlay, never
  promoted taxonomy).
