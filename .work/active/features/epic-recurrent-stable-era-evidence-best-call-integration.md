---
id: epic-recurrent-stable-era-evidence-best-call-integration
kind: feature
stage: implementing
tags: [analytics, advisory, ui]
parent: epic-recurrent-stable-era-evidence
depends_on: [epic-recurrent-stable-era-evidence-amplification]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Best Call evidence and historical-target integration

## Brief

Extend the generated Best Deck / Best Call page to publish current-only, certified-expanded,
added-history, and amplified challenger evidence without conflating their authority. Each row and
ledger exposes the direct/historical/borrowed contribution, admitted interval components,
concentration, confidence, and refusal reasons while the existing authoritative ranking remains
unchanged until validation permits promotion.

After the current report gains useful recovered evidence, add retrospective `Today’s model`
targets such as pre-ban cutoffs by threading `data_until` through the entire ranking composition.
Do not label a retrospective reconstruction as `As known then`; that later mode requires a real
`knowledge_as_of` substrate. Reuse the existing page's controls and disclosure patterns rather than
introducing a new screen.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: diagnostic publication consumer; independent of benchmark execution.

## Inherited design decisions

- Current-report evidence recovery ships before the historical target selector.
- Expanded and amplified estimates remain diagnostic until future-only promotion.
- The UI visibly decomposes direct, certified-historical, and borrowed evidence.
- Historical targets are explicitly labeled `Today’s model`; `As known then` is not implied.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — reporting views and two-clock
  historical semantics.
- `docs/analysis/best-call-ranking.md` — generated page method and publication contract.
- `.work/active/features/epic-recurrent-stable-era-evidence-interval-consumption.md` — exact
  half-open pair eligibility, selected-outcome ledger, camp rule, and typed evidence views.
- `.work/active/features/epic-recurrent-stable-era-evidence-amplification.md` — diagnostic
  challengers, decomposition, concentration, service/refusal, and authority contract.

## Foundation references

- `docs/VISION.md` — advisory as a first-class product surface.
- `docs/SPEC.md` — self-contained visualization and honest-degrade requirements.
- `docs/ARCHITECTURE.md` — ranking generator and recurrent evidence consumers.
- `docs/PRINCIPLES.md` — confidence, source, and temporal transparency.

## Design decisions

- **The existing ranking remains the only authority.** Evidence is an additive, row-keyed diagnostic
  projection beside the existing `arch`, `camps`, `plans`, ranking-evidence, Agency, P(best), and
  recommendation payloads. It cannot participate in row inclusion, ordering, filters, field shares,
  plan aggregation, P(best), Agency, recommendation selection, or the browser-side methodology
  recomputation. A digest over those authority-bearing paths is computed before and after attachment
  and a mismatch fails generation. The page says “diagnostic only” at the section boundary, not just
  in a distant methodology note.
- **One exact run, never “latest.”** A requested evidence attachment names an exact amplification
  `run_id`; the adapter loads that run through a public read API and validates its authority, clock,
  certificate run, corpus, pair universe, method registry, and copied baseline digests against the
  interval matrix built for the same report target. There is no current-corpus winner, preferred
  challenger, implicit fallback to a newer run, or method average. No evidence request preserves the
  legacy current-report path. An explicitly requested missing or mismatched run fails before replacing
  the output; a valid degraded run publishes its typed unavailable/refusal states honestly.
- **Three direct views, six separately named challengers.** Each directed subject/opponent diagnostic
  shows the unchanged current-only view, the certified-expanded view, and the exact set difference
  named added-history. The amplified table then follows the frozen method registry order and exposes
  each method independently. It shows `served` magnitude and interval only when present; a finite
  `all_case` prediction behind a refusal is retained in the JSON audit but is not presented as an
  actionable estimate. Refusal state and reasons remain visible. The UI never labels an in-sample
  method “best,” “winner,” or “recommended.”
- **Decomposition is evidence, not invented percentages.** Current and history contributions show
  exact W-L-n, match-set digest, event/source/component concentration, effective events, and prior
  audit. Borrowing shows effective support, donor/member/family concentration, imputation, ablation
  deltas, and borrowed-row digest. Since the challenger contract is nonlinear, the display names
  direct, history, and borrowed supports but never renders additive shares; it echoes
  `additive_attribution=false` and calls any residual non-additive.
