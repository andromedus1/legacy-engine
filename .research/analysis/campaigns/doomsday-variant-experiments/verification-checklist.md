# Adversarial verification checklist

Campaign: `doomsday-variant-experiments`  
Reviewed: 2026-08-20  
Posture: fresh-context, full-rigor adversarial read  
Verdict: **NEEDS-REVISION**

## Severity-ranked revision requirements

### High — cited ordinals do not exist in two load-bearing attestations

`parent.md` cited `ddx-construction-results` passage 1 nineteen times and
`ddx-construction-registry` passage 1 four times, including throughout **At-a-glance comparison**
(lines 75–92), **Deterministic construction and draw experiments** (lines 163–168), and
**Disconfirming analysis** (lines 213–215). Neither attestation defines a numbered passage or
section `1`; both use unnumbered headings/bullets. The handles resolve, and the attestation bodies
usually contain the relevant facts, but the asserted sub-attestation anchors do not exist.

Revision action: add stable numbered anchors to
`.research/attestation/ddx-construction-results.md` and
`.research/attestation/ddx-construction-registry.md`, then repoint each claim to the narrowest
supporting anchor. Do not merely retain a catch-all `{1}` for unrelated method, principal-arm, and
alternate-branch claims.

### High — prospective allocation is read-but-not-attested

`parent.md` **Prospective played tests** (lines 178–183) states that thirteen non-control
candidates across five roles at four matches each produce 260 candidate plus 260 paired-control
matches, then cites only `[ddx-strategy-playtest-protocol]{1–3}`. Those passages attest pairing,
balancing, and the 20-match stopping threshold; they do not attest the thirteen-candidate/five-role
matrix or either 260 total. The same unsupported chain is projected in `report-content.json`
**experiments / Paired physical screen** (lines 351–359) and **next_tests / Complete the registered
screen** (lines 433–442), whose only handle is the protocol.

The totals are numerically correct against `experiments/strategy/physical_test_matrix.csv` (65 rows
at four candidate and four control matches) and `scenario_summary.json`, but no `ddx-*` attestation
records those result specifics. Revision action: attest the generated strategy outputs before citing
them, then cite that attestation; alternatively present the allocation explicitly as composed
prospective design with the required epistemic marker and citations to each attested input.

### Moderate — analytical claims are mislabeled as observed/deterministic in the JSON projection

`report-content.json` **comparison_rows** labels every principal observed arm
`observed+deterministic`, but several `signal` fields are interpretations: “Balanced live
reference” (lines 132–133), “Board-building value package … timing control” (lines 171–172),
“Broad shield bundle” (lines 184–185), and “support a genuine denial-tempo posture” (lines
223–224). The source data support the underlying counts/rules; they do not make those evaluative
phrases direct observations. Likewise **experiments / Outcome surface** says “no stable variant
ordering survives” while labeling the whole row `observed` (lines 326–330); that conclusion is an
inference from small, dependent, taxonomy-sensitive observations.

Revision action: split raw signals from interpretations or label the rows/fields `inferred` (or a
mixed class that explicitly includes inference). This is also required for faithful projection of
the parent, which marks the hierarchy and recommendations as inference.

### Moderate — two parent claims lack a complete semantic chain

- `parent.md` **Read this first**, Current Dimir rank (lines 33–36), calls its opening access
  “strong” but cites only the outcome extract and Dimir list attestation. Add the construction-result
  citation and mark the comparative judgment as inference, or replace “strong” with the exact
  measured value.
- `parent.md` **Contradictions and tensions** (line 231) states without citation that creature
  transformation consumes sideboard slots, while only the Paradigm Shift half of the row is cited.
  Cite the registered creature-pivot counts/list source or mark the full comparison as composed.

### Moderate — artifact and candidate counts are conflated

`parent.md` **Contradictions and tensions** (line 230) says “Fourteen artifacts are registered.”
`ddx-construction-registry.md` records **15 artifacts / 14 unique candidates**; the strategy
manifest attestation records 14 unique candidates. Revise the row to distinguish artifacts from
unique candidates. `report-content.json` consistently uses fourteen variants/candidates and does
not repeat this specific count error.

## Eight adversarial jobs

### (a) Semantic citation-chain walk

- **Blocking findings:** the prospective 260+260 matrix is not in the cited protocol attestation;
  Current Dimir's “strong” opening-access comparison lacks its construction evidence.
