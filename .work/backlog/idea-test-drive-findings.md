---
id: idea-test-drive-findings
created: 2026-06-13
tags: [advisory, generation, analytics]
---

Findings from test-driving the shipped engine on the real Dimir Tempo deck (2026-06-13), re-doing the
manual analysis. The engine WORKS and the new features reproduced/refined the manual conclusions
(generate doctor matched every count call + caught the 3-Scalding-Tarn outlier; report meta --venues
--regime current reproduced online Tron 12.9% vs paper 2.2%, spread 0.106; advise refresh ran
end-to-end with the honest primer). But the drive surfaced real quality gaps:

1. **(Medium) `report meta --venues` defaults to FULL-CORPUS, not the current regime.** The venue
   comparison showed regime-blended data (Dimir Reanimator 10%, Tron 1%) until `--regime current` was
   added (then Tron 12.9% vs 2.2%). The deck-based `report meta` full-corpus default is by design, but
   the NEW `--venues` comparison surface is precisely where ban-regime honesty matters most — it should
   default to current-regime (or loudly warn that it's full-corpus). Undercuts the regime-windowing work.
   Relates to [[idea-ban-regime-everywhere]] / feature-regime-windowing-consistency.

2. **(Medium) The field-tuner over-fits in `advise refresh`.** It cut all 3 Nethergoyf + 3 Scalding Tarn
   for 4 Marsh Flats + 2 more Bauble (→ 0 Nethergoyf, 4 Bauble, 4 Marsh Flats) on tiny presence-
   correlational lifts — then the SAME report's card-count-outlier section flags "Marsh Flats: you run 4,
   field modal 0" and "Bauble: you run 4, field modal 0", contradicting its own tuner. Either damp the
   greedy tuner (it shouldn't cut a mode-3 core card like Nethergoyf to 0) or have refresh reconcile the
   tuner output against the outlier check before presenting. The tuner's "indicative not precise" caveat
   isn't enough when the output is visibly self-contradictory.

3. **(Medium) The recommended sideboard ignores field SB staples.** advise refresh recommended
   4 Grafdigger's Cage + 3 Nihil Spellbomb + 4 Duress + 4 Hydroblast — graveyard-heavy and far from field
   consensus; the outlier section flags Force of Negation (field modal 2, you run 0) and Consign to Memory
   (modal 2, you run 0) as missing. Even with the empirical-pool filter (feature-archetype-empirical-
   recommendations), the recommender diverges hard from what real Dimir Tempo boards run. Investigate why
   the empirical pool / coverage solver isn't surfacing FoN/Consign. Relates to
   [[idea-archetype-empirical-followups]].

4. **(Low) Venue divergence note is too verbose** — it lists every archetype's spread/tier on one line.
   Truncate to the top-N high-spread rows (the summary table below it already does the useful part).
