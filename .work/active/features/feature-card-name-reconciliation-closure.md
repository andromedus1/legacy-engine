---
id: feature-card-name-reconciliation-closure
kind: feature
stage: implementing
tags: [ingestion, data-quality, benchmark]
parent: null
depends_on: [story-fix-missing-goblin-card-metadata, story-fix-set-prefixed-wasteland-name]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Close evidence-backed card-name reconciliation gaps

## Brief

Make the remaining tournament-provider card-name gaps resolvable without weakening card-dimension
closure or turning the package alias registry into a speculative bulk correction table. A fresh
ignored byte-copy of the current corpus, reconciled through the normal `refresh card-coverage`
command against the 2026-08-11 Scryfall all-cards alias snapshot, reduced the benchmark-relevant
inventory from 590 rows / 199 names / 398 decks to 90 rows / 74 names / 42 decks. This feature owns
the residual *classes* and their evidence workflow; it does not treat all 74 spellings alike.

The immediate benchmark blocker is three raw rows of
`Scavenger Regent // Exude Toxin // Scavenger Regent` first entering the training snapshot at cutoff
`2025-07-21`. The canonical card dimension already contains
`Scavenger Regent // Exude Toxin`; the source value repeats the first face after the adventure face.
The benchmark protocol, frozen source corpus, and raw provider caches remain immutable while this
feature is designed and verified.

## Strategic decisions

- **Authority boundary**: Scryfall oracle/all-cards data remains authoritative. Provider strings may
  be reconciled only through deterministic, provenance-retaining transformations whose canonical
  target already exists, or through individually researched exact aliases.
- **No bulk manual aliasing**: do not add 74 hand-written mappings merely to clear the benchmark.
  First consume current authoritative localized aliases, then implement narrowly typed provider
  serialization rules, and leave genuinely ambiguous/truncated inputs unresolved with named reasons.
- **No silent truncation repair**: single-token Cyrillic fragments and multi-target localized aliases
  stay fail-closed unless raw deck context plus authoritative data proves one target.
- **Benchmark separation**: fixes rebuild only derived state on byte-copies. The preregistered
  protocol and estimators are not changed or tuned in response to the gaps or later results.

## Research grounding

The preflight used a byte-copy of the newly refreshed `data/legacy.duckdb` and the production
`legacy-engine refresh card-coverage` path. Its `card_alias_manifest` identifies Scryfall source
snapshot `2026-08-11T21:18:07.865+00:00` with 241,911 unique aliases and 457 ambiguous normalized
keys. Reconciliation recovered 500 of the previously observed 590 gap rows. The residual audit is:

| Classification | Names | Rows | Required treatment |
|---|---:|---:|---|
| Exact set/edition prefix | 13 | 13 | Prove the provider field syntax, strip only a verified prefix grammar, require the suffix canonical target. |
| Exact duplicated full name | 2 | 5 | Collapse `A // A` only when `A` is an existing canonical target and source serialization is proven. |
| Exact duplicated final face | 2 | 8 | Collapse `A // B // A` to existing canonical `A // B` only at the provider reconciliation boundary. |
| Exact localized face composition | 2 | 2 | Resolve each face independently through one-to-one Scryfall aliases, then require the composed canonical target. |
| Ambiguous authoritative alias | 3 | 3 | Preserve ambiguity; require deck/raw context and explicit evidence before any exact mapping. |
| Suspected truncated localized token | 23 | 23 | Preserve as truncated/unresolved; no substring-selected canonical mapping. |
| Manual evidence required | 29 | 36 | Investigate exact raw spelling and authoritative target one by one; no edit-distance auto-repair. |

### Deterministic canonical-target possibilities

- Duplicated final face: `Scavenger Regent // Exude Toxin // Scavenger Regent` →
  `Scavenger Regent // Exude Toxin`; `Marang River Regent // Coil and Catch // Marang River Regent`
  → `Marang River Regent // Coil and Catch`.
- Duplicated full name: `Clarion Conqueror // Clarion Conqueror` → `Clarion Conqueror`;
  `Ulamog, the Ceaseless Hunger // Ulamog, the Ceaseless Hunger` → the same canonical single name.
