---
description: Read when auditing what actually shipped to main across 2026-07-31/08-01 — a fresh-context, adversarial post-merge deep review of the seven shipped features (superarchetype aggregation/chain/clustering, camp-incremental assignment, matchup-plan flex, era-alarm hygiene, multi-split matrix), with confirmed defects at file:line, vacuous-test findings, and implementation-note claims checked against code.
type: review
kind: research
summary: >
  Post-merge deep review of PRs #64-#75 era. Per-feature verdicts, confirmed
  defects with file:line, tests whose assertions do not bite, implementation-note
  claims that failed verification, and cross-cutting seam risks. Findings are
  reported for the orchestrator to file as follow-up items; no reverts.
updated: 2026-08-11
key_findings:
  - The random-effects aggregation estimator matched independent hand calculations, but refused and not-computable cells exposed misleading or incomplete provenance text.
  - The superarchetype local-veto contract was unevaluable for sparse sibling columns and did not surface that limitation to consumers.
  - Several shipped tests were mutation-sensitive, while named weaker assertions and vacuous fixtures required follow-up repair.
  - Cross-feature review found caller-dependent guards and implementation-note claims that needed verification at their consumption seams.
  - Findings were follow-up work for the orchestrator; the review performed no reverts or substrate mutations.
---

# Fresh-context deep review — features shipped 2026-07-31/08-01

Reviewer had no part in authoring any of this code. Code claims carry `file:line`
verified at review time against `main` at `5517e8d`. Card claims quote
`cards.oracle_text` / `cards.type_line` verbatim from a read-only open of
`data/legacy.duckdb`. Findings are follow-ups for the orchestrator to file — this
review performs no reverts and no substrate mutations.

Status legend: **CONFIRMED** = reproduced or read directly at the cited line.
**UNCONFIRMED** = suspicion stated explicitly as unproven.

---

## 1. `epic-superarchetype-layer-aggregation` (PR #72)

**Verdict: APPROVE-WITH-FOLLOWUPS.** The estimator core is correct — I reproduced the
DerSimonian-Laird math by hand and it is the textbook 1986 form. Two confirmed
honesty-surface defects in provenance assembly, one structural blind spot in the local
veto, and one caller-dependent guard that needs the chain review to close.

### Statistical correctness — verified

- **DL formula CONFIRMED correct** (`aggregate.py:174-218`). Hand-computed the headline
  pair (Aluren 4/13, Show and Tell 24/29): y₁=−0.7472/v₁=0.3275, y₂=1.4941/v₂=0.2226,
  Q=9.131, I²=0.8905, τ²=2.2366, n_eff=3.31 — every one matches the code, the brief's
  §6.3 worked example, and the implementation notes (Q≈9.1, I²=0.89, τ²=2.24, n_eff=3.3).
  Continuity-corrected logits, Cochran's Q with fixed-effect weights, DL moment estimator
  with the correct denominator `Σw − Σw²/Σw` (strictly positive for K≥2, as the comment at
  `aggregate.py:207-209` argues), I²=(Q−df)/Q clamped at 0.
- **n_eff construction** (`aggregate.py:239-269`): clamp to `≤ Σn` is unconditional, the
  `pq ≤ 0` branch is genuinely unreachable for finite logits and still named. Prior-strength
  moment match verified: τ²=2.2366, pq=0.2404 → s=0.86, clamps to floor 5 exactly as the
  notes claim.
- **Gate boundaries**: `m_eff == 2.0` passes (tested exactly, `test_aggregate.py:260-265`);
  `top_share == 0.60` fails (tested exactly, `:240-252` — a deliberate, documented deviation
  from the brief's `<= 0.60` wording, safe direction); I² exactly 0.75 → labelled and spread
  exactly 0.25 → refused are documented but **not pinned at the exact boundary** (tests use
  0.80-ish and 0.30). Nit-level gap.

### Confirmed defects

- **CONFIRMED (minor, honesty surface): refused cells carry `served with concentration
  label: …` in provenance** (`aggregate.py:866-870`). The provenance list is assembled
  *before* the refusal branch, so the headline refused cell's provenance reads
  `served with concentration label: dominated by Show and Tell (69% of pooled n)` — on a
  cell that is *refused*, not served. Reproduced at review time. Provenance strings are
  designed to be printed verbatim (audit-echo pattern); a surface printing this would state
  the opposite of the truth. One-line fix: build the concentration provenance line after the
  refusal branch, or word it neutrally (`concentration label: …`).
- **CONFIRMED (important, docstring vs code): a served cell with heterogeneity band
  `not-computable` carries NO honesty label in provenance.** The orchestrator docstring
  (`aggregate.py:790-792`) claims "a concentration failure or a `labelled`/`not-computable`
  band serves WITH its label in `provenance`" — but only `het.note` (populated solely by the
  `labelled` band) and the concentration label are appended (`aggregate.py:866-870`). The
  not-computable reason lives only in `heterogeneity.reason`. Reproduced: a 3-member
  all-tiny pool (n=4/4/4, passing concentration) serves `pooled_p=0.5` with provenance
  containing only the calibration note. The dilution-fixture test
  (`test_aggregate.py:522-543`) does not catch this because both fixtures *also* fail
  concentration, so the `dominated by Tron` line masks the gap. Mitigation: n_eff for such
  pools is tiny (12.0 → speculative tier), so tier gating mutes them downstream — impact
  depends on whether consumers read `heterogeneity.band`/`reason` or only `provenance`
  (resolved in the chain section: chain reads the band field, so this is docstring drift +
  a latent trap for any future provenance-only consumer, not a live wrong number).

