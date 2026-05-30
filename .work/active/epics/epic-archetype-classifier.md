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

## Design decisions
*(Captured via `/epic-design --only-questions`, 2026-05-29 — locked inputs for the feature-design pass; do not re-ask.)*
- **Golden-test oracle:** **Both — fixtures now, C# corpus as follow-up.** Build the matcher golden-tested against hand-curated label fixtures (a few dozen community-consensus-labeled Legacy decks) so the epic isn't blocked on the archived .NET 8 binary. Add a **separate follow-up story** to attempt the full C#-parser golden corpus (≥99% agreement) *if* the binary proves runnable / labels are recoverable. Resolves the campaign's must-verify item pragmatically (don't block; strengthen later).
- **Conflict/Unknown handling:** **Store the raw matcher label faithfully** — persist exactly what the C# engine emits (`Conflict(A,B)`, `Unknown`) into `decks.archetype`. Keeps the port a faithful, golden-testable replica; the **analytics/meta-share epic owns the bucketing policy** (Conflict→review, Unknown→"Other"). Do NOT bake PreferSimpler or Unknown→Other into the classifier.
- **Fallback tier:** **Rules-only for now.** Match the community pipeline exactly (MTGOFormatData rules + fallback piles); `Unknown` is honest signal. No ML/statistical tier — revisit only if the real-data Unknown rate proves high.
- **Rules vendoring (settled, not a fork):** vendor MTGOFormatData's `Formats/Legacy/` JSON pinned to a commit SHA in a manifest (`config.RULES_PINNED_SHA`); `legacy refresh rules` pulls + diffs upstream; unknown condition `Type` fails fast at load (mirrors the foundation's fail-fast convention).

## Anticipated child features
- Vendor MTGOFormatData rules (git subtree @ SHA + RULES_MANIFEST + `legacy refresh rules` diff/fail-fast)
- Typed rule loader (12 condition types; archetype/variant/fallback)
- Matcher port (`classify`; ConditionTests ports 1:1 as a parametrized suite)
- Deck-color computation (lands ∩ nonlands; guild/shard naming table)
- Labeler (resolve → colors → classify → persist labels)
- Golden-test harness (≥99% agreement vs archived C# parser; fallback fixtures) — resolves the golden-oracle open question
