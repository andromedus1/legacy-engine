---
id: bug-card-dimension-localized-and-new-card-gaps
created: 2026-08-04
tags: [bug, ingestion, data]
---

`advise sideboard` / `whattoplay` log a long tail of `unknown card '<name>' — skipping`
warnings that silently shrink the pool. Two distinct causes, both fixable:

**(a) Localized card names are never normalized to English.** Observed in one run
(2026-08-04, `advise sideboard --deck decks/orzhov-energy-overlord.txt`):

```
unknown card 'estocar' / 'Estocar'            -> Swords to Plowshares (pt)
unknown card 'Aldeia de Nevoalta'             -> Mistveil Plains (pt)
unknown card 'Forca de Vontade'               -> Force of Will (pt)
unknown card 'Fim Prismatico'                 -> Prismatic Ending (pt)
unknown card 'Vista Prismatica'               -> Prismatic Vista (pt)
unknown card 'Planicie'                       -> Plains (pt)
unknown card 'Lorien Revelada'                -> Lorien Revealed (pt)
unknown card 'Narset, Rasgadora de Veus'      -> Narset, Parter of Veils (pt)
unknown card 'Forca da Negacao'               -> Force of Negation (pt)
unknown card 'Mago da Conjuracao-relampago'   -> Lightning-Rig Crewmate? (pt)
unknown card 'Perfurar Magica'                -> Spell Pierce (pt)
unknown card 'Теснина' / 'Орала' / 'Пойма' / 'Штурм' / 'Озеро' / 'Завершение' /
             'Терминут' / 'отрицания' / 'Заклинаний' / 'Заклинания'   (ru, truncated)
```

These come in from paper events (Brazilian and Russian tournaments are well represented
in the corpus). Scryfall bulk data carries `printed_name` and foreign-language faces, so
the fix is an alias table built at `seed cards` time keyed on normalized foreign name ->
English `name`, consulted by the decklist parser. Note some Russian entries look
truncated to a single word, so exact-match aliasing will not recover all of them —
those should be counted and reported, not silently dropped.

**(b) Genuinely new cards are missing from the card dimension**, i.e. `seed cards` is
behind the ingested decklists:

```
'Yera and Oski, Weaver and Guide'  'Kraza, the Swarm as One'  'Kavaero, Mind-Bitten'
'Spectral Restitching'  'Phenomena Recorder'  'Fire-Brained Scheme'
'Skittering Kitten'  'Makdee and Itla, Skysnarers'  'Reality Fulcrum'
'Basil, Cabaretti Loudmouth'
```

Ask for both: an explicit **coverage report** rather than per-card WARNING spam —
`// card dimension: 34 unresolved names across N decks (12 localized, 10 new-set,
12 unrecoverable)` — so the size of the hole is visible at a glance and a stale
`seed cards` is obvious.

Third, smaller finding from the same run: the hoser catalog emits
`oracle_text attribution unknown — using fallback attacks=['combo']` for nine promoted
empirical cards — **Clarion Conqueror, Deafening Silence, Disruptor Flute, Forth
Eorlingas!, Jegantha, Meltdown, Price of Progress, Prismatic Ending, Stony Silence**.
That is the existing `idea-hoser-catalog-new-card-gap` metric firing; several of these
(Deafening Silence, Stony Silence, Disruptor Flute, Prismatic Ending) are mainstream
staples whose attack axes are well defined and should just be catalogued.
