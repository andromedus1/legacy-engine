---
id: idea-consensus-blends-exclusive-build-clusters
created: 2026-08-05
updated: 2026-08-05
tags: [generation, consensus, honesty]
---

`generate consensus` takes per-card modes across the whole archetype pool, so when a pool contains
two **mutually exclusive build configurations** it emits a blend that no player runs — and it
reports the result as a clean 60/15 with `// Legality: OK`, giving no signal that the pool was
bimodal.

Observed 2026-08-05 on `Oops! All Spells` (window since 2026-05-25, n=42, `evolving`). The pool is
two disjoint builds:

```
tsz  pact  decks          (Thoughtseize / Summoner's Pact maindeck counts)
  0     4     17          "Pact build"     — 0 Thoughtseize, 4 Summoner's Pact
  4     0     22          "Discard build"  — 4 Thoughtseize, 0 Summoner's Pact
  -     -      3          neither
```

The two cards **never co-occur**. Whole-pool consensus emitted **1 Thoughtseize** and no
Summoner's Pact. Of the 22 decks that run Thoughtseize, *all 22 run exactly 4*; **zero decks in the
corpus run 1**. The emitted card count is not a compromise between the builds — it is a count that
does not exist in the data, produced by a card that's in 52% of decks landing at a low mode after
reconciliation.

This is the same failure the copy-count study already documented for sideboards ("the engine's raw
1-of hedge spread", 2026-07-04), but here it is structural rather than a taper artifact: the pool
has two centroids and the mode operator collapses them.

**What made the deliverable work instead.** Scoping the consensus to one cluster produced a list
with no reconciliation guesswork at all — the Pact cluster is unanimous on 22 of 24 maindeck slots
across 17/17 decks and its modal counts sum to **exactly 60 main + exactly 15 side**. The Discard
cluster's modes sum to **64**, i.e. that cluster genuinely has no agreed list and the four cuts are
a judgment call. Those two facts are exactly what a user needs to know and neither is currently
surfaced.

Sketch of what would help, roughly in order of value:

1. **Detect bimodality and say so.** Anti-correlated card pairs within a pool (co-occurrence far
   below the product of their inclusion rates) are a cheap signal. Emit an audit line naming the
   split and its sizes rather than silently averaging:
   `// ⚠ POOL IS BIMODAL: Thoughtseize(4x, n=22) and Summoner's Pact(4x, n=17) never co-occur —
   consensus below blends two builds; pass --cluster to scope`
2. **`--cluster` / cluster-scoped consensus**, so the operator can generate the coherent list per
   configuration instead of hand-querying it.
3. **Report whether the cluster's modes actually reconcile** — "modal counts sum to 64, 4 cuts are
   judgment" is a first-class honesty fact, distinct from the current silent reconciliation.
4. **Never emit a copy count that appears in zero corpus decks** for that card, or if forced to,
   label it.

Note the archetype's discovery camps do *not* solve this: `discover run` clusters the flex band and
did not separate these two builds, so the cluster that matters here had to be found by hand-querying
`deck_cards`. Whether this belongs in discovery or in consensus is part of the question.

Related: `bug-consensus-ignores-companion-deck-size` (another case of consensus emitting a
structurally impossible list with a passing legality banner), `feature-min-viable-copy-count`.
