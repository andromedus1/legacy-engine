---
id: feature-doomsday-variant-rankings
kind: feature
stage: implementing
tags: [analytics, advisory, ui]
parent: null
depends_on: [feature-deck-rankings]
release_binding: null
gate_origin: null
research_refs: [doomsday-splash-variants, doomsday-pivot-performance, doomsday-variant-experiments]
created: 2026-09-05
updated: 2026-09-05
---

# Doomsday variant rankings and deck learning report

## Authorized outcome
Create a self-contained Doomsday comparison deliverable in the Deck Rankings style:
sortable variant rows, agency map, compact matchup dropdowns, and concrete decklists.
Compare Esper Teferi, Sultai Veil, Grixis Hexing Squelcher, plus omitted mana-base
families grounded in the corpus (Dimir and white/green four-color). Be direct about
tiny or historical samples while still producing useful estimates and insights.
Keep historical observations distinct from current-field projections. Reuse the
existing Doomsday research/candidate lists and current global field/model rather
than restating the dated field guide as a current win-rate study.

## Directional design pass
The user explicitly chose the existing ranking map/table style and blunt small-sample
methods. No open audience or layout decision. Existing components/patterns are the
reference; this specialized report uses their layout and needs no new visual mock.
First inspect exact color/package cohorts and resolvable rounds before fixing the
historical window and estimation contract. Ordinary observational reporting must not
turn published 5-0 leagues into an all-entry win rate or zero evidence into certainty.

## Simplification
Use the shared posterior ranking kernel and read-only corpus extraction. Keep this
report separate from the canonical global rankings and from the older research field
guide. No taxonomy mutation, database migration, ingestion rewrite, or causal ranking.

## Evidence grounding and choice
The existing splash studies contain actual Dimir, Esper and white/green registrations;
their August 20 snapshot is superseded for currency by a read-only September 3 probe.
The new probe already finds two current pure Sultai Veil entries (August 19/23), so
the older absence finding must not be repeated. Grixis Squelcher remains an older
comparison candidate. White without Teferi and green without Veil need explicit
residual cohorts so color and signature cards are not conflated.

Alternatives: (1) reuse dated field-guide rates (wrong current denominator); (2) infer
variant effects from the global Doomsday posterior (double-counting/confounded borrowing);
(3) extract exact variant rounds and apply a simple declared smoother on a common field.
Choose (3). This is deliberately a descriptive exploratory comparison, not a claim that
the general ranking methodology has validated these tiny variant samples.

## Implementation contract
One Luna xhigh implementation owner builds the full feature. Host owns source/evidence
grounding, actual-corpus interpretation, browser verification, independent standard
feature review and PR/CI. No child story fanout: extraction/model/render form one bundle.

- `src/legacy_engine/advisory/doomsday_variants.py`: read-only extraction plus pure
  variant classification and report projection. Public `build_variant_report(con,
  global_payload, *, since='2026-01-01', draws=10000) -> dict` and a testable classifier.
  One registry owns id/label/signature/explanation. Target cohorts always include Dimir,
  Esper+Teferi, Sultai+Veil, Grixis+Squelcher, four-color W/G; observed white-without-Teferi,
  green-without-Veil, red-without-Squelcher and other splashes are separate residual rows.
- Classify actual basic/dual/shock/surveil colored mana sources plus the 75's protection
  cards. Fetchlands, Lotus Petal, Cavern and cycling Edge of Autumn alone do not imply
  a splash. Record main/side signature counts and actual splash lands. Keep malformed
  or unclassifiable entries explicit in an audit rather than forcing a target label.
- Use current source cards/ban snapshot to distinguish registrations containing banned
  cards. Projection evidence includes resolvable decisive physical rounds only when
  BOTH participating lists are free of cards banned at the report cutoff. This defines
  a card-compatible historical slice, not proof of unchanged metagame. Excluded records
  remain counted in the audit. Do not rewrite old 75s or pretend they are current.
