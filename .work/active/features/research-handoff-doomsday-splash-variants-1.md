---
id: research-handoff-doomsday-splash-variants-1
kind: feature
stage: review
tags: [advisory, generation]
parent: null
depends_on: []
release_binding: null
gate_origin: null
research_origin: doomsday-splash-variants
created: 2026-08-20
updated: 2026-08-20
---

# Build current Doomsday comparison 75s

Produce exact, playable candidate 75s for the current evidenced directions: Dimir
creature-transform as the control, Esper Teferi/Swords, light green-white, and the full
green-white/four-color shield. Preserve the observed distinction between chassis, protection,
interaction, and post-board plan rather than treating color as the complete variant definition.

## Research grounding

**Source**: `.research/analysis/campaigns/doomsday-splash-variants/parent.md` (slug:
`doomsday-splash-variants`)

The post-ban corpus contains exact registrations for each direction, making them the lowest-
assumption starting set for a comparative learning program.

## Design decisions

- Use exact post-ban registrations without card substitutions. A published finish establishes a
  playable source list, not package-level superiority or an estimated matchup win rate.
- Keep deck contents in four import-text files and machine-readable identity/provenance in one JSON
  manifest. The manifest is the candidate-id authority used by the later comparison program.
- Validate both the dated August 10 ban snapshot and the repository's current ban snapshot. This
  preserves historical reproducibility while making a later ban fail loudly.
- Record shared-base compatibility against the Dimir control under a fetchlands-only rule, but do
  not normalize the lists or construct the interchangeable-sideboard series in this feature.
- No child stories: the four files, manifest, and one focused data-contract test form one bounded
  implementation stride.

## Architectural choice

Three shapes were considered:

1. Four standalone text files with provenance comments: simplest, but duplicates metadata and
   gives the later playtest tooling no stable list-id authority.
2. **Chosen — four text files plus one JSON manifest and a short README:** preserves the repository's
   Moxfield-compatible `N Card Name` / `Sideboard` convention while centralizing provenance,
   evidence posture, hashes, and compatibility metadata.
3. A JSON card registry that generates the text files: stronger derivation, but introduces a
   generator and a second card-list representation for only four frozen registrations.

The chosen design treats each `.txt` file as the card-list source and `manifest.json` as the
metadata source. A canonical hash of the parsed boards binds them without copying all 75 cards into
the manifest.

## Implementation Units

### Unit 1: Pin the four exact registrations and manifest contract

**Files**:

- `decks/doomsday-variants/manifest.json`
- `decks/doomsday-variants/README.md`

The manifest contract is:

```json
{
  "schema": "doomsday-variant-candidates",
  "banlist_snapshot_as_of": "2026-08-10",
  "legality_checked_on": "2026-08-20",
  "compatibility_baseline_id": "current-dimir-creature-transform",
  "shared_base_policy": "fetchlands-only",
  "candidates": [{
    "id": "<closed candidate id>",
    "path": "<repository-relative .txt path>",
    "status": "exact-registration",
    "source": {
      "cache_path": "<local fetched source path>",
      "tournament_id": "<stored tournament id>",
      "deck_idx": 0,
      "event_date": "YYYY-MM-DD",
      "event_name": "<name>",
      "player": "<player>",
      "result": "<published result>",
      "attestation_handle": "<ddv handle>"
    },
    "canonical_deck_sha256": "<sha256>",
    "observed_axes": {
      "chassis": "<descriptive construction label>",
      "protection": ["<observed card/package>"],
      "interaction": ["<observed card/package>"],
      "postboard_plan": "<observed construction label>"
    },
    "shared_base_compatibility": {
      "status": "baseline|compatible|incompatible-spells|incompatible-nonfetch|incompatible-spells-and-nonfetch",
      "spell_delta": 0,
      "nonfetch_land_delta": 0,
      "fetchland_delta": 0
    }
  }]
}
```

Candidate ids and compatibility statuses are closed vocabularies; unknown values fail with the
offending value and allowed set. Deltas are multiset copy deltas against the Dimir maindeck, with
fetchlands classified by the local card dimension. The README explains how to import the lists,
states that results are observational, and links the manifest rather than duplicating it.

**Acceptance Criteria**:

