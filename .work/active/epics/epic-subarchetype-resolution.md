---
id: epic-subarchetype-resolution
kind: epic
stage: done
tags: [analytics, archetype]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-29
updated: 2026-07-11
brief: docs/briefs/subarchetype-discovery.md
---

# Subarchetype resolution

## Brief

The engine carries a **flat archetype label per deck**. Subarchetypes that play completely
differently collapse onto one parent label, so they pool into a single matchup row and a single
card-win-rate denominator — which distorts every downstream stat. This wall has been hit in three
consecutive dogfooding sessions:

- **Doomsday** (2026-06-29 / 07-05): the Legacy one-card rule labels every maindeck-Doomsday deck
  "Doomsday", but `report subgroup --archetype Doomsday --signature "Murktide Regent"` shows a clean
  **292/878 split, both established tier** — a tempo/mana-denial camp (Tamiyo +2.7, Wasteland +2.1,
  Bowmasters +1.0) vs an all-in mana camp (Personal Tutor, Lotus Petal, Cabal Ritual). ~25% of the
  archetype is a different deck.
- **WU Phelia / Quantum Riddler** (2026-07-11): the real deck is split three ways by the parser
  (Azorius Midrange + White Beanstalk + Azorius Stoneblade, by engine package) and had to be
  **hand-merged into one cohort** to recover matchup sample — the inverse problem (one deck read as
  three labels).
- **Dimir Tempo card keep/cut** (2026-06-27): `report cards --archetype "Dimir Tempo"` showed
  Mishra's Bauble at −0.040 marginal lift (a "cut" signal), while `report subgroup` showed
  Goyf+Bauble was the *best* cell (59.7%, n=159) — the marginal number is cross-archetype
  contaminated and pointed backwards.

**Why it matters:** matchup accuracy, card keep/cut calls, and field composition are all only as
honest as the partition they condition on. Today that partition is a single flat label. Same risk
lurks in every broad bucket — Eldrazi, Painter, the *Delver family, the Midrange labels.

**Known integration constraint (from prior investigation):** `analytics/match_results.py` keys on
`decks.archetype` only, so persisting `decks.variant` labels alone does **not** split the matchup
matrix — the matrix builder must gain a variant dimension. Existing primitives are a starting point,
not a solution: `archetype/variants.py` (hand-authored card-presence registry, `data/variants/legacy.json`),
`report subgroup` (manual single-card split), `report variants` / `report meta --by-variant` /
`generate consensus --variant`.

## Strategic decisions

- **Epic membership**: discovery + variant-conditioned matchup cells + archetype-conditioned card
  win-rate. — One analytics-infrastructure arc. `idea-archetype-id-trainer` stays in the backlog: it
  is a separate in-game coaching product surface that consumes flat archetype knowledge and does not
  depend on subarchetype resolution.
- **Discovery method: full unsupervised, statistically self-validating**: the pilot lacks the subject
  expertise to reliably hand-confirm a hybrid registry today, so discovery cannot lean on human
  judgment as its correctness gate — clusters must earn their split via statistical validation
  (cohesion/separation, both-camp sample tiers, card-inclusion divergence like the Doomsday case).
  Preserve a **human-confirm hook** so camps can be promoted/renamed into the curated registry as the
  pilot's expertise grows. — The core of the research/scout brief.
- **Sequencing: discovery-first**: the data-driven discovery engine ships before the analytics
  conditioning consumes it; the conditioning features `depends_on` discovery. (Note: the matchup-cell
  and card-win-rate slices are technically computable off the *existing curated* variants today —
  discovery-first is a deliberate choice to build the real classifier before wiring analytics to it,
  not a technical constraint.)
- **Honesty bar: surface labeled, never hide**: splitting a parent shrinks per-cell n, often into
  speculative tier (e.g. Dimir Tempo Tempo/Turbo was n=47/49). Variant-conditioned cells surface at
  whatever tier they land with mandatory honesty labels — consistent with the project's
  honest-degrade policy. No split is hidden for being thin, and none is silently blended away.

## Design decisions

Captured from `/epic-design --only-questions` (2026-07-11). Feature-design inherits these as fixed inputs.

- **ML dependency appetite**: scikit-learn **+ umap-learn**. — sklearn supplies HDBSCAN (≥1.3),
  TruncatedSVD, TF-IDF, and the validation indices; umap-learn adds the UMAP reduction the brief lists
  as the richer embedding (accept the numba build weight). Both are net-new (numpy/scipy/pulp already
  present).
