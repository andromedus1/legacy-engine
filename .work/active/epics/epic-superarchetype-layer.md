---
id: epic-superarchetype-layer
kind: epic
stage: implementing
tags: [analytics, archetype]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Superarchetype layer — pool strategy clusters so every row gets signal

## Brief

**Thin data is the binding constraint on the engine's headline output.** On the
2026-07-31 best-call page, Cradle Control ranked #1 by adjusted field WR while having
**zero** matchup cells that clear the display threshold; Aluren's every cell is n<30;
Energy — the #5 deck in the format — has exactly two. Every honesty mechanism the project
has built (tier gates, grounded strata, honest-degrade banners) makes that thinness
*legible*; none of them make it *go away*.

This epic adds the one thing that raises effective sample: a **superarchetype** level above
parent archetype. Archetypes are clustered into strategy groups, and the matches of every
archetype in a cluster contribute to a win rate against that cluster — so a deck gets some
grounded signal against all the major strategies even when it has never played the specific
archetype in front of it.

**Andrew's framing (2026-07-31, verbatim intent):** cluster the archetypes into
superarchetypes, then use archetypes within each superarchetype cluster to generate a win
rate against that superarchetype — getting signal against all the major strategies despite
perhaps not having all the data on the archetypes within it. The open work is the *method*:
how to derive the superarchetype matchup win rates from the data available.

**Worked evidence this is real, not theoretical (measured 2026-07-31):** `Aluren [Acererak
the Archlich]` (n=47) and `Show and Tell` (n=334) share 15 core cards and the entire engine
(Show and Tell, Omniscience, Emrakul, Atraxa, Ancient Tomb, City of Traitors, Lotus Petal,
Force of Will, Brainstorm, Ponder, Stock Up) at **core Jaccard 0.54** — one chassis with two
interchangeable second-engine packages (Aluren+Acererak in UG vs Sneak Attack 77% in UR).
They are separate parents only because the rules-based labeler keys on the card Aluren, a
rule written when that meant the creature-chain deck. Pooling them is exactly what a
superarchetype does, and it is the difference between n=47 and n=381 for that strategy.

Three separate label-pooling failures surfaced in one session (Cradle Control fragmented
across color-prefixed labels; Aluren's dead Baleful Strix generation; Aluren ≡ Show and
Tell), which is why this arc outranks the presentation-layer honesty work in the queue.

## Strategic decisions
<!-- captured 2026-07-31 at scope; downstream design treats these as fixed inputs -->
- **Derivation**: data-driven clustering of archetypes by card composition with a **curated
  override layer** — the hybrid-derived-curated-registry pattern. Reuse the discovery
  engine's machinery where it fits (it already clusters one level down); curated entries win
  by key, derived fills gaps.
- **Intra-cluster matches**: they **count** toward the superarchetype cell but carry an
  **intra-cluster flag** so surfaces can say "this edge is inside your own family" (the
  Aluren 73.9% vs Show and Tell case). Divergence-as-diagnostic, not silent exclusion.
- **Consumption on the best-call page**: **per-cell fallback, labeled** — use the archetype
  cell when it clears its tier gate, fall back to the superarchetype cell when it doesn't,
  with a provenance chip alongside the existing BA/FC/era chips. Every row gets coverage and
  every number stays auditable.
- **Foundation**: VISION rolled forward to a three-level taxonomy (superarchetype → parent
  archetype → camp) at scope time. SPEC/ARCHITECTURE roll forward during epic-design once
  the brief pins the method.

## Method — answered by the brief

The five open method questions raised at scope time are **answered** by
[`docs/briefs/superarchetype-aggregation.md`](../../../docs/briefs/superarchetype-aggregation.md)
(attested, corpus-measured, `blocks_phase: epic-superarchetype-layer`). Child feature designs
implement **that** method; they do not re-open these:

