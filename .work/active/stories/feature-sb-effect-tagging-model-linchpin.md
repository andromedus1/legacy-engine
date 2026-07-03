---
id: feature-sb-effect-tagging-model-linchpin
kind: story
stage: review
tags: [advisory]
parent: feature-sb-effect-tagging-model
depends_on: [feature-sb-effect-tagging-model-vocab-catalog]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Linchpin hybrid model (derive + curated overrides)

## Brief

Build the archetype linchpin model — the `centrality` input Feature B's impact score consumes.
Hybrid: auto-derive candidate linchpins from composition (near-mandatory inclusion × engine/combo
role) and merge curated overrides on top (curated centrality wins). New module + curated JSON SSOT +
config path, following the `curated-json-resource-loader` pattern. Depends on the vocab-catalog story
because `neutralized_by` references the effect-tag vocabulary it defines.

## Implementation

Covers parent feature unit **4** — see `feature-sb-effect-tagging-model` § Implementation Units
(Unit 4) for the `Linchpin` dataclass, `load_linchpin_overrides` / `derive_linchpins` /
`linchpins_for_archetype` signatures, the curated JSON schema, and acceptance criteria. New files:
`advisory/linchpins.py`, `data/linchpins/legacy.json`, `config.py` additions; tests in
`tests/test_linchpins.py`.

## Implementation notes (as-built)

**New module** `src/legacy_engine/advisory/linchpins.py`:
- `Linchpin` (frozen dataclass): `archetype`, `name`, `role`, `centrality: float in (0,1]`,
  `neutralized_by: frozenset[str]` — exactly per the parent unit's spec.
- `load_linchpin_overrides(path)` — curated-json-resource-loader pattern (mirrors
  `sideboard.load_hoser_catalog`): standalone, path-taking, fails fast with `ValueError` citing
  `<archetype>/<name>` on bad/missing `name`, `role`, out-of-range or non-numeric `centrality`,
  non-list `neutralized_by`, non-list archetype entries, or a non-dict top-level `linchpins` key.
  `neutralized_by` defaults to `[]` when omitted. Raises `FileNotFoundError` on a missing path.
- `_load_default_linchpin_overrides()` resolves `config.LINCHPINS_REGISTRY_PATH` and degrades to
  `{}` on any error (logged), matching `_load_default_hoser_catalog`. Bound once at import:
  `LINCHPIN_OVERRIDES = _load_default_linchpin_overrides()`.
