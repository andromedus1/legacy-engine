---
id: fix-shrinkage-triple-display
kind: story
stage: done
tags: [analytics, honesty]
parent: null
depends_on: []
release_binding: v0.4.0
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Shrinkage triple-display: raw WR always travels with the shrunk estimate

## Brief
Three analysis mirages in one day traced to displaying Beta-Binomial posteriors as if they were
records (Azorius floor mirage; Lands "worst matchups look even" — camp cell shown 43.2% where the
raw record was 28.6% on n=7; camp-vs-parent S* compression). The α=β=7.5 prior is sound for
estimation; the display convention was the deception. New convention: **shrunk%|raw% n=** triple
everywhere a matchup estimate prints.

## Changes
- `report matchups` grid cells: `54%|54% n=392` + a legend line ("small n is pulled toward 50%").
- H2H reverse line gains raw; the forward block already carried both.
- viz matchup-row tooltip gains "Win rate (raw)".
- Goldens updated — and the fixture itself vindicated the change: the old golden displayed 16.7%
  where the raw record was 2.8% (1-35).

## Review (2026-07-11)
Merged CI-green; goldens updated to the new contract; the fixture's 1-35 cell displayed-as-16.7% case is the canonical proof. Done.
