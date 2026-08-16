---
description: Read before refreshing or interpreting the Best Deck / Best Call agency ranking page — the one-command refresh runbook, the metric definitions, and the honesty gates baked into the page.
type: design
kind: planning
status: active
updated: 2026-08-16
summary: |
  Runbook + method spec for decks/best-deck-best-call-ranking.html (gitignored, fully
  regenerable). One tracked script recomputes the page from the DuckDB corpus through a
  tracked HTML template: scripts/refresh_best_call_ranking.py +
  scripts/best_call_ranking_template.html. Defines gated Agency % as the default
  authority, the opt-in seeded posterior lean, grounded/current strata, rank stability
  and paths to grounding, the cross-camp P(best) column, and the five-plan strategic
  taxonomy, including exact archetype-versus-plan evidence in every archetype dropdown;
  the page itself carries the authoritative definitional prose. Typed report targets may
  add diagnostic-only recurrent interval and amplification evidence without changing the
  mature ranking payload, and may publish exclusive-cutoff “Today’s model” siblings in a
  failure-safe offline bundle.
decisions:
  - "Agency % = min(adjusted field WR, worst measured matchup) x 100 — the page's single ranking number; theory under test: maximum agency = most fun."
  - "Measured cells only: a matchup counts at n>=8; era-windowed cells preferred; the fallback pools matches since the last ban that affected either deck (BA label, archetype_valid_since) — full-corpus FC only when neither deck was ever ban-affected. The Nadu rule: a banned engine's matches never inflate a row (Nadu Cephalid inflated agency 40.5 vs honest 31.1, 2026-07-28)."
  - "Every measured cell (n>=8 by default) can set the floor using its shrunk estimate; this exposes apparent holes sooner. Because better-covered decks have more chances to reveal a low matchup, ungrounded agency remains an explicit upper bound and must be read with measured coverage. Blowouts classify on the raw observed rate after the same measured-cell gate."
  - "Grounded row = top-8 field opponents all measured AND >=80% of field share-mass covered; ungrounded rows are labeled leans (agency shown as an upper bound), and sorting never intermixes strata."
  - "Gated Agency remains the default and authoritative ranking number. The opt-in seeded posterior lean is diagnostic only: it uses the era candidate regardless of n, falls back only when the era candidate is absent, uses Jeffreys cells for resolved evidence, a weak row-centred prior for unresolved cells, and continuous field-share × precision weighting; it reports Q25, median, and 95% CI."
  - "Rank stability compares raw, CI-gated, ban-scoped, and era-only variants within each peer table; rank spans are shown only when all four variants rank the row. Interactive n changes mark generated stability and grounding paths stale, while the posterior lean remains independent of the interactive gate."
  - "Grounding paths collect every shortfall among the top-k opponents first, then prioritize remaining cells by share gained per additional match until the coverage target; the page displays the first three actions plus a remainder count and total projected matches/coverage. Plan rows expose grounding paths but do not expose lean or stability."
  - "Field basis = the current ban-regime window; --field-since defaults to the latest confirmed ban event so regime changes auto-track; its confidence tier is computed from window size, never hardcoded."
  - "Camp sweep = ONE multi-split pass (build_multi_split_adaptive + one uniform multi-split matrix per distinct ban-fallback date) — numerically identical to per-parent split builds (parity-tested at engine and script level, ~25x cheaper), keeping the per-pair max(subj_ban, opp_ban) Nadu-rule fallback windows."
  - "Cross-camp P(best) = ONE shared-field rank_decks MC (fixed seed) over all camps + unsplit field archetypes on the page-used cells; candidacy is gated at the same coverage threshold that suppresses display (<5% measured coverage -> n/a + reason) because zero-coverage candidates otherwise absorb the whole argmax as imputation noise; S* labels full-field values below 85% coverage."
  - "Strategic plans are a curated, independent five-plan taxonomy: every current-field archetype has exactly one primary plan for mutually exclusive match-level aggregation and may carry secondary labels for hybrid explanation only. Plan cells pool decisive matches directly rather than averaging archetype rates."
  - "Strategic-plan same-plan play is structural 50% context: the diagonal displays zero directional wins, losses, and n, while observed_n separately reports cross-archetype same-plan matches and mirror_n reports mirror context. It contributes to adjusted field WR but is never measured, never sets the floor, and is excluded from the external-coverage denominator. External plan cells use the page's n>=8 measured gate; grounding requires the top external plans measured and >=80% external field-share coverage."
  - "Every archetype dropdown begins with five Against strategic plans cells built directly from that archetype's decisive non-mirror MatchResults, grouped by opponent primary plan. Cells carry shrunk/raw rates, W-L, observed n, the page's uniform field window/provenance, and measured/thin state. Exact-archetype mirrors are reported separately as mirror_n and shown only as structural 50% context; they never contribute to the observed n, raw/shrunk estimate, or n>=8 measured gate. The exact archetype ledger remains below."
  - "Each taxonomy layer surfaces at its own altitude. Composition-derived superarchetypes stay internal to matrix construction and statistical borrowing — no page-visible dropdown payload, family lean, family range, or presentation audit line. A COLOUR SPLIT is archetype-level: the curated registry rewrites decks.archetype at label time, so each branch earns its own archetype row, its own field share, and its own column in every OTHER archetype's ledger. Camps stay subject-side only (the multi-split matrix pools the opponent side back to parent), so a distinction that changes how opponents must play against you belongs in a colour split, not the camp table. Energy is the first: Boros Energy / Mardu Energy on mainboard-nonland black."
  - "The output page is gitignored and disposable; the template + refresh script are the tracked artifacts — regenerate, don't hand-edit (data changes go in the script, presentation changes in the template)."
  - "Every ranking row is derived from a typed selected-cell ledger. Its serialized replay must reproduce adjusted field WR exactly; a mismatch suppresses the headline. A strict-common-era estimate is shown separately as a divergence diagnostic and is never averaged into the adaptive headline."
  - "Every row reports floor observability at n>=10 and display-grade n>=30 independently of the interactive page gate. Zero display-grade cells means floor unobserved; missing bad matchups are not evidence of none. Event/month concentration >=40% is labeled on measured selected cells, never automatically corrected away."
  - "The benchmark protocol freezes the exact fold schedule and as-of B&R ledger. Claim coverage uses classified held-out deck mass, while field-weighted regret includes structural 50% mirror utility and requires a stable event-bootstrap oracle. Deterministic artifacts allow byte-identical replay and refuse different content."
  - "Benchmark launch requires a zero-gap card-metadata preflight at every planned training cutoff on the same derived copy; exact Scryfall/current aliases and evidence-backed provider serialization may resolve names, while ambiguous, truncated, and manual candidates remain fail-closed."
  - "The generated page names its future-only validation status and summary artifact id. No supplied summary is shown as not-run; a supplied canonical summary remains honestly not-evaluable, descriptive, or predictive-claim-supported."
  - "Recurrent interval and amplification evidence is diagnostic-only. The attachment exposes current-only, certified-expanded, and added-history views plus six named challenger slots, while a canonical authority-payload digest proves that Agency, candidacy, P(best), ordering, and every mature row metric are unchanged."
  - "Parents may consume an exact certification run; camps remain current-only and cannot acquire certified historical intervals or added-history observations. Missing, invalid, non-final, future, unpromoted, or guard-mismatched certificates abstain with named reasons rather than widening evidence."
  - "An explicitly requested amplification run is exact-run only: no latest-run lookup or approximate reuse. Missing or mismatched corpus, clock, certificate, direct baselines, profile registry/order, fit identities, match-set digests, or comparison audit fails generation before atomic replacement; omitting the run is a valid typed not-assessed state."
  - "A retrospective report target uses an exclusive data_until cutoff, the latest confirmed ban boundary strictly before that cutoff, and the label Today’s model because taxonomy/configuration are current at knowledge_as_of. It is never represented as what the engine knew then."
  - "A report bundle stages every available page and its escaped manifest before publication, replaces historical siblings before the canonical current page, and restores the complete prior bundle after any replacement failure. Unavailable targets have reasons but no href and remain disabled in navigation."
