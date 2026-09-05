---
description: Read before refreshing or interpreting the Doomsday Variant Rankings report — its exclusive cohort rules, evidence ledgers, current-field projection, and uncertainty limits.
type: design
kind: planning
status: active
updated: 2026-09-05
summary: |
  Runbook for decks/doomsday-variant-rankings.html, a self-contained comparison of
  exclusive Doomsday color-and-signature cohorts against one current non-Doomsday
  field. It keeps tournament standings, compatible resolved rounds, and exact observed
  decklists separate so sparse or historical evidence remains useful without looking current.
decisions:
  - "The report is a separate descriptive surface from the canonical Deck Rankings page and the dated Doomsday field guide; it does not change taxonomy or ranking authority."
  - "Cohorts are mutually exclusive combinations of actual colored mana sources and protection-package signatures, with white, green, red, other-splash, and unclassified residuals retained instead of forced into target variants."
  - "Compatible external matchup rounds use a fixed Beta(1,1) prior per cell and never borrow from the Doomsday parent; missing cells remain neutral with full visible uncertainty."
  - "Published non-League standings and uniquely resolved physical rounds are separate ledgers and are never converted into one denominator."
  - "The generated page is disposable. Edit the tracked Python or HTML template, then regenerate the gitignored output; do not hand-edit it."
---

# Doomsday Variant Rankings — refresh runbook

The generated page is [decks/doomsday-variant-rankings.html](../../decks/doomsday-variant-rankings.html).
It is offline, self-contained, and gitignored. It is separate from the default
[Deck Rankings](../../decks/deck-rankings.html) and from the older dated Doomsday field guide.

## Refresh

After the local database and canonical Deck Rankings report are current, run:

```bash
.venv/bin/python scripts/refresh_doomsday_variant_rankings.py
```

The defaults read `data/legacy.duckdb` and `decks/deck-rankings.html`, include compatible
registrations from `2026-01-01` through the canonical report's exclusive cutoff, and atomically
replace `decks/doomsday-variant-rankings.html`. Override those inputs with `--db`,
`--field-report`, `--since`, and `--out`. The script validates its inputs before publication,
refuses to overwrite the canonical field report, and records the source report hash, protocol,
dates, and extraction audit in the generated page.

The source database and canonical field report are inputs, not outputs. Refresh them through
their own documented workflows; this focused command performs a read-only corpus analysis and
publishes only the specialized report. It is a manual command and is not part of the scheduled
default decision refresh.

## What is compared

Each registration belongs to at most one cohort. Classification reads actual colored mana sources
from basic, dual, shock, and surveil lands together with protection cards in the registered 75.
Fetchlands, Lotus Petal, Cavern of Souls, and Edge of Autumn do not establish a splash by
themselves. Main-deck and sideboard signature counts and the splash lands remain visible for audit.

The target rows are Dimir, Esper with Teferi, Sultai with Veil of Summer, Grixis with Hexing
Squelcher, and four-color white/green. White without Teferi, green without Veil, red without
Squelcher, other splashes, and malformed or unclassifiable registrations remain explicit residual
or audit categories. This prevents a color from standing in for its signature package and keeps
the named variants mutually exclusive.

The report can therefore show a target row with little or no round evidence. That is a useful
absence, not permission to merge the row into its parent or a nearby splash.

## Two evidence ledgers

Tournament standings and resolved matchup rounds answer different questions:

Before either ledger is counted, byte-identical whole-event source aliases sharing the same
non-League MTGO event identity, date, and name collapse to one observation. Distinct event IDs and
daily League publications remain distinct. The extraction audit reports this report-local
deduplication; it does not rewrite the database or the inherited global-field artifact.

- **Standings** are published non-League tournament W-L-D records joined uniquely by normalized
  player and event whose subject list contains no card banned at the report cutoff. Their opponents
  are unknown and unfiltered, and their decisive win rate can include opponents whose lists or
  individual rounds are unavailable, so the report shows record and pilot counts with this denominator.
- **Compatible rounds** are deduplicated physical matches for which both exact lists can be joined
  unambiguously and neither contains a card banned at the report cutoff. This is a card-compatibility
  filter, not a full reconstruction of deck-construction legality. League 5-0 publications are
  registration evidence only and never become five invented wins. Ambiguous joins, duplicates,
  banned-card lists, and other exclusions stay counted in the audit.

The **All compatible** view starts at `--since`. The **Current regime** view starts at the canonical
field report's `field_since`. Both end at the same exclusive report cutoff, and each row exposes its
own W-L/n and evidence date span. There is no outcome date weighting; old evidence is labeled old
rather than made to look current.

## Projection and uncertainty

Every cohort is compared against the same current external field taken from the canonical report.
Only Doomsday-family opponent mass is removed; the remaining shares, including unknown external
archetype mass, are renormalized once. The report does not model the unknown internal Doomsday
variant mix as a mirror.

Each cohort-opponent cell uses its observed compatible rounds with a fixed Beta(1,1) prior. There
is no fitted or outcome-tuned prior and no borrowing from parent Doomsday results. An unseen cell
therefore remains a 50% prior with broad uncertainty. The field-weighted performance interval uses
the canonical field concentration rescaled to the retained external mass.

Projected performance is the field-share-weighted posterior mean. Modeled floor is the minimum
posterior mean over every positive-share external opponent, including unseen cells. The report
shows the named floor pairing's n and interval, the full minimum interval, direct field coverage,
and prior-backed mass. A row with no direct rounds remains visible but cannot become a supported
recommendation or tradeoff. These values are exploratory and are not numerically comparable with
the canonical Deck Rankings projection, which uses richer fitted priors and evidence selection.

The agency map uses projected performance on x, modeled floor on y, and compatible round evidence
for point size. The table sorts numeric and text columns while retaining expanded rows. Search,
coverage, and sample controls change which rows are shown; they do not recompute estimates.

## Exact registered decks

Expanded rows show up to three recent distinct registered lists per cohort with an exact 60-card
main deck and 15-card sideboard, preferring lists without cards banned at the cutoff. This is not a
full format-construction check. Each includes date, pilot, event, source link, recorded finish,
canonical main/side cards and hash, and copyable Moxfield text. These are live observations from the
current local corpus. An old list or League finish demonstrates a registration, not current
performance. Prior candidate files may appear as references but never substitute for observed lists.

## Interpretation limits

Read the date span, pilots, events, dominant-pilot/event shares, direct coverage, and prior-backed
mass before comparing rows. Tiny samples can be dominated by one pilot or event; historical-only
rows and rows without compatible rounds are labeled plainly. Standings can be broader than the
resolvable matchup ledger, while compatible rounds deliberately discard subject or opponent lists
that contain cards banned at the cutoff. The corpus observes published lists rather than all event
entries, and the model does not remove pilot dependence, event dependence, selection effects, or
era drift. Neither ledger identifies a causal splash-card effect.

The report is a sortable evidence review for Esper Teferi, Sultai Veil, Grixis Squelcher, Dimir,
white/green four-color, and residual families. It supports descriptive comparisons without a
leader tile; it does not rewrite old 75s or promote a cohort into the global taxonomy.
