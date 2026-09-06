---
description: Adversarial-read verification of the recurrent-era interval research campaign.
type: research
summary: The correction passes resolve the citation-chain, substrate, marker, and acquisition-binding findings; the campaign is approved.
updated: 2026-08-13
provenance: agent-synthesis
decisions:
  - Approve after terminal verification of the three second-pass residual repairs.
key_findings:
  - Jensen-Shannon symmetry, FDA wording, ECP acquisition removal, attestation cleanup, W3C anchors, and substrate-confidence repairs are complete.
  - The campaign-level PROV-DM acquisition is source-bound and all identified composed claims carry explicit inference markers.
---

# Recurrent stable-era intervals — adversarial-read checklist

## Terminal correction result

The three second-pass residuals are resolved: `acquisitions.md` binds the PROV-DM candidate to
`[recurrent-consume-w3c-prov]{1}` and now declares analytical provenance; the two parent passages
carry `{inferred: cross-synthesis}` markers; and Discover marks the TICC density comparison as a
project inference. Terminal lint on the acquisition reports one resolved citation, zero broken,
zero thin, and zero pattern flags. A direct marker/acquisition spot-check found no residual from the
second-pass set.

## Second-pass correction result

The completed correction pass resolves the original required repair set:

- `[recurrent-lin-jensen-shannon]{4}` now attests equal-weight symmetry, and both analytical claims
  say **equal-weight** and cite `{4}`;
- the FDA contradiction row now says numeric margins plus design-specific sample-size calculation and
  cites the matching `{1}` and `{3}` details; it no longer claims a source-prescribed minimum count;
- Discover's unattested ECP companion-paper candidate is removed;
- the previously identified Discover method-role extensions and most parent inheritance now carry
  `{inferred: ...}` or `{extends}` markers;
- project application prose is removed from all six identified attestations;
- W3C detail 4 now names exact sections and properties; and
- all four Discover attestations now declare `substrate_confidence: source-direct`.

The no-URL lint rerun reports 162 resolved citations, zero broken chains, zero thin attestations, and
zero omitted `substrate_confidence` fields. The remaining source-liveness results supplied to this
pass are low-severity reprobe warnings. The Discover named-feature wording flag at line 262 is a
surface false positive: the E-Divisive capability is cited on the same table row. It is not an
adversarial finding.

Three residual actionable findings prevent approval:

1. **Medium — campaign acquisition is not source-bound at its own surface.** `acquisitions.md:7-9`
   names the W3C PROV-DM Recommendation, classifies it, and says PROV-O names it, but contains no
   citation. The equivalent specialist entry is correctly bound at
   `specialists/consume-validate.md:315-318`. Add `[recurrent-consume-w3c-prov]{1}` to the campaign
   acquisition entry so this standalone candidate points at the fetched source that names it.
2. **Medium — residual parent inheritance remains unmarked.** `parent.md:115-117` prescribes the
   diagnostic status and concentration display fields before the cluster-regression transfer marker;
   `parent.md:206-215` composes four disconfirming shortcuts and a certification-policy conclusion.
   Add a scoped `{inferred: cross-synthesis}` marker to each of those two composed passages. Existing
   source-specific sentences and citations need no change.
3. **Low — the cleaned TICC attestation exposes an unmarked comparison.**
   `specialists/discover.md:193-197` cites source detail `{5}`, which now correctly records only the
   paper's 36,000-observation demonstration. “Far denser than a weekly metagame trace” is the
   specialist's project comparison, not part of the cleaned attestation. Add an inference marker to
   that comparison; do not restore project framing to the attestation.

## Revisions

- **2026-08-13 — correction, terminal approval:** verified the three second-pass residual repairs,
  reran targeted citation lint, and changed the terminal verdict to approved.
- **2026-08-13 — correction, second adversarial pass:** verified every first-pass repair against the
  updated parent, specialists, acquisitions ledger, attestations, and lint outcome. Preserved the
  first-pass record below and narrowed the terminal verdict to the three residuals above.

## First-pass record

The sections below record the initial adversarial findings. They are resolved by the correction pass
except where the second-pass result above identifies a residual.

