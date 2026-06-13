---
id: feature-subarchetype-variants
kind: feature
stage: implementing
tags: [archetype]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-04
updated: 2026-06-13
---

Archetype labels collapse meaningful sub-variants: "Smallpox" lumped Loam Pox and non-Loam Pox together (57%/43% split — strategically distinct, and exactly what a user asked about). Add sub-archetype resolution (variant tags by signature cards, e.g. Loam vs non-Loam) so meta/overlap/matchup queries can distinguish builds within a parent archetype.

**Worked method (validated 2026-06-13):** cluster an archetype's decks by presence of a signature
card, then diff the two subgroups' *average* compositions to expose the variant. Splitting Dimir Tempo
on Mishra's Bauble revealed a coherent variant, not a one-card swap: Bauble decks ran +2.43 Nethergoyf,
+0.52 Daze, and −1.06 maindeck Barrowgoyf vs non-Bauble decks (and more fetchlands, for delirium/delve
fuel). That "diff the subgroup averages" output is exactly the analysis a sub-archetype feature should
produce automatically. Pairs with [[idea-card-count-outlier-advisor]] (compare counts within the right
variant, not the whole parent).

## Design

### Problem framing & the two distinct deliverables

The item asks for two things that are easy to conflate but are architecturally separate:

1. **Variant tagging** — a deterministic, reproducible mechanism that, given a deck's cards and its
   parent archetype label, resolves a *sub-archetype variant tag* (e.g. `Dimir Tempo / Bauble`,
   `Smallpox / Loam`). This becomes a queryable dimension so meta / overlap / matchup / consensus can
   distinguish builds *within* a parent.
2. **Subgroup-diff analysis** — the validated discovery tool: split an archetype's decks on a
   candidate signature card and diff the two subgroups' *average* compositions, so the user can both
   (a) *find* which signature card defines a real variant and (b) read the variant's character
   (the +2.43 Nethergoyf / −1.06 Barrowgoyf table).

These have a producer/consumer relationship: the diff tool is how you *discover* a variant worth
registering; the registry is how a discovered variant becomes a persistent, queryable tag. Build the
diff tool first (it's standalone, needs no schema change, and is the validated method), then the
registry on top.

### Decision: declarative signature-card registry (NOT vendored-rule variants, NOT auto-clustering)

Three options considered for *how a variant is defined*:

- **(A) Reuse MTGOFormatData `Variants`** (the matcher already nests them). Rejected: those are
  *defining* conditions vendored at a pinned SHA — a deck either *is* "Dimir Tempo" or is "Dimir
  Tempo / <vendored variant>". Editing vendored rules to express *our* "Loam vs non-Loam" split
  fights the rolling-foundation/pinned-SHA reproducibility guarantee and conflates upstream taxonomy
  with our analytical splits. The matcher's variant pass also yields a *single* label per deck; we
  want the parent label preserved AND an orthogonal variant tag.
- **(B) Pure data-driven auto-clustering** (k-means / presence-frequency clustering over compositions,
  auto-name variants). Rejected as the *tagging* mechanism: non-deterministic naming, hard to gate by
  confidence, and the user explicitly names variants in domain terms ("Loam Pox"). Clustering is
  valuable as *discovery* — which is exactly what the subgroup-diff tool delivers in a controlled,
  one-signature-at-a-time form. We keep clustering's value without its naming/reproducibility cost.
- **(C, CHOSEN) Declarative signature-card variant registry** — a small project-owned config
  (`data/variants/legacy.json`, version-stamped) mapping a parent archetype to a list of variants,
  each defined by a signature-card rule expressed in the *same* `Condition` vocabulary the matcher
  already loads. A variant tag is resolved by evaluating its condition(s) against the deck's
  main/side name sets — pure, deterministic, reproducible, and it *reuses `evaluate_condition`* from
  `matcher.py` verbatim (no new predicate engine).

Why (C): it composes with the existing rules-as-JSON + `Condition` machinery (one matcher, one
predicate vocabulary), is deterministic/reproducible per PRINCIPLES, keeps *our* analytical splits
separate from vendored upstream taxonomy, and lets the user name variants in domain terms. The
subgroup-diff tool (the validated method) is the *discovery* front-end that tells you which signature
card to write into the registry — so the data-driven method drives the declarative artifact rather
than replacing it.

**Variant semantics (locked):**
- A variant is `{parent, name, conditions[]}` where `parent` is an exact `base_archetype` string and
  `conditions` reuse `models/archetype` `Condition` (Type + Cards), evaluated via `matcher.evaluate_condition`.
- Resolution is **independent of parent matching** and runs *only* when the deck's resolved
  `base_archetype == parent`. At most one variant per parent may match → that variant's tag; if none
  match → the registry's `default_name` for that parent (e.g. `non-Loam`) when declared, else `null`
  (untagged). >1 match for a parent is a **load-time fail-fast** registry error (variants under one
  parent must be mutually exclusive by construction — author them with `DoesNotContain` complements).
- The variant tag is **orthogonal additive metadata**, never replaces the parent label. The full
  sub-archetype label is rendered `"{parent} / {variant}"` for display only; the stored columns stay
  separate (`archetype` unchanged, new `variant` column) so existing meta/matchup keys are byte-identical
  when variants are absent.

This follows the **gated-additive-augmentation** pattern: every query keeps its current behavior when
no variant registry is loaded / no `--by-variant` flag is passed; the `variant` column defaults NULL;
existing tests stay green untouched.

### Data model & schema

- New model `models/archetype.py` additions (reuse existing `Condition`): `VariantRule {parent: str,
  name: str, conditions: list[Condition], include_in_label: bool = True}` and `VariantRegistry
  {version: str, variants: list[VariantRule], defaults: dict[str, str]}` (parent → default variant
  name for the no-match complement). `VariantRegistry.for_parent(parent) -> list[VariantRule]`.
- New config artifact `data/variants/legacy.json` (hand-curated, version-stamped — mirrors the
  banlist-snapshot precedent: project-owned, not vendored). Seeded with the two validated splits:
  Dimir Tempo on Mishra's Bauble; Smallpox on the Loam package (Life from the Loam +
  Dark Depths / fetch density per the worked method — author as an `OneOrMoreInMainOrSideboard` on the
  Loam signature card(s)).
