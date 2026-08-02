---
id: epic-superarchetype-layer-three-level-page
kind: feature
stage: review
tags: [analytics, viz]
parent: epic-superarchetype-layer
depends_on: [epic-superarchetype-layer-chain, epic-superarchetype-layer-best-call-fallback]
release_binding: null
gate_origin: null
created: 2026-08-01
updated: 2026-08-02
---

# Three-level best-call page + superarchetype agency map

## Brief

**Andrew's directive (2026-08-01, verbatim intent):** whenever the superarchetype methodology is
finished and producing nice quality output, add it to the best-deck/best-call doc as a THIRD table
(superarchetype, archetype, subarchetype/camp). Also do an agency map for superarchetype — and
maybe one for subarchetype as well.

Deliverables:
1. **Third ranking table at superarchetype granularity** on
   decks/best-deck-best-call-ranking.html, alongside the existing archetype (View 1) and camp
   (View 2) views — same agency methodology, computed over pooled/licensed superarchetype cells.
   Consider (design option, not committed) nesting: superarchetype row expands to its member
   archetypes, archetype expands to its camps — the full taxonomy as one navigable surface.
2. **Superarchetype agency map**: the S×S strategy-level matchup heatmap. This is where the
   coarse level shines — the brief measured cluster×cluster displayability at 70.3% (K=8) vs
   0.3% at archetype level, so the map is DENSE where the archetype matrix is empty. Agency
   metric definition needs care at this level: worst-grounded-matchup is vs other
   superarchetypes; intra-family cells carry their flag; gates/refusals render as labeled holes,
   never blanks.
3. **Camp-level agency map — RECOMMENDED FORM: rectangular camps × parent-level opponents**,
   which is literally what MultiSplitMatrix produces (cheap since the 26x adaptive build).
   Camp × camp is REJECTED for the map: mostly speculative cells (the thinness this epic exists
   to fight); revisit only if pooling changes that picture.

## Quality gate (Andrew's bar: "nice quality output")
Ships only AFTER -chain and -best-call-fallback are done AND their output has passed a
dogfooding quality review — the pooled/imputed cells must have survived real use before they
anchor a headline table. Do not bind to a release before that review happens.

## Inherited constraints
Epic addenda #1/#2 bind: labeled leans never grounded rows; freshness/churn provenance on every
pooled or imputed number; the I² one-sidedness caveat on the definitional card; page muting rules
apply at all three levels.

## Taxonomy preview evidence — 2026-08-02

The completed era-aware core-pools pass (`n_boot=200`, seed 0, read-only) yields 65 clusters from
106 definers and places 98.52% of the field. It is current and well-supported as a composition
taxonomy, but it is not automatically a useful page hierarchy: 40 of the 65 clusters have exactly
one defining archetype. Current-field leaders illustrate both successes and failures:

- coherent families: `Dimir Delver + Dimir Tempo`, `Aluren + Show and Tell`, `Mystic Forge Combo +
  Post + Tron`, the curated `White creature`, and the ANT/TES storm family;
- label-level survivors rather than strategy families: Doomsday, Izzet Delver, Grixis Reanimator,
  Lands, Dimir Midrange, Eldrazi, and Dredge each define singleton branches;
- questionable composition neighbors that need explicit review before headline use: Azorius
  Midrange/Stoneblade/Stiflenought and Cephalid Breakfast/Esper midrange-tempo shells.

Therefore the raw 65-cluster candidate should not silently become the third ranking table. The page
needs an explicit product decision among: (a) exploratory rendering of the current serving registry,
(b) a reviewed curated strategy roll-up over era-aware membership, or (c) waiting for the full
future-only decision benchmark. No registry was written during this preview.

## Design decisions

- The first HTML review is an exploratory/navigation surface. It does not change the archetype-level
  Best Call recommendation until the future-only predictive/decision benchmark passes.
- Preserve the existing report's restrained visual language while exploring materially different
  information hierarchies and densities.
- Use realistic illustrative values in mockups; production HTML must source every value from the
  serving registry and generated analysis payload.

## Mockups

- Screens: `.mockups/screens/epic-superarchetype-layer-three-level-page/index.html`
- Selected direction: Option 2's expandable hierarchy combined with Option 1's explicit
  strategy-family heatmap; refined at `option-hybrid.html` (2026-08-02).
- Selected: `option-hybrid.html` — approved by Andrew on 2026-08-02.

## Architectural choice

Use one additive, self-contained `families` payload beside the existing `arch` and `camps`
payloads. The generator derives it from the serving registry and the adaptive builder's typed
`cluster_cells`; the template only renders. This keeps the registry as taxonomy SSOT, preserves
the existing archetype/camp headline calculations byte-for-byte, and makes an absent registry an
honest empty-state instead of a fabricated hierarchy.

Alternatives rejected: recomputing clusters in the page refresh would violate the offline-registry
boundary; deriving family cells from rendered ledger strings would discard typed refusals and
provenance; replacing the two existing tables would make a navigation experiment silently change
the authoritative recommendation surface.

