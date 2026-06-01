---
id: idea-regime-aware-advisory
created: 2026-06-01
tags: [advisory, analytics, correctness]
---

The advisory pillar — `analytics/matchup.build_matrix`, `analytics/match_results.compute_match_results`,
and everything downstream (`advisory/positioning` best-deck/best-call, `report matchups`, `advise *`,
`report gaps`) — is computed over the FULL CORPUS and is NOT ban-regime / banlist aware. `compute_match_results`
takes no `since/until` (windowed wrw already raises NotImplementedError for this reason). Consequence: after a
format-defining ban, the advisory layer is STALE and actively wrong — e.g. with data through 2026-05-30 the
full-corpus positioning ranked **Dimir Reanimator the #1 best deck AND best call**, but the Entomb ban
(2025-11-10) had already collapsed it from 9.1% → 0.1% share; it is dead in the current format. The meta-share /
`trends` layer IS regime-aware and correctly shows the decline, so the engine contradicts itself between layers.
Fix direction: make the matchup matrix + positioning regime/window-aware (thread `since/until` through
`compute_match_results` → `build_matrix` → `positioning`/`rank_decks`/`gaps`; add `--since/--regime` to
`report matchups`/`advise`/`report gaps`), and/or recency-weight cells so post-ban data dominates. Also add
`--since`/`--regime` to `report meta` (currently un-windowed; only `trends` windows). Gate on the current regime
having enough rounds-bearing data (the post-Undercity-Informer regime had only 16 rounds-events / 483 decisive
rounds 12 days in — thin), degrading honestly to "regime too new for reliable matchup math" when it doesn't.
Likely a small epic. Surfaced 2026-06-01 while spinning the engine for a meta read.