---

# Best Deck / Best Call agency ranking — refresh runbook

The page: [decks/best-deck-best-call-ranking.html](../../decks/best-deck-best-call-ranking.html)
(gitignored, self-contained offline HTML). Tables are click-sortable per column
(default: agency % descending); sorting stays within honesty strata. Coverage
filters and column sorting apply to the strategic-plan, archetype, and camp peer
tables. Only direct headers of those outer peer tables are sticky; headers in
nested plan ledgers scroll with their expanded row. Rows expand to accessible
per-opponent matchup ledgers.

## Refresh (one command)

The composed refresh calls reusable Python primitives in dependency order, reports card-dimension
coverage plus B&R/release/era awareness, and writes the ranking only after every prerequisite
succeeds:

```bash
.venv/bin/python scripts/refresh_decision_data.py
```

The order is tournament cache + rules + release-aware cards, exact name reconciliation, full
labeling, every staged camp parent in sorted order, era detection, then ranking. Required failures
stop dependent steps and leave the prior ranking untouched. Release scanning and alias-download
outages degrade explicitly and retain last-good inputs. B&R awareness reads the operator-confirmed
ledger; it does not scrape announcements or confirm changes automatically.

The individual CLI commands and `scripts/refresh_best_call_ranking.py` remain available for focused
operation and debugging. The composition excludes prices, upstream hot-spare behavior, cloud state,
git commits, and pushes.