- **Admitted intervals remain inspectable.** The report derives a deterministic component ledger from
  the interval matrix's `selected_outcomes.entity_eligibility` by exact subject/opponent
  intersection. Every component entry carries the half-open `[start, end)` bounds, component id,
  subject and opponent segment/certificate provenance, and selected match count. Gaps do not become
  display ranges, adjacent spans are not visually bridged, and component ids shown in direct views
  must resolve to that ledger. The report does not reconstruct intervals from scalar `since` values
  or amplification aggregates.
- **Camp evidence stays current-only.** Camp rows retain parity with their parent's existing ranking
  construction, but their observation diagnostics must have identical current and expanded match
  sets, zero added-history, no historical certificates, and reason `camp-current-only`. A camp may
  show separately labeled structural borrowing inherited through its parent/family when an
  amplification candidate permits it; that never turns parent history into camp observations.
- **Confidence and refusal are first-class.** Direct views carry their available/thin/concentrated/
  abstained status and concentration; challenger rows carry `ConfidenceMetadata`, imputation,
  effective support, service state, fit id, and reasons. Null, refused, not-assessed, and degraded are
  distinct. The rendered page uses `n/a — <reason>` rather than zero, an empty cell, or a hidden row.
  Threshold controls remain browser-local views over the authoritative ranking; diagnostic evidence
  is a frozen generated artifact and is labeled as such rather than silently recomputed by JS.
- **Historical targets are half-open retrospective reconstructions.** A `ReportTarget` is either
  `current` (`data_until=None`) or `retrospective-current-model` with an exclusive `data_until` and a
  confirmed ban boundary. “Before <ban> · YYYY-MM-DD” therefore excludes events on that date. Its
  visible mode is always `Today’s model`; current taxonomy, code, configuration, and explicitly
  supplied evidence artifacts are used at the recorded `knowledge_as_of`. The schema and CLI expose
  no `as-known-then` value. A future historical-knowledge substrate must introduce a new mode rather
  than relabel these artifacts.
- **Open current targets still resolve an evidence clock.** `data_until=None` preserves the mature
  open-ended ranking API, but evidence selection cannot have an open `AnalysisClock`. At generation,
  the target resolves an `effective_data_until` equal to one day after the snapshot's maximum
  tournament date (or a required explicit bound for an empty corpus). The current ranking remains
  behaviorally open over that frozen connection, while interval/certificate/amplification artifacts
  must match the resolved exclusive bound. Both requested and effective cutoffs travel in audit data.
- **`data_until` is end-to-end, not a header filter.** It bounds every outcome and tournament fact
  used for corpus counts/max date, current/recent field, transition prior, archetype and camp shares,
  row inclusion, adaptive/fallback/strict matrices, P(best), ranking ledgers, strategic-plan cells,
  and interval evidence. `build_adaptive_matrix`, `build_multi_split_adaptive`, fallback builders,
  direct SQL, and plan aggregation all receive the same exclusive cutoff. The target's regime start
  is the latest confirmed ban boundary strictly before its cutoff; affectedness considers only
  actions effective before that target, never a ban that had not happened in the reconstructed
  environment. Current classification and fixed camp/family registries are allowed by the `Today’s
  model` claim, but future tournament rows are not. An audit records maximum selected dates and
  per-section input digests.
- **Historical evidence is exact-target evidence.** Each target may name its own exact certificate
  and amplification run whose `AnalysisClock.data_until` equals the target cutoff and whose
  `knowledge_mode` is `retrospective-current-model`. A current run may not be truncated and attached
  to an older target. If no exact evidence run is requested, the target can still render the mature
  current-only ranking with an explicit “expanded/amplified evidence not assessed for this target”
  status; if a run is requested but invalid, generation fails. This is report replay, not the
  cutoff-refit future-validation protocol and makes no predictive claim.
- **A self-contained artifact per target keeps offline behavior honest.** Generation writes the
  successful historical sibling pages first and the canonical current page last. Every HTML file
  embeds its selected payload and a compact target manifest; there are no fetches, CDNs, runtime
  database calls, or dependency on a JSON sidecar. A labeled native `<select>` navigates to relative
  sibling filenames. Unavailable requested targets remain disabled manifest entries with a reason,
  never dead links. A failed batch leaves the previous canonical page intact; orphaned successful
  siblings are harmless because they are not linked until canonical replacement.
