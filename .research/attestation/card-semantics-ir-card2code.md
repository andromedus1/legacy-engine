---
source_handle: card-semantics-ir-card2code
fetched: 2026-07-31
source_url: https://arxiv.org/abs/1603.06744
provenance: source-direct
source_class: paper
version: arXiv:1603.06744 (ACL 2016)
---

# Ling et al. 2016 — "Latent Predictor Networks for Code Generation" (arXiv:1603.06744)

## Summary

The ACL 2016 paper that created the card2code datasets: paired corpora mapping collectible
card game cards (Magic: the Gathering and Hearthstone) to their implementing code, used to
train neural models that generate a card's engine code from its structured fields plus rules
text. This is the academic anchor for the "oracle text → executable semantics" task: the
authors frame card implementation as generating "programming code from a mixed natural
language and structured specification," which is exactly the extraction problem an IR
pipeline automates in bounded form. The paper's existence (and the MTG dataset's source
being Forge-style card implementations) evidences that per-card machine semantics at corpus
scale has been treated as a supervised-learning problem over exactly the kind of per-card
capability DSL Forge maintains.

## Key passages

> Using this framework, we address the problem of generating programming code from a mixed
> natural language and structured specification. — Abstract

> We create two new data sets for this paradigm derived from the collectible trading card
> games Magic the Gathering and Hearthstone. — Abstract

> On these, and a third preexisting corpus, we demonstrate that marginalising multiple
> predictors allows our model to outperform strong benchmarks. — Abstract

## Structural metadata

arXiv abstract page; authors Wang Ling, Edward Grefenstette, Karl Moritz Hermann, Tomáš
Kočiský, Andrew Senior, Fumin Wang, Phil Blunsom (DeepMind/Oxford). Published at ACL 2016.
Dataset release known as card2code (github.com/deepmind/card2code).