## Recurrent evidence diagnostics and report targets

A typed report target adds a separate diagnostic attachment to the mature Best Call payload. It does
not feed Agency, the practical or production ordering, candidacy, grounding, P(best), the posterior
lean, or any browser threshold recomputation. Generation hashes the complete authority payload before
attachment and verifies it again afterward. Each parent pair can show three direct, exact-match views:

- **Current only** — the scalar/current reference interval used as the no-certificate baseline.
- **Certified expanded** — current evidence plus historical half-open components admitted by both
  entities' exact certificates.
- **Added history** — only the matches contributed by those admitted historical components.

Each view carries W-L/n, shrunk and raw estimates, interval, confidence/status, concentration,
match-set digest, component ids, certificate ids, and prior audit. The detail also lists admitted
half-open components and six named amplification challengers. All of this remains frozen generated
evidence: changing the page's interactive matchup threshold neither recomputes nor promotes it.
Without an amplification run, the attachment and all six challenger slots are explicitly
`not-assessed`; the direct interval views still render. Certificate defects or an unavailable exact
certificate result abstain to current-only evidence with named reasons. Camps are deliberately
current-only: their expanded view must equal current-only, their added-history set must be empty, and
they cannot carry a historical certificate.

Amplification is exact-run and fail-closed. `--amplification-run-id` performs an id lookup, never a
latest-run lookup, and the requested run must bind to the report's interval corpus, clock,
certificate, direct baselines, diagnostic-only profile, complete six-method registry/order, fair
comparison audit, fit identities, and exact current/history/borrowed match-set digests. A missing or
mismatched requested run raises before the ranking file's atomic replacement, preserving the last
good page. Omitting the flag is not a failure; it is the honest `not-assessed` posture.

For a single retrospective page, use the supported typed-target flags:

```bash
.venv/bin/python scripts/refresh_best_call_ranking.py \
  --db data/legacy.duckdb \
  --out decks/best-deck-best-call-ranking--before-2026-08-10.html \
  --data-until 2026-08-10 \
  --knowledge-as-of 2026-08-16T00:00:00-06:00 \
  --target-id before-2026-08-10 \
  --target-label "Before The Fantasticar"
```

`--data-until` is exclusive: every outcome-bearing section uses event dates strictly before the
cutoff, confirmed bans are also restricted to dates strictly before it, and the field begins at the
latest confirmed prior ban boundary. Section-level row counts, maximum event dates, and input hashes
are embedded in the target audit. The page labels this mode **Today's model** because
`knowledge_as_of` supplies current taxonomy, configuration, certificates, and derived structure; it
does not claim “as known then.” Optional `--certificate-run-id` and `--amplification-run-id` bind
exact evidence runs. The amplification run's cutoff must equal the requested target cutoff.

The package-level bundle writer can publish one ordered target set containing exactly one Current
target and zero or more Today's-model siblings. It stages all available HTML and escaped manifest
JSON before touching canonical paths, publishes historical siblings first and Current last, and
rolls back every prior artifact if any replacement fails. Every page's manifest selects that page's
own target. Available entries have an href and no reasons; unavailable entries have reasons, no
href, appear disabled in the selector, and are listed visibly. Navigation only follows a manifest
href, target labels/reasons are HTML-escaped, and row disclosure state is scoped by target id so one
historical page cannot restore another target's UI state. There is currently no bundle CLI; callers
use `legacy_engine.advisory.best_call_bundle.generate_ranking_bundle`.

## Future-only ranking benchmark