- [ ] The manifest contains exactly the four ids below, once each, with unique paths and hashes.
- [ ] Every source object identifies a fetched local cache source, tournament/deck key, player,
      event date, published result, and attestation handle; no source metadata is filled from memory.
- [ ] Observed axes describe only registered contents; strategic roles and matchup claims are not
      presented as measured outcomes.
- [ ] Compatibility deltas are computed, not hand-waved, and every non-Dimir candidate is evaluated
      against the fetchlands-only constraint without changing its 75.

### Unit 2: Materialize the exact four candidate 75s

**Files and immutable source registrations**:

1. `decks/doomsday-variants/current-dimir-creature-transform.txt` — 2plus2isfive, Legacy Challenge
   32, 2026-08-16, 10th; tournament
   `https://www.mtgo.com/decklist/legacy-challenge-32-2026-08-1612851673`, `deck_idx=9`, attestation
   `ddv-compare-current-corpus`; canonical hash
   `02eb0b378efbd7861e7be9e9b5aac61e34e83fc842af627bf061ba48262d62ab`.
2. `decks/doomsday-variants/current-esper-teferi-swords.txt` — Battlegrounds, Legacy League,
   2026-08-12, 5-0; tournament
   `https://www.mtgo.com/decklist/legacy-league-2026-08-1210967`, `deck_idx=3`, attestation
   `ddv-packages-list-esper-battlegrounds`; canonical hash
   `e0237b790a3c7579331903611147df3f32892afcf1b1bce3cf7a9c090fdf7620`.
3. `decks/doomsday-variants/current-light-green-white.txt` — wizardpasta, Legacy Challenge 32,
   2026-08-15, 17th; tournament
   `https://www.mtgo.com/decklist/legacy-challenge-32-2026-08-1512851657`, `deck_idx=16`, attestation
   `ddv-packages-list-green-white-wizardpasta`; canonical hash
   `dbd444ab43279a87d82d58fc1eef244f5451116451797c017a5057d7bf4b0f98`.
4. `decks/doomsday-variants/current-four-color-shield.txt` — wakame, Legacy League, 2026-08-14,
   5-0; tournament `https://www.mtgo.com/decklist/legacy-league-2026-08-1410967`, `deck_idx=9`,
   attestation `ddv-packages-list-four-color-wakame`; canonical hash
   `4109763e425cb4db5cf2b41cc1e2b9214aa56573b393cf3ab1930fb5a71480fe`.

Each file contains comments only before the card block, then exactly 60 maindeck cards, one
`Sideboard` marker, and exactly 15 sideboard cards. The hash algorithm is SHA-256 over compact UTF-8
JSON `{"main":[[name,count],...],"side":[[name,count],...]}` with each board sorted by card name.

**Acceptance Criteria**:

- [ ] Parsing each file with `legacy_engine.models.decklist.parse_decklist` returns 60 main and 15
      side cards and the pinned canonical hash.
- [ ] The lists are exact registrations: no inferred substitutions, shared-base edits, or merged
      packages are introduced.
- [ ] The Dimir list is the comparison control; Esper, light green-white, and full four-color remain
      distinct candidates rather than color-swapped copies of it.

### Unit 3: Add the data-contract validation

**File**: `tests/test_doomsday_variant_decks.py`

```python
def load_candidate_manifest(path: Path) -> dict[str, object]: ...
def canonical_deck_sha256(main: dict[str, int], side: dict[str, int]) -> str: ...
def board_delta(
    candidate: dict[str, int],
    baseline: dict[str, int],
    *,
    fetchland_names: frozenset[str],
) -> tuple[int, int, int]: ...
```

The test module derives candidate paths and ids from the manifest rather than re-enumerating them.
It parses with the public decklist parser, validates construction through
`validate_deck(main, side, banlist_as_of(date(2026, 8, 10)))` and again through
`validate_deck(main, side, current_banlist())`, requires exact 60+15 counts, verifies hashes and
manifest/file agreement, and rejects The Fantasticar explicitly as a diagnostic guard. The local
card dimension supplies fetchland classification and an implementation-time name-coverage check;
the committed test must use a small deterministic injected fixture rather than depend on the mutable
local DuckDB.

**Acceptance Criteria**:

