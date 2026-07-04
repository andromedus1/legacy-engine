# Dimir Tempo vs Doomsday Tempo — cross-meta comparison (2026-07-04)

Stage 4 of the deck-prep arc. Decks: [dimir-tempo-optimized](dimir-tempo-optimized.txt) vs
[doomsday-tempo-local](doomsday-tempo-local.txt) / [-online](doomsday-tempo-online.txt).
Method: `advise compare` (adaptive ban-aware matrix, MC field EV, 20k draws) + `advise
positioning --candidates` (seed 42) per meta. All numbers are leans — every CI pair overlaps.

## Verdict shape (never blended across venues)

| Lens | the local meta (107-player paper room) | Online (top-15 field, 75% mass) |
|---|---|---|
| Field EV — Dimir Tempo | **50.9%** [41.3, 60.1] | 48.5% [36.6, 59.9] |
| Field EV — Doomsday | 49.6% [40.1, 59.4] | **50.4%** [39.0, 62.7] |
| P(Dimir beats Doomsday) | **0.56** | 0.37 |
| Positioning rank | Dimir #4 (S*=0.508) vs Doomsday #6 (0.498) | Doomsday **#1** (0.580) vs Dimir #3 (0.534) |
| Matchup-data coverage | A=64% / B=58% | A=52% / B=45% (Tron 15.6% imputed) |

**The venue divergence is the finding**: the blue-heavy local room (Izzet 11.2% + S&T 10.3%
+ mirror + Jeskai/Azorius) is exactly where Dimir Tempo's cells are strongest (Izzet 55%,
S&T 62%) and Doomsday's weakest (Izzet 41.5%); the online field's Tron/Lands/D&T/Reanimator
mass inverts it (Doomsday: D&T 68.8%, Lands 54.6% — Dimir: 35.7%, 36.1%). This also reverses
the 2026-06-27 regime-clean lean (then: Doomsday 0.501 > Dimir 0.483 on the local meta) — that run
predated 3× corpus growth AND used the earlier field snapshot; the flip is data movement, not
methodology drift.

## Head-to-head

Dimir Tempo 54.0% vs Doomsday directly (thin cell, n<30 — present-but-unreliable marker).
The tempo pilot is slightly favored in the pseudo-mirror; both decks' worst shared enemy is
Death & Taxes (35.7% / — vs Doomsday's 68.8%, the single biggest divergence cell).

## Caveats (analysis-statistical-context-gates)

- **Archetype-level cells, not variant-level**: "Doomsday" in the matrix is ALL Doomsday
  (tempo+turbo+residue). The tempo camp shares Dimir's Tamiyo/Murktide shell, so its true
  cells vs blue decks may sit closer to Dimir's — the harder-tempo-pivot hypothesis remains
  LIVE and untested. The persisted variant labels now make variant-conditioned matchup cells
  feasible (n=47/49 — speculative, but computable); parked as a follow-up.
- Imputed cells carry field mass online (Tron 15.6%, Energy 8.6%, Reanimator 8.4% all `*`) —
  the online EV gap (1.9pts) is well inside imputation noise. The positioning ranking
  (Doomsday #1 online) leans the same way independently, which is why the venue verdict
  holds direction while its magnitude stays soft.
- MC CIs are wide (±10pts); P(A>B)=0.56/0.37 are the honest summary statistics, not the EVs.

## Practical delta (collection + cost)

- **Dimir Tempo: fully owned, zero acquisitions** (stage 1). Sleeve tonight.
- **Doomsday Tempo: 14 maindeck names not fully owned** (incl. 1 LED ≈ $814-class, 4
  Doomsday, ritual/petal kit) + 5 cheap SB cards. The binder's dual-land accounting gap
  (plays 4 Underground Sea, binder lists none) must be reconciled before trusting land math.

## Bottom line

For the local room the maintainer actually plays in: **stay Dimir Tempo** — favored lean in the
venue's blue field, zero cost, established-tier board validation. Doomsday (tempo camp) is
the ONLINE lean and remains the field-contingent option it was in June — now with a cleaner
trigger: adopt if the local meta's composition drifts from blue tempo toward D&T/Lands/Tron-style
fair-prison mass (the exact cells that flip the comparison).