- `derive_linchpins(archetype, cards_with_counts, inclusion_pct)` — PURE, no DB (objective-search-
  split: caller already resolved `Card` objects + inclusion% once). A card qualifies when
  `inclusion_pct.get(name, 0.0) >= _LINCHPIN_INCLUSION` (0.90) AND its `whattoplay._card_roles(card)`
  intersects the role-priority map below; qualifying cards are emitted at the flat
  `_DERIVED_CENTRALITY` (0.6), deliberately below any curated 1.0 so an over-eager derivation is a
  small error, not a blowup (per the parent feature's risk note).
- `_infer_neutralized_by(card)` — derives `neutralized_by` for a *derived* linchpin from its own
  `type_line`/`oracle_text`: Artifact + activated-ability shape (`Cost: Effect`, reminder-text
  stripped) → `{artifact-ability-lock, artifact-bounce, artifact-removal}`; Artifact without one →
  `{artifact-removal}`; Creature → `{creature-removal, board-sweep}`; Enchantment →
  `{enchantment-removal}`; `graveyard_recursion` role → adds `exile-graveyard`; Instant/Sorcery →
  `{counter-on-cast}` (a one-shot effect can only be stopped on the stack). Returns `frozenset()`
  (not a guessed default) when nothing is inferable — an honest-degrade, not a fabricated tag.
- `linchpins_for_archetype(archetype, cards_with_counts, inclusion_pct)` — derives, then merges the
  shipped `LINCHPIN_OVERRIDES[archetype]` on top via `_merge_linchpins` (curated wins by
  case-insensitive name match; unmatched derived entries are kept). `_merge_linchpins` is split out
  as a pure, directly-testable function so the merge policy doesn't require monkeypatching the
  module-level registry in every test.

**`neutralized_by` capability vocabulary (new — owned by this model, documented in the module
docstring, NOT the hoser `attacks` tag space)**: `artifact-ability-lock`, `artifact-bounce`,
`artifact-removal`, `exile-graveyard`, `counter-on-cast`, `board-sweep`, `creature-removal`,
`enchantment-removal`. No new tokens were needed beyond the story's initial set. Bridging a
hoser's `attacks` to a linchpin's `neutralized_by`, and folding that into an impact/centrality
score, is explicitly deferred to Feature B — this story only ships the vocabulary + inference.

**Role-name mapping (`_LINCHPIN_ROLE_PRIORITY`, priority-ordered — first match wins for a card
carrying several `_card_roles`)**: `whattoplay._card_roles` has no `combo-engine`/`combo-tutor`/
`key-payoff` labels of its own (its vocabulary is `fast_mana`, `counter`, `removal`, `ritual`,
`tutor`, `storm`, `graveyard_recursion`, `graveyard_fuel`, `protection`, `stax`, `card_advantage`,
`discard`, `threat`), so derivation maps the closest existing roles:
- `tutor` → `combo-tutor` ("search your library for a/an/up to ..." is the textbook tutor effect).
- `storm` → `key-payoff` (the storm-count payoff spell itself — Tendrils/Grapeshot — is what the
  deck is building toward, i.e. the plan's payoff, not its engine).
- `ritual` → `combo-engine` (net-positive-mana spells power the rest of the combo).
- `fast_mana` → `combo-engine` (Moxen/fast-mana artifacts play the same accelerant role as rituals).
This mapping is deliberately conservative: real linchpins like Grindstone and Show and Tell match
NONE of these roles by oracle text, which is exactly why the hybrid (derive + curate) design was
chosen over pure derivation — see curated seed below.

**Curated seed** `src/legacy_engine/data/linchpins/legacy.json` (`version: 1`), grounded against
`data/legacy.duckdb` (`cards.oracle_text` + `generation.consensus.card_frequencies`) at authoring
time:
- **Painter** → `Grindstone` (combo-engine, centrality 1.0, `{artifact-ability-lock,
  artifact-bounce}` — per the unit spec; inclusion 1.00/2 modal copies) and `Painter's Servant`
  (combo-engine, centrality 1.0, `{creature-removal, artifact-removal, board-sweep}` — inclusion
  1.00/4 copies; the two-card Painter's Servant + Grindstone combo is equally load-bearing on both
  halves, which a generic inclusion-threshold heuristic can't express as 1.0 vs the derived 0.6).
- **Show and Tell** → `Show and Tell` (combo-engine, centrality 1.0, `{counter-on-cast}` — a
  one-shot Sorcery; inclusion 1.00/4 copies; the entire cheat-a-fatty-into-play plan is this one
  card resolving).
- **Eldrazi** → `Chalice of the Void` (role `lock-piece` — curated roles are free-text, not
  constrained to the derivation vocabulary; centrality 0.75, not 1.0, since the archetype has
  redundant disruption — Thought-Knot Seer, Cavern-backed threats — and functions, just less
  consistently, without it; `{artifact-removal}` since its counter-trigger is not a colon-activated
  ability). Inclusion 1.00/4 copies.

**`config.py`**: added `LINCHPINS_DIR = PACKAGE_DATA_DIR / "linchpins"` and
`LINCHPINS_REGISTRY_PATH = LINCHPINS_DIR / "legacy.json"`, mirroring the `HOSERS_*` lines exactly.
No packaging changes needed — `pyproject.toml` ships `src/legacy_engine` as one hatchling package,
so `data/linchpins/legacy.json` ships the same way `data/hosers/legacy.json` already does.

**Tests** `tests/test_linchpins.py` (41 new tests, all green; full suite 2349 passed, 0 failed):
`TestDeriveLinchpins` (role-mapping + inclusion-threshold + priority-order + empty-input paths),
`TestInferNeutralizedBy` (all 8 vocabulary tokens exercised), `TestLoadLinchpinOverrides` (happy
path + every fail-fast schema violation, each asserted to name the offending archetype/entry),
`TestLoadDefaultLinchpinOverrides` (shipped file loads clean; degrades to `{}` on a bad/missing/
malformed path via `monkeypatch.setattr(config_module, "LINCHPINS_REGISTRY_PATH", ...)`),
`TestMergeLinchpins` (pure merge policy, case-insensitive name match), `TestLinchpinsForArchetype`
(the three parent-unit acceptance criteria: curated Grindstone beats a derived 0.6 both via a
monkeypatched registry AND against the real shipped catalog; a derived-only archetype still
surfaces its near-mandatory engine piece at 0.6; `load_linchpin_overrides` fail-fasts on
out-of-range centrality naming the entry).

**Deviations from the parent unit's literal spec**: none structural. The only judgment calls were
(a) the role-name mapping and (b) the `neutralized_by` inference heuristic, both of which the
parent unit explicitly delegated to this story ("map sensibly; document your mapping") and both
documented in the `linchpins.py` module docstring plus this note.

**Explicitly out of scope / deferred to Feature B**: bridging hoser `attacks` tags to linchpin
`neutralized_by` capability tokens (i.e. "does sideboard card X actually answer this linchpin"),
and folding `centrality` into the impact/scoring model. This story ships only the model, loader,
derivation, curated seed, and tests.