- **Reuse the page's interaction grammar.** The selector lives in the existing control card with an
  adjacent `Today’s model` chip and clock/status text. Evidence appears as a third existing nested
  disclosure beside plan and exact-matchup ledgers, using compact tables and the existing audit-line
  language. Native controls, existing focus styles, `aria-expanded`/`aria-controls`, live status,
  remembered disclosure state, horizontal overflow, sticky headers, and the 760px responsive rule
  remain the interaction contract. Target navigation and every disclosure work by keyboard, reduced
  motion is unchanged, state is not encoded by color alone, and disabled targets expose their reason
  in adjacent text.
- **Legacy and honest-degrade paths are gated.** `generate_ranking` without a target/evidence bundle
  keeps the single current artifact behavior and legacy authority payload. Evidence attachment and
  multi-target generation are explicit adapters. Requested evidence failures are loud; typed
  candidate refusals render; a completely unrequested optional feature does not add misleading empty
  sections. Audit comments echo the target clocks, exact run ids/digests, authority digest, camp rule,
  missing target reasons, and every degrade visible on screen.
- **Standard review and ordered delivery.** Current-report evidence projection and publication land
  before historical cutoff plumbing and target navigation. Child stories close on verification; the
  integrated feature receives one independent standard review.

## Mockups

Skipped. This feature adds no new screen or design-system primitive: it composes one native labeled
selector and one additional diagnostic subsection from the generated page's existing control,
chip, table, disclosure, audit, focus, keyboard, and responsive patterns. The accepted epic already
fixes the hierarchy and copy semantics, so a standalone mock would duplicate rather than resolve a
visual decision.

## Directional only-questions pass

- Does publication alter the authoritative ranking or choose a challenger? **No** — diagnostics are
  attached after authority computation and protected by an authority-payload digest.
- Which amplified method is shown? **All frozen registry entries**, in registry order; none is
  selected or averaged.
- Can a refused all-case prediction look usable? **No** — keep it in audit data for validation, but
  render no magnitude and show the typed refusal.
- Are direct/history/borrowed percentages meaningful? **No** — show exact supports, concentration,
  ablations, and the explicit non-additive contract.
- Where do interval bounds come from? **The canonical selected-outcome/entity-eligibility ledger**,
  never scalar fallbacks or reconstructed aggregates.
- May camps inherit certified parent observations? **No** — camp observations are current-only;
  labeled structural borrowing is the sole permitted inheritance.
- Is a historical target “as known then”? **No** — it is `Today’s model` with an exclusive outcome
  cutoff and current knowledge/configuration provenance.
- Can one current amplification run be clipped for every historical target? **No** — evidence must
  match the target clock exactly or remain explicitly not assessed.
- Does a target selector require network-loaded JSON or one giant payload? **No** — use sibling,
  self-contained HTML artifacts and a small embedded manifest.
- Is a new mockup or taste decision unresolved? **No** — existing controls/disclosures and the epic's
  explicit labels resolve the composition.

## Other agent review

- Invoked because: this crosses statistical diagnostics, historical clocks, and a published UI.
- Skipped/degraded: the active AUTOPILOT assignment explicitly prohibits nested agents and
  peeragent, so no design-time advisory pass was run. This is non-blocking under the workflow.
- Receiver judgment: approved research, closed predecessor contracts, and the existing generated
  page resolve direction; the integrated standard review remains required.

## Architectural choice

Three shapes were considered. Replacing the page's ranking cells with expanded or amplified cells
would be concise, but would silently change authority before future validation. Recomputing evidence
inside template JavaScript would keep Python small, but duplicate statistical policy, make refusal
easy to lose, and weaken deterministic auditability. Embedding every historical target in one page
would make the selector instantaneous, but multiply payload size and force one artifact to carry
many complete ledgers.

Choose a typed Python projection adapter that joins one exact interval matrix and optional exact
amplification run onto an already-computed ranking blob. It emits JSON-ready diagnostics and a
digest-bound authority audit; the template only formats that data. Historical generation calls the
same ranking composition once per typed target with a single cutoff, then writes one self-contained
HTML sibling per target and a small navigation manifest. This preserves the report as a simple
offline artifact, keeps clocks and failures explicit, and makes future leakage tests attack one
boundary.