- Localized face composition: `Bruxa Encantadora // Prado Abençoado pela Bruxa` resolves facewise to
  `Witch Enchanter // Witch-Blessed Meadow`; `Caloteiro Descarado // Pequeno Furto` resolves facewise
  to `Brazen Borrower // Petty Theft`.
- Set/edition prefixes whose suffix already exists: `[AL] Helm of Obedience`, `[A] Dark Ritual`,
  `[A] Swamp`, `[FE] Hymn to Tourach`, `[GP] Leyline of the Void`, `[LRW] Thoughtseize`,
  `[MR] Vault of Whispers`, `[PLC] Urborg, Tomb of Yawgmoth`, `[SHM] Painter's Servant`,
  `[TE] Ancient Tomb`, `[TE] Grindstone`, `[TE] Lotus Petal`, and `[US] Ill-Gotten Gains`.

These are design candidates, not permission for generic slash or bracket stripping. Each rule must
prove its provider grammar, reject non-matching shapes, retain original provenance in its audit, and
fail when the canonical target is absent or ambiguous.

### Fail-closed residuals

- Authoritatively ambiguous: `Explosao de Chamas` (`Flame Burst` or `Pyroblast`),
  `Fractius Hibernante` (`Dormant Sliver` or `Hibernation Sliver`), and `Pantano`
  (`Quagmire` or `Swamp`).
- Suspected truncated: `Гробница`, `Духов`, `Завершение`, `Заклинаний`, `Заклинания`, `Луны`,
  `Могильников`, `Молотов`, `Озеро`, `Орала`, `Пойма`, `Пустоты`, `Священница`, `Тени`,
  `Теснина`, `Тишина`, `Урзе`, `Фонарь`, `Штурм`, `извлечение`, `луна`, `миром`, and
  `отрицания`.
- Manual evidence required: `Aldeia de Nevoalta`, `Cata-magia Vodaliana`,
  `Emrakul, the Awons torn`, `Emrakul, the Eons Torn`, `Estocar`,
  `Explosao Elemental do Azul`, `Explosao Elemental do Vermelho`, `Fairy Macabre`,
  `Grub Storied Matriarch`, `Lavapur Boots`, `Mirror Void`, `Red Element Blast`, `Rough/Tumble`,
  `Sphere of Resistence`, `Stingscurger`, `Tessa’s oracle`, `Treinador Pegatrovao`, `Undercity`,
  `Verdant Catacomb`, `bridge from bellow`, `broadside bombadiers`, `da spade a spighe`, `estocar`,
  `fable of the mirror breaker`, `hudroblast`, `ruba pensieri volteggiante`, `unlicensed hearth`,
  `verdade reberberante`, and `Терминут`.

## Raw-provider evidence ledger

Every residual is present verbatim under `CardName` in the listed cache artifact. The event URI is
the tournament primary key/provenance retained in DuckDB; counts and first-cutoff membership come
from the read-only residual query on the reconciled copy.

