---
source_handle: card-semantics-ir-mtg-grammar-blog
fetched: 2026-07-31
source_url: https://hudecekpetr.cz/a-formal-grammar-for-magic-the-gathering/
provenance: source-direct
source_class: blog-post
---

# Petr Hudeček — "A formal grammar for Magic: the Gathering"

## Summary

A practitioner report on writing an ANTLR4 formal grammar for MTG card text. Scope: the
grammar handles all 273 cards of one Standard set (Guilds of Ravnica) — a deliberately
bounded, single-set corpus, not the full game. The documented failure modes are the
canonical reasons full-grammar approaches stall: referent/pronoun ambiguity ("those
creatures" resolving to the wrong antecedent on Beamsplitter Mage without contextual
constraints), templating exceptions where an assumed universal template has counterexamples
(the "[object] gains [abilities] until [something happens]" template broken by Chance for
Glory's "Creatures you control gain indestructible" — no "until"), and structural ambiguity
in noun compounds ("a basic Forest" supertype+subtype vs "Plains card" subtype-only). The
author additionally documents seven specific cards needing special handling within even this
273-card scope. Relevance: quantifies how quickly per-card exceptions accumulate under a
grammar approach, supporting a facet-extraction (rather than full-parse) IR for a
35k-card corpus.

## Key passages

> It handles all 273 cards of Guilds of Ravnica, the most recent Standard set as of now.
> — § opening

> I thought that the template '[object] gains [abilities] until [something happens]' would
> work for all ability-gaining abilities, but Chance for Glory reads, 'Creatures you control
> gain indestructible.' There's no 'until.' — § difficulties (templating inconsistency)

> On Beamsplitter Mage, "the parser sees the phrase 'those creatures'" and resolves its
> referent incorrectly by missing contextual constraints like "if you control".
> — § difficulties (pronoun/referent ambiguity, paraphrase-adjacent extraction)

## Structural metadata

Personal blog post; sections: approach (ANTLR4 grammar producing parse trees), worked
difficulties per card, acknowledged limitations (seven cards with workarounds, including
Aurelia and Pelt Collector). Companion repository: github.com/Soothsilver/mtg-grammar
("ANTLR4 grammar for all Magic: the Gathering cards in Guilds of Ravnica").