The ranking benchmark is a preregistered, future-only validation of the parent-archetype
decision surface. Its immutable registry has ten estimators: `coin-50`, `recent-raw-wr`,
`field-share`, `top-finish-conversion`, `simple-jeffreys-shrinkage`, and five production
variants (`production-raw`, `production-ci-gated`, `production-ban-scoped`,
`production-era-only`, `production-lean`). `production-ci-gated` is the required primary;
evaluation cannot tune or promote any production estimator.

There are two taxonomy replay modes. `retrospective-fixed-parent` freezes the current parent
rules identity and reclassifies held-out decklists through it, rejecting later rule or stored-label
drift; it remains a deliberately degraded benchmark surface (no camps or families). The
optional `contemporaneous` mode requires a dated, exact-mapped taxonomy snapshot effective no
later than the fold cutoff. Both modes build a raw-facts snapshot strictly before the cutoff;
the prediction artifact is hashed before later outcomes are opened, and evaluation records both
the prediction and evaluation-data hashes.

The protocol JSON contains the exact walk-forward fold schedule and dated as-of B&R ledger;
freeze/evaluate/run consume that frozen plan rather than mutable globals or corpus dates. Folds are
non-overlapping, whole-date windows of 28 days, truncated and reset at confirmed B&R boundaries.
A boundary origin uses a declared trailing 28-day pre-cutoff field horizon because no same-regime
deck can precede it; later origins use same-regime field evidence. Held-out outcomes exclude mirrors, byes/draws, ambiguous players,
unclassified labels, emerging labels, and actions outside the frozen universe. Fold support gates
are explicit (common matches, events, dates, supported actions, and future
field coverage). Coverage is classified held-out deck mass represented by the frozen universe,
independent of match activity. Insufficient fold support censors decision claims, while calibration
intercept/slope are independently censored below their registered prediction minimum and must be
available for any predictive claim. Player identity is evaluation metadata only: player-sensitivity
analysis is reported only when identity coverage reaches 80%.

Forecast quality uses log loss, Brier score, calibration intercept/slope, and cumulative
calibration. Decision quality uses Kendall rank tau, top-three hit, and field-weighted realized
regret with structural 50% mirror utility. Regret requires a stable event-block bootstrap oracle;
insufficient support, practical ties, unstable oracles, and unavailable recommendations are named
censors. Optional external estimators require dated parent-taxonomy, exact-mapped snapshots and
report missing actions plus common-case coverage against the full eligible held-out set.

Plan and freeze/evaluate/run commands require an explicit `--db`; `plan` writes the protocol,
`freeze` writes the cutoff-safe snapshot and immutable predictions, `evaluate` verifies hashes
and scores one fold, and `run` composes every fold. Byte-identical replay is allowed, but different
content cannot overwrite an existing deterministic artifact path. JSON and Markdown expose proper
scores, calibration, support/coverage, rank/top-three/regret uncertainty, exclusions, player and
external evidence, and censor reasons. These artifacts are evidence, not a tuning
loop, and a predictive claim requires the preregistered fold, regime, calibration, and primary
vs baseline gates.

The generated Best Call page does not infer validation from the presence of benchmark code. Pass
the canonical aggregate summary explicitly when refreshing it:

```bash
.venv/bin/python scripts/refresh_best_call_ranking.py \
  --db data/legacy.duckdb \
  --benchmark-summary data/benchmarks/<protocol-id>/summary.json
```

Its audit header then prints the summary's content-derived artifact id and one of
`not-evaluable`, `descriptive`, or `predictive-claim-supported`. Omitting
`--benchmark-summary` prints `not-run` with no artifact id. A failed or malformed summary is an
error; the page never silently upgrades or substitutes validation evidence. The current production
call printed beside it comes from the same grounded/current/Agency ordering used by the benchmark.

Before `advise benchmark run`, reconcile and gate the same ignored derived database copy against
the frozen protocol:

```bash
legacy-engine refresh card-coverage \
  --db data/benchmarks/<protocol-id>/reconciled-corpus.duckdb \
  --benchmark-protocol data/benchmarks/<protocol-id>/protocol.json
```

