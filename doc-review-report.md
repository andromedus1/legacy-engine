# Doc Review Report

**Project:** legacy-engine
**Date:** 2026-08-17
**Documents reviewed:** 6 system planning documents plus project instructions, the knowledge index,
the Best Call source/template, and the generated report
**Passes run:** 1 system pass plus a fresh independent full re-audit; no module planning corpus was
discovered
**Final issues:** 0 Critical, 0 High, 1 Medium, 1 Low, 1 Info
**Exit gate:** **PASS — 0 Critical / 0 High**

## Pass 1: System-Level

### Critical (0)

None.

### High (0)

None.

### Medium (1)

#### Principle 10 retains a superseded ban-regime-only default

**Files:** `docs/PRINCIPLES.md:83`, `docs/SPEC.md:58`, `docs/ARCHITECTURE.md:199`

**What:** Principle 10 describes ban-regime-aware windowing as the universal default. The shipped
system uses entity-era and pairwise windowing, with confirmed ban boundaries retained as hard guards
and ban-only fallback. SPEC and ARCHITECTURE describe the current hierarchy correctly.

**Fix:** Rewrite Principle 10 around entity-era/pairwise eligibility while retaining ban boundaries
as hard guards and fallbacks. This is non-blocking for the reviewed Best Call copy.

### Low (1)

#### One brief lacks research provenance

**File:** `docs/analysis/copy-count-distribution-study.md`

**What:** The document is `type: brief` but has no `research_method` field.

**Fix:** Add its known method, or `research_method: migrated` if its origin is unknown.

### Info (1)

No separate module-planning documents were discovered, so this review required one system-level
pass rather than additional system-plus-module passes.

## Best Call Methodology Verification

The source template, generator, field policy, durable runbook, and regenerated HTML agree:

- The observed field is an exact post-ban presence/recentness claim. The current generated payload
  contains 197 observed decks.
- The thin observed slice is stabilized to a 500-deck decision field with 303 bounded
  preceding-regime pseudo-decks after affected archetypes are removed. `% of meta`, opponent
  weighting, Agency-related field metrics, and P(best) use these effective shares.
- Camp share uses the parent's decision share times its current-window camp fraction when the parent
  is observed. A prior-only parent instead uses its preceding-regime camp fraction. Both methodology
  locations in the template and generated HTML name this exception.
- Localized exact-clean-interval direct estimates are `diagnostic-only`. They cannot change Agency,
  its floor, grounding, P(best), candidacy, or ordering; the authority payload is hashed before and
  checked after attachment.
- The generated payload has 0 grounded rows and `proof_grade_call: null`, while all 50 supported
  archetypes have a readable diagnostic direct estimate.
- All 42 `// [warn] ranking subject ...` lines are filtered out of the first-read header and placed
  in the collapsed **Ranking exclusions and diagnostics** disclosure near the bottom.
- The field-basis disclosure, rather than the compact top audit line, is correctly documented as the
  place that reports both observed and effective counts.

The generated HTML was rebuilt after the final template corrections. Its size is 38,640,596 bytes,
and its embedded data remains through 2026-08-16.

## Frontmatter and Cross-References

- Scoped planning frontmatter: **6/6 compliant**.
- All scoped document-to-document references resolve.
- `docs/knowledge-index.yaml` was read as the generated navigation source. Its Best Call entry still
  reflects the pre-edit date; this is expected pending regeneration and was not counted as a
  contradiction. Generated index files were not edited by this review.
- `CLAUDE.md` and `docs/architecture/README.md` correctly describe the top-level foundation docs and
  `.work/` delivery substrate; the prior review report's contrary statement was stale and has been
  removed by this replacement.

## Blocking Briefs Status

| Brief | Blocks | Exists on disk? | Status |
|---|---|---:|---|
| `docs/briefs/card-semantics-ir.md` | `epic-card-semantics-ir` | Yes | Written |
| `docs/briefs/change-point-detection.md` | `epic-stable-era-windows` | Yes | Written |
| `docs/briefs/data-autonomy-upstream.md` | `epic-data-autonomy` | Yes | Written |
| `docs/briefs/deck-generation-and-moxfield.md` | `epic-deck-generation` | Yes | Written |
| `docs/briefs/scorer-flexibility-valuation.md` | `epic-scorer-flexibility-valuation` | Yes | Written |
| `docs/briefs/sideboard-core-and-hedge.md` | `epic-sideboard-core-and-hedge` | Yes | Written |
| `docs/briefs/subarchetype-discovery.md` | `epic-subarchetype-resolution` | Yes | Written |
| `docs/briefs/superarchetype-aggregation.md` | `epic-superarchetype-layer` | Yes | Written |

No roadmap-style DONE phases were present in the reviewed planning set. The Best Call paths named by
the methodology all exist: `scripts/refresh_decision_data.py`,
`scripts/refresh_best_call_ranking.py`, `scripts/best_call_ranking_template.html`,
`src/legacy_engine/advisory/field.py`, and `decks/best-deck-best-call-ranking.html`.

## Provenance Summary

| `research_method` | Briefs | Latest updated |
|---|---:|---|
| `/deep-research` | 9 | 2026-05-29 |
| `/brief` | 10 | 2026-07-31 |
| `/research` | 3 | 2026-07-04 |
| `adversarial-reader` | 1 | 2026-07-31 |
| Missing | 1 | 2026-07-04 |

No refresh candidates arise under the review skill's tier-and-recency rule.