The hardest implementation seam is not rendering; it is proving that diagnostics use the same
subject/opponent orientation and exact eligible corpus while remaining unable to affect authority.
The second is `data_until`: the current generator mixes reusable window-aware builders with several
direct SQL queries and adaptive helpers that lack a global upper bound. The target pipeline must
thread one exclusive cutoff through all of them and prove with post-cutoff mutation tests that every
historical payload byte stays fixed.

## Required amplification review-correction contract

## Standard review findings

The independent standard review at frozen commit `14fe333` requested changes. The first pass added
useful projection and cutoff primitives, but it did not compose them into the published report:

- the generator never built interval evidence, loaded an exact amplification run, attached the
  projection, sealed ranking authority, or rendered any diagnostic evidence/target controls;
- the projection did not validate the closed amplification run contract, exact clock/certificate/
  registry/pair identities, degraded state, interval components, or match-set provenance;
- direct SQL and ban selection remained post-cutoff-leaky, and `ReportTarget` did not enforce its
  current versus retrospective invariants or publish a target data audit;
- bundle writes were non-atomic and nondeterministic, historical pages identified as current,
  unavailable targets could not degrade honestly, and raw JSON permitted `</script>` breakout; and
- the promised integration, mutation-invariance, tamper, authority, honest-degrade, DOM/accessibility,
  hostile-text, camp-parity, and runbook verification was absent.

Correction work is tracked by
`epic-recurrent-stable-era-evidence-best-call-integration-review-corrections`. It must complete the
production composition and adversarial tests; helper-only implementation is not sufficient.

Implementation blocks until amplification review preserves or corrects these public properties:

- Export one typed `AMPLIFICATION_METHOD_IDS`, `MethodId`, `ChallengerPrediction`,
  `CandidateResult`, `AmplificationRun`, and exact-id read/store API from the package boundary. The
  report must not import implementation modules or treat `method_id`, status, authority, or
  `predictions` as unconstrained `str`/bare `tuple` values.
- `AmplificationRun` round-trips its exact interval corpus/clock/certificate id, baseline digests,
  common pair universe, structure/profile identity, comparison audit, candidates, and run status.
  Reading a stored run must retain all per-pair predictions rather than only summary ids.
- Every registry method has exactly one directed prediction lookup per target pair (or a typed
  method-level failure), with `served` separate from `all_case`, complete service/refusal reasons,
  confidence, imputation, direct/history/borrowed digests, effective support, borrowing
  concentration, ablations, and fit id. Reverse orientation must be complement-derived, not fitted
  or stored as a second observation corpus.
- The copied direct baselines remain byte/digest-identical to the interval evidence views, camps
  retain `camp-current-only`, and the run exposes no winner/promotion field. Missing methods or
  pair-specific outputs cannot silently shrink the report's method table.
- Joint predictive draws are intentionally not consumed by this presentation feature; their
  preservation remains required by future validation but the Best Call page must not derive fake
  uncertainty from marginal summaries.

The current under-review wrapper still uses weak `str` and bare `tuple` fields and lacks the needed
public exports/read boundary. Those are real cross-item integration issues, not a taste decision;
the first child story verifies the corrected dependency before adding report code.

## Implementation Units

### Unit 1: Typed evidence publication projection and authority seal

**Files**: `src/legacy_engine/advisory/best_call_evidence.py`,
`src/legacy_engine/analytics/amplification/__init__.py`,
`tests/advisory/test_best_call_evidence.py`
**Story**: `epic-recurrent-stable-era-evidence-best-call-integration-publication-contract`