Scryfall oracle cards and current one-to-one printed-name aliases are authoritative. The package
registry admits only evidence-bearing exact historical exceptions and narrowly typed provider
serialization rules. Those rules require complete singular provider provenance, retained rule
evidence, and an exact canonical target already present in the card dimension. Missing provenance
fails closed. They do not generically strip brackets, guess by edit
distance, truncate tokens, or select among ambiguous localized aliases. The preflight prints every
planned cutoff cohort plus the post-last-cutoff tail. Any planned-cutoff gap is a hard benchmark
launch stop; structured gap lines retain provider and event-URI provenance, while ambiguous,
suspected-truncated, and manual-evidence values stay visible and unresolved. The protocol schedule
is validated before reconciliation can mutate the derived copy.

### Residual card-metadata quarantine (historical sensitivity only)

The default benchmark policy remains `require-complete`: an unresolved card dimension is a hard
fail, preserving the frozen v1 protocol and its bytes. A separately registered protocol may opt into
`quarantine-unresolved-decks` with both ceilings declared (at most 0.5% of decks and 2% of rounds).
The planner closes one typed, outcome-blind ledger before taxonomy or result parsing. It removes the
entire affected deck, its standings row, and every round involving its tournament-local player key;
duplicate keys are conservatively named. JSON and Markdown retain raw/retained denominators,
source/event URIs, unresolved names, excluded identities, fractions, reasons, and canonical hashes.

A protocol registered after its historical first origin is permanently capped at `descriptive`, even
if statistical gates pass. It is a labeled sensitivity replay, not prospective validation; a new
predictive-capable protocol must be registered before its first unopened cutoff. The two-phase
`freeze`/`evaluate` and composed `run` paths consume the same ledger and refuse ceiling breaches or
mutated immutable artifacts. A negative, descriptive, or not-evaluable result is valid evidence, and
the v1 protocol/artifacts and raw cache are never overwritten.

### Current validation evidence (2026-08-12)

The fixed current-corpus historical replay remains **not evaluable**, and the unchanged benchmark
was not restarted. A fresh ignored byte-copy of `data/legacy.duckdb` matched its source SHA-256
`abb9cfc628335609ff063a1ed50c3463faf26021b97d4cf866366e7bdf098d7e`, then ran the normal
reconciliation and frozen-protocol preflight above. The alias manifest was the 2026-08-11 Scryfall
snapshot with 241,911 unique aliases and 457 ambiguous normalized keys. The preflight found 60 rows
across 53 names entering planned training cutoffs, plus two rows/two names first appearing after the
last cutoff. Therefore the zero-required-gap launch gate failed and no benchmark process opened
future outcomes.

The earliest open cohort is cutoff 2025-08-18 (`Explosao Elemental do Vermelho`); later cohorts
retain the named ambiguous, suspected-truncated, and manual-evidence spellings rather than guessing
targets. Protocol `best-deck-decision-trust-current-corpus-v1` still plans 24 whole-date folds from
2024-12-16 through the exclusive 2026-08-06 bound under byte hash
`6416fe6141d3f572c5c8f68a52021147a63639a6e2b2eba3482c2a1d0a2ac561`. No estimator, threshold,
protocol byte, source row, or production recommendation changed in response. The generated evidence
page reports the current production call separately, but it must not be described as predictively
validated until a future-only run clears all gates.

A separate corrected historical sensitivity replay used the opt-in residual quarantine policy and
protocol hash `800a1c4ccbc2d2e5e10c78727ce3d2f23cd1b416e685eb2d2afe63e6737695f2` on a byte-identical
reconciled corpus copy. It completed all 24 planned folds: 22 were evaluable, two were support-
censored, and every quarantine stayed within the declared 0.5% deck / 2% round ceilings. Its
canonical summary artifact id is
`9b14df2113c2b517c6e614f68812725b8576e9f6cbaa294703181cde55d4c6c0`; status is **descriptive**.
The promotion gate refused a predictive claim because stable event-block regret advantage was not
established against both ranking baselines, required primary calibration metrics were unavailable,
and the posthoc protocol ceiling forbids a stronger claim. The generated Best Call page embeds that
exact status and identity while keeping the current production recommendation separate. Routine
page refreshes should reuse this reviewed summary; rerunning every historical fold is reserved for
material methodology, taxonomy, or history changes.

### Experimental player-effect diagnostic

`advise benchmark player-effect plan|freeze|evaluate|run` asks whether repeat pilot identity adds
future-only predictive value beyond both `production-ci-gated` and a deck-residual-only control.
It is a separate three-estimator experimental registry (`deck-residual-control`,
`player-intercept`, `player-familiarity`); it does not add an estimator, score, or P(best) value to
the Best Call page.

