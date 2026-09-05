---
id: epic-local-meta-support-meta-report
kind: feature
stage: implementing
tags: [analytics, advisory]
parent: epic-local-meta-support
depends_on: [feature-decision-unit-taxonomy]
release_binding: null
gate_origin: null
created: 2026-06-29
updated: 2026-09-05
---

# Generate Deck Rankings for an expected local field

## Brief
Apply the same served posterior model and independent performance/floor priorities to a supplied expected field. Reuse the existing field-file parser (shares and optional counts), render a private local report with an explicit scenario label, and compare it with the global view. Keep scheduled default publication pointed at the global report.

## Outcome boundary
One CLI invocation generates the local report with the same cards, map, tables, camps, tooltips and evidence filters. Reweight complete matchup posteriors for the supplied opponents; unknown opponents remain explicitly prior-backed rather than disappearing. Custom field composition does not define which playable candidate decks may be recommended. Floor covers positive-share non-mirror scenario opponents. Counts represent supplied evidence only; shares alone do not imply observations. Invalid input fails before replacing any output. No public hosting or geo ingestion.

## Simplification
Extend Deck Rankings and the existing build_custom_field parser; retire this item's separate bespoke local comparison-report design.

## Authorized direction
Andrew approved the four-part sequence on 2026-09-05 and asked to execute it: improve historical borrowing and evaluate the exact current model; explain refresh changes concisely; examine pilotable archetype units; apply both independent priorities to custom fields. Keep estimates visible throughout. Existing data integrity and incompatible-era boundaries remain in force. Current report styling and interactions are the approved reference. No new audience, hosted product, or geographic ingestion is in scope.

## Execution
Standard feature review (default): one independent pass followed by verification of accepted fixes. Features run in the approved order. Reuse existing implementation and research before adding abstractions; preserve unrelated Hogaak files and uv.lock changes. Design records concrete interfaces before implementation.

## Design decisions (--only-questions directional pass)
User approved the existing private local-field workflow and the same independent performance/floor priorities. No new geography, hosting, or interactive field editor. Use an explicit field file and optional label, generate a separate local HTML, and preserve the global scheduled landing page. Reuse every existing report component; scenario identity is a compact header/caption, so no new mock is needed. The existing decks/local-field-current.txt is a saved May-era local sample, not verified September observations; a generated example must say so and retain unmatched historical labels as unknown-data opponents.

## Architectural choice
Options: a separate local-meta report; an in-browser second ranking engine; or a field override to the shared server-side projection. Choose the third: the same posteriors, intervals, provenance, controls, and tables serve global and custom fields. Candidate eligibility remains based on current corpus presence/direct support, independently of scenario opponent shares. A deck need not be expected among opponents to be a playable choice.

## Implementation units
- Extend `generate_ranking(..., field_path: Path | None = None, field_label: str | None = None)` and script CLI `--field`, `--field-label`. Parse/validate custom input before expensive calculations and before any output mutation using the existing advisory.report._load_field/build_custom_field path; do not duplicate the file grammar. `--field` requires a separate output path and rejects the canonical global destination. Missing field label uses the input stem; labels are escaped in HTML.
- Extend shared ranking projection integration with `field_override: FieldDistribution | None`. Build the global posterior/candidate universe once; apply normalized scenario weights/counts to those same selected matchup cells, including explicit weak priors for unknown opponents. Preserve source/observation dates. Pass global current presence separately from scenario field shares; expose both values rather than overloading active status. No counts means fixed scenario weights; supplied counts influence concentration centered on supplied shares and remain distinct from observed corpus sample size.
- Recompute strategic-plan shares/cells as coherent scenario aggregates or explicitly omit an unavailable plan projection with reason when unknown field mass cannot map to a plan. Never silently drop unknown mass and present the renormalized plan field as complete. Archetype/camp ledgers preserve that unknown mass. Performance includes the subject mirror at0.5; floor excludes only the exact subject mirror and all zero-share opponents.
- Store `meta.field_scenario` with kind, label, source file/hash, shares, supplied counts/currency, unknown opponents, and compact global-versus-scenario independent calls. Current model/corpus freshness is separate from scenario sample currency. Adjust table/tooltip field-share wording to scenario share while keeping actual observed-list counts identified as global corpus observations.
- Refresh-change comparisons require matching scenario identities and remain separate from the static global-versus-scenario comparison. Scheduled refresh defaults pass no override and remain unchanged. Add a concise runbook command and generate a real private report from the saved local field with an honest dated-sample label.

