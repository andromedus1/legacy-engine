---
id: epic-stable-era-windows
kind: epic
stage: implementing
tags: [analytics, methodology, ingestion]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Per-entity stable-era detection → maximal solid windows everywhere

## Brief

**Andrew's framing (2026-07-11, verbatim intent):** when we look for deck matchups, look across
card-release and ban notices to identify STABLE ERAS per archetype and subarchetype — grab the
longest-running package of data that's in the entity's CURRENT era, where "current era" is a
per-archetype-and-subarchetype definition. Need a way to assess whether an archetype was DISTURBED:
play-rate shifts, win-rate shifts, cards directly removed by ban, cards suddenly appearing via
release. It's like the subarchetype clustering, but subarchetypes OVER TIME — and matchup
comparisons then use this to grab the biggest possible window of solid data.

**Why this is the right generalization (unifies four open threads, three of them absorbed here):**
- `build_adaptive_matrix` already does per-archetype windows but ONLY from ban-affectedness
  (`valid_since`) — it is blind to RELEASE-driven disturbance (Flow State rebuilt Doomsday/Izzet/
  Dimir with no ban; the 07-11 era audit showed camps ARE list generations).
- The era-cluster confound (absorbed idea-discovery-temporal-gate): clustering an 18-month pool lets
  new-card signatures date-stamp clusters — 27/46 ranked camps were TIME clusters, and
  best-build-ranking.html is a historical lens. Detect each entity's change-points FIRST, then
  discover camps within stable windows (camps over time = the change-points).
- The banlist announcement lag (absorbed bug-banlist-regime-gap): the regime table ended 2026-05-18
  and missed the 2026-06-29 Candelabra of Tawnos ban; the corpus fingerprint was unmistakable
  (Tron 59/wk → 1). Per-entity disturbance detection from the CORPUS ITSELF catches what
  announcement feeds miss, automatically.
- Thin post-disturbance cells (absorbed idea-hierarchical-cell-shrinkage): the short windows this
  epic creates need a better prior than flat 0.5 — hierarchical shrinkage supplies it.

## Strategic decisions (locked at scope, 2026-07-11)

- **bug-banlist-regime-gap: absorbed entirely.** No standalone registration fix; the epic's
  corpus-fingerprint detection layer supersedes manual regime registration, and the Candelabra ban
  (Tron collapse fingerprint, ~2 days post-ban data) is the epic's first ground-truth validation
  case. Regime-table currency (rules pin refresh / `seed banlist` flow) is handled inside the epic.
- **idea-hierarchical-cell-shrinkage: absorbed as a child feature.** One epic owns both: era windows
  create the thin-cell problem, hierarchical priors solve it, consumers eat ONE all-cells-shift
  rollout instead of two. Full scope: camp cell → leave-camp-out parent cell → marginal → 0.5 chain
  per the two-level-empirical-bayes pattern, PLUS the cross-era prior (a new-era cell shrinks toward
  its own pre-disturbance value, labeled). Design must resolve double-counting (leave-camp-out
  parent estimates) and consumer impact.
- **stable_since is the NEW DEFAULT horizon, honest degrade.** Replaces `valid_since` as the
  adaptive-matrix horizon everywhere; every cell carries its detected window + named trigger
  ("window since 2026-06-20: Flow State adoption jump"); falls back to current ban-only behavior
  when detection is thin or uncertain. Self-healing banlist lag only works if it's the default path.
- **Scope reach: ALL regime-windowed surfaces.** Replace the advisory-window-resolution block
  (~15 call sites) AND the `_latest_regime_window` consensus/card-frequency family with per-entity
  era resolution — consensus decklists, card-frequency reports, and discovery gain stable-era
  windowing too (eliminates the 07-11 hand-windowing of consensus to current camps). Discovery
  gains the temporal gate / stable-window default. Field composition semantics (global field windows
  to the current global regime per analysis-statistical-context-gates) must be reconciled in
  epic-design: the field is a cross-entity distribution and may keep a global-era definition derived
  from the union of per-entity disturbances.

## Design decisions

Locked with Andrew via `--only-questions` (2026-07-11). Child feature designs treat these as
fixed inputs — do not re-ask.

- **Shrinkage rollout — one shot, both default together**: hierarchical cell shrinkage
  (camp → leave-camp-out parent → marginal → 0.5, plus the cross-era prior) becomes the default in
  the SAME release as stable_since windows. Consumers eat one all-cells-shift event; goldens
  re-pinned once; triple-display (shrunk%|raw% n=) carries the change.
- **Field window — global, detection-derived**: keep ONE global field-composition window (the
  analysis-gates convention), but the "current era" boundary is derived from the detection layer —
  a confirmed high-share disturbance opens a new global field era automatically instead of waiting
  on BAN_EVENTS. Field comp self-heals the same way cells do.
- **Self-heal gate — auto-truncate, labeled**: a disturbance that clears the calibrated statistical
  bar (FDR-corrected, min-segment floor) truncates windows immediately, even when unattributed;
  affected cells carry "window since <date>: unattributed disturbance — possible unregistered B&R
  change". Human confirmation later upgrades the label and updates BAN_EVENTS; it never gates the
  truncation.

## Disturbance signals to detect (change-point detection on per-entity weekly series)

1. composition drift: distance between adjacent windows' consensus vectors / card-inclusion
   distributions (the same flex-band representation discovery already builds) — a jump = new era;
