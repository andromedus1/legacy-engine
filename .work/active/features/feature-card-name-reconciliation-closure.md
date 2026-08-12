---
id: feature-card-name-reconciliation-closure
kind: feature
stage: drafting
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