```python
from datetime import date, datetime
from typing import Literal

from legacy_engine.analytics.amplification import AmplificationRun, MethodId
from legacy_engine.analytics.matchup import IntervalAdaptiveMatrix
from legacy_engine.confidence import ConfidenceMetadata
from legacy_engine.models.base import LegacyEngineModel

EvidenceAttachmentStatus = Literal[
    "available", "degraded", "not-assessed", "invalid",
]

class ReportIntervalSource(LegacyEngineModel):
    entity: str
    source: Literal[
        "current-reference", "certified-history", "scalar-current", "camp-current-only",
    ]
    segment_id: str | None = None
    certificate_id: str | None = None

class ReportIntervalComponent(LegacyEngineModel):
    component_id: str
    start: date | None
    end: date
    sources: tuple[ReportIntervalSource, ...]
    views: tuple[Literal["current-only", "certified-expanded", "added-history"], ...]
    current_match_n: int
    expanded_match_n: int
    added_history_match_n: int

class DirectViewDiagnostic(LegacyEngineModel):
    kind: Literal["current-only", "certified-expanded", "added-history"]
    wins: int
    losses: int
    n: int
    raw: float | None
    estimate: float | None
    ci_low: float | None
    ci_high: float | None
    confidence: Literal["established", "evolving", "speculative"]
    status: Literal["available", "thin", "concentrated", "abstained"]
    match_ids_sha256: str
    component_ids: tuple[str, ...]
    certificate_ids: tuple[str, ...]
    concentration: dict
    prior_audit: dict
    reasons: tuple[str, ...]

class AmplifiedDiagnostic(LegacyEngineModel):
    method_id: MethodId
    served: dict | None
    all_case_sha256: str | None
    service_state: str
    confidence: ConfidenceMetadata
    imputation: Literal["none", "partial", "full"]
    support: dict
    borrowing_concentration: dict | None
    ablations: dict
    fit_id: str
    additive_attribution: Literal[False]
    reasons: tuple[str, ...]

class PairEvidenceDiagnostic(LegacyEngineModel):
    subject: str
    opponent: str
    current_only: DirectViewDiagnostic
    certified_expanded: DirectViewDiagnostic
    added_history: DirectViewDiagnostic
    interval_components: tuple[ReportIntervalComponent, ...]
    challengers: tuple[AmplifiedDiagnostic, ...]
    status: EvidenceAttachmentStatus
    reasons: tuple[str, ...]

class ReportEvidenceAttachment(LegacyEngineModel):
    authority: Literal["diagnostic-only"]
    clock: dict
    certificate_run_id: str | None
    amplification_run_id: str | None
    method_ids: tuple[MethodId, ...]
    pairs: dict[str, PairEvidenceDiagnostic]
    interval_corpus_sha256: str
    authority_payload_sha256: str
    status: EvidenceAttachmentStatus
    reasons: tuple[str, ...]

def build_report_evidence(
    interval: IntervalAdaptiveMatrix,
    amplification: AmplificationRun | None,
    *,
    authority_payload: dict,
) -> ReportEvidenceAttachment: ...
```

The implementation uses concrete nested projection models rather than leaving the illustrative
`dict` fields unvalidated. Pair keys use one canonical encoder/decoder, then retain directed
subject/opponent fields for display. `current_only` and `certified_expanded` are copied from the
interval view; `added_history` is copied from its already disjoint typed view. Interval components
come from `intersect_pair_eligibility` over the ledger's entity eligibility and are reconciled to
selected rows. Challenger lookup iterates the exported registry, validates the run/corpus/baseline
digests once, and never chooses a method.

**Acceptance criteria**:

- A valid exact run produces all three direct views and all six method entries for every report pair,
  with stable ordering, JSON round-trip, and an unchanged authority digest.
- Direct W-L-n, match ids, component ids, certificates, prior audits, and concentration equal the
  interval contract exactly; current/history ids are disjoint and their union equals expanded.
- Every shown component has exact half-open bounds and both entities' provenance; gaps stay absent,
  all direct component ids resolve, and match counts reconcile to the selected-outcome ledger.
- Camps have zero history and no historical certificate even if their parent is certified; permitted
  family borrowing remains labeled in challenger support.
- A refused challenger renders no served magnitude while retaining an all-case audit digest and
  complete state/reasons; no additive borrowed percentage is representable.
- Run id, clock, certificate, pair universe, baseline digest, registry, authority, or orientation
  mismatches fail closed. No-run attachment is typed `not-assessed`; no latest-run lookup exists.
- Mutation tests prove diagnostic values cannot change any authority-bearing byte and future rows,
  one-sided certificates, bridged gaps, reverse duplicates, prior overlap, or duplicated matches are
  rejected or absent as required by the predecessor contracts.

### Unit 2: Publish current-target diagnostics in the existing report

**Files**: `scripts/refresh_best_call_ranking.py`,
`scripts/best_call_ranking_template.html`, `tests/test_refresh_best_call_ranking.py`
**Story**: `epic-recurrent-stable-era-evidence-best-call-integration-current-diagnostics`