### Structural findings (follow-up material, not bounces)

- **The local veto has a structural blind spot** (`aggregate.py:989-1017`, `:1233-1244`):
  `_column_divergence` requires ≥2 contributor siblings at n≥12 to be *evaluable*; below
  that the veto silently cannot fire. Consequences: (a) a single sibling with n≥25 imputes
  a cell with no divergence check possible at all; (b) `[A n=25, B n=11]` imputes even if
  B's rate diverges wildly — B is invisible to the veto. This matches the probe's measured
  floor (the design's own calibration), but the docstring promise "a column with significant
  measured member divergence never imputes, license or not" is conditional on measurability
  in a way no output field names. Follow-up: surface `veto_evaluable: bool` (or a named
  reason string) on granted `ImputedCell`s so the surface can distinguish "checked, agrees"
  from "could not check".
- **The intra-family guard is caller-dependent** (`aggregate.py:1195-1200`): family
  membership is inferred as `{t.archetype for t in sibling_tallies} | {subject}`. If the
  caller omits the opponent-sibling's own tally from `sibling_tallies`, an intra-family
  opponent passes the guard. The kernel cannot do better (it never receives the membership
  list). Verified at the chain call site in section 2 — chain iterates opponents from the
  full matrix axis and passes sibling tallies vs each; whether a family-internal opponent
  can reach `impute_cell` without its own tally present is the load-bearing question there.

### Test quality

99/99 pass in 0.06s, hermetic, no DB. These tests bite:

- The self-caught m_eff vacuity fix is real: `test_m_eff_arm_binds_alone_under_the_share_cap`
  (`test_aggregate.py:267-276`) is the *only* red under `_MEFF_MIN` 2.0→1.5 — verified by
  in-process mutation at review time (1 failed, 98 passed).
- `_SPREAD_FORCE` 0.25→1.1 mutation: exactly 1 red
  (`test_direction_guard_forces_refusal_even_at_low_i2`) — verified at review time, matches
  the implementation-notes table.
- The headline no-leak walk (`test_aggregate.py:500-511`) genuinely walks every dataclass
  leaf and rejects 42, 28/42±0.005, and the "66.7"/"0.667" substrings.
- **One weak property test (not vacuous, but narrower than its name):**
  `test_n_eff_is_non_increasing_in_tau2` (`test_aggregate.py:198-207`) varies τ² via
  `dataclasses.replace` while holding `logit_mean` fixed — it tests the partial derivative
  through the variance term only. In a real refit, τ² and the RE-weighted `logit_mean` move
  together and p̄(1−p̄) can shift the other way. The safe bound (`n_eff ≤ Σn`, separately
  property-tested across 5 fixture families) is what actually protects downstream, so this
  is a labeling nuance, not a hole. Same pattern in
  `test_strength_is_non_increasing_in_tau2_at_fixed_evidence` — there "at fixed evidence"
  is honest about it.

### Claims vs code

- "17 mutations / 0 survivors": spot-checked 2 of 17 by runtime patching (no file edits);
  both match the table's exact red counts and named tests. The remaining 15 are consistent
  with test-reading (traced `_MAX_MEMBER_SHARE`, `_I2_FREE`, `_I2_REFUSE`,
  `_HET_MIN_MEMBER_N`, `_CONTINUITY` to their asserting tests). Credible.
- "99 tests, hermetic, no DB": confirmed (99 passed; only the parity test imports
  `matchup`, which is test-side and deliberate).
- "no NaN/inf escapes any path, walk-asserted": the walk exists and covers 5 aggregate paths
  + 3 impute paths; the `pq ≤ 0` and zero-margin chi² degenerate branches are named. Holds.
- "floor 5 = 1/3 of SHRINK_STRENGTH = 15" recorded check: arithmetic true; the floor remains
  uncalibrated and is marked as such at `aggregate.py:552-555`. Honest.

### Prioritized follow-ups

1. Fix the `served with concentration label` wording on refused cells (one line,
   `aggregate.py:866-870`).
2. Either make the orchestrator append a not-computable provenance line or correct the
   docstring at `aggregate.py:790-792`; add the missing masked-fixture test (tiny pool with
   *passing* concentration).
3. Name veto non-evaluability on granted ImputedCells (structural honesty gap).
4. Nit: pin I²=0.75 and spread=0.25 exact-boundary behavior in tests.

---

## 2. `epic-superarchetype-layer-chain` (PR #74)

**Verdict: APPROVE-WITH-FOLLOWUPS.** The wiring is careful and the byte-identity story
is *stronger* than claimed — I independently proved it below. The concerns are a
partially vacuous diagnostic test, a dead-wired code path with zero coverage, and one
implementation-note number that is already stale (benignly, via PR #75).

### The golden and the 12-sig-fig re-pin — VERIFIED, cannot mask a regression

The specific worry (sha re-pinned with float rounding after arm64/x86_64 ulp drift,
commit `3a3845b` landing *after* the builder mutations) is discharged:

- Reproduced the **original full-precision canonicalization** (pre-`3a3845b`) against
  today's post-mutation code on this arm64 machine: sha =
  `ea63df1c…673bc66` — **exactly the original pre-mutation pin** captured at `bfc7f4f`
  on the untouched builder. The off path is therefore *bit-identical* through every
  chain mutation at full precision; the re-pin laundered nothing.
- The 12-sig-fig `_stable()` (`test_matchup_superarchetype_golden.py:73-81`) can only
  mask changes below 1e-12 relative — i.e. reordered-but-equivalent arithmetic, which is
  precisely the ulp class it exists to tolerate. Ints, strings (labels, windows,
  audit lines), and structure are hashed exactly; NaN would stringify to `"nan"` and
  break the sha. No real regression class fits under the rounding.

### Chain wiring — verified correct

- **LOO exclusion excludes what it names** (`chain.py:273-275` member exclusion in
  `draw_pool_tallies`; `chain.py:377-389` leave-S-out + leave-O-out + self-pair skip in
  `draw_cluster_pair_tallies`). Tested with fixtures that would fail if the excluded
  tally leaked (`test_chain.py:181-189`, `:279-307` — the `("B","P"): (9,9)` poison pill
  is real).
- **Intra-cluster flag at the boundary**: subject==member injects the mirror
  (estimator excludes it from the rate, reports `mirror_n` — `chain.py:276-281`); camp
  subjects never inject (the `(camp, own_parent)` pair is structurally absent —
  verified against `_pool_opponent_tallies` at `matchup.py:489-490`).
- **The aggregate kernel's weak intra-family guard is properly backed**: the builder
  pre-filters intra-family imputation targets at the *membership* level
  (`matchup.py:1144-1147`, `view.cluster_of.get(opponent) == gs_id` → named skip), so
  the kernel's name-inference guard (section 1 finding) never has to carry the load in
  the shipped path. Camp-subject leave-subject-out is handled at draw time
  (`chain.py:442`), closing the hole the kernel could not see.
- **Ladder closed vocabulary fails fast** (`chain.py:606`, `:631-635`; tested
  `test_chain.py:514-519`).
- **No pooled/imputed leak into `multi.cells`**: overlay maps are assembled after cell
  construction and never written back (`matchup.py:1267-1315`). The only sanctioned
  touch is the prior rung changing `p_shrunk` with a labeled `prior_source`, and
  `test_only_rung_labeled_cells_changed` (`test_matchup_superarchetype.py:221-232`)
  pins changed-set == rung-labeled-set; `test_engaged_cells_change_only_the_prior_fields`
  pins that wins/n/p_raw/CI/tier/display never move.
- **Regime-start bucket guarantee** (`_regime_n`'s `pooled_by_since[regime_start]`
  KeyError risk) is discharged at `matchup.py:1122-1128` — the builder scans the bucket
  when absent. Holds only for the builder path; a direct kernel caller could KeyError
  (documented assumption, acceptable).
- **`not-computable` is not a pass for priors** (`chain.py:68-71`, `_admissible` at
  `:522-529`; tested `test_chain.py:397-411`). Display ladder deliberately admits
  served-with-label pools (concentration-failed or not-computable band) as
  `kind="pooled"` — labels ride only on the `PooledCell` in `cluster_cells`, not on the
  ladder token (`chain.py:692-706`). **Handoff requirement for `-best-call-fallback`:
  the renderer must read `concentration.label` / `heterogeneity.band` off the map, or
  the honesty labels vanish at the surface.** This interlocks with section 1's
  provenance-gap finding.

### Confirmed weak tests

- **CONFIRMED (vacuous float pins): the representative-cell "readable diff" tests
  self-compare their float fields** (`test_matchup_superarchetype_golden.py:111-117`:
  `"p_shrunk": got["p_shrunk"]`, same for `ci_low`/`ci_high`/`prior_mean`). The
  docstring promises "pinned field-for-field so a golden break is diagnosable without
  decoding a hash" — but if the sha breaks because a float moved, these tests stay green
  and diagnose nothing. Pin the floats with `pytest.approx(..., abs=1e-9)` instead.
- **Zero coverage on the family-first override branch** (`matchup.py:1244-1257`):
  `FAMILY_FIRST_KINDS = frozenset()` makes the branch dead today, and the only test is
  `assert FAMILY_FIRST_KINDS == frozenset()` (`test_chain.py:414-419`). The impl notes
  sell "a future re-measure is a one-line recalibration" — but that one line would
  activate ~14 lines of never-executed prior-substitution logic in the hottest builder
  loop. Follow-up: one test that monkeypatches `FAMILY_FIRST_KINDS` and exercises the
  branch on the hero corpus.

### Claims vs code (real corpus, re-run read-only at review time)

- "144 rung-labeled cells, changed-set == rung-labeled set": **144 reproduced exactly**
  (serving registry, staged parents, `min_row_share=0.001`).
- "557 granted imputations (all from sa-003, the only family clearing the license)":
  **now 573, from sa-003 AND sac-001** (ladder: none 15938 / imputed 573 / pooled 126 vs
  the recorded 15956/557/124). Not a defect — PR #75's curated `sac-001` family landed
  *after* the spot check and now clears the license too, which is the layer working as
  designed. But the implementation note reads as a standing property ("the only family
  clearing the license") and is already false; anything downstream calibrated against
  "557/sa-003-only" is calibrated against a stale world.
- "Stale-taxonomy audit fires": **reproduced** — `⚠ registry window 2026-05-11 predates
  the current regime start 2026-06-29` is live on today's corpus. This is a real open
  operational item: the serving registry needs a `superarchetype run --since 2026-06-29`
  regeneration.
- LOO harness verdict (anchor-first, all kinds thin): not re-run (script-verifiable via
  `scripts/loo_ladder_harness.py`); the measured MAEs are recorded at the
  `FAMILY_FIRST_KINDS` definition site with floors preregistered — methodologically
  honest, thin-kind fallback named. UNVERIFIED-AS-WRITTEN but reproducible by one
  command.

### Nits

- `matchup.py:1035-1036` docstring: "``None`` or an empty registry is BYTE-IDENTICAL" —
  an empty registry adds the `// superarchetype: registry empty — layer off` audit line
  (its own test proves the difference at `test_matchup_superarchetype.py:179-181`).
  Cells are identical; the docstring overstates.
- `imputed_cells[(camp_label, O)].subject` holds the *base* archetype
  (`matchup.py:1153-1154` passes `base` to `impute_cell`), so key and field disagree for
  camp subjects. Deliberate (family evidence is parent-level) but undocumented.
- Window-mix note semantics differ between `draw_pool_tallies` (counts members) and
  `draw_cluster_pair_tallies` (counts non-empty member×opponent pairs) —
  `chain.py:296-298` vs `:404-406`. Cosmetic.

### Prioritized follow-ups

1. Regenerate the serving registry for the current regime (the live `⚠ stale taxonomy`
   audit line) — operational, affects everything downstream of the layer.
2. Real float pins in the representative-cell golden tests.
3. Coverage for the family-first override branch before any recalibration flips it on.
4. Correct the "557/sa-003-only" implementation note or timestamp it as superseded by
   PR #75 (sac-001 licensed).

---

## 3. `epic-superarchetype-layer-clustering` (PR #69)

**Verdict: APPROVE** (nits only). The taxonomy foundation is the strongest of the seven
deliverables: the statistics match the cited method, the honesty tripwires are real and
fire-proofed, and the boundary behavior is pinned inclusively where the spec says
inclusive.

### Statistical correctness — verified

- **The pvclust AU port is faithful** (`cluster.py:306-336`). Checked the coefficient
  mapping by hand: the code fits `psi(r) = v/√r + d·√r` (X rows `[1/√r, √r]`) and returns
  `AU = 1 − Φ(d − v)`; pvclust fits `z = v_pv·√τ + c_pv/√τ` with `AU = 1 − Φ(v_pv − c_pv)`
  — so code-`d` ≡ pvclust-`v` and code-`v` ≡ pvclust-`c`, and the composition is exactly
  pvclust's. The WLS weights `n_boot·φ(ψ)²/(p(1−p))` (`cluster.py:326`) match pvclust's
  msfit variance weights.
- **The two sourcing caveats the epic ordered discharged are discharged in code**
  (`cluster.py:24-33`): (a) feature-axis resampling is argued as pvclust's own axis
  (rows = the non-clustered axis); (b) the no-multiplicity-correction admission ships as a
  *persisted reason string* (`_NO_MULTIPLICITY_CORRECTION_NOTE`, `cluster.py:118-121`,
  appended in `select_supported_clusters` and tested at `test_cluster.py:174-179`), not
  just prose.
- **Two project additions beyond the brief, both defensible and flagged**:
  `_AU_MIN_BP = 0.30` (`cluster.py:91-99` — blocks the AU-extrapolation-without-evidence
  mega-cluster failure, with the measured BP-flatness rationale at the definition site,
  vetoing tested at `test_cluster.py:181-192`) and `_MIN_FIT_POINTS = 3`
  (`cluster.py:297-303` — mean-BP fallback, conservative direction, with the AU-0.70
  incident that motivated it recorded). Both CLI-exposed.
- **Boundary behavior pinned inclusively**: core inclusion at exactly 0.50 is core
  (`test_cluster.py:22-30`); definer floors at exactly 30 decks / 8 cards
  (`test_cluster.py:33-43`); the AU cut strictly `>` (`cluster.py:89`, documented). Staple
  fraction at exactly 0.30 is documented `>=` (`cluster.py:200-209`) but not pinned by an
  exact-boundary test — nit.

### The no-rounds guarantee — real, and fire-proofed

`test_no_rounds.py` is the best test file in the arc: a tokenize-based source tripwire
over *executable* source (comments/docstrings/f-strings stripped) for
`rounds|match_results|wins|losses|winrate`, PLUS a runtime SQL spy over a full
`run_superarchetypes` pass against a corpus **with a populated `rounds` table**, PLUS
structural checks that no dataclass in the package exposes an outcome field. Critically,
both tripwires have meta-tests proving they would fire
(`test_no_rounds.py:140-144`, `:182-190`) — the vacuous-test failure mode this week's
history warns about is explicitly defended against here.

### Registry / curated merge — correct

- Curated-wins-by-key with the replaced derived assignment recorded on each member note
  (`registry.py:283-294`); emptied derived clusters dropped with a reason (`:305-311`);
  curated-claimed archetypes removed from `unassigned` (`:318-322`).
- Identity matching is greedy max-overlap, deterministic tie-break, curated ids never
  remapped, retirements named (`registry.py:354-432`); churn declines to fabricate
  agreement below 2 shared archetypes (`:462-467`).
- The fixture corpus is deliberately non-degenerate: the conftest documents *why* eight
  definers and weak cross-family links are needed (a perfectly symmetric fixture makes
  spurious upper-tree nodes score BP=1.0 — an artifact the authors caught themselves,
  `tests/analytics/superarchetype/conftest.py:44-52`).
- 202/202 package tests pass in 1.3s at review time.

### Nits (no follow-up items required, fold into any future touch)

- Staple fraction exact-boundary (0.30) untested.
- A derived cluster's label is built from its definers (`_label_for`,
  `cluster.py:514-515`); if a curated entry later pulls a definer out, the surviving
  cluster keeps the stale label naming the removed member. Cosmetic, self-heals on the
  next derivation.
- `bp_at_unit_scale` silently falls back to the middle scale when 1.0 is absent from a
  custom `--scales` (`cluster.py:384`) — only reachable via explicit flags.

---

## 4. `feature-camp-incremental-assignment` (PR #66)

**Verdict: APPROVE-WITH-FOLLOWUPS** (the follow-ups are largely ones the feature already
names about itself). The headline claim survives independent reproduction.

### The 98.65% claim — REPRODUCED EXACTLY

The measurement harness was not committed, so I rebuilt it from the implementation
notes' description (30 staged splits, pools from each record's `params.since`, centroids
re-derived from `member_keys` + current `deck_cards`, nearest-centroid recovery) and ran
it read-only against `data/legacy.duckdb`:

- **Overall: 20,844 / 21,130 = 98.6465%** — matches "98.65% — 20,844 / 21,130" exactly.
- Worst three: Lands 92.1% (n=1133), Jeskai Midrange 92.4% (n=567), Grixis Midrange
  94.7% (n=398) — all three match the notes verbatim; every split clears the 90% bar.

The riskiest architectural assumption (raw L2-normalized cosine as a proxy for the
TF-IDF+SVD space) is genuinely validated, not just asserted. The hermetic regression
floor (`TestReconstructionAccuracy`, `tests/analytics/test_discovery.py:658-701`)
includes the harder shared-staples three-camp case flagged in Risks.

### Code verified

- `project_flex_vector` / `camp_centroid` / `nearest_camp`
  (`analytics/discovery.py:150-261`): shared projection function on both sides (the
  invariant the design demands), all-zero-vector decline with a named reason,
  deterministic tie-break by name, centroid-dimension mismatch fails fast as corrupt
  state. Boundary: similarity exactly at `min_similarity` assigns (`<` declines) —
  consistent with the reason strings.
- `assign_incremental` (`archetype/discovered.py:404-543`): supersession clears all prior
  incremental rows for the parent, resets `decks.variant` to NULL only for decks the
  current generation's `member_keys` does not claim, then reassigns fresh. Both
  supersession branches, parent-scoping of the sweep, and the closed-vocabulary
  refusal (`assigned_by` outside `{'incremental'}` → ValueError, placed at the actual
  trust boundary — reading rows back — rather than ceremonially at the write site) are
  all tested and bite (`tests/archetype/test_discovered.py:744-835`).
- The single-query candidate read + pure decision loop deviation is faithful to
  objective-search-split and semantically identical to the design's per-deck reads.

### Findings (minor)

- **The real-corpus calibration harness is not committed.** The 98.65% figure was
  reproducible only by reimplementing the harness from prose. The chain feature set the
  right precedent (`scripts/loo_ladder_harness.py` committed, one-command reproduce);
  this feature's equivalent ~30-line script should exist too, since the planned
  `min_similarity` calibration pass will need exactly it. Follow-up.
- **Supersession correctness depends on CLI call order** (`apply_split` before
  `assign_incremental`) — documented in the docstring, enforced only by the CLI wiring.
  A direct API caller inverting the order can leave a previously-incremental deck
  carrying its old camp label while claimed by new `member_keys`. Nit (documented
  assumption).
- **Partially-populated centroids** (some camps carrying `centroid`, others not — only
  reachable by hand-editing staged JSON) proceed against the subset rather than
  degrading; a candidate genuinely nearest the centroid-less camp would be scored only
  against the others. Nit; the all-or-nothing degrade check
  (`archetype/discovered.py:478-488`) covers the realistic pre-feature-record case.
- `DEFAULT_MIN_SIMILARITY = 0.35` remains uncalibrated — the feature says so itself at
  the definition site and in its follow-ups; the decline-rate observations (0-23 per
  split) are recorded as the calibration input. Honest, still open.

---

## 5. `epic-sb-advisor-correctness-matchup-plan-flex` (PR #68)

**Verdict: APPROVE-WITH-FOLLOWUPS** (one real gap, low severity). The corpus-grounded
design work here is exactly right, and I re-verified every card claim against the live DB.

### Card claims re-verified verbatim (read-only `data/legacy.duckdb`)

- `Sink into Stupor`: `type_line = 'Instant'`, `is_land = TRUE` — the row that decides the
  test; the `is_land` column would have made it un-sideboardable. CONFIRMED.
- `Dryad Arbor`: `'Land Creature — Forest Dryad'`; `Westvale Abbey`: `'Land'`;
  `Scalding Tarn`: `'Land'`; `Boggart Trawler`: `'Creature — Goblin'` / `is_land = TRUE`;
  `Ojer Pakpatiq, Deepest Epoch`: `'Legendary Creature — God'` / `is_land = FALSE`. All
  match the feature file's table exactly.
- **The `ILIKE '%land%'` substring risk is empirically zero on this corpus**: I queried
  for any `type_line` matching the pattern without containing the literal type word `Land`
  — zero rows across all 39k cards. (It remains a substring test, not a word-boundary
  test; no current MTG type word contains "land" as a fragment, so this is a
  future-vocabulary nit, not a defect.)

### Code verified

- `_in_axis_verdict` (`sideboard.py:2665-2691`): branch order matches the design exactly
  (opponent-unknown → card-unknown → on-axis → `_hate` field-wide → off-axis); never
  promotes, only declines; absence-of-evidence never suppresses.
- Structural flex pool computed once, before the opponent loop, on eligibility alone
  (`sideboard.py:2832-2843`) — this is what makes `no-legal-flex` (degrade) genuinely
  distinguishable from `no-dead-cards` (a real answer), fixing the old both-causes `or`
  note. The no-flex note names locked-core count + land count + declined-with-signal cards
  (`:2929-2960`).
- `out_suppressed` records only signal-bearing declines (gate + negative lift read before
  eligibility, `:2874-2893`) — the design's "never the whole locked core" rule holds.
- 28 flex tests + 474 total sideboard tests green at review time.

### Test integrity — the self-caught vacuity is fixed properly

The implementation notes disclose that the first-pass integration tests were a "green
lie" (looping over zero plans from an all-land fixture — one of the four vacuous-test
families this week). The replacements assert `pkg.matchup_plans` non-empty first and use
a monkeypatch spy to prove the wiring actually passes `land_names`/`opponent_axes`/
`card_axes`. This is the correct fix shape, and the disclosure itself is the right
culture.