- **Human-confirm hook surface**: `discover` → **staging registry** → `promote`. — A discovery CLI
  writes candidate splits to a staging registry (status: candidate) that analytics reads as
  labeled-speculative; an explicit `promote` command moves a confirmed split into curated
  `data/variants/legacy.json`. Mirrors the `report subgroup` / `report variants` surface. Discovery
  never silently rewrites the curated taxonomy (epic's locked bar).
- **Default analytics behavior**: **opt-in overlay**. — Parent-level output stays the default
  everywhere; variant conditioning is explicit via a flag (like the existing `--by-variant` /
  `--variant`). Default outputs stay byte-identical (gated-additive-augmentation + honest-degrade
  ethos). No auto-splitting of the matrix as camps mature.
- **Feature granularity**: **three features** — discovery engine → variant-conditioned matchup cells →
  variant-conditioned card win-rate (discovery-first `depends_on` order). Each independently shippable
  and dogfoodable; the higher-value matchup-cells slice can land before card-win-rate.

## Decomposition

Split by capability, discovery-first (the locked three-feature granularity). The discovery engine is
the foundation feature that produces `decks.variant` labels; the two analytics consumers depend on it
and parallelize after it lands. Not split by layer, and no manufactured refactor/test features. The two
consumers share one "resolve a deck's variant" helper — whichever is designed first establishes it.

### Child features

- `epic-subarchetype-resolution-discovery` — the research-gated discovery engine (flex-band matrix →
  reduce → HDBSCAN → two-gate validation → auto-name → `discover`/`promote` staging registry). depends on: `[]`
- `epic-subarchetype-resolution-matchup-cells` — optional variant dimension on the subject side of the
  matchup matrix (`(archetype,variant) × opponent`), opt-in flag, tier gates reused. depends on: `[epic-subarchetype-resolution-discovery]`
- `epic-subarchetype-resolution-card-winrate` — archetype/variant-scoped card-winrate denominator +
  honest-degrade sign-conflict warning + subgroup win% in `report subgroup`. depends on: `[epic-subarchetype-resolution-discovery]`

### Decomposition risks

- **Discovery is the big feature** (representation + reduction + clustering + two-gate validation +
  naming + staging registry + two CLI leaves + new deps). If it exceeds one implement pass, feature-design
  spawns child stories along the seams noted in its body — keep the clustering/validation logic DB-free
  and unit-testable (objective-search-split pattern).
- **Shared variant-read helper** across the two consumers — the first-designed consumer owns it; the
  second reuses. Flagged so feature-design coordinates rather than duplicating.
- **umap-learn/numba build weight** in CI — the discovery feature must confirm the CI image builds it;
  fall back to sklearn TruncatedSVD-only reduction if numba proves unavailable (the brief supports either).

## Foundation-doc status

VISION rolled forward at scope time (two-level taxonomy). ARCHITECTURE + SPEC rolled forward at this
epic-design pass now that the method is decided — see the archetype/analytics discovery + variant-dimension
additions and the subarchetype-resolution constraint.

## Next

Brief **written** and attested: `docs/briefs/subarchetype-discovery.md` (ARD citation chain clean;
15 source-direct attestations under `.research/attestation/`, corpus
`.research/reference/subarchetype-discovery/`). It locks the method — flex-band representation,
TF-IDF/count + cosine/Bray-Curtis, HDBSCAN-primary (self-determines k, labels noise) on a
reduced embedding, two-gate validation (resampling stability >0.9 / prediction strength >0.8 **and**
both-camp evolving tier + signature divergence), the double-dipping guard, and the optional
`(archetype, variant) × opponent` matchup-cell key that reuses the existing tier gates unchanged.

Ready for `/epic-design` to decompose into the three features (discovery engine → variant-conditioned
matchup cells → archetype/variant-conditioned card win-rate).

## Completion summary (2026-07-11)

All three features shipped, merged, and review-approved in one autopilot run:

| PR | Feature | Verdict |
|---|---|---|
| #36 (0fee3d0) | discovery engine (`discover run\|list\|promote`) | APPROVE (3 minors parked) |
| #37 (d3fa9f7) | variant-conditioned matchup cells (`--split-variant`) + display-key labeler fix | APPROVE (2 minors fixed in #38) |
| #38 (7b94243) | conditioned card win-rate + sign-conflict + subgroup win% | APPROVE (2 minors noted) |

Suite 2604 → **2725** (+121 tests). Ground-truth validations: Doomsday rediscovered its validated
Tempo/Turbo camps + a third established Flow State camp (stability 0.980); Dimir Tempo [Bauble]
54.3% (n=43 evolving) vs [non-Bauble] 61.8% (n=282 established) vs Show&Tell; Mishra's Bauble
marginal −0.018 vs within-archetype +0.014 with sign-conflict honest-degrade lines firing.
Bonus fixes en route: HDBSCAN min_samples/root-bias parameterization (caught by ground-truth
dogfood); variant-resolution display-key bug that had silently NULLed every color-prefixed
archetype's variants. Foundation docs rolled forward (SPEC capability → [Built]; ARCHITECTURE CLI
diagram + discovery.py row + opt-in variant overlays). Deps added: scikit-learn (core), umap-learn
(optional `discovery` extra).

