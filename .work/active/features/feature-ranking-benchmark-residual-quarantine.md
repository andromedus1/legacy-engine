---
id: feature-ranking-benchmark-residual-quarantine
kind: feature
stage: implementing
tags: [analytics, advisory, testing, data-quality]
parent: null
depends_on: [feature-ranking-future-only-benchmark, feature-card-name-reconciliation-closure]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Outcome-blind residual quarantine for ranking benchmarks

## Brief

Add an explicitly versioned benchmark policy for the small set of tournament decks whose card
metadata remains unresolvable after authoritative Scryfall aliases, verified provider serialization,
and exact evidence-backed exceptions. The original frozen protocol and its fail-closed result remain
immutable. A new protocol may exclude an entire corrupt deck and every match involving that deck,
using only pre-outcome card-dimension completeness, while recording exact names, providers, events,
deck identities, match counts, fractions, hashes, and censor reasons.

The current reconciled corpus has at most 26 affected training decks among 67,477 decks and 100
affected rounds among 81,167 at the last planned cutoff. This feature must set small, round-number
support ceilings before evaluation, refuse folds that exceed them, and distinguish a historical
sensitivity replay from a genuinely prospective validation protocol. It must never infer a card
identity, silently drop a row, overwrite the preregistered v1 protocol, or promote descriptive
results into a validated headline.

## Strategic decisions

- **Immutable evidence**: preserve protocol v1, its hashes, and its not-evaluable/partial artifacts.
  Every quarantine-capable run uses a new protocol id and content hash.
- **Outcome blindness**: quarantine eligibility depends only on deck-card closure against the
  cutoff-safe card dimension. Results, standings, win rates, archetype labels, and downstream scores
  cannot affect which deck or match is removed.
- **Whole-unit removal**: exclude the complete deck and all rounds involving its tournament-local
  player identity. Never delete only the unknown card row and then classify a partial deck.
- **Claim separation**: replaying already-opened historical folds is a labeled sensitivity analysis,
  not prospective validation. A separately frozen future protocol is the only path to a new
  predictive-validation claim.
- **Modern remains out of scope**: this work changes only the Legacy benchmark contract and does not
  extract a format core, create a Modern profile/database, or deploy another format.

## Simplification opportunity

Replace serial fail-stop discoveries and speculative name repair with one reusable, typed exclusion
ledger at the benchmark snapshot/evaluation boundary. Retain strict card-name preflight as the
default and keep the quarantine policy opt-in and protocol-bound.

## Research grounding

The project validation brief requires an exclusion ledger to close before scoring, separate raw and
retained denominators, identical common forecast cases, outcome-blind constraints, and typed
`NOT_EVALUATED` results when a preregistered requirement is missing. It also states that coverage
cannot substitute for predictive or decision value. The existing future-only benchmark already
implements those principles for match outcomes; this feature extends the same contract to corrupt
deck metadata rather than creating a second evaluation engine.

On the current reconciled corpus, the cumulative maximum at the last origin is 26 affected decks of
67,477 (0.039%) and 100 affected rounds of 81,167 (0.123%). Per held-out fold, the observed maxima
are 0.422% of decks and 1.465% of rounds. These counts were obtained without opening any additional
outcomes and are used only to establish feasibility. The protocol ceilings are deliberately rounded
and conservative—0.5% of decks and 2.0% of rounds—not fitted to a score, rank, or win rate.

## Design decisions

- **Default stays strict**: existing protocols deserialize to `require-complete`, with zero
  quarantine ceilings and byte-stable behavior. Quarantine is opt-in and must declare both ceilings.
- **Two evidence postures**: a protocol declares `claim_ceiling` as `descriptive` or
  `predictive-claim-supported`. The historical replay created after v1 opened is permanently capped
  at `descriptive`; the evaluator enforces the cap even if every statistical gate passes.
- **Registration is explicit**: new protocols record an actual `registered_at` timestamp separately
  from the logical origin timestamp used to reproduce historical artifacts. Immutable v1 remains
  readable without that additive field.