Identity defaults to a provenance-local normalized handle. The same unaliased string on online and
paper sources is not treated as one person. Cross-handle/source merging requires an operator-supplied
dated curated alias snapshot effective no later than the fold cutoff; alias suggestions are never
consumed. Reports expose only aggregate accessibility, repeat/familiarity counts, coefficient
quantiles, and grouped scores. They never render handles, ids, individual coefficients, or player
rankings, and every identity count below the privacy floor is suppressed. Ambiguous match sides
remain in the identity-coverage denominator, while repeat and familiarity eligibility are
recomputed independently within online and paper rather than inherited from the combined corpus.

The diagnostic first measures online/paper identity accessibility and descriptive pilot stickiness
for existing parent/variant configurations. Stickiness is an input to later taxonomy research, not
a one-deck/two-deck verdict. The model then fits deterministic L2-pooled deck-pair residuals, repeat-
player intercepts, and separately gated player-by-parent familiarity on pre-cutoff matches only.
The player and per-player familiarity coefficients are frequency-weight centered inside the fitted
penalized objective. Penalty selection uses distinct earlier chronological origins whose full
production artifact and base grid are independently hash-bound at each cutoff. Rows outside that
frozen action universe are excluded with named training/validation counts rather than crashing or
silently borrowing a later grid. Player-neutral deck forecasts set identity terms to zero; player-aware
forecasts use an outcome-free participant schedule hashed before result strings are opened.
Historical participant replay does not prove the source exposed pairings before an event.

Evaluation keeps player-aware, player-masked, and player-neutral estimands separate, and reports
known-known, known-cold, cold-cold, below-repeat-floor, online, and paper strata. The strongest
possible status is `candidate-for-promotion-study`, requiring the full preregistered conjunction:
fold/regime and identity support; event-block log-loss advantage plus Brier/calibration nonharm;
the benchmark's common-match/event/date/action/field-mass support verdict; player-neutral regret
improvement from paired event-block draws; and declared match/event/date floors plus nonharm in
each cold-start and venue stratum. Missing support is
`not-evaluable`; adverse evidence is `stop`; incomplete improvement is `diagnostic-only`. Even a
candidate requires a new reviewed promotion feature. This command never tunes, selects, deploys,
or changes the production ranking or threshold-only strong-player surface.

Optionally re-run discovery first (`discover run --archetype <parent> --since 2024-12-16`
per parent) when the corpus has grown materially — staged splits carry frozen
membership, so **new decks get camp labels only after a re-staged PASS + apply**.
A gate-A FAIL keeps the old frozen split; treat that parent's camp rows as stale.

Knobs (defaults are the page's published method): `--field-since` (legacy untargeted mode;
defaults to the latest confirmed ban event date), `--ground-n 8`, `--top-k 8`,
`--cover-min 0.8`, `--min-row-share 0.001`, `--db`, and `--out`. Typed target generation adds
`--data-until`, `--knowledge-as-of`, `--certificate-run-id`, `--amplification-run-id`,
`--target-id`, and `--target-label`. A typed target derives its field window from its confirmed
historical regime and rejects a conflicting `--field-since` override.

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
as the page. Same-plan matches are shown as structural 50% context. The diagonal
therefore reports zero directional wins, losses, and `n`; `observed_n` separately
reports decisive cross-archetype matches within that plan, and `mirror_n` reports
exact-archetype mirror context. The displayed 50% contributes to adjusted field WR
at that plan's field share, but the diagonal is never marked measured, never sets
the floor, and never enters external coverage. The floor is
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

**Archetype dropdowns lead with direct plan evidence.** Opening any archetype row
shows two independent disclosures: **Against strategic plans** (open by default) and
**Exact archetype matchups**. Each carries a measured-of-total cell count in its header and
opens or closes on its own, so neither must be scrolled past to reach the other; the
open/closed choice persists across row expansions. Camp rows have no plan block and keep a
single always-open section. The plan block is exactly five cells in registry order.
Each cell is aggregated directly from that archetype's decisive `MatchResults`
against opponents assigned to the corresponding primary plan; it is not derived
from rendered archetype percentages or from composition-family evidence. Each
cell carries shrunk/raw rates, W-L, observed `n`, the uniform field window and
provenance, and its measured/thin state under the same `n>=8` page gate. In the
archetype's own primary-plan cell, exact-archetype mirrors are retained separately
as `mirror_n` and displayed only as structural 50% context. They do not contribute
to observed `n`, the raw or shrunk estimate, or the `n>=8` measured gate. The exact
archetype-versus-archetype ledger follows this five-cell block.