### Confirmed gap (the one real follow-up)

- **A `_resolve_land_names` DB failure silently resurrects the land-cut bug**
  (`sideboard.py:2659-2661`): any exception returns `frozenset()` at `log.debug` level,
  which re-enables exactly the pre-feature behavior (land cuts proposed) with **no trace
  in any plan note or audit line**. Compare the locked-core failure path, which sets
  `lock_note` and surfaces it (`:2822-2825`). The honest-degrade pattern requires the
  degrade to be *named on the output surface*; a debug log is not that. Low likelihood
  (same `con` everything else uses), but the failure mode is the feature's own headline
  bug returning invisibly. Follow-up: thread a `land-exemption-unavailable` note into the
  plans when resolution fails, mirroring `lock_note`.

### Known limitation, correctly scoped

The `no-legal-flex` path cannot be reached end-to-end through `recommend_sideboard` on
the existing hermetic fixture (an all-land maindeck never reaches the planner). Covered
at the `_plan_matchups` level; the corpus-shaped fixture belongs to the backtest-ci-gate
feature. Reasonable and recorded.

---

## 6. `feature-era-alarm-hygiene` (PR #64)

**Verdict: APPROVE** (nits only; the feature's own risk register already names the real
residual risks honestly).

### Verified

- **The tier-ordering crux is implemented exactly as designed**
  (`attribution.py:119-149`): verified-and-affecting (by inclusion desc) > unverifiable
  (`None` — unproven, not disproven) > verified-below-threshold. This ordering is what
  makes the Tron/Candelabra case survive sharing a date with any other ban, and it is
  pinned by dedicated tests. The Nadu/Entomb fix (Finding B) follows directly: 91%
  verified beats unverifiable alphabetical-first.