## Testing and risks
Use a synthetic field reversal to prove a globally absent-from-room candidate can become performance/floor leader. Test shares/counts, normalization, unknown positive mass, exact mirrors, zero mass, scenario-specific floor support, no invented observed counts, invalid input preserving existing output, global-output protection, and unchanged global default. Browser checks verify both cards, tooltips, evidence filters, camps, and scenario labeling. Historical aliases in saved local fields are not silently remapped: unknowns remain visible until grounded taxonomy mapping exists. Standard independent feature review and final combined CI complete this delivery; the parent epic's deferred geographic work stays open.

## Saved-scenario grounding

No newer expected shares have been supplied in response to the optional early question. Use the
saved May sample as the starting scenario, clearly dated. Its file describes 107 players but
contains only 103, excluding four unclassified Affinity Combo players. For the demonstration,
write a separate dated scenario input that retains the supplied 103 counts and adds the documented
four as an explicitly unclassified opponent with a weak prior. This preserves all 107 players
without inventing an archetype mapping or changing the existing saved input. Use counts/107 for
shares rather than the original rounded decimals. Label the output as a historical sample scored
with the current model; keep original historical labels, including any now-unmatched labels.

## Parser integration constraints

The existing `_load_field` fills missing per-row counts with synthetic ones when any other row
has a count. The new ranking surface must not present those as supplied observations. Reuse the
parser grammar, adding an opt-in strict count contract for this caller if needed; preserve
established legacy callers. Treat `effective_n` explicitly as an effective concentration, not
observed players, and preserve its declared total (the current minimum-one integer allocation
can overshoot small totals). Share-only inputs remain valid fixed-weight scenarios. Invalid or
incomplete declared evidence must fail before replacing a report.

The saved sample's end date is unspecified: its documented period starts after May 18. Label the
example "Saved post-May 18 field (107 players)" rather than inventing a May collection date.

## Implementation notes (2026-09-05)

- Added `advisory.field_scenario.load_field_scenario` as a thin adapter over the existing field
  grammar. It records source hash, label, supplied counts, declared effective concentration,
  unknown positive mass, and a stable scenario identity. Declared effective-N concentrations are
  scaled back after the legacy minimum-one allocator so the posterior uses the declared total;
  materialized counts remain available as provenance.
- Added `field_override` to the shared ranking projection. It reweights the same selected matchup
  cells and weak 50% named priors while receiving global current-corpus presence separately for
  candidate eligibility. The publisher maps parent scenario shares onto camp rows, retains
  unmapped camp mass, and omits strategic-plan estimates with an explicit unavailable reason until
  composition-specific plan cells can be formed coherently.
- `refresh_best_call_ranking.py` accepts `--field` and `--field-label`, validates before compute
  and atomic output replacement, and refuses the canonical global output for custom scenarios.
  Custom reports carry `meta.field_scenario`, global observed-field provenance, and compact
  global-versus-scenario calls. Refresh snapshots hash the stable scenario identity.
- Added the dated saved input `decks/local-field-saved-post-may18-107.txt`, preserving four
  explicitly unmapped Affinity Combo players and historical labels such as Energy. No actual
  corpus result is claimed here; the saved input is a private current-model scenario.
- Focused verification: field-scenario/parser, projection, refresh comparison, report, and
  evaluator compatibility tests pass (74 selected tests at the last run); Ruff passes on all
  touched Python files. Full corpus generation and final browser/integration checks remain
  pending host verification.

Verified implementation committed as 678c619 (32 final focused tests; earlier integration set
99 passed; Ruff and diff checks clean). Advance to standard fresh feature review while host owns
actual-corpus generation, browser checks, and final CI. Parent geography scope remains open.

## Standard review corrections

One fresh Sol xhigh pass found four blockers, all accepted: camp rows must keep parent opponent
labels rather than remap them to variant names; row counts must take precedence over effective_n;
global-versus-scenario calls/shares must be visible; and local plan shares must actually be
attached and rendered. Commits 6187320 and 0286d6f implement those corrections with targeted
publisher/parser/presentation regressions. Local plan estimates stay unavailable; the plan share
column and mapped-field coverage remain useful and explicit.

Host contract verification identified an additional eligibility edge: candidate support was still
being counted only against scenario opponents. A wholly unfamiliar field could therefore remove
all globally supported candidates. The remaining correction preserves the global eligible set
while retaining zero local direct coverage and honest weak priors. No new publication gate.
Standard pass count is one; closure follows verification of this named fix set, not another review.