- **One deterministic planner**: training snapshots and held-out evaluation call the same pure
  planner over event-local deck identities, card closure, and tournament-local normalized player
  keys. A corrupt deck removes all of its cards, standings row, and every round involving that
  player. Duplicate/ambiguous player keys remove every affected round conservatively and are named.
- **Separate denominators and hashes**: each ledger stores raw and retained decks/rounds, overall
  and source counts, exact unresolved names and event URIs, excluded identities, fractions, ceiling
  verdicts, and a canonical digest. Snapshot source fingerprints bind pre-quarantine facts while
  retained-facts hashes bind the actual training corpus.
- **No repair shortcut**: the planner never deletes just the unresolved card row, guesses a
  canonical name, reuses mutable stored archetype labels, or admits a fold above either ceiling.
- **No new UI structure**: JSON, Markdown, and audit comment lines extend the existing benchmark
  operator surface. No mockup is needed.
- **Direct-read design**: the relevant benchmark contracts, snapshot adapter, evaluator, CLI, and
  tests are bounded and already mapped; exploratory fan-out would add no distinct evidence.

## Architectural choice

Three options were considered. Continuing exact-name research until every historical input resolves
would preserve a complete corpus, but it creates pressure to guess ambiguous/truncated provider
strings and has poor leverage for 27 decks. Dropping only unknown card rows would let classification
run, but it fabricates partial decklists and can silently change archetypes. The chosen option is a
protocol-bound whole-deck quarantine with a complete evidence ledger and hard support ceilings.

The trickiest unit is not deletion; it is proving that training and evaluation exclude the same
observational unit without consulting results. A pure planner therefore produces an immutable
ledger before taxonomy replay or result parsing. Adapters consume the ledger to filter full deck
identities and tournament-local player rounds. Evaluation hashes the ledger with held-out decks and
matches, making later mutation or a two-phase/composed mismatch fail loudly.

## Implementation Units

### Unit 1: Protocol-bound quarantine policy and pure evidence ledger

**Files**: `src/legacy_engine/advisory/ranking_benchmark.py`,
`src/legacy_engine/workflows/ranking_benchmark.py`, `tests/test_ranking_benchmark.py`,
`tests/test_ranking_benchmark_snapshot.py`
**Story**: `feature-ranking-benchmark-residual-quarantine-policy-ledger`

```python
CardMetadataPolicyMode = Literal["require-complete", "quarantine-unresolved-decks"]
BenchmarkClaimCeiling = Literal["descriptive", "predictive-claim-supported"]

class CardMetadataPolicy(LegacyEngineModel):
    mode: CardMetadataPolicyMode = "require-complete"
    max_deck_fraction: float = 0.0
    max_round_fraction: float = 0.0

class QuarantinedDeck(LegacyEngineModel):
    tournament_id: str
    deck_idx: int
    player_key: str | None
    event_date: str
    source: str
    event_uri: str
    unresolved_names: tuple[str, ...]
    identity_ambiguous: bool = False

class CardMetadataQuarantineLedger(LegacyEngineModel):
    policy: CardMetadataPolicy
    raw_decks: int
    retained_decks: int
    raw_rounds: int
    retained_rounds: int
    excluded_decks: tuple[QuarantinedDeck, ...]
    excluded_round_keys: tuple[tuple[str, int], ...]
    deck_fraction: float
    round_fraction: float
    counts_by_source: dict[str, dict[str, int]]
    within_ceiling: bool
    reasons: tuple[str, ...]

class BenchmarkProtocol(LegacyEngineModel):
    # existing fields unchanged
    registered_at: str | None = None
    claim_ceiling: BenchmarkClaimCeiling = "predictive-claim-supported"
    card_metadata: CardMetadataPolicy = Field(default_factory=CardMetadataPolicy)

def plan_card_metadata_quarantine(
    con: duckdb.DuckDBPyConnection,
    *,
    start: str | None,
    end: str,
    policy: CardMetadataPolicy,
) -> CardMetadataQuarantineLedger: ...
```