- `is_plausible_ban` (`attribution.py:86-95`) is genuinely shared by both call sites
  (attribution decision + alarm wording) — the design's "can never quietly disagree"
  claim holds structurally.
- `events_on_nearest_date` (`attribution.py:98-116`): single-closest-date cohort,
  earliest-date tie-break, `None` outside tolerance — matches the deliberate "same-date,
  not same-window" narrowing recorded in the design.
- **The chain seam (`attribution_kind`, PR #74) is clean**: `consume.py:100-174` derives
  `EraHorizon.attribution_kind` from the *winning boundary's stored attribution* —
  vocabulary `{ban, release, unattributed}` — while era-alarm's `AlarmFlag.kind`
  (`{unattributed, registered_pending}`) is deliberately NOT persisted and never reaches
  `attribution_kind`. The two "kind" vocabularies share the token `unattributed` but never
  the same field. `chain.FAMILY_FIRST_KINDS ⊆ {ban, release, unattributed}` keys off the
  right one.
- The "no changes needed to cli.py/store.py/window.py/consume.py" claim was verified by
  the implementer with cited line numbers *and* holds at review time (all four sites
  interpolate `alarm_note`/`h.alarm` as plain strings).
- 178 tests across `tests/analytics/eras/` + `tests/test_cli_eras.py` green at review
  time.

### Nits / known residuals (all named by the feature itself — no new findings)

- The peak-date anchor (argmax over the last 3 weekly buckets) is validated against one
  real shape (sharp cliff); a slow multi-week decline could miss the ledger lookup. The
  failure mode is graceful (keeps the old wording).
- `BAN_AFFECT_THRESHOLD = 0.25` doubles as the alarm-wording bar without separate
  dogfooding; split-constant fallback recorded.
- `AlarmFlag.kind`/`card` not persisted (deliberate Option-3 scope cut) — any future
  stored-run consumer of "which entities are registered_pending" needs a DDL follow-up.
- The ubiquitous-card permissiveness (an entity that runs the banned card 0% still reads
  `registered_pending`) is pre-existing `_card_inclusion_before` semantics, correctly
  flagged as not-new-scope.

---

## 7. `feature-multi-split-matrix` (PRs #65/#70/#73) — spot-check

**Verdict: APPROVE (spot-check depth).** Not a full review — the budget went to the
estimator stack per the priority order — but the load-bearing surfaces were read in the
course of the chain review and the test discipline was checked directly.

- The pooling/hierarchy kernels (`_pool_opponent_tallies`, `_multi_split_inclusion`,
  `_multi_hierarchy_inputs`, `matchup.py:465-606`) were read line-by-line as chain
  prerequisites: the camp-partition exactness argument, the LCO non-negativity asserts
  (never clamped), and the deliberately-absent `(camp, own_parent)` cell are all coherent
  and documented at the definition sites.
- **The full-precision golden identity proof in section 2 transitively validates this
  feature's parity corpus**: the adaptive multi-split build over the shared fixture is
  bit-stable through the superarchetype mutations.
- The one-pass story (`feature-multi-split-matrix-best-call-onepass`) shows the corrected
  mutation discipline post-trap: **symbol-anchored, one-sided** (`subj_ban=p_ban -> None`
  at one call site), with the exact red set named (3 parity parametrizations + the Nadu
  pin, window flips BA→FC / n 15→30) — the text-substitution-patches-both-sides failure
  mode this week's history recorded is explicitly not repeated here.
- Its two design-judgment deviations (ranking on page-used cells instead of the literal
  `ranking_view()`; candidacy gated at the 5% coverage threshold) are empirically
  motivated, logged with the observed failure they prevent (100% of P(best) mass on
  suppressed rows), and carry named degrade output (`p_best=None` + `s_cov`).
- 99 tests across the three suites green at review time.
- Not verified: the recorded real-corpus top-row P(best) numbers (0.274/0.226/0.208…) —
  timestamped snapshot values, reproducible via the committed
  `scripts/refresh_best_call_ranking.py`; not re-run under this review's budget.

---

## Cross-cutting

### 1. The serving registry is stale — the single highest-priority follow-up

Reproduced live at review time: the serving superarchetype registry (window 2026-05-11)
predates the current regime start 2026-06-29, and every adaptive build with the registry
now emits `// superarchetype: ⚠ registry window 2026-05-11 predates the current regime
start 2026-06-29 — stale taxonomy (window mismatch)`. The audit machinery is doing its
job; the operational action (`superarchetype run --since 2026-06-29`, then re-check the
license/imputation landscape) has not happened. Everything the layer serves — 144 rung
priors, 573 imputations, 124+ pooled ladder entries — currently rides a taxonomy derived
over a mixed-regime window.

### 2. PR #75 (`sac-001`) invalidated chain's recorded landscape — benignly, but silently

The chain implementation notes assert "557 granted imputations (all from sa-003, the only
family clearing the license)". At review time it is 573 across sa-003 AND sac-001 — the
curated white-creature family that merged *after* the spot check. The code handled the new
curated family correctly with zero changes (curated members are contributors, the license
was earned) — the seam works. But the notes' "the only family" phrasing reads as a
standing property and is already false; nothing in the repo marks it superseded. Pattern
risk: real-corpus snapshots in implementation notes need timestamps/config stamps or they
silently rot into false claims.

