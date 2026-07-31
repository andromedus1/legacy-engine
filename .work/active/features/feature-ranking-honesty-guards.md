---
id: feature-ranking-honesty-guards
kind: feature
stage: drafting
tags: [advisory, analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Ranking honesty guards — imputation quarantine + regime-currency warning

## Brief

Two honest-degrade gaps in the ranking/field surfaces, both dogfooding-verified: (1)
`rank_decks`' headline sort can crown a deck on pure marginal-winrate imputation
(Mystic Forge #1 with data_coverage=0.00) — ranking needs an imputation quarantine so
imputation-dominated rows are partitioned/labeled, not silently blended; (2) field-load
should surface a regime-currency % and warn when a custom field's implied window is
dominated by a prior ban regime (the maintainer's "last 4 months" local field was only ~29%
current-regime). Also absorbs the residual of roadmap-young-regime-data-strategy — the
young-regime serving posture (the weeks between disturbance and era confirmation are
where the engine serves its worst data with its most confident face); the structural spine
shipped in epic-stable-era-windows, this feature owns the remaining presentation-layer
honesty. Full member texts below.

## Member findings (absorbed from backlog)

---

### idea-ranking-imputation-quarantine


**Ranking surfaces need an imputation quarantine.** `rank_decks`' headline Q25 sort put Mystic
Forge Combo #1 overall (S=0.83 at min_row_share default / 0.68 at 0.003, P(best)=0.85) with
`data_coverage=0.00` — pure marginal-winrate imputation, zero measured cells vs the current
field. The CLI suppresses P(best) below 5% coverage but S itself carries the same noise. Any
ranking surface (`advise positioning --candidates-file`, future reports) should split measured
vs imputation-only rows (the hand-built `decks/best-deck-best-call-ranking.html` from the
2026-07-13 session did this manually), and surface n<30 thin cells as labeled leans instead of
hiding them entirely — at camp level only 4 of 92 camps have any display-grade cell vs the
young post-ban field, so thin-cell leans are most of the available signal.

---

### idea-regime-currency-warning


**Surface a "regime-currency %" on field-load, and warn when a custom field's implied
window is dominated by a *prior* ban regime.**

Found dogfooding (2026-06-27): the maintainer's "last 4 months" local organizer data spans two ban
regimes — only **~29%** of it is the current (Undercity Informer, 2026-05-18→) regime;
**71%** is the prior post-Entomb/Nadu regime. We built a custom `--field` file from that
4-month aggregate and ran best-deck/best-call on it. The conclusion **flipped** under
regime correction: Dimir Tempo ranked *above* Doomsday on the polluted field (0.507 vs
0.488) but *below* it on a regime-clean current field (0.483 vs 0.501). Nothing in the
tool flagged that the field was ~1/3 quality.

What to add:
- When `_load_field` ingests a custom field with per-line counts (or when building the
  global field over a window), compute and print a **regime-currency %**: the share of
  the contributing data that falls in the current ban regime (use the same
  `regime_windows()` the trends/affectedness code already uses).
- **Emit an honest-degrade warning** when regime-currency < ~50% (e.g.
  `// [warn] field is 29% current-regime (71% prior regime 'after Entomb...'); composition
  may not reflect the current meta — consider windowing to the current regime`).
- Reinforce the existing guardrail in docs/help: **window the FIELD composition to the
  current regime, but keep the MATCHUP MATRIX adaptive** — `--regime current` on the matrix
  collapses coverage to ~0% (26-day window starves n≥30 cells). The two windows are
  independent and should be set independently.
- Stretch: a `--regime-window` flag on field-load that reweights a multi-regime custom
  field toward the current regime using the engine's own composition movers, for cases
  where the user only has a blended aggregate (the maintainer's local-meta data can't be split).

Related honesty gaps from the same session: [[idea-archetype-conditioned-card-winrate]],
idea-acquire-color-identity-filter. Methodology lives in the user-memory
`analysis-statistical-context-gates`.

---

### roadmap-young-regime-data-strategy


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