## (a) Semantic citation-chain walk

All 17 cited handles resolve to files under `.research/attestation/`, and every cited ordinal exists.
The reported lint result—31 resolved parent citations, no broken chains, and no thin-chain flags—is
consistent with the mechanical walk. The following semantic gaps remain:

1. **Medium — Jensen-Shannon symmetry is read-but-not-attested.** `parent.md:39-42` and
   `specialists/discover.md:67-72` call Jensen-Shannon divergence symmetric while citing
   `[recurrent-lin-jensen-shannon]{1}` and `{2}`. Detail 1 records the zero-support problem of directed
   Kullback divergence; detail 2 records nonnegativity, identity at equality, and weights. Neither
   numbered detail records symmetry. Extend the attestation toward the source with the source-anchored
   symmetry statement, then retain/re-point the claim; do not weaken an otherwise source-true claim.
2. **Medium — the FDA minimum-count claim points at the wrong specifics.** The certification
   contradiction row at `specialists/certify.md:255` says the guidance contains numeric margins and
   minimum counts and cites `{2}` and `{3}`. Those details cover prespecified adaptation/error control
   and design-specific sample-size calculation; they do not record a minimum-count rule. Either attest
   the actual minimum-count passage with an anchor and cite that new ordinal, or remove only the
   minimum-count half of this source claim. The attestation summary is not a substitute for the cited
   numbered specific.
3. **Medium — Discover's acquisition candidate lacks an attested chain.**
   `specialists/discover.md:278-281` supplies a full title and author pair for a companion change-point
   paper and says the fetched E-Divisive paper names it, but the candidate has no citation and
   `recurrent-ecp-james-matteson.md` does not record that bibliographic detail. Acquisition candidates
   and their metadata are source-bound. Record the named companion and its source-internal anchor in
   the ECP attestation, then cite it from the candidate, or drop the candidate.
4. **Low — cluster-inference scope is broader than its attested setting.** `parent.md:108-112` and
   `specialists/consume-validate.md:110-116` generalize a cluster-robust regression review into claims
   about matchup-posterior precision. The underlying dependence warning is relevant, but the transfer
   to this estimator is composed. Mark the application as `{inferred: ...}` (or `{extends}` where it
   specifies diagnostics) and keep the regression setting visible.

The remaining sampled chains—change-point assumptions and algorithms, sticky HDP-HMM behavior,
TICC structure and optimization, equality-null versus equivalence tests, FDR/FWER, covariate shift,
multirange operations, forward splits, calibration/proper scores, temporal queries, and PROV
relations—are supported by their cited attestation details.

## (b) Uncited or overextended claim shapes

**High — the parent synthesis leaves composed design claims unmarked.** The issue is systematic, not
one sentence. Examples include the production-method ranking at `parent.md:34-42`; the feature
firewall, complete-link rule, and candidate payload at `parent.md:46-61`; the ordered certification
gates at `parent.md:71-85`; evidence-view and concentration requirements at `parent.md:102-113`; and
the promotion contract at `parent.md:161-166`. These are cross-specialist conclusions or project
extensions, not facts carried by the adjacent source attestations. Add scoped `{inferred:
cross-synthesis}` / `{extends}` markers wherever a paragraph moves beyond its source-specific claims.
The existing markers at lines 32 and 150 show the expected form but do not cover the other sections.

**Medium — Discover contains unmarked named-method extensions.** In particular,
`specialists/discover.md:124-128` maps E-Agglo's supplied initial segmentation to bans, taxonomy
migrations, and outages, then derives a cross-ban policy; `specialists/discover.md:173-176` specifies
a finite sticky-HMM implementation, Viterbi/posterior output, and label alignment; and lines 207-210
assign production roles in the comparison table. These may be reasonable design choices, but the
attestations do not prescribe them. Mark them as inference/extension. This also resolves the lint's
low-severity named-feature wording concern without pretending the source chose the project's role.

No composed absolute effort estimate or uncited comparative superlative was found.

## (c) Smoothed-contradiction coherence read

