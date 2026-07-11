---
id: epic-subarchetype-resolution-discovery-cli
kind: story
stage: done
tags: [analytics, archetype]
parent: epic-subarchetype-resolution-discovery
depends_on: [epic-subarchetype-resolution-discovery-cluster]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Discovery: staging registry + discover/promote CLI

## Brief
Units 5-6 — the human-confirm surface. Staging-registry models (`DiscoveredSplitRecord` etc.) +
loader/promotion in `archetype/discovered.py` (curated-json-resource-loader pattern; new
`DISCOVERED_VARIANTS_PATH` config const), and the `discover run|list|promote` CLI group (nested-group +
fail-loud-stub, audit-echo `// ...` provenance, honest report even on FAIL). `promote` appends
`VariantRule`s to the curated `legacy.json` + sets `defaults` for the complement.

## Implementation
Parent feature `## Implementation Units` → Unit 5 (models + `archetype/discovered.py`) + Unit 6
(`discover` CLI group in `cli.py`). Tests: `tests/archetype/test_discovered.py` load/stage/promote
round-trip + fail-fast; hermetic CLI `discover run/promote --db <tmp>` (never default DB); FAIL split
still prints the honest report.

## Implementation notes

- **Unit 5 models** (`src/legacy_engine/models/variant.py`): `DiscoveredCamp` /
  `DiscoveredSplitRecord` / `DiscoveredRegistry` per the spec signatures, all subclassing
  `LegacyEngineModel`. A staged camp's `signature_cards` are its top over-represented cards only
  (positive delta vs the rest, desc, capped at `TOP_SIGNATURE_CARDS = 5`) — the first entry is the
  promotion condition source. `status` defaults `"candidate"`, flipped to `"promoted"` on promote.
- **Unit 5 loader/staging/promotion** (`src/legacy_engine/archetype/discovered.py`):
  - `load_discovered(path)` follows curated-json-resource-loader with one *documented divergence*:
    an absent file loads as an empty registry rather than erroring, because `discovered.json` is a
    DERIVED artifact under `DATA_DIR` (absent = "nothing staged yet", the normal pre-first-run
    state), not a package resource. A malformed file still fails fast citing the path.
  - `stage_split(reg, record)` is pure — upsert by parent (replace in place, else append), returns
    a new registry. `record_from_split(split, *, generated_from, params)` converts the analytics
    `DiscoveredSplit` into a staging record (provenance fields: what run, what knobs).
  - `promote_split(parent, camp_name, discovered_path, registry_path) -> VariantRule` (returns
    the appended rule for the CLI to echo — the spec said `-> None`, returning the rule is a
    strict superset used for the audit echo). Builds `InMainboard [top signature card]`, appends
    to the curated registry; in the 2-camp case the complement camp's name becomes
    `defaults[parent]` (mirrors Bauble/non-Bauble via the defaults mechanism rather than an
    explicit `DoesNotContain` rule — same resolution semantics through `resolve_variant`, verified
    by test). Fail-fast `ValueError` on: unknown parent, unknown camp (lists available), split
    already promoted, `(parent, name)` already in the curated registry, camp with no
    over-represented signature card.
  - Curated-registry writes go through `_write_variant_registry` with `by_alias=True` (keeps the
    hand-edited `Type`/`Cards` casing) + `exclude_defaults=True` per rule (doesn't spray
    `include_in_label: true` noise into the curated file).
- **`DISCOVERED_VARIANTS_PATH = DATA_DIR / "variants" / "discovered.json"`** added to `config.py`
  (derived side, distinct from the package-shipped `VARIANTS_REGISTRY_PATH`).
- **Unit 6 CLI** (`src/legacy_engine/cli.py`, new `discover` group at the end): `run | list |
  promote` per spec. `run` = compute → honest report → stage-if-PASS. Every leaf:
  `_setup_logging(verbose)` first, `// ` audit-echo provenance (data freshness via
  `_echo_data_freshness`, window, params, stability + silhouette-as-diagnostic, per-camp n+tier+
  signature, every gate reason verbatim incl. the double-dipping guard note, `// verdict:
  PASS|FAIL`). A FAIL split prints the full report + `// not staged: ...` and exits 0 (the report
  is the product; only author errors like unknown camp on `promote` raise `ClickException`).
  **Judgment call**: FAILed splits are reported but NOT staged — the feature brief defines
  candidates as "the survivors" of validation, and staging rejects would pollute the registry the
  analytics side reads as labeled-speculative. The never-silently-dropped requirement is satisfied
  by the mandatory full report.
  - `--reducer svd|umap` (svd default), `--seed`, `--n-boot` (the Risks-section escape valve),
    `--db`, and `--discovered-path`/`--registry-path` overrides (default to the config constants) —
    the path flags are what make the CLI tests hermetic without monkeypatching config.
- **Tests**: `tests/archetype/test_discovered.py` (17 tests — loader absent/malformed/round-trip,
  record conversion positive-delta-cap, stage upsert/purity, promotion round-trip incl.
  `resolve_variant` end-to-end + all 5 fail-fast paths + preserves-existing-entries) and
  `tests/test_discover_cli.py` (10 hermetic CLI tests — `_build_discovery_db(tmp_path)->str` +
  `_build_blob_db` per the file-backed builder pattern, every invoke pins `--db` AND
  `--discovered-path`/`--registry-path` to tmp; PASS stages, FAIL reports honestly and does not
  stage, list, promote happy + 3 loud-failure paths).
- Full suite green after integration: **2667 passed, 1 xfailed** (xfail pre-existing, unrelated).