The approved composition is the nested hierarchy from mock Option 2 plus Option 1's explicit
family heatmap. Family metrics are exploratory summaries over valid subject-vs-family pooled cells;
the page labels them non-authoritative until the future-only benchmark passes.

## Implementation Units

### Unit 1: Typed family presentation payload (trickiest unit)

**File**: `scripts/refresh_best_call_ranking.py`

```python
def build_family_payload(registry, cluster_cells, archetype_rows) -> tuple[list[dict], list[dict]]:
    """Return family hierarchy rows and an S×S matrix with typed refusal states."""
```

Aggregate member field share/current counts, retain registry membership/provenance, and summarize
each subject-family response against every opponent family. A point is emitted only from non-refused
`PooledCell` values; missing/refused evidence remains a labeled cell with member split and gate
reason. Never feed this payload into archetype Best Call, camp P(best), or existing strata.

**Acceptance Criteria**:
- [ ] Empty/absent registry emits empty family payload and leaves existing outputs unchanged.
- [ ] Every field archetype appears under at most one registry family; unassigned rows remain visible.
- [ ] Refused family cells carry a reason and no numeric point estimate.
- [ ] Family metrics and heatmap use the same generated cell payload.

### Unit 2: Approved nested hierarchy and maps

**File**: `scripts/best_call_ranking_template.html`

Render an exploratory boundary banner, expandable family → archetype → camp hierarchy, the S×S
family agency heatmap, and the camps × parent-opponents map. Use text labels in addition to color,
keyboard-operable disclosure controls, horizontal overflow, and the current light/dark tokens.

**Acceptance Criteria**:
- [ ] The approved hierarchy and explicit heatmap appear when family data exists.
- [ ] Family refusals render hatched/labeled rather than blank.
- [ ] Existing archetype and camp tables remain available and authoritative.
- [ ] No-registry pages render an explicit unavailable state without JavaScript errors.

### Unit 3: Generator contracts and regenerated artifact

**Files**: `tests/test_refresh_best_call_ranking.py`, `decks/best-deck-best-call-ranking.html`

Add pure payload tests plus end-to-end HTML assertions. Regenerate against the project corpus and
inspect the final document in a browser.

## Implementation Order

1. Unit 1 — the typed refusal-safe payload determines whether the UI can be honest.
2. Unit 3 tests — pin payload and no-registry behavior before template wiring.
3. Unit 2 — translate the approved mock into the existing self-contained template.
4. Regenerate and inspect the actual report.

## Testing

- Unit tests cover registry-off, membership nesting, weighted family metrics, refusal propagation,
  and deterministic ordering.
- Existing script parity tests prove archetype/camp rows remain unchanged.
- End-to-end render asserts the embedded family payload and required hierarchy/map DOM anchors.
- Full project suite and knowledge-index lint run before review.

## Risks

- **Serving taxonomy is composition-useful but not decision-validated**: the page could imply more
  authority than earned. **Fallback**: persistent exploratory banner and archetype Best Call label.
- **Subject-level aggregation can hide member disagreement**: family summaries could look overly
  precise. **Fallback**: only summarize accepted typed pools; expose refusals and member detail.
- **Dense matrices can become unreadable**: 21 families exceed a fixed viewport. **Fallback**:
  scrollable table with compact labels and cell tooltips; hierarchy remains the primary surface.
- **Registry absent or stale**: refresh must still complete. **Fallback**: explicit unavailable
  section and existing two-level report remain fully functional.

## Implementation summary

Implemented the approved nested hierarchy plus explicit heatmap in the tracked refresh generator
and template. The additive `families` payload reads the serving registry and typed adaptive
`cluster_cells`; it carries concise/full labels, deterministic two-sentence group descriptions,
member provenance, exploratory family metrics, and refusal-safe S×S cells. Intra-family cells remain
visible in the map but cannot set family agency/floor. The template renders expandable
family → archetype → camp rows, the family heatmap, and the rectangular camps × parent-opponents
map while retaining the existing authoritative archetype and camp tables.

The no-registry/`--no-superarchetypes` path emits `families: []`, displays an explicit unavailable
state, and leaves the existing surfaces intact. The production artifact was regenerated at
`decks/best-deck-best-call-ranking.html` (gitignored by design) from the real corpus: 1,876 field
decks through 2026-07-30, 94 archetype rows, 115 camp rows, and 21 serving-registry families.

## Verification

- Approved mockup: `.mockups/screens/epic-superarchetype-layer-three-level-page/option-hybrid.html`
- Focused generator suite: `24 passed`
- Full project suite: `3526 passed, 1 existing UMAP warning` via
  `.venv/bin/python -m pytest -q`
- Generated page JavaScript: parsed successfully with Node (`new Function` syntax validation)
- Knowledge index: `0 errors, 6 pre-existing warnings`
- Browser: regenerated production HTML opened successfully; automated macOS screenshot capture was
  unavailable because the execution environment exposes no capturable display.