**Implementation notes**:

- Validate the policy as a closed vocabulary. Strict mode requires both ceilings to equal zero.
  Quarantine mode requires `0 < max_deck_fraction <= 0.005` and
  `0 < max_round_fraction <= 0.02`; the first historical sensitivity protocol uses those maxima.
- `registered_at` is required for quarantine protocols. `claim_ceiling=descriptive` is required when
  registration occurs after the first historical origin.
- The planner joins `deck_cards` to `cards`, groups unresolved names by complete deck identity, maps
  tournament-local normalized players, and calculates round keys before any result is parsed.
- Empty closure produces a zero ledger, not `None`, under quarantine mode. Strict mode preserves the
  existing fail-loud error and does not create an exclusion path.

**Acceptance criteria**:

- [ ] Existing v1 bytes deserialize with strict behavior and unchanged protocol hash semantics.
- [ ] Changing only results/standings cannot change the quarantine ledger or its digest.
- [ ] One unknown card quarantines the whole deck and all tournament-local rounds involving it.
- [ ] Duplicate player identity is conservative and named; missing provenance remains visible.
- [ ] Either ceiling breach returns explicit reasons and cannot produce a snapshot/evaluation.

### Unit 2: Apply the ledger symmetrically at snapshot and held-out boundaries

**Files**: `src/legacy_engine/workflows/ranking_benchmark.py`,
`src/legacy_engine/advisory/ranking_benchmark.py`, `tests/test_ranking_benchmark_snapshot.py`,
`tests/test_ranking_benchmark.py`
**Story**: `feature-ranking-benchmark-residual-quarantine-corpus-boundaries`

```python
OutcomeExclusionReason = Literal[
    # existing values,
    "card-metadata-unresolved",
]

class SnapshotManifest(LegacyEngineModel):
    # existing fields unchanged
    card_metadata_quarantine: CardMetadataQuarantineLedger | None = None
    card_metadata_quarantine_sha256: str | None = None

class HeldoutOutcomes(LegacyEngineModel):
    matches: tuple[HeldoutMatch, ...]
    decks: tuple[HeldoutDeck, ...]
    card_metadata_quarantine: CardMetadataQuarantineLedger | None = None

def build_origin_snapshot(
    source_db: Path,
    destination_db: Path,
    *,
    fold: BenchmarkFold,
    protocol_hash: str,
    card_metadata_policy: CardMetadataPolicy | None = None,
    # existing arguments unchanged
) -> SnapshotManifest: ...

def load_heldout_outcomes(
    source_db: Path,
    fold: BenchmarkFold,
    *,
    card_metadata_policy: CardMetadataPolicy | None = None,
    # existing arguments unchanged
) -> HeldoutOutcomes: ...
```

**Implementation notes**:

- Build the training ledger on raw pre-cutoff facts, then filter `decks`, `deck_cards`, `standings`,
  and `rounds` before taxonomy replay. Retain tournaments even when all their corrupt decks are
  removed so event/date accounting stays reproducible.
- `training_source_fingerprint` binds raw pre-quarantine facts; `training_facts_sha256`, counts,
  taxonomy, card availability, and predictions bind retained facts.
- For held-out data, plan exclusions before `_classified_labels_with_rules`; do not classify corrupt
  partial decks. Matches and field decks carry `card-metadata-unresolved`, and the ledger participates
  in `evaluation_data_sha256` and Markdown denominators.
- Two-phase `freeze`/`evaluate` and composed `run` must produce byte-identical ledgers and evaluation
  artifacts for the same protocol/database.

**Acceptance criteria**:

- [ ] Snapshot closure passes because quarantined decks—not individual card rows—are absent.
- [ ] Stored-label, result, and standings mutations cannot affect quarantine selection.
- [ ] Held-out corrupt decks never reach taxonomy classification or common-case scoring.
- [ ] Training and held-out raw/retained denominators, source counts, names, and event URIs serialize.
- [ ] Ledger or database mutation after freeze causes a hash mismatch or a different immutable output
  path, never silent reuse.

### Unit 3: Operator controls, honest claim ceiling, and empirical sensitivity artifact

**Files**: `src/legacy_engine/cli.py`, `src/legacy_engine/advisory/ranking_benchmark.py`,
`tests/test_ranking_benchmark_cli.py`, `docs/analysis/best-call-ranking.md`,
`docs/ARCHITECTURE.md`
**Story**: `feature-ranking-benchmark-residual-quarantine-artifact-run`

```python
# advise benchmark plan additions
--registered-at ISO_TIMESTAMP
--claim-ceiling [descriptive|predictive-claim-supported]
--card-metadata-policy [require-complete|quarantine-unresolved-decks]
--max-quarantined-deck-fraction FLOAT
--max-quarantined-round-fraction FLOAT
```

**Implementation notes**:

- CLI defaults remain strict. Quarantine planning refuses omitted registration/ceilings and echoes
  the posture, thresholds, and protocol hash.
- `aggregate_benchmark` appends a claim-limitation reason and caps status at `descriptive` whenever
  the protocol ceiling is descriptive, even if all other gates pass.
- Markdown reports foldwise raw/retained deck/round counts, fractions, source counts, exact evidence
  ledger hash, and the claim ceiling. JSON remains canonical and immutable.
- After verification, create a new historical-sensitivity protocol/artifact directory; never reuse
  `best-deck-decision-trust-current-corpus-v1`. Run the card-coverage preflight for evidence, then
  the v2 benchmark on an ignored reconciled byte-copy. A negative, descriptive, or not-evaluable
  result is successful evidence. Refresh the Best Call HTML only with the exact resulting status/id.
- Document the prospective path but do not pretend the historical sensitivity is prospective. A
  predictive-capable protocol may be registered only before its first unopened cutoff and must be
  restarted/versioned if a later B&R event invalidates its frozen schedule.

**Acceptance criteria**:

- [ ] Old strict CLI behavior and artifacts remain unchanged without the new options.
- [ ] A posthoc historical quarantine protocol cannot emit `predictive-claim-supported`.
- [ ] CLI output and Markdown make every exclusion and claim limitation visible.
- [ ] The v2 protocol, summary, and page reference distinct immutable hashes/paths; v1 remains intact.
- [ ] No Modern port, sideboard model, rules engine, or estimator tuning is introduced.

## Implementation order

1. `policy-ledger` — freeze the outcome-blind contract and ceiling validation first.
2. `corpus-boundaries` — apply the same ledger to training and held-out data.
3. `artifact-run` — expose the safe controls, document them, verify the repository, and execute the
   separately labeled sensitivity replay.

## Testing

### Unit tests

- Pure ledger tests cover zero gaps, one corrupt deck, multiple unknown names in one deck, duplicate
  players, missing provider/URI, source grouping, deterministic ordering, and both ceiling breaches.
- Protocol tests cover legacy defaults, invalid vocabulary, missing registration, descriptive cap,
  and immutable hash changes for every policy field.

### Integration tests

- File-backed snapshot tests compare raw versus retained facts and prove post-cutoff/outcome mutation
  invariance.
- Held-out tests prove corrupt decks are excluded before taxonomy and never enter common scoring or
  field coverage silently.
- CLI tests use explicit temporary DuckDB paths, compare `freeze` + `evaluate` with `run`, reject
  artifact tampering, and assert complete Markdown/JSON evidence.
- The affected ranking/CLI suite, full repository suite, changed-file lint/compile, and knowledge
  index must be green before review.

## Risks

- **Selection bias despite low volume**: corrupt decks cluster in localized paper events, so even a
  small overall fraction may be non-random. **Fallback**: keep the historical replay descriptive,
  publish source/event concentration, and require an unopened prospective protocol for validation.