- [ ] Tests fail on malformed manifest shape, unknown candidate/status tokens, duplicate ids or
      paths, absent files, count drift, copy-limit/banned-card errors, hash drift, or compatibility
      delta drift.
- [ ] A focused source-reconciliation check against the four fetched cache records is run during
      implementation; CI remains offline and does not require `data/legacy.duckdb` or the cache.
- [ ] Tests use `TestX` classes and parametrization/fixtures where repetition is real; they assert
      stable data contracts rather than formatting trivia.

## Implementation Order

1. **Unit 1 — source/hash and manifest contract first**, because silently choosing the wrong deck
   row or ambiguous compatibility semantics would invalidate every downstream artifact.
2. Unit 2 — transcribe the four source registrations and reconcile their canonical hashes.
3. Unit 3 — lock counts, legality, provenance binding, and compatibility calculations in tests.
4. Run the focused test, source reconciliation, and `git diff --check`.

## Testing

### Unit tests: `tests/test_doomsday_variant_decks.py`

- Valid shipped manifest and four pinned hashes.
- Parametrized rejection of unknown ids/statuses, duplicate entries, missing files, malformed lines,
  59/15 and 60/16 lists, a fifth nonbasic copy, a banned card, and a changed card with unchanged hash.
- Compatibility classification boundaries: fetch-only difference is compatible; a spell difference
  and nonfetch-land difference receive their distinct fail-closed statuses.

### Integration seams

- `parse_decklist` proves Moxfield/import-text compatibility.
- `banlist_as_of` plus `current_banlist` proves dated and current legality.
- The manifest's ids/paths are the sole enumeration consumed by the later playtest protocol.

## Risks

- **Wrong source row or transcription:** a plausible 75 could still be the wrong registration.
  **Fallback:** pin tournament id, deck index, player, source path, and canonical hash; reconcile once
  against fetched source before accepting the files.
- **Manifest/list dual drift:** metadata can outlive changed text. **Fallback:** canonical hash and
  unique path/id checks fail immediately.
- **Legality moves after delivery:** a historically exact list may stop being current. **Fallback:**
  retain the dated snapshot and also validate against `current_banlist()` so the feature becomes
  loudly stale rather than silently illegal.
- **Compatibility field overclaims modularity:** a color label can hide spell and nonfetch-land
  changes. **Fallback:** derive three separate deltas against a named baseline and do not build the
  shared-base series here.
- **Local refresh status is stale/pending-action:** the research DB reaches August 19, but the ops
  projection reports a stale terminal run. **Fallback:** source identity and legality are dated;
  rerun source reconciliation after the next operator refresh without changing the design contract.

## Implementation notes

- Execution capability: GPT-5.6 Luna high; this bounded data-and-contract stride required exact
  source reconciliation and legality/hash verification but no production code path.
- Review weight: standard (default).
- Files changed: `decks/doomsday-variants/manifest.json`, `decks/doomsday-variants/README.md`,
  the four `decks/doomsday-variants/current-*.txt` registrations, and
  `tests/test_doomsday_variant_decks.py`.
- Tests added/removed: added 15 focused contract tests covering manifest closure/provenance,
  parser and board counts, dated/current legality, hash binding, ban diagnostics, and compatibility
  boundaries; the full suite passed (4032 passed, 1 skipped).
- Simplification: kept the text files as the authoritative card-list representation and used one
  compact hash/manifest instead of introducing a generator or duplicate card registry.
- Discrepancies from design: none; the four cached source rows reconciled exactly to the pinned
  deck indices, registrations, and canonical hashes.
- Adjacent issues parked: none.

### Review-fix verification

- Replaced the Esper protection label with registered Force of Will/Teferi evidence and require
  every observed protection/interaction card to occur in its parsed 75.
- Added tracked immutable source-row fixtures under `tests/fixtures/doomsday_variants/`; tests now
  derive board/date/result/anchor data from those fixtures while retaining each manifest upstream
  `data/cache/...` provenance path.
- Added deterministic closed card-dimension classification with named unknown-card failures,
  compatibility status/delta consistency checks, and mutation tests that preserve intended 60/15
  shape for copy-limit and hash diagnostics.
- Review-fix verification: focused contract suite 16 passed; no stage change; unrelated changes
  remain unstaged.
