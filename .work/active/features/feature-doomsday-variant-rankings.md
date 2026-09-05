---
id: feature-doomsday-variant-rankings
kind: feature
stage: done
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
- Also show published non-League tournament standings W-L-D and decisive win rate,
  joined uniquely by normalized player/event, for subject lists legal at cutoff.
  These totals can include opponents whose lists/rounds are missing or now banned;
  label this denominator separately from the compatible external matchup rounds.
  Never convert League 5-0 publications into tournament standings. Both evidence
  views select these records by date. Show record count and pilots for each ledger.
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

## Implementation dispatch
One Luna xhigh worker owns extraction, model, renderer, template and focused tests;
host owns documentation, live generation, browser verification and standard review.
The ranking dependency is archived done. No child dependencies or cycles. Standard
review weight is the workflow default. Existing unrelated uv.lock and Hogaak work
are outside scope. The read-only probe found current Esper standings of 5–4 but no
resolved rounds, motivating the separate standings ledger above. Probe counts are
diagnostics, not hardcoded expected report totals (final both-side legality and
external-field filtering may reduce them).


## Implementation and verification (2026-09-05)
Luna xhigh produced the initial cohesive module, publisher, template and five
fixture tests. Host completed the effective-count schema correction, exact 60+15
selection, date/input validation, verified whole-event alias exclusion, and
compact table/map integration. No taxonomy, source database, scheduled default,
or older field-guide artifacts changed. The read-only alias check compares all
four fact tables only within same-date/name/non-League MTGO numeric-id groups;
it removed 31 duplicated event URLs. Shared ingestion/global field correction is
parked as bug-mtgo-event-url-alias-duplicates; this report inherits the supplied
field apart from its declared Doomsday exclusion and exposes that limitation.

Actual generation: decks/doomsday-variant-rankings.html, through September 3,
current field since August 10. Compatible matchup n: Dimir 320, Esper 20, Sultai
Veil 71, Grixis Squelcher 12, four-color W/G 5, white/no-Teferi 2. Current-only
rounds: Dimir 8, Sultai Veil 3. Published current event records retain Dimir 65–39,
Esper 5–4, Sultai 10–5, W/G 3–3, green/no-Veil 6–6 with their distinct denominator.
Grixis has nine registrations, latest June 27; its 19–6 published event record
comes from four records and must not be interpreted as twelve resolved rounds.

Verification: 13 focused hermetic tests; 79 combined focused/related/kernel tests
pass; changed-file ruff and diff checks pass. Real Chromium checks cover all seven
sorts, expansion retention, filters leaving estimates unchanged, hover/focus/Escape
tooltips, exact75 clipboard text, current/history toggle, and desktop/mobile/dark
layout. Expanded matchup row height is 24.6px; no JS errors or mobile body overflow.
README, runbook and foundation entries updated; generated knowledge index has
zero errors and six pre-existing warnings. Independent standard review and CI
remain required before closure.


## Review (2026-09-05)
**Verdict:** Approve after verified corrections. Standard weight, one balanced
fresh Sol xhigh same-harness pass; no second independent review.

**Blockers resolved:** (1) Nonempty card fragments were incorrectly accepted as
complete lists. Ledger eligibility now requires main >=60, side <=15, positive
counts and known board labels on both round participants and the standings
subject. Valid 61/80-card mains and short sideboards remain eligible. The live
Melee 403459 malformed Black Stompy list is excluded, restoring that Sultai cell
to an unseen prior; Sultai compatible n is 70, with every current record unchanged.
There are 33 implausible corpus lists and zero Doomsday subject lists excluded by
this check. Ambiguous registrations remain ambiguous before eligibility filters.
(2) Public since and field dates now strictly validate canonical YYYY-MM-DD and
reject suffix garbage, impossible dates and reversed field windows.

**Other findings:** None. The scoped system/module documentation consistency
check found only the two contradictions above; runbook and doc-review-report.md
now match the corrected behavior. No new thresholds on statistical support.

**Verification:** 30 focused regressions; 96 integrated focused/related/kernel
tests; changed-file Ruff and diff checks pass. Real source-case exclusion and
recomputed payload verified. Chromium rechecked all seven sorts, 24.6px matchup
rows, current-observation counts, coherent view/filter behavior, exact75 clipboard,
keyboard tooltips, escaping of untrusted source-date text, and mobile/dark layout.
Full CI run 33997017752 passed on Python 3.11 and 3.13. PR #93 carries the final
commit's required checks; keep it draft until those checks pass. The generated
HTML is local-only and rebuildable; source DB/global report remain read-only.