The three specialist briefs and parent all include explicit contradiction sections with relationship
types. Equality-null versus equivalence, FDR versus family-wise protection, exact set eligibility
versus statistical transport, and database time versus analytical provenance remain side-by-side;
the selected production policy is stated after rather than disguised as a merger. No
resolution-by-average was found.

**Low — several parent contradiction counterparts are composed but unmarked.** For example,
`parent.md:170-176` juxtaposes source-attested method capabilities with project-specific dependence,
fit-instability, and cutoff-refit judgments. Preserve the structural contradiction, but mark the
project-side positions as inference so the row does not imply both sides are directly attested.

## (d) Noise and relevance weighting across attestations

The source set is relevant to its assigned facets, and no low-relevance source dominates the
decision. Cross-domain sources are generally qualified: FDA guidance supplies equivalence design
logic rather than deck-era constants; meta-analysis supplies a heterogeneity lens; PoSI is explicitly
limited to its regression setting; and SQL temporal documentation is not treated as full analytical
provenance.

The four low-severity parent `unreachable-source` reprobe findings and 20 corresponding
Consume/Validate findings are maintenance warnings, not evidence that an attestation was never
fetched. They should remain queued for reprobe, but they do not by themselves invalidate the
source-direct corpus used here.

## (e) Quote-context walk

No load-bearing verbatim quotation appears in the parent or specialist briefs. Quoted UI labels and
hypothesis text are authored design language, not attributed source quotations. Nothing surfaced.

## (f) Analytical-tier-inheritance walk

No `[handle]{N}` resolves to a specialist brief, campaign synthesis, glossary, position, or other
analytical-tier artifact. There is no direct lens-as-substrate citation laundering.

**High — uncited inheritance still obscures epistemic status.** The parent closely carries forward
specialist recommendations—complete-link discovery, independent event splitting, ordered gates,
three evidence views, two-clock history, and chained promotion—without marking most of them as
cross-synthesis. A specialist brief cannot silently serve as substrate merely because its handle is
omitted. Apply the markers listed in job (b) at the parent tier; source-specific claims may remain
unmarked only where their attestation citation directly carries them.

## (g) Line and section reference walk

Most attestations provide usable page, section, or source-line anchors. One residual is substantive:

- **Low — vague W3C anchor.** `recurrent-consume-w3c-prov.md:28-29` records detail 4 only as
  “document vocabulary and property definitions,” without a section, fragment identifier, or line
  range. Because `{4}` supports several manifest/provenance claims, replace that generic pointer with
  exact property-definition anchors for `generatedAtTime`, `used`, and `wasDerivedFrom`.

No analytical artifact asserts a stale source line range. The current page/line references in the
other cited attestations are internally consistent with the claims made from them.

## (h) Substantive thin-attestation review

No cited attestation is structurally empty or globally thin, agreeing with lint. However, six
attestations leak project analysis into the descriptive tier:

- `recurrent-consume-calibration.md:16-18` applies the paper to an expanded-era matchup posterior;
- `recurrent-consume-heterogeneity.md:17-18` applies it to era-to-era variation;
- `recurrent-consume-pg-multirange.md:16-17` names the archetype-era implementation;
- `recurrent-consume-sklearn-timeseries.md:16-18` evaluates use for irregular tournament arrivals;
- `recurrent-consume-w3c-prov.md:16-17` evaluates the proposed historical report; and
- `recurrent-hallac-ticc.md:33-35` compares the paper's data density with the project's weekly trace.

These summaries/details fail the project-framing half of the substrate test. Move the application
sentences to the relevant specialist brief and leave only source-descriptive content in the
attestations. The cited specifics remain usable after that cleanup.

The four Discover attestations that omit `substrate_confidence` are
`recurrent-ecp-james-matteson.md`, `recurrent-fox-sticky-hdphmm.md`,
`recurrent-hallac-ticc.md`, and `recurrent-lin-jensen-shannon.md`. The field is currently optional
and defaults to source-direct, so this is nonblocking schema-forward cleanup rather than a present
verification failure.

## Verdict

**APPROVED**
