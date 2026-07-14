---
id: roadmap-young-regime-data-strategy
created: 2026-07-13
tags: [eras, advisory]
---

**Young-regime / post-disturbance data strategy.** Theme from the 2026-07-13 dogfooding
session: the gap between "disturbance happens" and "era detection confirms" (~weeks) is where
the engine serves its worst data with its most confident face — Mystic Forge's hot marginal
(55.4%, era since 04-20) straddled the Candelabra ban and blended two different decks; camp
coverage collapsed to 4/92 display-grade; the consensus generator averaged a mid-rebuild pool
into a Franken-list. Six related arcs, roughly ordered by leverage:

1. **Provisional eras from registered events** — BAN_EVENTS is ground truth on day one;
   affectedness is mechanically computable (fraction of entity's recent decks playing the
   banned card). Affected entities get a provisional boundary at the ban date immediately
   (marginals + cells split, pre-ban side demoted to prior); detection later confirms or
   dissolves. Pieces exist: report affectedness, flex-band attribution, boundary registry.
2. **Shape-break detection at n=5** — per-deck distance from the pre-event consensus 75 as a
   leading indicator (all 5 post-ban Mystic Forge lists were radically far from the Candelabra
   consensus — knowable at n=2). Gates consensus generation ("pool mid-rebuild, refusing to
   average"), powers the not-current chip, proposes provisional boundaries. Discover machinery
   already vectorizes decklists.
3. **Never print a straddling number unblended** — any marginal/cell whose window crosses a
   registered event renders split: "era 55.4% = pre-ban 52% (n=180) · post-ban 71% (n=33,
   speculative)". Divergence-as-diagnostic applied to time.
4. **Imputation-share on every ranked row** — decompose S into measured-cells vs prior
   contribution: "S=0.68 (92% imputed)". Self-labeling; replaces hand-built measured/quarantine
   table splits (see decks/best-deck-best-call-ranking.html, built manually 2026-07-13).
5. **Graded prior handoff** — extend the existing pre-disturbance-value anchoring with
   affectedness-weighted decay: untouched decks carry pre-ban cells at near-full weight into a
   new era; rebuilt decks discounted hard. Attacks the post-ban coverage collapse (most of the
   field wasn't changed by the ban).
6. **`report early-regime` surface** — per archetype post-event: placement-weighted record,
   shape-break flag, provisional era status. One command replacing the hand-assembly done for
   Mystic Forge (Challenge 6-2 3rd + 4-2 10th, three shells).

Arcs 1-3 are one coherent unit: "let registered events do immediately what detection does
eventually." Related parked items: [[idea-eras-alarm-stale-after-registration]],
[[idea-ranking-imputation-quarantine]], [[idea-consensus-ban-aware-shell-coherent]].