### 3. The honesty-label handoff to `-best-call-fallback` is the compounding risk

Three findings interlock into one seam requirement for the unshipped renderer:

- refused PooledCells carry a misleading `served with concentration label:` provenance
  line (section 1);
- served not-computable cells carry NO heterogeneity label in provenance at all
  (section 1);
- the display ladder admits concentration-failed / not-computable pools as
  `kind="pooled"` with a token that carries n_eff/tier but no honesty label (section 2).

Individually each is minor because `heterogeneity.band`/`reason` and
`concentration.label` ride the typed objects. But a renderer that consumes only
`provenance` strings and ladder tokens — the path of least resistance — would print
refused cells as "served" and serve unverifiable pools with no caveat. **The fix belongs
in aggregate.py (make provenance truthful and complete) before the renderer ships, not in
renderer discipline.**

### 4. Windowed-registry consumption is defended

The task flagged "check nothing assumes the full-corpus taxonomy shape". Verified: chain
warns loudly on `window_since is None` (full-corpus = exploratory) and on window-predates-
regime; the kernel takes membership as data, never re-derives; camp labels resolve through
the explicit `camp_parent` map, never prefix parsing. No full-corpus assumptions found.

### 5. Vacuous/weak test tally (surviving, post the four self-caught families)

| # | Location | What fails to bite |
|---|---|---|
| 1 | `tests/test_matchup_superarchetype_golden.py:111-117` | Representative-cell test self-compares `p_shrunk`/`ci_low`/`ci_high`/`prior_mean` (`"p_shrunk": got["p_shrunk"]`) — the advertised readable-diff fallback covers no float field. |
| 2 | `tests/analytics/superarchetype/test_aggregate.py:198-207` | `test_n_eff_is_non_increasing_in_tau2` holds `logit_mean` fixed via `dataclasses.replace` — tests the partial derivative, not the joint property its name claims. Safe bound covered elsewhere. |
| 3 | `tests/analytics/superarchetype/test_aggregate.py:522-543` | Dilution fixtures assert the concentration label in provenance, but both fixtures also fail concentration — masking that a not-computable band alone leaves provenance empty (the docstring-claimed label is never emitted). |
| 4 | `matchup.py:1244-1257` | Not a vacuous test but a zero-coverage branch: the family-first override is dead (`FAMILY_FIRST_KINDS == frozenset()`) and its only test asserts the set is empty. |