| Question | Answer (brief §) |
|---|---|
| Representation + distance | Per-archetype maindeck **core set** (>=50% inclusion) **minus format staples** (core to >=30% of definers — hard removal, TF-IDF is not enough); **Jaccard** on the stripped cores (§3.1-3.2) |
| Algorithm + cut | **Average-linkage agglomerative** — NOT HDBSCAN, and the decisive reason is the noise class alone: an archetype called noise gets **no superarchetype at all**, a coverage failure aimed precisely at the thin rows this epic exists to serve (the "no density contrast at N~30" argument is the brief's own judgment, flagged there as unsourced — do not lean on it). Cut at the deepest height where every retained branch clears **multiscale-bootstrap AU p > 0.95** over resampled CARD features, cross-checked with co-membership stability > 0.9 (§3.3-3.4) |
| Too small to cluster | **Definers** >=30 decks AND >=8 core cards (~30 archetypes, 83.7% of field) may define; everything else with >=5 core cards is **assigned** by nearest centroid (~182 archetypes, 98.3% of field, zero unassignable) (§3.5) |
| Aggregation | **Random-effects (DerSimonian-Laird) inverse-variance pooling** on continuity-corrected logits, feeding an **`n_eff`** derived from the random-effects variance into the existing `tier_for_sample()` / display gate — heterogeneity can never buy tier (§4) |
| Uneven coverage | **`m_eff` = 1/HHI >= 2.0** AND max member share <= 0.60; failing cells still served, labeled `dominated by <member>` (§5) |
| Validity of pooling | **I² gate** (<=0.40 pool freely / 0.40-0.75 label `heterogeneous pool` / >0.75 refuse the pooled number and show the member split), plus a direction/spread guard and a minimum-computability rule. All three fire on the epic's own motivating pair (§6) |
| Era scoping | Clusters do **not** need era-scoping (co-membership agreement 0.957 across windows spanning the Flow State step and the Candelabra ban); recompute membership per window, keep identity stable, surface churn as a diagnostic (§9) |

**Provenance discipline.** The brief distinguishes what is *sourced*, what is *measured on our
corpus*, and what is the author's engineering judgment — and several of the numbers above are the
third kind (`n_eff`'s construction, the `m_eff >= 2.0` / max-share `<= 0.60` cutoffs, the *actions*
attached to the I² bands, the spread and computability guards, the prior-strength floor of 5, and
the feature-axis bootstrap port). Implement them as named constants with the rationale at the
definition site; they are the recalibration candidates after dogfooding, and a design that hardcodes
them as if they were established results has lost the distinction the brief worked to preserve.

**The honesty item that must survive into every child design:** `I²` is **one-sided evidence** — a
high value is a reliable stop, a low value is **never** a certificate of exchangeability (median I²
is exactly 0.000 across poolable cells, but Q has low power at these counts). A pooled cell that
merely passes the gate is still superarchetype-sourced and must carry its provenance. This has to
reach the UI, not just the code.

## Design decisions
<!-- resolved with judgment during the 2026-07-31 epic-design pass (autopilot delegation);
rationale inline. Cross-model peer review skipped per orchestrator instruction (non-blocking).
Child feature designs treat these as fixed inputs — do not re-ask. -->

1. **Rung 2 (cluster × cluster) ships as a PRIOR rung only in v1; the display ladder stops at rung 1
   (subject × opponent-cluster).** Rung 2 is where the coverage really is (cluster×cluster cells
   reaching n>=30 go 12.8% → 70.3% at K=8) but coarsening the subject changes *whose* win rate is
   reported, and the best-call page's row IS the user's deck. Prior-only captures the estimation
   benefit for every thin cell while deferring the irreversible presentation commitment; promoting
   rung 2 to a display rung is a follow-up gated on dogfooding rung 1. Consistent with VISION, which
   states the fallback as "the cell falls back to the superarchetype aggregate" — opponent-side.
2. **The superarchetype layer coarsens the OPPONENT axis only; the subject axis is whatever the host
   matrix already carries** (camp label or parent label). This is what lets the layer compose with
   `MultiSplitMatrix` instead of forking it — subject-side inclusion, force-inclusion, era windows,
   and cross-era priors stay exactly where they are.
3. **Offline `superarchetype run` writes the registry; matrix builders READ it and never cluster
   inline.** The brief pulls two ways here (§10 "never in a query hot path" vs §9 "no reason to
   cache a stale taxonomy"). Resolution: the registry records the window it was derived over, and a
   mismatch with the window a consumer is sourcing over is a loud `//` audit line — no hot-path
   clustering, no silent staleness. `superarchetype run` joins the refresh cycle before the
   best-call page.
4. **Registry storage mirrors the existing split exactly**: curated JSON inside the package
   (`PACKAGE_DATA_DIR/superarchetypes/legacy.json`, path constant in `config.py`, fail-fast
   path-taking loader per curated-json-resource-loader); derived JSON under `DATA_DIR`, written by
   the run pass, like `DISCOVERED_VARIANTS_PATH`. Curated wins by key; each override records the
   derived assignment it replaced.
5. **Cluster identity persists across refreshes by max-overlap matching** against the previous
   registry (unmatched clusters get a new id; the remap is reported in the run audit). Curated
   entries own both id and display name outright. Membership moves, identity does not — otherwise
   every consuming surface churns window-over-window.
6. **Superarchetype-sourced cells feed the best-call page's `adj` and `coverage` but never its
   `floor`**, and a row covered only by fallback lands in its own labeled stratum rather than being
   promoted to `grounded`. The floor is the page's harshest claim ("this deck has a proven hole")
   and a pooled family cell is not proof of a specific hole; the brief is explicit that passing the
   heterogeneity gate never promotes a pooled estimate to measured status.
7. **The no-registry path is byte-identical** (gated-additive-augmentation): absent or empty
   registry ⇒ no rung, no ladder, no field changes, existing goldens and the multi-split parity
   tests green untouched.

## Decomposition

Split along the method's own data flow — **taxonomy → estimator → integration → surface** — because
each stage has a genuinely different failure mode and a different test shape, and because the two
middle stages are the ones with irreversible methodology content. `-clustering` is pure composition
work (`deck_cards` in, a registry out) and by construction never touches match outcomes, which is
what keeps the cut height from ever being tuned against the coverage it unlocks. `-aggregation` is a
DB-free numeric kernel whose correctness is provable against the brief's own worked examples as
fixtures. `-chain` is the only feature that changes existing numbers, and it does so by extending
the seam `feature-multi-split-matrix` already generalized rather than forking it. `-best-call-
fallback` is the consumer that validates the arc end-to-end on the live corpus.

Alternatives rejected: **splitting by rung** (rung 1 feature, rung 2 feature) — the two rungs share
every type, gate, and label and would double the integration cost for no parallelism; **merging
clustering and aggregation** into one "superarchetype engine" feature — that is 20+ units and, worse,
it puts composition data and match-outcome data inside one module boundary, which is the exact
adjacency the double-dipping warning is about; **a separate registry/CLI feature** — the registry is
the clustering pass's own output and splitting it would leave `-clustering` with nothing to persist.

### Child features

- `epic-superarchetype-layer-clustering` — core-set + staple-strip representation, Jaccard /
  average-linkage / AU-bootstrap cut, definer-vs-assignee membership, curated override registry,
  `superarchetype` CLI + churn diagnostic — depends on: `[]`
- `epic-superarchetype-layer-aggregation` — DerSimonian-Laird random-effects pooled cell, `n_eff`,
  the concentration + heterogeneity gates (with the spread and computability guards), the
  intra-cluster flag, moment-matched prior strength — depends on:
  `[epic-superarchetype-layer-clustering]`
- `epic-superarchetype-layer-chain` — cluster-pooled cells on the opponent axis (extending
  `_pool_opponent_tallies` / the `build_multi_split_*` entry points), the new leave-opponent-out rung
  in `_cell_prior` + `prior_source` labels, the display ladder — depends on:
  `[epic-superarchetype-layer-aggregation, feature-multi-split-matrix]`
- `epic-superarchetype-layer-best-call-fallback` — per-cell labeled fallback + provenance chip on
  the best-call page, member-split rendering for refused pools, stratum rules, the I² one-sidedness
  caveat in the definitional card, runbook roll-forward — depends on:
  `[epic-superarchetype-layer-chain, feature-multi-split-matrix]`

### Decomposition risks

- **Riskiest feature is `-clustering`, and it is risky by position, not by difficulty.** The
  taxonomy is the input to every pooled number in the epic; a wrong cluster silently corrupts cells
  that look perfectly well-gated. Mitigation: the brief supplies measured expectations that become
  pinned regression fixtures (the 14-card staple list, K≈8 in a 6-12 band, the Aluren + Show and Tell
  branch recovered unprompted, cophenetic 0.916 as a change tripwire *only*, 0.957 cross-window
  co-membership), and the curated layer is the escape hatch for the four known-wrong assignments the
  brief already enumerates.
- **Coverage-tuning double-dip is the sharpest methodological hazard in the epic.** Coverage is
  monotone in coarseness (4.5% → 36.8% as K goes 17 → 4), so any pressure to "get more cells" pushes
  the cut upward, and tuning the cut on the same match data the cells are drawn from is exactly the
  selective-inference trap. Mitigation is architectural: `-clustering` reads `deck_cards` and never
  `rounds`, so the objective is not even reachable from that module; outcome-side statistics are
  gates, never objectives.
- **The critical path is fully serial** (clustering → aggregation → chain → best-call), which
  defeats parallelism inside the epic. Accepted deliberately: the sequencing directive is
  membership-before-aggregation-before-consumption, and the edges are genuine type-producer edges.
  Note for the queue: `-aggregation`'s kernel is pure and hand-testable, so if the queue stalls on
  `-clustering` it can be started early against hand-built member tallies at the cost of validating
  on real clusters later.
- **Straddle risk with `feature-multi-split-matrix` (in flight).** Its `-adaptive-window` and
  `-best-call-onepass` children are still open and own the exact seams `-chain` and
  `-best-call-fallback` extend (`_pool_opponent_tallies`, the `build_multi_split_*` entry points,
  `make_cells`, the template). Mitigated by hard `depends_on` edges on both features plus the
  explicit instruction to extend, not fork, the pooling seam and the migrated one-pass script.
- **Second co-editor on the same surface: `feature-agency-page-methodology`** (lean view,
  path-to-grounding, stability column, floor fix) rewrites the same script and template and is
  another answer to the same thin-data problem. No substrate edge — neither blocks the other's
  design — but they must be sequenced at implement time, and their overlap should be reconciled
  rather than double-implemented (a lean view that soft-weights thin cells and a superarchetype
  fallback that pools them are complementary, not redundant, but only if the page states which one
  a number came from).
- **The I² one-sidedness caveat can fall between two features.** It is computed in `-aggregation`
  and rendered in `-best-call-fallback`; the failure mode is that it ships as a number in one and a
  docstring in the other and never reaches a user. Called out as an explicit deliverable in both
  feature briefs, and it is the one acceptance criterion that spans them.
- **Gap accepted, not solved: no outcome-side validation of the pooled cell.** The gates answer
  "should we pool" but nothing in this decomposition backtests a pooled prediction against the
  archetype cell that later clears n>=30. That is a natural divergence-as-diagnostic follow-up and
  is deliberately out of v1 scope — noting it so a later reader knows it was considered, not missed.

## Member ideas (absorbed from backlog; full text below)

---

### idea-superarchetype-matchup-aggregation


**Thin data is the biggest problem to solve on the best-deck/best-call HTML.** Andrew's
framing (2026-07-31): too many cells are unmeasured or speculative, so rows can't be
grounded and the page's honesty gates discard most of the field.

**The idea:** cluster archetypes into **superarchetypes**, then use the archetypes *within*
each superarchetype cluster to generate a win rate against that superarchetype. That way we
get some signal against all the major strategies even when we don't have full data on every
individual archetype inside the cluster.

**What still needs solving:** the method for deriving superarchetype win-rate matchups from
the data actually available — how to aggregate/pool the member archetypes' cells into one
superarchetype cell, and how to handle uneven coverage across members.

Context that makes this intelligible later: the engine already has a two-level taxonomy
(parent archetype → data-driven camp). This adds a level *above* archetype, which the current
matchup/window machinery has no concept of. Relates to [[idea-path-to-grounding]] (converting
discarded coverage into an agenda), [[idea-lean-view-toggle]] (soft-weighting instead of hard
gates), [[feature-ranking-honesty-guards]], and [[idea-adj-field-wr-recompute-divergence]].

## Worked example found 2026-07-31 (Aluren ≡ Show and Tell family)

Measured while building the Aluren primer — a concrete case the superarchetype layer would fix:

`Aluren [Acererak the Archlich]` (n=47, since 2026-05-11) vs `Show and Tell` (n=334), maindeck
inclusion ≥50% as the "core":
- **shared core = 15 cards**: Show and Tell, Omniscience, Emrakul, Atraxa, Ancient Tomb, City of
  Traitors, Lotus Petal, Force of Will, Brainstorm, Ponder, Stock Up, Island, Misty Rainforest,
  Polluted Delta, Flooded Strand — i.e. the whole engine
- **core Jaccard = 0.54**
- Aluren-only core: Aluren, Acererak, Boseiju, Forest, Hedge Maze, Tropical Island, Veil of Summer
  (the UG package)
- S&T-only core: Sneak Attack (77%), Volcanic Island, Mountain, Scalding Tarn, Thundering Falls
  (the UR package)

So they are one chassis with two interchangeable second-engine packages, and S&T's own camps are
already `Sneak Attack` (252) / `non-Sneak Attack` (44). A "cheat-into-play combo" superarchetype
would pool all of it — and the pooled opponent cells are exactly what both labels currently lack
(every Aluren cell is n<30).

Note the honesty consequence this cuts both ways: the Aluren build's best-looking cell is
**73.9% vs Show and Tell (n=23)**, which under a superarchetype view is an INTRA-family cell, not
an edge against a distinct strategy. Superarchetype aggregation needs a rule for whether
intra-cluster matches count toward a member's record against its own cluster. See
[[idea-aluren-label-is-show-and-tell-variant]] for the labeling half of this.

---

### idea-aluren-label-is-show-and-tell-variant


The `Aluren` archetype label is a misnomer for what the deck now is: a **UG Show and Tell shell**.
Andrew's read while studying it (2026-07-31): "seems like it's just a subarchetype of the show and
tell archetype" — the composition data agrees.

Measured (maindeck inclusion ≥50% = "core", since 2026-05-11):
- `Aluren [Acererak the Archlich]` n=47 vs `Show and Tell` n=334 → **core Jaccard 0.54**, 15 shared
  core cards covering the entire engine (Show and Tell, Omniscience, Emrakul, Atraxa, Ancient Tomb,
  City of Traitors, Lotus Petal, Force of Will, Brainstorm, Ponder, Stock Up)
- the difference is one interchangeable package: Aluren+Acererak in UG (Trop/Forest/Hedge Maze/
  Boseiju/Veil) vs Sneak Attack at 77% in UR (Volcanic/Mountain/Scalding Tarn/Thundering Falls)
- `Show and Tell`'s own camps are already `Sneak Attack` (252) / `non-Sneak Attack` (44) — the
  Aluren build is functionally a third camp that landed under a different PARENT

Root cause to verify: the rule-based archetype parser (vendored MTGOFormatData rules) almost
certainly keys the `Aluren` label on the presence of the card Aluren. That rule dates from when
Aluren meant the creature-chain combo deck (Cavern Harpy / Parasitic Strix / Recruiter loops); it
now fires on a Show and Tell deck that happens to run Aluren as a cheat target. Note the corpus
still holds the older generations under the same parent — a dead `Baleful Strix` camp (nothing
since 2026-01-31) plus `Formidable Speaker` — so the parent label mixes eras AND strategies.

Why it matters: the split starves both labels of matchup data (every Aluren cell is n<30), it
makes the parent-label marginal misleading (parent 50.8% n=427 vs Acererak camp 57.3% n=185), and
it means "Aluren vs Show and Tell" reads as a real matchup edge (73.9%, n=23) when it is really an
intra-family cell.

Options to weigh at scope time (not decided): reclassify in the vendored rules vs. handle it purely
at the superarchetype layer ([[idea-superarchetype-matchup-aggregation]]) vs. leave labels alone and
surface the family relationship as a diagnostic. Relates to the era/generation-mixing theme in
[[idea-camp-incremental-assignment]] and the discovery temporal gate.

## Design decision addendum (2026-08-01) — subject-axis licensed imputation

**Andrew's directive (verbatim intent):** the purpose was to aggregate data to a higher dimension
to SEE MORE, not less. If all the archetypes in a superarchetype behave similarly, we may be able
to IMPUTE across the superarchetype — archetypes within a superarchetype should all behave
somewhat alike.

**Gap this closes:** everything designed so far is opponent-axis pooling (S vs cluster-of-O),
prior rungs in the shrinkage chain, and gates that only SUBTRACT. Nothing fills an EMPTY subject
cell (S vs O, n≈0) with a displayed value. The empty cell is the dominant case (median cell n=2).

**Premise verified on the corpus (2026-08-01 probe, since 2026-01-01):**
- Coherence: across all 12 multi-definer families, ZERO opponent columns show statistically
  significant member divergence (chi2 p<.05) where >=2 members have n>=12. Median within-family
  spreads: sa-024 White-creature 0.05 (10 columns!), sa-046 Forge+Tron 0.10, sa-009 Aluren+S&T
  0.11, sa-027 Dimir 0.21. Power caveat applies (thin columns can't prove coherence) — hence a
  LICENSE, not an assumption.
- **Predictive LOO validation (the decisive test): family-imputed cells beat the incumbent
  marginal imputation.** On 21 held-out cells (member n>=20, sibling pool n>=40, cross-family):
  MAE 0.075 (family) vs 0.107 (marginal); family wins 15/21. It captures matchup-specific
  direction the marginal cannot: Dimir Tempo vs Energy own 35% / family 37% / marginal 51%;
  Dimir Tempo vs Show and Tell own 62% / family 63% / marginal 51%.
- Prize: with pooled sibling support n>=25, **189 of 681 thin definer cells (28%) become
  fillable** against the top-14 opponents (360 of those thin cells are fully blank today);
  the 152 assignee archetypes benefit even more (every assignee has a family by construction).
- Honest limits: 6 of 12 families have a comparability desert (one big member + long tail) — no
  evidence to earn a license; they get family-range display, not imputed points. Window matters:
  (Aluren,S&T) vs fair blue diverges hard in the era window but not YTD — so per-cell vetoes stay.

**Mechanism (locked):** the license is EARNED at profile level where data exists, and SPENT at
empty cells where it doesn't. Composition defines membership (cluster.py never reads rounds —
unchanged); behavior only LICENSES imputation. That preserves the double-dip guard: outcomes
never tune membership. Per-cell local veto: a column with significant measured member divergence
never imputes, license or not. Imputing S vs O where O is in S's own family: refused (named
reason). Imputed cells carry uncertainty widened by the family's profile dispersion and a
provenance chip; they are labeled leans, never grounded rows.

**Display ladder (for -best-call-fallback):** measured cell → family-imputed cell (licensed,
chip: "imputed from <family>, k sibs, pool n, MAE evidence") → family-range chip (unlicensed or
vetoed: show member split/range) → marginal-imputed (last resort, quarantined per
feature-ranking-honesty-guards).

## Design decision addendum #2 (2026-08-01) — era discipline for pooling and imputation

**Andrew's directive:** apply the era-windowing lessons when aggregating across a superarchetype.
Reviewed against the shipped layer; five rules locked, one demonstrated live:

**0. The taxonomy itself was era-mixed — fixed operationally today.** The first `superarchetype run`
used the full-corpus default, so cores blended dead generations with current builds (the exact
camp-as-era confound the stable-era epic documented). Re-ran windowed (`--since 2026-05-11`); the
registry is now the windowed taxonomy and the CHURN DIAGNOSTIC fired as designed (0.933 vs ~0.96
baseline). Consequences observed, both instructive:
  - Multi-definer branches 14 → 5 (many small members drop below the 30-deck definer floor in an
    81-day window) — but pooling membership largely SURVIVES via assignment (the Cradle family's
    color labels all assigned back into sa-004).
  - **The best behavioral family dissolved**: D&T + Energy + Orzhov (median within-family spread
    0.05 over 10 columns — the tightest measured) split into singletons because their CURRENT
    composition diverged while their behavior did not. Era-honest composition clustering cannot
    see behavioral kinship — that is what the CURATED OVERRIDE layer is for, and the license
    validates it independently. Curation from a measured coherence report is human judgment
    (auditable per key, like `eras confirm`) — the double-dip guard forbids the ALGORITHM reading
    rounds, not the human reading a report.
  - **Curated-override candidates recorded**: ADD white-creature {Death & Taxes, Energy, Orzhov
    Midrange, Orzhov Scam} (justification: the 0.05-spread probe); REVIEW the windowed sa-003
    mega-branch (Dimir family + Doomsday + TES + Grixis Reanimator at BP 0.39) — behaviorally
    implausible; expect the license/gates to refuse most of its pools, and split it by curation
    if they do.

**1. Contribute vs receive.** Pool contributions come from DEFINERS + CURATED members only.
Assignees RECEIVE imputation but never contribute tallies — an assignee with meaningful data would
have been a definer, and this rule makes assignment pollution (Maverick/Elves assigned into
Cradle's cluster today) harmless to the pooled numbers.

**2. Member tallies enter pools only from the member's CURRENT stable era** (entity_eras
stable_since) — never a rebuilt member's pre-disturbance generation. Pairwise validity comes free:
sibling-vs-opponent tallies are drawn from the adaptive multi-split build, whose cells are already
(sibling-era ∩ opponent-era)-windowed with cell_windows/horizon_meta attached.

**3. Pooled/imputed provenance carries freshness.** Window mix + current-regime share of the pool
ride on every pooled/imputed cell; the page's existing not-current muting rules apply to them; a
subject whose family membership churned on the latest run gets a churn flag (labeled, not hidden).

**4. The license is era-windowed and re-earned.** Profile coherence is computed on era-windowed
profiles and recomputed at refresh; the 2026-01-01 probe (LOO MAE 0.075 vs 0.107) is directional
evidence only — Unit 7's harness re-measures on serving windows.

**5. Young-regime rule (hypothesis, decided by measurement).** For a subject whose era just reset
with COMPOSITION attribution (ban/release rebuild), family-current imputation plausibly beats the
existing own-pre-disturbance anchor; where attribution is drift-only, the anchor stays first.
-chain's design must decide the ladder order per attribution kind via a LOO harness over historical
disturbances, not by assertion. This makes era-aware imputation the young-regime serving strategy
the roadmap item asked for.