**Superarchetypes are internal only.** Composition-derived superarchetypes may
still support matrix construction and statistical borrowing, but the ranking
page exposes no family fallback payload: no archetype or camp dropdown gains an
imputed/pooled lean, family range, provenance chip, or superarchetype presentation
audit line. The page-visible dropdown evidence is the direct strategic-plan block
followed by the exact archetype ledger.

The full refresh runs in ~40s on the current corpus (~11s archetype matrices +
~13s one-pass camp matrices + ~2s shared-field ranking); the script echoes each
phase's wall time.

Metric definitions live in the page's "What is Agency %?" card and in the
frontmatter decisions above — the page prose is authoritative.

**Measurement reconciliation.** Each cell keeps the era and ban-scoped fallback candidates, the
selected source, the outcome-blind selection reason, its exact window, and concentration evidence.
The package-owned ledger is the canonical rounded cell projection consumed by both Python and the
offline browser controls; replaying it must match the headline within floating roundoff or the page
emits `n/a` with a named reason. Each selected candidate also carries validated subject/opponent
pair-window provenance; invalid provenance suppresses the headline. A separate
strict-common-era matrix uses one uniform start at the latest subject/opponent horizon. The page
shows its exact start, contributing coverage, display-grade coverage, estimate, and delta beside
the adaptive value as a diagnostic—never as a blend, even when the estimate is unavailable.

**Posterior lean and rank stability.** Gated Agency is the page's default and authoritative
ranking value; the posterior lean is opt-in and diagnostic. Its seeded smooth-floor draw uses the
era candidate whenever one exists, regardless of its `n`; only an absent era candidate permits the
ban-scoped fallback (or full-corpus fallback where applicable). Resolved cells draw from Jeffreys
(`wins + 0.5`, `losses + 0.5`) posteriors. Unresolved cells use a weak prior centred on the row's
resolved-rate mean μ (0.5 when no cells resolve): `Beta(2μ, 2(1−μ))`, with the implementation's
`1e-6` positivity guard at the endpoints. For resolved cell `i`, strength is `n_i + 1`; for an
unresolved cell it is exactly `2`. Each cell's continuous weight is
`v_i = field_share_i × strength_i / (strength_i + 30)`, then normalized as
`w_i = v_i / Σ_j v_j`. On posterior draw `d`, the smooth floor is exactly
`A_d = −0.05 × log(Σ_i w_i × exp(−p_i,d / 0.05))`. Replay uses **20,000 draws**, RNG seed
**730021**, temperature **0.05**, precision scale **30**, Jeffreys pseudo-count **0.5**, and
unresolved-prior strength **2**. The row reports Q25 of `{A_d}` as the lean, alongside its median
and 95% interval. This path remains gate-independent when the interactive matchup `n` changes.
Stability compares raw, CI-gated, ban-scoped, and era-only
agency variants within the row's peer table; a rank span is shown only for rows ranked by all four,
otherwise the missing variants explain the n/a. Plan rows can show a grounding path, but have no
posterior lean or rank-stability payload.

**Paths to grounding.** For an ungrounded row, the generated path first includes every unmet
top-`--top-k` opponent shortfall. It then adds non-top-k cells in descending field-share gained per
additional match until `--cover-min` is projected. The page displays three actions, followed by
the number of undisplayed actions and the total additional matches and projected coverage. Paths
are generated at the default `--ground-n`; changing the interactive gate marks the path stale
rather than presenting a path for the wrong evidence state. The same path behavior applies to plan
rows, without adding lean or stability diagnostics. Canonical grounding, path planning, and browser
replay all resolve equal field shares by stable opponent id ascending before taking top-k; input or
database row order never decides which tied opponent crosses the cutoff.

**Observable floors.** The interactive `--ground-n` still determines which cells can set the page
floor. Alongside it, the page reports how many opponents reach n>=10 and the engine display gate
(n>=30), plus display-grade field-share coverage. A row with no n>=30 cells says `floor unobserved
-- absence of bad cells is not evidence of none`. When one event or calendar month supplies at
least 40% of a selected measured cell, the expanded ledger names that cluster, its match count,
share, and selected window. Concentration evidence belongs to each candidate source, so changing
the interactive gate selects or clears the warning together with its numeric cell; the rate is left
unchanged for inspection.