- Reuse `analytics.match_results.resolve_match_records` and normalized event/player
  identity to attach exact deck cohorts, excluding ambiguous joins. Deduplicate exact
  physical match IDs; league publications never become 5-0 round evidence. Retain
  physical match IDs, date span, pilots, events and dominant-pilot/event shares for audit.
  Source publication counts and round results are separate. Do not silently collapse
  distinct same-day events just because a pilot reused a list.
- Default evidence view: compatible registrations since January 1 through the global
  report's exclusive cutoff. Also provide a current-regime-only view using its field_since.
  Keep older and current W-L/n/date spans visible in each row. No date weighting for
  matchup outcomes: this intentionally blunt model exposes age instead of pretending
  to estimate historical transport. Keep all history bounded by the same report cutoff.
- Use the shared `rank_matchup_rows` kernel with explicit `build_cell` overrides and a
  fixed Beta(1,1) prior (strength 2, mean .5). No outcome-tuned prior or parent borrowing.
  Missing cells remain weak 50% priors with full uncertainty. Compare ALL rows against
  the same current NON-DOOMSDAY field (remove only the Doomsday family opponent mass,
  explicitly disclose and renormalize once). This avoids treating unknown variant mix
  within Doomsday as a known mirror. Unknown external archetype mass stays present.
  Use global field counts for performance-interval concentration, rescaled to the
  retained external mass; shares remain the prescribed center. Prior-only rows remain
  visible but are not marked as a supported tradeoff or recommendation.
- Raw observed W-L covers included external opponents, distinct from field-reweighted
  performance. Floor is minimum posterior mean over every positive-share external
  opponent, including unseen neutral priors. Show named floor pairing n and interval,
  full minimum interval, direct field coverage and prior-backed mass. No best-deck tile.
  Mark historical-only / sparse / no-round-evidence states plainly. This model is not
  directly comparable numerically with the richer global ranking's fitted priors.
- Include up to three recent distinct exact registered 75s per cohort, preferring
  current legal registrations, with date, pilot, event, source URL, recorded finish,
  canonical main/side cards/hash and copyable Moxfield text. Label old evidence; league
  finishes demonstrate registrations only. Reuse prior candidate files as reference
  links, not substitutes for live observations or invented newly observed builds.
- `scripts/refresh_doomsday_variant_rankings.py`: CLI `--db`, `--field-report`, `--since`,
  `--out`; default output `decks/doomsday-variant-rankings.html`. Parse/validate inputs
  before publication, protect the canonical global input/output, safely embed JSON,
  atomically replace the report, retain source report SHA and protocol/date/audit metadata.
- `scripts/doomsday_variant_rankings_template.html`: use the current Deck Rankings
  palette/typography/table/map interaction pattern. Variant rows sort numeric/string
  columns, unknowns last, retain expanded rows, and show compact matchup/decklist
  disclosures. Map x=projected performance, y=modeled floor, dot size=round evidence;
  keyboard/hover/tap tooltip includes evidence dates and n. Current/all-compatible view
  selector updates map/table coherently; search/coverage/sample filters never alter
  computed estimates. No leader tiles, duplicate sort buttons or generic narrative bloat.

## Verification and pre-mortem
Meaningful fixtures cover exclusive color/package classification (including cycling,
fetch/rainbow false positives and residual cohorts), physical rounds in both orientations,
duplicate/ambiguous players, league-only samples, banned-card exclusion on either side,
date cutoffs/current-vs-history views, no field-mass loss except declared Doomsday exclusion,
weak unseen priors, reproducible rankings, and safe/atomic publication. Test real semantics,
not generated wording. Use the actual DB only for a read-only generation, never unit tests.
Browser-check actual global-field report on desktop/mobile: sort, filters, view changes,
map accessibility, readable compact rows and exact list copy. Standard review = one
fresh Sol pass, fix accepted blockers and verify; no repeated review unless requested.

The largest risks are confusing 5-0 publications with match outcomes, classifying a
cycler as a green splash, silently importing banned shells, and making unseen 50% cells
look like demonstrated good matchups. Visible denominators/date bands and exact cohort
rules address those risks without withholding useful estimates.