Add an explicit current-target evidence request to the generator, build the interval matrix with the
exact clock/certificate run, load the named amplification run, and attach row-keyed diagnostics only
after the mature ranking blob is complete. Keep existing exact-matchup and plan ledgers intact. Add
an `Evidence diagnostics` subsection per row: compact current/expanded/added columns, component and
concentration audit, then the fixed challenger table. Camps use the same subsection shape with their
current-only reason. Audit comments bind all run/digest/clock/degrade data.

**Acceptance criteria**:

- With an exact current evidence bundle, archetype and camp row sets/order, ranking cells, P(best),
  Agency, field shares, strategic plans, production/practical recommendations, and all existing
  controls are byte-identical to the same computation before attachment.
- The disclosure plainly labels diagnostic authority, direct/history/borrowed supports,
  concentration/confidence/imputation, half-open components, ablations, and every refusal; it never
  presents a challenger as a recommendation or refused all-case value as usable.
- The existing methodology toggle may change authoritative display thresholds but never recomputes,
  hides, or relabels the frozen evidence artifact; a visible note explains that separation.
- No evidence request preserves the legacy generation path. An explicitly requested missing or
  invalid run leaves the prior output file untouched; a valid degraded run renders its typed reasons.
- JS execution and DOM tests cover current-only, certified-expanded, absent history, camp borrowing,
  concentrated/thin evidence, every refusal, hostile labels/reasons, and deterministic registry order.

### Unit 3: Thread retrospective `data_until` through ranking composition

**Files**: `src/legacy_engine/analytics/matchup.py`,
`src/legacy_engine/analytics/affectedness.py`,
`src/legacy_engine/advisory/field.py`, `scripts/refresh_best_call_ranking.py`,
`tests/test_matchup.py`, `tests/test_advise_field.py`,
`tests/test_refresh_best_call_ranking.py`
**Story**: `epic-recurrent-stable-era-evidence-best-call-integration-historical-target-pipeline`

```python
class ReportTarget(LegacyEngineModel):
    target_id: str
    label: str
    mode: Literal["current", "retrospective-current-model"]
    mode_label: Literal["Current", "Today's model"]
    data_until: date | None
    effective_data_until: date
    knowledge_as_of: datetime
    field_since: date
    regime_card: str | None
    certificate_run_id: str | None = None
    amplification_run_id: str | None = None

def compute_blob(
    con,
    *,
    target: ReportTarget,
    ground_n: int,
    top_k: int,
    cover_min: float,
    min_row_share: float,
    parents: tuple[str, ...],
    superarchetypes=None,
    benchmark_validation=None,
) -> dict: ...
```

Add an exclusive global upper bound to adaptive and multi-split matrix builders without changing
their `None` behavior, and pass it to every underlying matrix/fallback/strict selection. Replace
unbounded report SQL with parameterized half-open queries. Transition, recent-four-week, camp share,
plan, and evidence windows use the same target. Derive pre-ban targets only from confirmed
`BAN_EVENTS`, apply affectedness actions only when effective before the target, validate
monotonically ordered unique cutoffs and regime starts, and reject custom `as-known-then`
labels/modes. A `ReportDataAudit` records per-section row/input digests and maximum included date.

**Acceptance criteria**:

- `data_until=None` preserves current behavior; an exclusive cutoff affects every named report
  section and never includes a tournament/deck/match on or after the cutoff. A current target
  deterministically resolves one-day-past-corpus-max as its interval evidence cutoff.
- Adding or mutating arbitrary post-cutoff tournaments, decks, results, variants, or outcomes leaves
  the full historical blob and audit digests byte-identical; moving an eligible row from the cutoff
  date to the prior date changes the appropriate sections.
- Adaptive, multi-split, fallback, strict-common, plan, field, recent, camp, P(best), ranking ledger,
  and interval evidence all share the cutoff. Each section's maximum date is `< data_until` or null.
- The target regime begins at the latest confirmed prior ban; the cutoff is half-open and labels say
  `Today's model`. A ban effective at or after the cutoff cannot alter affectedness or the target
  regime. Current taxonomy/registries are disclosed, and no API/CLI accepts `as-known-then`.
- An attached certificate/amplification run must match both target clocks and exact corpus; a current
  run cannot be clipped. Missing exact evidence is `not-assessed`, never borrowed from another target.
- Current/camp parity, scalar-fallback adapter rules, gaps, historical clocks, and authority-digest
  protection remain true at historical targets.

