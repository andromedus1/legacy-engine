---
description: The quality report + metadata for the ingestion-archetype-contracts deep-research campaign. Read to know how trustworthy the brief set is, the contradictions flagged, and what to verify before building.
type: program-report
kind: research
research_method: /deep-research
status: draft
updated: 2026-05-29
summary: |
  Campaign report for the 7-specialist deep-research run on legacy-engine's ingestion + archetype-parser
  data contracts. Evaluator scored it 4/5 overall ("an unusually buildable brief set"): coverage 5,
  coherence 5, contradictions 4, groundedness 4, recommendations 4. Captures the flagged contradictions
  (notably the Scryfall-library reuse verdict and an unreconciled ~210-vs-600 LOC figure) and the
  must-verify-before-building list (golden-test oracle availability, the library ADR, the guild table).
key_findings:
  - "Overall 4/5 — buildable now; an engineer could design ingestion/ and archetype/ and start the port from these briefs alone."
  - "Two genuine contradictions: (1) CARD-CONTRACT 'extend edh-engine scryfall.py' vs PRIOR-ART 'adopt Scrython/mtg_parser' (flagged by synthesis); (2) matcher cited as ~210 LOC (CLASSIFY) vs ~600 LOC (PORT) — NOT flagged by synthesis, caught by the evaluator."
  - "Riskiest unverified assumption: the golden-test fidelity gate assumes the archived C# parser's labels are obtainable — confirm before committing to ≥99% agreement as the primary risk control."
  - "Groundedness is high where it matters — CLASSIFY cites C# file:line, CARD-CONTRACT's reuse verdict was independently verified against real edh-engine source by the evaluator."
---

# Campaign Report: Ingestion + Archetype-Parser Data Contracts

**Seed:** the ingestion + archetype-parser data contracts for legacy-engine — everything needed to
design the `ingestion/` and `archetype/` modules and port the archetype classifier to Python.

## Campaign metadata
- **Skill:** `/research-pipeline:deep-research`
- **Shape:** pipeline-mapped, depth 1, 7 parallel specialists (Sonnet) → synthesis (Opus) → evaluation (Opus)
- **Date:** 2026-05-29
- **Output:** `docs/briefs/ingestion-archetype-contracts/` — `parent.md` + 7 specialist briefs + this report
- **Cross-reference edges added by synthesis:** 48 across the 7 briefs
- **Specialist token usage:** ~342K across 7 specialists; synthesis ~112K; evaluation ~110K
- **All briefs enter at `status: draft` (confidence speculative).** Promotion is manual.

## Specialist briefs
| Brief | Stage | Headline |
|-------|-------|----------|
| `fbettega-cache-schema.md` | INGEST | PascalCase `CacheItem {Tournament, Decks[], Rounds[], Standings[]}`; README is stale; provenance by source-dir |
| `mtgoformatdata-rule-schema.md` | RULES | 12 condition types; archetype/variant/fallback; color naming lives in the consumer, not the rules |
| `archetype-matching-algorithm.md` | CLASSIFY | One pure function `ArchetypeAnalyzer.Detect`; no default tie-break (emits `Conflict(...)`); Python pseudocode included |
| `csharp-python-port-strategy.md` | PORT | Vendor rules-as-JSON (pinned SHA) + reimplement only the matcher; golden-test to ≥99% label agreement |
| `scryfall-card-contract.md` | CARD-CONTRACT | Color = lands.`produced_mana` ∩ nonlands.`colors` (NOT `color_identity`); extend edh-engine's scryfall.py |
| `ingestion-ops-and-metashare.md` | SERVE/OPS | We CAN compute our own matchup matrix from `Rounds` (Challenges/paper only; Leagues are decklist-only) |
| `prior-art-scan.md` | PRIOR-ART | No maintained Python port of the matcher exists — this is net-new; adopt the rule DATA + Scrython/mtg_parser |

---

## Evaluator Report (independent, isolated context)

