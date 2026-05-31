---
id: improve-positioning-pbest-uneven-sample
kind: feature
stage: drafting
tags: [advisory]
parent: epic-advisory-hardening
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Positioning P(best) is biased toward thin-matchup-data decks

## Brief
Found running `rank_decks` on the current-meta window (post-2025-11-10, 174 events). `P(best)` ranked
**Death & Taxes (2.7% share, 3/9 measured cells) at 37.7%** and Energy/Lands high, while the three
best-measured, most-played decks (Dimir Tempo, Izzet Delver, Show and Tell — 9/9 cells n≥30) sat at
**~0.0–0.1%**. That ordering is an artifact, not signal.

## Root cause
`positioning._sample_S` imputes no-data opponents (mean-vs-known, weak Beta) and samples Beta cells. A deck
with **few measured cells** has a **high-variance** S posterior (most of its field is imputed with wide
uncertainty). In the shared-field MC, `rank_decks` takes the argmax across decks per draw — so the
high-variance (thin-data) decks spike to "the max" far more often than well-measured decks whose S is
tightly centered near 50%. `P(best)` therefore **rewards uncertainty**, exactly backwards, whenever the
candidate set mixes well-sampled and thinly-sampled decks (the normal case for a real metagame).

## How to apply
- **Gate or down-weight candidates by matchup-data sufficiency** before/within ranking: require a minimum
  fraction of measured (n≥`DISPLAY_GATE_N`) cells against the field mass, or weight a deck's draw
  contribution by its effective sample. Surface excluded/low-data decks separately ("insufficient matchup
  data to rank"), never silently mixed in.
- Consider reporting **risk-adjusted rank** (lower posterior quantile, the existing `risk_averse` path) as
  the default headline rather than raw `P(best)`, since it penalizes the thin-data spikes.
- Add a `data_coverage` field to `PositioningResult`/`DeckRanking` (measured-cell fraction vs the field)
  so consumers and `report` can label/condition on it — consistent with the confidence-gating principle.
- Recalibrate against the real corpus: the well-measured top decks should rank sensibly; thin-data decks
  should be flagged, not crowned.

## Foundation references
- `docs/briefs/advisory-methods.md` — §2 (ranking under uncertainty, P(best) from shared-field draws, the
  n<30 display gate). The gate exists for display; this asks it to also inform ranking.
- Source: `src/legacy_engine/advisory/positioning.py` (`_sample_S` imputation, `rank_decks` argmax).

## Notes
Route through `/feature-design`. Not a shipped-pillar blocker — meta-share + the matchup matrix (with its
n/tier labels) are reliable; this is about making the *ranking* honest under uneven sample sizes. Workaround
today: read the matchup matrix + S only for decks with dense cells (the analysis that surfaced this did so).

## Design decisions (--only-questions, 2026-05-30)
- **Default headline ranking = risk-adjusted lower-posterior-quantile (mean−variance)** (user-directed),
  which naturally penalizes thin-data spikes. Keep raw `P(best)` as a *secondary* reported view, not the
  headline. Still attach a `data_coverage` field (measured-cell fraction vs the field) to
  `PositioningResult`/`DeckRanking` so consumers can see/condition on sufficiency. The existing
  `risk_averse` lower-quantile path becomes the default sort; ties handled evenly (see the argmax-ties bug
  in [[fix-advisory-peer-review-bugs]]).