## Interpretation guardrails

- **Custom-field currency is exact or unavailable.** A field file uses
  `<share> <archetype> [count]`; `# current_regime_n: N` is accepted only when every row has a
  real count, or when `# effective_n` supplies the complete allocated denominator. Partial row
  counts still retain the historical synthetic-one Dirichlet fallback, but never claim an exact
  currency percentage. Share-only and undated aggregates say why currency is unavailable.
- **Field and matchup windows are independent.** Window field composition to the current regime;
  keep matchup cells adaptive unless explicitly diagnosing another window. A current-only matchup
  matrix can starve coverage even when the current field composition is trustworthy.

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
- **The measured-cell gate is interactive in each table.** `Minimum matchup n`
  defaults to the generated `--ground-n` value (normally 8) and recomputes the
  era-preferred / ban-scoped-fallback selection, adjusted field WR, floor,
  agency, blowouts, coverage, grounding strata, labels, and sorting in-browser. Stability and
  paths remain generated evidence and are marked stale when the selected gate differs; the
  posterior lean remains available because it is independent of this gate.
  Cross-camp P(best) remains the generated-threshold Monte Carlo and is shown as
  n/a when the interactive gate differs rather than presenting a stale value.
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
- **Archetype plan cells are direct evidence** — read their shrunk/raw rates, W-L,
  observed `n`, measured/thin state, and uniform field provenance before the exact
  opponent ledger below. `mirror_n` in the row's own primary-plan cell is separate
  structural 50% context: mirrors contribute neither directional wins/losses nor
  observed `n`, estimates, or measured-gate eligibility.
- **Cross-camp P(best) is a shared-budget number** — all camps and unsplit
  archetypes compete in ONE argmax, so the values are comparable across parents
  and can never sum past 1. n/a means the row failed the 5% measured-coverage
  candidacy gate (its score would be pure imputation); S* means the supporting
  field WR is a full-field estimate leaning on imputation for unmeasured share,
  which always includes the camp's own parent (that cell is absent by
  construction).
- **Evidence exclusions name the reason.** `inactive` means raw current-field presence is exactly
  zero (a positive share below display rounding remains active); `unscorable` means no resolved
  matchup cells or measured coverage below 5%. Both show `S=n/a` and `P(best)=n/a`. Grounded,
  lean, and imputation-dominated rows remain eligible. When the interactive matchup-n differs from
  the generated gate, evidence percentages are labeled `generated n=<gate>` and evidence grouping
  is disabled so generated strata cannot masquerade as interactive state.

## Credible-window utility contract

The page has two deliberately separate current-field views. The observed slice is the exact
post-ban deck count and remains the only presence claim. When that slice is below the 500-deck
field floor, `build_transition_field` may add at most `500 - observed_n` integer pseudo-decks from
the immediately preceding confirmed regime, after removing directly affected archetypes and
deterministically renormalizing the survivors. Effective counts drive ranking shares; observed
counts remain adjacent and prior-only labels are `transition-prior`, never post-ban sightings.
The transition projection never widens a matchup `PairWindow`.

The status payload retains a practical ordering of supported rows by the existing posterior lean
Q25, then median, then label. The generated page does not render a separate practical-shortlist
card; the archetype and camp tables remain the single decision surface, with the posterior lean
available only through the explicitly diagnostic methodology toggle. This is an uncertainty view,
not a new estimator and not benchmark evidence. The unchanged future-only benchmark remains the
sole authority for any predictive-validation claim.

Refresh generation emits a typed usefulness summary. Contradictory metadata (supported rows with
no practical call, a call omitted from the rendered shortlist, or unreconciled observed/effective
counts) fails before atomic replacement. A thin run can publish as `degraded` when practical rows
exist but few are grounded; an evidence-empty run is explicitly `unavailable`.

The August 10 cold-start failure chain was: a global post-ban field reset removed nearly all
current composition, an older stored era could override the direct ban boundary for affected
entities, `grounded` was promoted from a badge to a speaking gate, and file-exists status counted
the resulting silent page as operational success. The preventive seams are entity-level horizon
clamping, labeled transition provenance, status-level practical ordering, the opt-in posterior
table view, and the usefulness contract.
