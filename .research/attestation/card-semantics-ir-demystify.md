---
source_handle: card-semantics-ir-demystify
fetched: 2026-07-31
source_url: https://raw.githubusercontent.com/Zannick/demystify/master/README
provenance: source-direct
source_class: standard
---

# Demystify — a Magic: The Gathering parser (Zannick/demystify README)

## Summary

Demystify is the longest-lived community attempt at a general MTG card-text parser: an ANTLR
3.5 grammar plus Python driver whose stated goal is "to make it possible for a computer to
understand what general Magic: The Gathering cards do." The README documents a heavyweight
toolchain (Java + ANTLR 3.5 + ANTLR3 Python3 runtime), grammar files regenerated from a
keywords module, and a load pipeline that reads Scryfall card data. GitHub's license
detection reports "Other/NOASSERTION" at the repo level (COPYING/COPYING.LESSER files are
present, indicating GPL/LGPL-family licensing). Relevance as prior art: a full-corpus
grammar parser for MTG exists only as a perpetually in-progress project with a substantial
build apparatus — corroborating (alongside the single-set mtg-grammar effort) that
full-text parsing of the entire oracle corpus is a research project in itself, not an
implementation detail to inline into an advisory engine.

## Key passages

> Demystify is an attempt to make it possible for a computer to understand what general
> Magic: The Gathering cards do. It is currently written in a combination of ANTLR 3.5 and
> Python 3.2. — README §1 ABOUT

> To build the parser generator, you need to have the macro.g and Words.g grammar files
> up-to-date. If they don't exist, or demystify/keywords.py has changed, run
> $ python3 demystify/keywords.py to regenerate them. — README §3 BUILDING

> Loads the card data from the Scryfall data file in demystify/data/cache/ — README §4 RUNNING

## Structural metadata

Plain-text README (no extension) at repo root; sections: ABOUT, INSTALLATION, BUILDING,
RUNNING. Repo root also carries COPYING and COPYING.LESSER. GitHub repo description: "A
Magic: The Gathering parser"; license per GitHub API: spdx_id NOASSERTION ("Other").