- **Partial-deck leakage**: classification could run before exclusion or a helper could retain the
  unknown deck with missing cards. **Fallback**: planner runs before taxonomy, snapshot closure
  asserts no unresolved rows, and adversarial tests fail if partial classification occurs.
- **Result-informed protocol drift**: v2 could accidentally inherit a predictive claim after some v1
  folds were opened. **Fallback**: immutable protocol id/hash plus a type-validated descriptive claim
  ceiling enforced in aggregation and rendering.
- **Over-quarantine from player joins**: duplicated provider handles can remove extra rounds.
  **Fallback**: conservative removal is explicit, identity ambiguity is recorded, and either fraction
  ceiling fails the fold rather than guessing.
- **Future provider corruption grows**: a prospective fold may exceed the declared ceiling.
  **Fallback**: return not-evaluable, repair authoritative inputs if possible, and register a new
  protocol only before another unopened block; never widen a live protocol threshold.

## Other agent review

No design-time advisory pass was commissioned. The feature is bounded to the existing benchmark
boundary, direct evidence resolves the alternatives, and the execution environment does not expose
a different model class through the required advisory path. The normal standard independent feature
review remains required after implementation.

## Implementation summary

- Implemented typed policy/ledger contracts, deterministic outcome-blind planning, and frozen-v1
  protocol hash compatibility.
- Applied one ledger before taxonomy/result parsing at snapshot and held-out boundaries, including
  retained-facts/source fingerprints and evaluation-data hashes.
- Added strict-default CLI controls, descriptive claim-ceiling enforcement, audit lines, Markdown
  denominators/evidence, and architecture/runbook documentation.
- Child commits: `7eaeb44` (policy-ledger), `b9c3275` (corpus-boundaries), `abf76bd` (artifact-run).
- Focused verification: 29 benchmark/snapshot/CLI tests, Ruff checks, and compileall passed.
- Empirical artifact: ignored `data/benchmarks/ranking-residual-quarantine-v2/` on a reconciled byte
  copy. The required preflight found 53 unresolved names entering planned cutoffs, so this remains
  historical/descriptive and cannot support a prospective claim. Full fold replay was launched after
  controls verification and remains CPU-bound; final status/summary identity will be recorded if it
  completes.
- Discrepancy: the first child commit includes shared adapter plumbing consumed by the second child;
  behavior and acceptance remain independently verified.

## Review findings (2026-08-12)

**Effective weight**: standard (project default). Exactly one same-harness fresh-context Sol pass
completed; this was independent context but not a different model lineage. Closure requires
verification of the named fix story only and no second independent pass.

**Receiver-confirmed blockers**: tracked by
`feature-ranking-benchmark-residual-quarantine-review-fixes`.

- Quarantine ledger identity must hash only pre-outcome dimensions; neither training results and
  standings nor held-out classifications and outcomes may change its digest.
- Blank or ambiguous player identity cannot leave an affected round in the retained corpus or
  understate the round ceiling. The planner must remove it conservatively or fail with a typed reason.
- Registration must be strictly before the exact first-cutoff instant for a predictive-capable
  protocol, and typed summaries must reject any status above their declared claim ceiling.
- Strict/v1 raw and canonical artifacts must preserve their previous card-inclusive hashes and omit
  additive default fields where compatibility requires it, including the page-visible summary id.
- Freeze and evaluation must validate that the manifest/held-out ledger exists, equals the protocol
  policy, passes ceilings, matches its declared digest, and binds the retained corpus.

**Accepted important finding**: the operator-facing Markdown must render exact quarantined deck,
identity, unresolved-name, event/provenance, ledger-reason, and digest evidence already available in
JSON.

**Review action**: the in-flight v2 replay was stopped after fold 1 because its artifacts were built
under invalid contracts. Partial ignored files are non-authoritative debugging output and will not be
used for the page. After the fix story is green, create a fresh artifact directory and restart only
from corrected committed code.