| First training cutoff | Residual names / rows | Raw provider artifacts |
|---|---:|---|
| 2025-07-21 | 1 / 3 | `MTGmelee/2025/07/19/oklahoma-land-run-25-legacy-open-212849-2025-07-19.json` |
| 2025-08-18 | 2 / 2 | `MTGmelee/2025/08/03/circuito-legacy-rs-2025-etapa-7-346874-2025-08-03.json`; `MTGmelee/2025/08/16/liga-curitibana-de-legacy-temporada-20252-1a-etapa-regular-343876-2025-08-16.json` |
| 2025-09-15 | 17 / 19 | `MTGmelee/2025/08/30/8-etapa-liga-sul-mineira-de-legacy-ancestral-cards-e-games-358059-2025-08-30.json`; `MTGmelee/2025/09/04/mont-weekly-legacy-360595-2025-09-04.json`; `MTGmelee/2025/09/11/mont-weekly-legacy-363001-2025-09-11.json` |
| 2025-10-13 | 15 / 27 | MTGmelee event ids `365230`, `355775`, `357953`, `370107`, `364669`, `371105`, `371530`, `371538`, and `358609` under their dated cache directories |
| 2025-11-10 | 2 / 2 | `MTGmelee/2025/10/23/mont-weekly-legacy-374768-2025-10-23.json` |
| 2026-03-30 | 3 / 3 | `MTGmelee/2026/03/02/legacy-league-cologne-390364-2026-03-02.json` |
| 2026-04-27 | 29 / 29 | `MTGmelee/2026/04/04/topdeckru-2026-legacy-championship-403563-2026-04-04.json`; `MTGmelee/2026/04/12/3a-etapa-5a-liga-legacy-jundiai-411904-2026-04-12.json` |
| 2026-05-18 | 1 / 1 | `MTGO/2026/04/29/legacy-challenge-32-2026-06-2712841320.json` |
| 2026-06-15 | 2 / 2 | `MTGmelee/2026/05/30/legacy-de-aniversario-do-gordao-431445-2026-05-30.json` |
| no later training cutoff | 2 / 2 | `MTGmelee/2026/07/30/mont-weekly-legacy-444802-2026-07-30.json` |

The common cache root is `data/cache/Tournaments/`. Design must turn this ledger into a reproducible
machine-readable audit or test fixture derived from immutable inputs, rather than maintaining a
second hand-authored list.

## Repair plan boundaries

1. Reproduce the residual audit from a byte-copy after normal oracle/all-cards refresh and record the
   alias-manifest identity in the output.
2. Add typed, provider-scoped reconciliation for the four deterministic serialization classes above;
   each transformation must prove a unique existing canonical target and emit original → canonical
   evidence.
3. Add an evidence queue/report for ambiguous, truncated, and manual-research values. Context may
   rank investigation candidates, but must never write a mapping automatically.
4. Verify cutoff-by-cutoff snapshot closure on derived copies and rerun the unchanged benchmark only
   when the next required cutoff has no unresolved metadata. Preserve any later stop as evidence.
5. Keep exact curated aliases for exceptional historical spellings; do not duplicate mappings that
   current Scryfall aliases or typed serialization rules already cover.

## Simplification opportunity

Replace serial one-name benchmark discoveries with one cutoff-aware coverage preflight and typed
provider normalization audit. The authoritative Scryfall alias table should eliminate most localized
manual entries; deterministic provider serialization rules should eliminate repetitive exact aliases.
Retain the existing small curated registry only for source spellings that neither authority nor a
proved provider grammar can represent.

## Design decisions

- The reconciliation seam receives the observed name's tournament-source set. A provider
  serialization rule runs only when every occurrence belongs to its declared provider; an observed
  spelling shared across supported and unsupported providers remains unresolved rather than being
  globally rewritten.
- Set prefixes are not stripped by a regex alone. The package registry records each admitted prefix,
  provider, and evidence URI; the resolver then accepts only those declared prefixes and requires the
  suffix to be an exact canonical card. The existing exact `[TMP] Wasteland` alias remains valid and
  is not broadened implicitly.
- Face serialization is structural and canonical-target-backed: only exact `A // A`, exact
  `A // B // A`, and independently unique localized faces whose composed target exists can resolve.
  Arbitrary repeated tokens, slash forms, or fuzzy candidates remain unresolved.
- Preflight is an additive option on `refresh card-coverage`, using the same just-reconciled
  connection and a frozen benchmark protocol path. It reports every required training cutoff with
  counts and names, plus post-final-evaluation residuals separately; it never edits the protocol or
  suppresses gaps outside the next fold.
- Direct reading resolved the integration surface; no exploratory fan-out was needed. This is one
  tightly coupled reconciliation module, CLI adapter, and hermetic test seam.

## Architectural choice