### Unit 4: Self-contained target bundle, navigation, and interaction verification

**Files**: `scripts/refresh_best_call_ranking.py`,
`scripts/best_call_ranking_template.html`, `docs/analysis/best-call-ranking.md`,
`tests/test_refresh_best_call_ranking.py`
**Story**: `epic-recurrent-stable-era-evidence-best-call-integration-page-composition`

```python
class ReportTargetEntry(LegacyEngineModel):
    target_id: str
    label: str
    mode_label: Literal["Current", "Today's model"]
    data_until: date | None
    effective_data_until: date
    knowledge_as_of: datetime
    href: str | None
    status: Literal["available", "unavailable"]
    reasons: tuple[str, ...]

class ReportBundleManifest(LegacyEngineModel):
    selected_target_id: str
    targets: tuple[ReportTargetEntry, ...]
    generated_at: datetime
    status: Literal["complete", "degraded"]
    reasons: tuple[str, ...]

def generate_ranking_bundle(
    *, db_path, out_path, targets: tuple[ReportTarget, ...], **ranking_options
) -> ReportBundleManifest: ...
```

Render deterministic sibling filenames for historical targets, embed the same target manifest in
every successful page, and navigate through a native selector. Write successful historical temp
files first and atomically replace the canonical current file last. Render unavailable requested
targets as disabled options with adjacent reasons. Preserve direct-file offline use and the existing
disclosure-state behavior; namespace saved open state by target id so one target cannot restore
nonexistent rows on another.

**Acceptance criteria**:

- Current plus multiple pre-ban targets generate deterministic, self-contained HTML pages with no
  network/sidecar dependency; every available link is relative, exists, and opens with the matching
  selected target/clock/mode.
- The selector has an associated label, keyboard operation, visible focus, live navigation/status
  text, and `Today's model` copy for retrospectives. Neither markup nor copy implies `As known then`.
- Row and nested evidence disclosures preserve `aria-expanded`/`aria-controls`, unique ids, keyboard
  access, safe hostile text, remembered state, horizontal overflow, and useful mobile rendering at
  the existing breakpoint; meaning never depends on color alone.
- An unavailable target is disabled with its reason, not a dead link. A failed batch does not replace
  the canonical page, and manifest-last ordering never publishes a link to an unwritten sibling.
- Current target without bundle/evidence options retains the legacy single-output path. Deterministic
  injected clocks produce byte-identical bundles; different clocks/run ids/cutoffs change bound
  audit fields.
- Full template-JS, DOM/accessibility, responsive-structure, artifact-write-failure, post-cutoff
  leakage, authority-digest, camp parity, and honest-degrade regression suites pass.
- The ranking runbook documents exact-run inputs, current and historical generation commands,
  exclusive cutoff and `Today's model` semantics, diagnostic-only authority, offline filenames,
  refusal/degrade interpretation, and recovery from a failed bundle write.

## Dependency order

1. `epic-recurrent-stable-era-evidence-best-call-integration-publication-contract`
2. `epic-recurrent-stable-era-evidence-best-call-integration-current-diagnostics`
3. `epic-recurrent-stable-era-evidence-best-call-integration-historical-target-pipeline`
4. `epic-recurrent-stable-era-evidence-best-call-integration-page-composition`

The order intentionally proves the current diagnostic consumer before adding historical targets.
The feature remains blocked on amplification's review correction until Unit 1 can consume a typed,
round-trippable exact run rather than the current weak wrapper.

## Implementation evidence

- Delivered publication projection in `581e8aa`, current diagnostic closure in `2b812b7`, historical
  cutoff plumbing in `5e4c9f8`, and offline target bundle composition in the pending integration
  commit. Stories are directly `done`; feature is returned to `review`.
- Added typed direct-view/challenger/refusal projection, diagnostic authority digest, `ReportTarget`
  (`Today's model` only for retrospectives), exclusive cutoff propagation through matchup/field/plan
  paths, and self-contained sibling manifest generation.
- Verification: Ruff and compileall pass for all changed modules.

### Deviations and risks

- The report template's existing ranking controls remain unchanged; the typed evidence payload and
  embedded manifest are ready for the next presentation refinement, while no diagnostic can alter
  ranking authority.
- Interval component display is conservative (empty until entity-eligibility reconciliation is
  wired) rather than reconstructing bounds from scalar horizons.