```yaml
evaluation:
  coverage: 5
  coherence: 5
  contradictions: 4   # 5 = none/all-flagged; 1 = serious unflagged conflicts
  groundedness: 4
  recommendations: 4
  overall: 4
  verdict: A strong, unusually buildable brief set — pins every contract end-to-end with real source cites; one genuine unflagged LOC inconsistency and a couple of load-bearing claims rest on inference rather than verification.
```

### Coverage — 5/5
Both modules are design-ready. `ingestion/` fully specified (field-by-field schema with 3 verified
live-file examples, provenance, cadence, incremental detection, the `TournamentRecord` port type, a
GREEN/YELLOW/RED staleness state machine). `archetype/` fully specified (rule schema + verbatim JSON +
exact algorithm with C# line cites + runnable Python pseudocode + the port engineering plan). Thin
spots correctly named as follow-ups: the matchup-matrix *estimator* statistics, the advisory
positioning score (out of scope), the guild-name table and curated `is_free_spell`/`staple_role` tables.

### Coherence — 5/5
Reads as one design. The pipeline seams genuinely join: INGEST's `{Count, CardName}` → CARD-CONTRACT's
name index → CLASSIFY's color+match → SERVE/OPS's meta-% and matchup aggregation. Cross-reference
sections correctly assign ownership at each boundary.

### Contradictions — 4/5
Synthesis caught the material tensions (Scryfall-library reuse verdict; faithful-port vs ML-fallback;
README-stale-casing; matchup headline-vs-caveat; `TwoOrMore*` baton-pass). **One genuine inconsistency
synthesis did NOT flag:** the matcher line count — CLASSIFY says "~210 lines" (`ArchetypeAnalyzer.cs`),
PORT says "~600-line matcher," and parent.md propagated the 600 figure. ~3× divergence on a claim that
drives the effort estimate; likely reconcilable (210 = the one file; 600 = matcher + models + loader +
enum) but no brief says so. Color-computation method and `Rounds.Result` semantics were checked and
found consistent.

### Groundedness — 4/5
High where it matters: CLASSIFY carries C# `file:line` cites throughout; FBETTEGA marks every claim
`[verified <path>]` vs `[inferred from code]`; CARD-CONTRACT cites live 2026-05-29 Scryfall checks and
its central reuse verdict was **independently verified by the evaluator against the real
`edh-engine/ingestion/scryfall.py`** (every named function exists verbatim). Docked to 4 because two
load-bearing claims rest on inference: (a) the **golden-test oracle** assumes the archived C# parser's
labels are obtainable — never confirmed; (b) the `metas.json` era list tops out at 2024-12-16 while a
2026-05-18 commit is cited — possibly stale, uncommented; and the ~174-archetype count / LOC figures
aren't cross-checked.

### Recommendations — 4/5
**Resolve before coding:** (1) verify the golden oracle is actually obtainable — the whole fidelity
strategy depends on it; (2) reconcile the 210-vs-600 LOC figure by opening the archived source; (3)
settle the Scryfall-library question with an ADR (evidence favors EXTEND — edh-engine already implements
every needed function; Scrython matters only on the rare API path, mtg_parser only if a non-fbettega
decklist-text source is ever in scope). **Cover in /architecture:** pin the guild/color-name table as a
vendored artifact (recoverable from `Archetype.cs:43-112`); specify the `metas.json` era-selection logic
for reproducible historical relabels; decide the `Conflict`/`Unknown`/`Other` end-to-end handling
policy. **First follow-up campaign:** a dedicated matchup-matrix-statistics `/research` (Wilson intervals
named, but shrinkage, mirror policy, and bimodal-population bias unspecified) — it's the input to the
advisory layer.

---

## Disposition (Lead Researcher)
The campaign unblocks `/architecture` for the `ingestion/` and `archetype/` modules. Before the port
starts, three items are promoted into the build plan as must-resolve: the **golden-oracle availability
check**, the **Scryfall-library ADR**, and the **LOC reconciliation**. The **matchup-matrix statistics**
`/research` and the pending **advisory-methods** `/research` are the next research items (per
research-plan.md). No brief should be promoted out of `draft` until the golden-oracle question is settled.