Zero *fully* vacuous load-bearing tests found beyond these — notably, the four
families self-caught during the week (zero-plan fixture loop, empty-pool both-arms,
both-sides parity mutation, m_eff/cap dependence) were all genuinely fixed, and two of
the fixes (flex integration spies, symbol-anchored one-sided mutation) are now the best
tests in their files.

### 6. Implementation-note claim verification summary

| Claim | Result |
|---|---|
| Aggregation: 17 mutations / 0 survivors | Spot-checked 2/17 by runtime patch — exact match (1 red each, named tests); rest traced by reading. CREDIBLE |
| Aggregation: headline math (Q 9.1 / I² 0.89 / τ² 2.24 / n_eff 3.3 / s 0.86) | Hand-computed. CONFIRMED |
| Chain: off-path byte-identity | CONFIRMED beyond the claim — current code reproduces the ORIGINAL full-precision pre-mutation sha |
| Chain: 144 rung-labeled cells | Re-run on real corpus. CONFIRMED exactly |
| Chain: 557 imputations, sa-003 only | STALE — now 573 across sa-003 + sac-001 (PR #75). Was true at its timestamp |
| Chain: LOO harness MAEs / anchor-first | Not re-run; reproducible via committed script. UNVERIFIED-AS-WRITTEN |
| Camp: 98.65% (20,844/21,130), worst Lands 92.1% | Rebuilt the uncommitted harness, re-ran read-only. CONFIRMED to 4 decimal places |
| Flex: corpus card rows (Sink into Stupor et al.) | All six re-queried verbatim. CONFIRMED; ILIKE substring risk empirically zero corpus-wide |
| Era-alarm: "no consumer changes needed" | Re-verified at review time. CONFIRMED |
| One-pass: P(best) top rows | Snapshot values, script committed. UNVERIFIED (budget) |

### 7. Consolidated priority follow-ups

1. **Regenerate the serving superarchetype registry for the current regime** (live ⚠ on
   every build; everything downstream rides it).
2. **Fix aggregate.py provenance truthfulness** (refused-cell "served with" wording +
   missing not-computable label) before `-best-call-fallback` renders anything.
3. Real float pins in the golden's representative-cell tests; coverage for the
   family-first branch.
4. Surface `_resolve_land_names` failure as a named degrade on plan output (silent
   resurrection of the land-cut bug).
5. Name veto non-evaluability on granted ImputedCells (imputation's structural blind
   spot below 2 siblings at n≥12).
6. Commit the camp reconstruction-accuracy harness; timestamp/config-stamp real-corpus
   snapshots in implementation notes (the 557 lesson).