2. cards vanishing (ban: presence → 0 overnight) and cards appearing (release: 0 → adopted);
3. play-rate share shifts (Tron 59/wk → 1) and win-rate shifts (regime-scoped marginals);
4. cross-check against known ban/release dates (labels for detected change-points, not the source
   of truth) — and the inverse: a detected cliff with no known announcement should prompt a
   banlist-currency check (the absorbed drift-alarm idea), honest-degrading the windowing until
   confirmed.

## Consumption

`stable_since(entity) = last change-point`; matchup cells source over
`[max(stable_since(a), stable_since(b)), now]` — the adaptive-matrix mechanism with a better
horizon function. Honesty: every cell carries its detected window + the triggering disturbance;
thin post-disturbance windows degrade honestly (hierarchical prior + labels) rather than silently
pooling across a break.

## Decomposition

Split by capability layer along the data flow: detect → persist/attribute → consume, with the two
independent consumers (windowed surfaces; discovery gating) parallel after the ledger, and the
prior change last so goldens re-pin once at the end. Alternative shapes rejected: splitting
detection by signal type (S1-S4 share the series builders and the ensemble/FDR machinery —
tightly coupled); merging consumption+shrinkage into one giant feature (each is a full
feature-design pass on its own; the one-shot constraint is a RELEASE property, enforced by
late-binding, not a PR property).

### Child features

- `epic-stable-era-windows-detection` — signal-typed detection engine + ledger-calibrated
  operating point (pure analytics; ruptures dep) — depends on: `[]`
- `epic-stable-era-windows-era-ledger` — persistence, attribution, drift alarm,
  explain/report CLI, BAN_EVENTS confirmation loop (Candelabra registration) — depends on:
  `[epic-stable-era-windows-detection]`
- `epic-stable-era-windows-consumption` — stable_since default horizon: adaptive matrix +
  advisory-window block (~15 sites) + consensus family + detection-derived global field —
  depends on: `[epic-stable-era-windows-era-ledger]`
- `epic-stable-era-windows-discovery-gate` — discovery stable-window default + temporal Gate C +
  %current/median-date in report — depends on: `[epic-stable-era-windows-era-ledger]`
- `epic-stable-era-windows-shrinkage` — hierarchical (leave-camp-out parent-anchored) + cross-era
  priors as the default cell estimate — depends on: `[epic-stable-era-windows-consumption]`

### Decomposition risks

- **Serial critical path** detection → ledger → consumption → shrinkage (only discovery-gate
  parallelizes). Accepted: consumers genuinely need persisted boundaries; do not stub.
- **Golden churn**: consumption re-pins CLI-body goldens, shrinkage re-pins them again in-tree.
  Accepted — the one-shot constraint binds the RELEASE, not individual PRs; release-deploy binds
  all five features to one version so users see a single shift.
- **Riskiest feature is detection** (method calibration). Mitigated: the attested brief locks the
  method families, and the calibration harness against the labeled ledger (Candelabra, Flow
  State, non-events) is in the feature's scope — a mis-calibrated detector fails its own pinned
  fixtures, not dogfooding.
- **Field-window semantics** (detection-derived global era) touches positioning outputs used in
  standing analyses; the audit header must make the field window's derivation visible so venue/
  era comparisons stay interpretable.

## Absorbed items (full context preserved above; original bodies in git history)

- `idea-discovery-temporal-gate` — per-regime/stable-window discovery default, temporal-mixing
  Gate C (camp date-distribution separation → "camps may be list generations" degrade), per-camp
  %current + median date in the discover report. Downstream: re-run discovery per stable era and
  re-rank best-build.
- `bug-banlist-regime-gap` — regime table ends 2026-05-18; missed Candelabra (2026-06-29); rules
  pin stale, `data/banlist/` flow never re-run this cycle. Becomes the epic's validation case +
  the drift-alarm signal (week-over-week collapse ≥70% → banlist-currency check).
- `idea-hierarchical-cell-shrinkage` — shrink camp cells toward the SHRUNK parent cell (not flat
  0.5), parents toward their marginal; e.g. Lands[Sphere/Tomb] vs S&T raw 31.2 n=16 displays 40.3
  today, ~38 under a parent-anchored prior. Cross-era: new-era cells shrink toward their own
  pre-disturbance value, labeled.

## Research gate

CLEARED 2026-07-11 — attested brief written: `docs/briefs/change-point-detection.md`
(12 source-direct attestations in `.research/attestation/`, corpus
`.research/reference/change-point-detection/`; citation-lint clean 57 resolved/0 broken/0 thin;
adversarial source-support read APPROVED after 3 revisions — composed-estimate removed, two
citations re-anchored). Read the brief before epic-design.

## Prior art in-repo

advisory-window-resolution-block (~15 call sites), `analytics/affectedness.py` (ban horizons —
the mechanism being generalized), `analytics/discovery.py` flex-band representation (reuse for
composition distance), matchup.py `build_adaptive_matrix` (the consumption seam),
`beta_binomial_shrink_to` + two-level-empirical-bayes pattern (the shrinkage primitive), the
era-audit's median-date/%current diagnostics (decks/best-deck-era-audit.html — the manual version
of this epic).

## Post-epic payoff (dogfooding, not in-scope)

Re-run best deck / best call on stable-era windows and compare against
decks/best-deck-era-audit.html's verdicts (Lands [Sphere/Ancient Tomb] best deck; Dimir Tempo
[Barrowgoyf] best owned call).