- Other load-bearing observed records, deterministic percentages/counts, card-rule descriptions,
  field shares, and evidence-posture claims semantically match the cited attestation bodies.

### (b) Claim shapes missed by mechanical lint

- **Findings:** the uncited creature-slot claim at `parent.md` line 231; the under-cited/comparative
  “strong raw opening access” at lines 33–36; and interpretive JSON `signal` fields presented under
  non-inferred evidence labels.
- No over-extended cite-through to a non-corpus author was found.

### (c) Coherence read for smoothed contradictions

- No smoothed source contradiction was found. The report preserves current-class versus historical
  exact-lineage tension, recurrence versus pilot independence, and protection count versus compound
  access as separate positions.
- The artifact/candidate count conflation is a factual terminology error, not a smoothed source
  disagreement.

### (d) Noise domination / relevance weighting

- **Finding:** the Current Dimir hierarchy claim uses outcome/list attestations while omitting the
  more relevant `ddx-construction-results` attestation for opening access.
- Otherwise the report consistently prefers the outcome extract for records, deterministic results
  for construction values, direct list/rules attestations for mechanisms, and the field-ranking
  attestation for scenario shares. No noise-dominating attestation was found.

### (e) Quote-context walk

- No verbatim quotation from a fetched source appears in the parent or JSON projection. Scare-quoted
  hypothesis labels in **Disconfirming analysis** are the synthesis's own propositions, so no source
  qualifier was stripped from a quote.

### (f) Analytical-tier inheritance walk

- No `[handle]{N}` citation resolves to a specialist brief, campaign parent, prior synthesis,
  glossary, or other analytical-tier artifact. All cited handles resolve under
  `.research/attestation/`.
- `report-content.json` identifies itself as a projection rather than an independent evidence
  source. No analytical lens was laundered as source substrate.

### (g) Line/ordinal-reference walk

- **Blocking finding:** `{1}` does not exist in `ddx-construction-results.md` or
  `ddx-construction-registry.md`; see the first high-severity requirement.
- The numbered anchors used for `ddx-outcome-db`, `ddx-outcome-manifest`, card rules, field ranking,
  individual lists, strategy manifest, and playtest protocol exist and correspond to the referenced
  passages.

### (h) Substantive thin-attestation check

- No substantively thin `ddx-*` attestation was found. The narrow list attestations contain exact
  main/side facts sufficient for their uses; the outcome attestation contains the census,
  sensitivity, historical, recurrence, and mismatch specifics; and the construction-results
  attestation contains precise methods and per-arm numbers.
- The construction attestations need stable granular anchors, but that is a reference-granularity
  defect rather than substantive thinness.

## JSON projection and numeric verification

The JSON preserves the parent's principal hierarchy, evidence legend, six recommendations,
principal-arm construction values, break-even grid, limitations, and next-test sequence. Displayed
construction values reconcile with `experiments/construction/comparison.csv` and
`results.json`; 18–16 and the category/recurrence values reconcile with the outcome CSVs; the four
displayed break-even rows recompute from `g = c × (1 − s) / s`; and the physical matrix
reconciles to 260 candidate plus 260 control matches. No incorrect displayed numeric value was
found.

Projection is nevertheless not yet faithful at the epistemic-label level because analytical
`signal`/ordering claims are labeled observed or deterministic, and its matrix totals inherit the
parent's missing attestation chain. Approval requires resolving the high- and moderate-severity
items above.

## Lead correction disposition

All revision requirements were applied after this independent pass:

- construction attestations now expose separate stable passages for method, principal arms,
  alternate branches, registry shape, posture, and legality/coverage;
- a new source-direct strategy-results attestation records the generated 260+260 prospective
  allocation and zero played results;
- parent citations were narrowed, Current Dimir's qualitative access claim was replaced by its
  measured event, the artifact/candidate count was separated, and both sides of the alternate-combo
  tension are sourced;
- JSON comparison and outcome interpretations now carry inferred evidence labels, and the
  prospective totals cite the deterministic strategy result.

Lead validation reran campaign citation lint, JSON parsing, deterministic experiment scripts, and
semantic spot checks. Per full-rigor ordering, the isolated evaluator follows this correction; the
independent adversarial verdict above remains the historical gate result.

## Revisions

- 2026-08-20: Recorded the lead correction disposition and escaped reviewer prose that resembled
  live citation syntax; the original verdict and findings remain unchanged.