Three shapes were considered. First, adding all remaining spellings as exact aliases is operationally
simple but duplicates Scryfall coverage and converts obvious provider serialization into permanent
manual data. Second, normalizing punctuation, brackets, slash segments, and edit distance generically
would be compact but can silently choose the wrong legal card. Third, the chosen hybrid keeps exact
exception aliases for true historical spellings, adds a small typed registry for verified provider
serialization grammars, and requires every derived candidate to match exactly one existing canonical
target. This preserves raw/provider authority while eliminating repetitive aliases.

The highest-risk unit is structural multi-face resolution because `cards` intentionally contains
both combined cards and individual face rows. Candidate construction therefore never chooses a face
by proximity: it creates only the three admitted shapes and succeeds only when the intended combined
or single canonical string exists exactly. Localized composition independently resolves each printed
face to one Scryfall canonical face, composes those names, and then checks the full target. Ambiguity
at either face is terminal and named.

## Implementation Units

### Unit 1: Typed provider serialization candidates

**Files**: `src/legacy_engine/ingestion/card_coverage.py`,
`src/legacy_engine/data/card_name_aliases/legacy.json`,
`tests/test_card_name_resolution.py`
**Story**: `feature-card-name-reconciliation-closure-provider-serialization`

```python
class ProviderSerializationRule(LegacyEngineModel):
    kind: Literal["set_prefix", "duplicated_name", "duplicated_final_face", "localized_faces"]
    provider: str
    evidence: str
    prefixes: tuple[str, ...] = ()

def provider_serialization_candidate(
    con: duckdb.DuckDBPyConnection,
    observed_name: str,
    *,
    providers: frozenset[str],
    canonical_names: frozenset[str],
    rules: tuple[ProviderSerializationRule, ...],
) -> CardNameResolution | None: ...
```

**Implementation notes**:
- Extend the package JSON schema additively with `serialization_rules`; validate kind-specific fields,
  provider, evidence, duplicate prefixes, and unknown keys at load time.
- Query observed names with `list(DISTINCT t.source)` through `deck_cards → tournaments`; missing or
  mixed provider provenance cannot use a provider serialization rule.
- Apply exact curated aliases first, then unique canonical normalization, then provider
  serialization, then Scryfall localized aliases. Preserve that explicit authority order.
- Emit `source="provider_serialization:<provider>"` and a reason naming the admitted shape. The
  update transaction remains the only mutation and the raw observed value stays in the report.

**Acceptance criteria**:
- [ ] The four deterministic shape classes in the evidence ledger resolve to their exact existing
  canonical target under MTGmelee provenance.
- [ ] An undeclared bracket prefix, unsupported provider, mixed-provider spelling, absent target,
  non-palindromic three-part name, or ambiguous localized face remains unresolved.
- [ ] Existing exact Goblin/Wasteland aliases, canonical names, and unique localized aliases retain
  their behavior and precedence.

### Unit 2: Cutoff-aware coverage preflight

**Files**: `src/legacy_engine/models/card.py`,
`src/legacy_engine/ingestion/card_coverage.py`, `src/legacy_engine/cli.py`,
`tests/test_card_coverage_cli.py`, `tests/test_card_name_resolution.py`
**Story**: `feature-card-name-reconciliation-closure-cutoff-preflight`

```python
class CardCoverageGap(LegacyEngineModel):
    observed_name: str
    row_count: int
    deck_count: int
    first_event_date: str
    providers: tuple[str, ...]
    event_uris: tuple[str, ...]

class CardCoverageCutoff(LegacyEngineModel):
    cutoff: str | None
    gaps: tuple[CardCoverageGap, ...]

def unresolved_card_coverage_by_cutoff(
    con: duckdb.DuckDBPyConnection,
    *,
    cutoffs: tuple[str, ...],
    final_evaluation_until: str,
) -> tuple[CardCoverageCutoff, ...]: ...
```

**Implementation notes**:
- Read protocol JSON at the CLI boundary, require non-empty ordered unique `planned_folds[*].cutoff`
  and `final_evaluation_until`, and do not import benchmark estimator code into ingestion.
- Assign a gap to the first training cutoff strictly after its first event date. Residuals first seen
  before final evaluation but after the last cutoff use `cutoff=None` and are labeled
  `no-later-training-cutoff`.