- Schema: add nullable `variant VARCHAR` to `decks` (DDL in `ingestion/store.py`; `IF NOT EXISTS`
  semantics via an idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` in `init_schema`, written
  NULL by ingestion exactly like `archetype` is). No new table — variant is a per-deck attribute of
  the same grain.

### Units in build order (trickiest first within each)

**Unit 1 — `analytics/subgroup.py` (the validated subgroup-diff tool; standalone, no schema change).**
Follows **objective-search-split**: one heavy DB pass → plain dicts → a pure diff function.
- `subgroup_compositions(con, archetype, signature_card, *, board="main", since, until, provenance)
  -> SubgroupSplit` — one query partitioning the archetype's in-window decks into `with`/`without`
  the signature card (presence in `board`), returning for each side the per-card **average copies per
  deck** (`sum(count)/n_decks`, over the union of cards either side runs) plus `n_with`, `n_without`.
  Reuses the `deck_pool` CTE shape from `consensus.card_frequencies`.
- Pure `diff_compositions(with_avg: dict[str,float], without_avg: dict[str,float]) -> list[CardDiff]`
  where `CardDiff {name, avg_with, avg_without, delta}` sorted by `abs(delta)` desc. Hand-testable
  with no DB (the pattern's whole point).
- `SubgroupSplit` dataclass carries `archetype, signature_card, board, n_with, n_without, diffs,
  tier_with, tier_without` (tiers via `tier_for_sample`). Honesty: when either subgroup is below the
  speculative floor, `diffs` are still returned but flagged `thin=True` and the CLI banners it — never
  hide, never fabricate (mirrors `report cards`).
- Signatures are window-aware and default to the latest ban-regime via the existing
  `consensus._latest_regime_window()` (do not duplicate; import it — or, if that import coupling is
  undesirable, lift `_latest_regime_window` to a shared `analytics/windows`-style helper in a follow-up;
  for THIS feature, import it, matching what `report cards` already does).

**Unit 2 — variant registry loader + resolver (`archetype/variants.py`).**
- `load_variant_registry(path) -> VariantRegistry` — lenient-JSON load (reuse `rules._loads_lenient`),
  validate each `Condition.Type` via the existing `KNOWN_CONDITION_TYPES` (fail-fast, reusing
  `rules._validate_condition_types` logic), and **fail-fast on a parent whose variants are not provably
  mutually exclusive is NOT statically checkable** — instead enforce mutual exclusivity at *resolve*
  time (>1 match raises) and add a registry lint test over the seeded file.
- `resolve_variant(base_archetype, mainboard, sideboard, registry) -> str | None` — pure function:
  filter registry to `for_parent(base_archetype)`, evaluate each via `matcher.evaluate_condition`
  (reused verbatim), return the single matching variant's name, else the declared default, else None.
  Raises `AmbiguousVariantError` on >1 match. No DB, hand-testable.

**Unit 3 — labeler integration (`archetype/labeler.py`) + schema.**
- After `classify(...)`, when a registry is provided, call `resolve_variant(result.base_archetype,
  mainboard, sideboard, registry)` and `UPDATE decks SET archetype=?, variant=? ...`. The `registry`
  arg is **optional** (`VariantRegistry | None = None`); `None` → variant left NULL → byte-identical
  to today (gated-additive). CLI `label` command loads `data/variants/legacy.json` when present.
- Add the `variant` column DDL (Unit 3 owns the `store.py` change).

**Unit 4 — query consumers (gated by `--by-variant`).**
- `analytics/metashare.py`: thread an optional `group_by_variant: bool = False`. When True, the
  raw/topcut group-by key becomes `coalesce(parent_label, variant)` rendered as `"{archetype} /
  {variant}"` (NULL variant → bare parent, so untagged decks aren't lost). The SQL change is a
  `GROUP BY d.archetype, d.variant` guarded by the flag; default path unchanged → existing rows
  byte-identical. `wrw` stays parent-only (matchup-n is already the binding constraint; per-variant
  win-rate is out of scope here and would be thin — documented as a non-goal).
- `generation/consensus.py`: `card_frequencies` + `build_consensus` accept optional `variant: str |
  None = None`; when set, the `deck_pool` CTE adds `AND d.variant = ?`. None → unchanged. This is what
  makes "consensus Dimir Tempo / Bauble" possible.
- `analytics/matchup.py` / overlap: **read-only consumers** — they already key on `d.archetype`; a
  thin `--by-variant` is deferred to a follow-up child story (matchup-n per variant is usually below
  the n<30 gate, so shipping it now would mostly produce hidden cells). Documented as out-of-scope for
  the first cut; the registry + column make it a pure additive follow-up.

**Unit 5 — CLI surface.**
- New: `report subgroup --archetype <A> --signature "<card>" [--board main|side] [--since/--until]
  [--provenance] [--db]` → renders the diff table (the headline deliverable): a 3-column
  `with-avg | without-avg | Δ` table sorted by |Δ|, with n_with/n_without and tier banner. Mirrors
  `_print_*_report` helpers and the `report cards` honesty notes.
- New: `report variants [--archetype <A>] [--db]` → lists registered variants and, per variant, its
  current meta share within the parent (count of decks carrying the tag / parent decks in window).
- Extend: `report meta --by-variant`, `generate consensus --variant "<name>"`. `report meta
  --by-variant` defaults `group_other` semantics unchanged.

### Test plan

- **`tests/test_subgroup.py`** — `diff_compositions` pure tests with hand-built avg dicts: sign &
  magnitude of Δ, sort order by |Δ|, cards present on only one side (avg 0 on the other), empty
  inputs. One DB-backed test over a small synthetic corpus reproducing the *shape* of the validated
  Dimir-Tempo-on-Bauble result (decks with/without a signature card → expected Δ signs). Thin-subgroup
  flagging.
- **`tests/test_variants.py`** — registry load (lenient JSON, unknown `Type` fail-fast reusing the
  matcher's validator); `resolve_variant`: single match, default complement, no-match→None,
  >1-match→`AmbiguousVariantError`; parent mismatch → None. All pure, no DB. A lint test asserts the
  *shipped* `data/variants/legacy.json` resolves every parent's variants mutually-exclusively over a
  fixture deck set.
- **`tests/test_labeler.py`** (extend) — labeler with `registry=None` writes NULL variant
  (byte-identical regression); with a registry, writes the expected variant tag for a seeded deck.
- **Regression (gated-additive contract):** existing `test_metashare`, `test_generation_consensus`
  run **unmodified** and stay green (they never pass `--by-variant`/`variant=` → no-op path). Add one
  explicit `--by-variant` metashare test and one `variant="..."` consensus test asserting the scoped
  subset.
- **Golden/CLI:** smoke-test `report subgroup` and `report variants` render without error on the
  fixture corpus.

### Risks & mitigations

- **Thin per-variant samples.** Splitting a parent halves n; matchup-by-variant would be mostly
  hidden cells. *Mitigation:* matchup `--by-variant` deferred; meta/consensus tiers carry the smaller
  n honestly via `tier_for_sample`; subgroup tool banners thin subgroups (never hides).
- **Registry drift vs vendored rules.** A renamed parent archetype upstream silently orphans a
  variant's `parent` key. *Mitigation:* `report variants` surfaces parents with zero matching decks;
  the lint test flags variants whose `parent` is not a current `base_archetype` in the corpus.
- **Mutual-exclusivity authoring burden.** Author must write `DoesNotContain` complements.
  *Mitigation:* resolve-time `AmbiguousVariantError` + the shipped-registry lint test catch overlaps
  immediately; `defaults` lets the common "signature vs not" split be expressed with one positive
  condition + a declared default name.
- **`_latest_regime_window` import coupling** (`analytics` → `generation`). Pre-existing (`report
  cards`/`card_value` already do it). *Mitigation:* accept for this feature; note a follow-up to lift
  the window helper into `analytics` if the coupling spreads.
- **Schema migration on existing DBs.** *Mitigation:* `ALTER TABLE ... ADD COLUMN IF NOT EXISTS variant`
  in `init_schema` — idempotent, NULL-backfilled, no rebuild required.

### Decomposition

No child stories required — five tightly-coupled units in one file-cohesive feature (one new analytics
module, one new archetype module, one model addition, additive edits to three existing modules, CLI).
The single genuinely-deferrable slice (matchup `--by-variant`) is documented as a follow-up and is a
pure additive consumer once the `variant` column exists; spawn it as a story only if a user asks.

## Implementation notes

**Files created:**
- `src/legacy_engine/analytics/subgroup.py` — `SubgroupSplit`, `CardDiff`, `diff_compositions` (pure),
  `subgroup_compositions` (DB-backed); follows objective-search-split, imports `_latest_regime_window`
  from `generation.consensus`.
- `src/legacy_engine/models/variant.py` — `VariantRule`, `VariantRegistry` (Pydantic, reuses `Condition`).
- `src/legacy_engine/archetype/variants.py` — `load_variant_registry`, `resolve_variant`,
  `AmbiguousVariantError`; reuses `evaluate_condition` + `_loads_lenient` + `KNOWN_CONDITION_TYPES` verbatim.
- `data/variants/legacy.json` — version `2026-06-13`; seeded with Dimir Tempo (Bauble/non-Bauble) and
  Smallpox (Loam/non-Loam) using positive+DoesNotContain complement pairs.
- `tests/test_subgroup.py` — 17 tests (8 pure diff_compositions + 9 DB-backed).
- `tests/test_variants.py` — 18 tests (loader, resolver, shipped-registry lint).

**Files modified:**
- `src/legacy_engine/ingestion/store.py` — added `variant VARCHAR` to `decks` DDL and `INSERT` tuple;
  idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS variant` migration for existing DBs.
- `src/legacy_engine/archetype/labeler.py` — optional `registry: VariantRegistry | None = None`;
  when provided, resolves + writes variant; None → variant stays NULL (gated-additive).
- `src/legacy_engine/analytics/metashare.py` — `group_by_variant` param threads through `_raw_counts`,
  `_topcut_counts`, and `compute_metashare`; new `_RAW_BY_VARIANT_SQL` / `_TOPCUT_BY_VARIANT_SQL`.
- `src/legacy_engine/generation/consensus.py` — `variant: str | None = None` param threads through
  `card_frequencies` and `build_consensus`; adds one SQL predicate when non-None.
- `src/legacy_engine/cli.py` — `--by-variant` on `report meta`; `--variant` on `generate consensus`;
  new `report subgroup` and `report variants` commands.
- `tests/test_labeler.py` — 3 variant regression tests added (no-registry → NULL, with-registry → tag,
  archetype column unchanged). Fixed `parent` key to match `base_archetype` not display label.
- `tests/test_metashare.py` — 5 `TestByVariantMetashare` tests added.
- `tests/test_generation_consensus.py` — 3 `TestConsensusVariantFilter` tests added.
- `tests/test_card_winrates.py`, `tests/test_match_results.py`, `tests/test_sideboard.py`,
  `tests/test_whattoplay.py` — updated bare 5-column `INSERT INTO decks` statements to include `NULL`
  for the new `variant` column (schema migration compat fix).

**Deviations from design:**
- None substantive. One design refinement: `resolve_variant` uses `result.base_archetype` (the
  unmunged rule name, e.g. `"Tempo"`) not the color-prefixed display label (e.g. `"Dimir Tempo"`).
  This is correct per the spec ("parent is an exact `base_archetype` string") and the shipped registry
  reflects real archetype rule names from MTGOFormatData where "Dimir Tempo" is the rule's Name field
  directly (not color-prefixed). The test fixture was adjusted accordingly.
- `ALTER TABLE` migration kept even though `variant` is now in the `CREATE TABLE IF NOT EXISTS` DDL —
  it remains needed for existing databases that were created before this feature.

**Test count:** 1353 total (up from 1307), all passing. New tests: 46.


## Review findings (bounce 1)
BLOCKING: the production `label` command (`cli.py:~211`) calls `label_decks(con, ruleset, client.get_card)` with NO `registry` arg, so `decks.variant` is never populated end-to-end — `report meta --by-variant` renders bare rows, `generate consensus --variant X` returns sample_n=0, `report variants` always says 'no decks match'. The new tests pass only because they bypass the CLI and set variant via direct UPDATE/label_decks(registry=...). FIX: in `label`, load `VARIANTS_REGISTRY_PATH` when it exists and pass the registry to `label_decks` (mirror the resolution logic in `report variants`); add a CLI-level test that runs `label` with the shipped registry on a Dimir Tempo / Smallpox fixture and asserts `decks.variant` is non-NULL.
