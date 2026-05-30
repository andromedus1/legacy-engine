---
id: epic-archetype-classifier
kind: epic
stage: drafting
tags: [archetype]
parent: null
depends_on: [epic-foundations-card-data, epic-tournament-ingestion]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Archetype Classifier

## Brief

The novel subsystem and the key architectural delta from edh-engine: Legacy decklists are bare 75-card
lists with no commander key, so archetype labeling is a *classification* problem. This epic wraps
Badaro's MTGOFormatData rules (vendored as pinned JSON) and reimplements the MTGOArchetypeParser
matcher in Python, then labels every ingested decklist into the community taxonomy.

Covers: vendoring the rules-as-JSON pinned to a commit SHA (+ a `refresh` flow that diffs upstream and
fails fast on unknown condition types), the typed rule loader (12 condition types, archetype/variant/
fallback), the matcher port (`classify(decklist, ruleset, card_colors) → ArchetypeResult`; AND-test,
Conflict handling, nested variants, ≥10%-overlap fallback, else Unknown), deck-color computation, the
labeler that persists `archetype_labels`, and the **golden-test harness** asserting ≥99% label
agreement against the archived C# parser. Carries the must-verify **golden-test-oracle open question**
(can we obtain the archived parser's published labels? — fallback: hand-curated fixtures).

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/mtgoformatdata-rule-schema.md` — the rule-as-data schema (conditions, variants, fallbacks, color flags, taxonomy).
- `docs/briefs/ingestion-archetype-contracts/archetype-matching-algorithm.md` — the exact matching algorithm + Python pseudocode + the input/output contract.
- `docs/briefs/ingestion-archetype-contracts/csharp-python-port-strategy.md` — vendor-rules + reimplement-matcher + golden-test plan; fail-fast drift handling.
- `docs/briefs/ingestion-archetype-contracts/prior-art-scan.md` — no maintained Python port exists; this is net-new.

## Foundation references
- `docs/ARCHITECTURE.md` — `archetype/` module (rules, colors, matcher, labeler, golden_test); the open-question dispositions (golden-oracle, matcher LOC).
- `docs/SPEC.md` — Archetype, ArchetypeRule, Condition entities.
- `docs/PRINCIPLES.md` — knowledge compiled not re-derived; fail-fast on unknown condition type.

## Anticipated child features
- Vendor MTGOFormatData rules (git subtree @ SHA + RULES_MANIFEST + `legacy refresh rules` diff/fail-fast)
- Typed rule loader (12 condition types; archetype/variant/fallback)
- Matcher port (`classify`; ConditionTests ports 1:1 as a parametrized suite)
- Deck-color computation (lands ∩ nonlands; guild/shard naming table)
- Labeler (resolve → colors → classify → persist labels)
- Golden-test harness (≥99% agreement vs archived C# parser; fallback fixtures) — resolves the golden-oracle open question