- Add `refresh card-coverage --benchmark-protocol FILE`; emit `// coverage preflight:` lines in
  cutoff order with row/name/deck counts and exact names. Any required-cutoff gap makes the command
  exit nonzero *after* printing the complete audit; post-last-cutoff gaps remain visible but do not
  claim to block training snapshot closure.

**Acceptance criteria**:
- [ ] A hermetic corpus assigns boundary dates correctly under strict cutoff semantics and reports
  all cutoff cohorts, not merely the first failure.
- [ ] Invalid or mutable-looking protocol input fails at the CLI boundary with a specific error.
- [ ] The command uses only the explicit test DB, preserves named ambiguity/truncation/manual gaps,
  and exits nonzero exactly when a planned training cutoff still has a metadata gap.

### Unit 3: Corpus closure gate and rolling documentation

**Files**: `docs/ARCHITECTURE.md`, `docs/analysis/best-call-ranking.md`,
`tests/test_card_coverage_cli.py`, `tests/test_ranking_benchmark_cli.py`
**Story**: `feature-card-name-reconciliation-closure-corpus-gate`

```text
refresh card-coverage --db <derived-copy> --benchmark-protocol <frozen-protocol>
advise benchmark run --db <same-derived-copy> --protocol <frozen-protocol> ...
```

**Implementation notes**:
- Document the authority ladder, fail-closed classifications, and zero-required-gap launch gate as
  current behavior, not migration history.
- Use a fresh ignored byte-copy of the current live DB only after any active scheduler writer closes;
  run normal reconciliation and record alias manifest identity plus the exact preflight command.
- Restart the unchanged benchmark only if every planned-cutoff cohort is empty. A nonzero preflight is
  the truthful terminal result for this feature, not permission to weaken closure or add guesses.

**Acceptance criteria**:
- [ ] Cross-feature CLI regression proves a nonzero preflight prevents the documented benchmark
  launch and a zero-gap corpus clears it without changing protocol bytes/hash.
- [ ] Current docs name Scryfall/current alias authority, provider serialization provenance, and the
  zero-gap gate without claiming ambiguous values were resolved.
- [ ] Fresh-copy evidence records required/post-last-cutoff counts and either the unchanged benchmark
  artifact identity or the named reason it was not restarted.

## Implementation order

1. Typed provider serialization candidates — establishes the only new resolution authority.
2. Cutoff-aware coverage preflight — measures that authority and prevents serial benchmark stops.
3. Corpus closure gate and docs — verifies the integrated behavior on current derived data before
   any benchmark restart.

## Testing

- `tests/test_card_name_resolution.py`: parameterized positive structural classes; negative provider,
  target, shape, prefix, ambiguity, and precedence cases; cutoff grouping at exact date boundaries.
- `tests/test_card_coverage_cli.py`: explicit file-backed DB and protocol fixtures; complete audit,
  invalid protocol, blocking exit, no-later-cutoff disclosure, and green zero-gap exit.
- `tests/test_ranking_benchmark_cli.py`: protocol bytes/hash remain unchanged across the preflight
  handoff and benchmark continues to reject snapshot metadata gaps independently.
- Focused verification covers card reconciliation + coverage CLI + benchmark CLI; integrated
  verification runs the complete repository suite before review.

## Risks

- **Provider grammar overreach**: a shape that looks mechanical may be meaningful card text.
  **Fallback**: provider allow-list + exact target requirement + negative tests; retain exact aliases
  when the grammar cannot be proved.
- **Face-table collision**: face-only rows can make a bad candidate look canonical. **Fallback**:
  construct the intended combined target explicitly for multi-face shapes; never choose among matches.
- **Freshness race with scheduler**: copying a DB during a write can produce misleading evidence.
  **Fallback**: confirm no writer, byte-copy, and perform every mutation/read on the copy.
- **Benchmark pressure encourages false closure**: unresolved tail may tempt fuzzy repair.
  **Fallback**: preflight is intentionally fail-closed and the feature may complete with a named
  nonzero residual; benchmark launch requires zero required gaps, not zero effort remaining.
