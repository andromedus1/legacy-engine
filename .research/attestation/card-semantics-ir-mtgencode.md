---
source_handle: card-semantics-ir-mtgencode
fetched: 2026-07-31
source_url: https://raw.githubusercontent.com/billzorn/mtgencode/master/README.md
provenance: source-direct
source_class: standard
---

# mtgencode (billzorn) — README

## Summary

mtgencode is the canonical "cards for neural nets" preprocessing project: it converts MTGJSON
card data into a normalized, machine-learnable text encoding and decodes model output back to
human-readable formats. Its self-description is explicit that the work is text-format
wrangling, not semantics: the encoding regularizes surface text (field ordering,
symbol/number normalization) so sequence models can learn card *shape*. Relevance as prior
art: the neural-generation lineage around MTG cards (mtgencode → RNN card generators) treats
oracle text as a token stream and never produces a queryable semantic representation — it is
the opposite end of the design space from a typed-facts IR, useful to cite as the boundary of
what text-normalization alone buys.

## Key passages

> Utilities to assist in the process of generating Magic the Gathering cards with neural
> nets. — README, header

> The purpose of this code is mostly to wrangle text between various human and machine
> readable formats. The original input comes from mtgjson; this is filtered and reduced to
> one of several input formats intended for neural network training... — README, intro

> This code does not have anything to do with neural nets; if you want to generate cards with
> them, see the tutorial. — README § Requirements

## Structural metadata

GitHub README.md; driver scripts encode.py / decode.py; references the mtgsalvation RNN
card-generation thread as origin. Python 2.7-era project (states it does not work with
Python 3).