## Completion-review follow-ups (2026-07-11)

A completion review of the epic surfaced four gaps closing the last acceptance item (the
Human-confirm hook design decision's "analytics reads as labeled-speculative" clause). All four
are implemented on `feat/discover-apply`:

1. **`discover apply` (the substantive gap)** — the staging registry could be inspected
   (`discover list`) but not actually *consumed* as labeled-speculative without promoting it
   first, contradicting the design decision. Added `apply_split(con, parent, *,
   discovered_path=None)` in `archetype/discovered.py`: builds the same transient `VariantRule`
   set `promote_split` would install (top signature card per camp; complement default only in
   the 2-camp case) and resolves every deck currently labeled `parent` against it, writing
   `decks.variant` for matches only — non-matching decks stay NULL (`[unlabeled]`, honest). Does
   NOT touch the curated registry and does NOT flip the staged record's `status` — it stays
   `candidate`. New CLI leaf `discover apply --archetype X [--db] [--discovered-path]` with
   `// ` audit lines including an explicit `STAGED CANDIDATE ... speculative provenance; not
   promoted` banner. `report matchups --split-variant X` now also echoes `// provenance: X has a
   STAGED (unpromoted) candidate split — variant labels may be speculative-provenance` when the
   default staging registry holds a candidate record for `X` (wrapped in try/except so a corrupt
   or absent registry never breaks the report; no-flag path stays byte-identical).
2. **`report cards --conditioned --vs` silently ignored `--vs`** — now fails loud with a
   `click.ClickException` naming `--vs` as a tracked follow-up (opponent-specific conditioned
   values aren't implemented) rather than quietly dropping the flag. The follow-up itself stays
   tracked, not implemented here — this closes only the silent-drop honesty gap.
3. **`stage_split` silently overwrote a same-parent staged candidate** — `stage_split` now
   returns `(new_registry, replaced_record_or_None)` (all callers updated); `discover run` echoes
   `// replaced prior staged candidate for '<parent>' (was: generated_from=<...>,
   camps=<names>)` only on a genuine same-parent overwrite, never on a fresh append or a
   different parent.
4. **ARCHITECTURE.md drift** — the discovery module row mis-stated its home as a bare
   `discovery.py` under `archetype/`; corrected to name both `analytics/discovery.py` (pure
   clustering core) and `archetype/discovered.py` (staging/promotion/apply, as-built), and added
   `apply` to the CLI diagram + the row's CLI-verbs mention.

Suite 2725 → **2740** (+15 tests), all green (`.venv/bin/python -m pytest tests/ -q`).

## Final completion review (2026-07-11)

Cross-model (Codex via peeragent, effort=high) completion pass over the full epic bundle. Four
findings, all closed in PR #39 (19eb391): (1) BLOCKING — the "analytics reads staged candidates as
labeled-speculative" half of the human-confirm-hook decision was unimplemented → `discover apply` +
membership persistence + staged-provenance echo in `--split-variant`; (2) `--conditioned --vs`
silently ignored → loud rejection (opponent-conditioned values remain an open idea, honest scope);
(3) silent same-parent staging overwrite → honest replaced-echo; (4) ARCHITECTURE module-placement
drift → corrected to as-built. En route, the real-data 3-camp apply exposed the transient-rules
ambiguity failure — fixed by labeling from exact cluster membership (Codex's own suggested remedy).
Final suite 2742 passed + 1 pre-existing xfail. Epic complete.
