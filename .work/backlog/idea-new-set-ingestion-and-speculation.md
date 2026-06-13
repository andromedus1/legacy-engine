---
id: idea-new-set-ingestion-and-speculation
created: 2026-06-13
tags: [ingestion, analytics, methodology]
---

**Regularly scan for upcoming set/edition releases and ingest their cards on release** — then provide
a way to **speculate on a new card's usefulness when there is no historical tournament data yet.**

Two parts:

1. **Release-aware ingestion.** Track the MTG release calendar (sets, Secret Lairs, supplemental
   products with Legacy-legal cards) and, on/after each release, pull the new cards into the `cards`
   table (Scryfall is already the ingestion source). Goal: the engine never reasons about a stale
   card universe and can recognize/parse decklists the moment new cards see play. Probably a
   scheduled scan + a "new cards since last ingest" diff.

2. **No-history speculation method.** A brand-new card has zero match results, so the engine's
   normal presence-correlational / matchup math is blind to it (it would sit at the `speculative`
   confidence floor forever — see confidence-metadata). We need a deliberate forecasting path:
   - score by intrinsic features derived from oracle_text + stats (CMC, card type, keywords, role
     tags) — leans on [[idea-oracle-text-grounded-reasoning]] for structured interaction facts;
   - compare to the nearest *analogous existing cards* and borrow their empirical signal as a prior;
   - clearly label all such output as **speculative / pre-data forecast**, never as established —
     consistent with the honesty posture in [[idea-ban-regime-everywhere]].

Why it matters: a new set can reshape the meta overnight, and that's exactly when the player most
wants guidance and exactly when historical data is absent. Also relevant: a new set IS effectively a
soft ban-regime shift in impact, even without a B&R announcement. Natural future consumer of the
[[idea-deck-tuning-refresh-workflow]] (flag "new cards to test this week").
