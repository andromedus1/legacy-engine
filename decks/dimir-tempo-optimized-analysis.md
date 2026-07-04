# Dimir Tempo — sideboard optimization analysis (the local meta, 2026-07-04 refresh)

Companion to [dimir-tempo-optimized.txt](dimir-tempo-optimized.txt) (Board A) and
[dimir-tempo-optimized-owned.txt](dimir-tempo-optimized-owned.txt) (Board B — converges, see §6).
Engine: post-sweep scorer (deterministic ILP, PR #35; equal-objective ties no longer vary
run-to-run). Regenerate: `advise sideboard --deck decks/dimir-tempo-current.txt --field
decks/local-field-since-518.txt --collection decks/binder.txt --smart` and `advise backtest
--archetype "Dimir Tempo" --field decks/local-field-since-518.txt --field-scope`.

**Data currency**: corpus refreshed 2026-07-04 to **2026-07-01** (was capped 2026-06-15), all
regime decks labeled. Dimir Tempo current-regime pool 71→125 decks. Backtest winner sample
**n=263 field-scoped top-finisher boards — ESTABLISHED tier** (283/449 candidate tournaments
excluded as off-the local meta-field). Confounds (always): winning boards are self-selected and
metagame-lagged; adoption %s validate, never drive, the scores.

## 1. The board (15) — and what changed

| Card | Copies | Winners' adoption | Winners' copy mode | Basis |
|---|---|---|---|---|
| Force of Negation | 2 | 99.2% | 2 | engine core (pitch: 2nd copy is fuel) |
| Consign to Memory | **3** ↑ | 95.4% | **3** (169/251) | engine core + 3rd copy judgment (see swap) |
| Hydroblast | 2 | 85.9% | 2 | engine core (via functional twin BEB) |
| Sheoldred's Edict | 1 | 52.1% | 1 | engine core |
| Engineered Explosives | 1 | 47.9% | 1 | engine core |
| Null Rod | 1 | 33.5% | 1 | engine core |
| Dauthi Voidwalker | 1 | 31.9% | 2 | engine core |
| Snuff Out | 1 | 30.0% | 1 | engine core |
| Harbinger of the Seas | 1 | 25.9% | 2 | engine core |
| Barrowgoyf | 1 | 84.0% | 2 | judgment fill (tracked blind spot) |
| Toxic Deluge | 1 | 63.1% | 1 | judgment fill (tracked blind spot) |

**Paired swap vs the 2026-07-03 board** (per the paired-swap rule — every add names its cut):

- **−1 Fatal Push (4th) → +1 Consign to Memory (3rd).** Mechanics first: the creature axis is
  already −60% maindeck-discounted (3 Push + 4 Bowmasters + 1 Snuff main), while Consign's 3rd
  copy is the solver's **top considering residual (0.0062)** and Consign is a pitch-class card —
  the copy-count study (docs/analysis/copy-count-distribution-study.md) found a hard valley-at-1
  for this class (global P(1)=0.044 vs P(2)=0.647). Validation: 4th Push appears in 6.1% of
  winner boards; Consign's copy mode among established Dimir winners is exactly 3 (67%).

Everything else held from 2026-07-03, with refreshed validation strengthening every slot
(Barrowgoyf 83.7→84.0%, Toxic 63.1%, sample tier speculative→established).

## 2. Copy-count histograms (winners, n=263; 0x = decks not running it)

Per the frequency-distribution-detail rule — full 0x-4x distributions, not inclusion%+avg:

| Card | 0x | 1x | 2x | 3x | 4x |
|---|---|---|---|---|---|
| Force of Negation | 2 | 30 | **226** | 5 | 0 |
| Consign to Memory | 12 | 5 | 67 | **169** | 10 |
| Hydroblast | 37 | 88 | **132** | 6 | 0 |
| Barrowgoyf | 42 | 78 | **120** | 23 | 0 |
| Toxic Deluge | 97 | **113** | 53 | 0 | 0 |
| Surgical Extraction | 116 | 59 | **88** | 0 | 0 |
| Sheoldred's Edict | 126 | **87** | 50 | 0 | 0 |
| Grafdigger's Cage | 128 | **108** | 23 | 4 | 0 |
| Engineered Explosives | 137 | **70** | 56 | 0 | 0 |
| Null Rod | 175 | **72** | 16 | 0 | 0 |
| Dauthi Voidwalker | 179 | 15 | **69** | 0 | 0 |
| Snuff Out | 184 | **79** | 0 | 0 | 0 |
| Harbinger of the Seas | 195 | 31 | **37** | 0 | 0 |
| Feed the Cycle | 210 | **53** | 0 | 0 | 0 |
| Fatal Push (SB) | 247 | **16** | 0 | 0 | 0 |
| Damping Sphere | 255 | 4 | 4 | 0 | 0 |
| Long Goodbye | 260 | 2 | 1 | 0 | 0 |

Reading: the pitch/free counters (FoN, Consign) have hard valleys at 1 — archetype-local
confirmation of the copy-count study. Reactive 1-ofs (Toxic, Edict, EE, Snuff) are legitimately
modal at 1, matching the study's finding that pure concavity is right for that class.

## 3. Overrides (engine recommends → human excludes; both TRACKED, now sweep-confirmed)

- **2 Defense Grid — 0.0% of 263 winner boards.** The sweep proved this systematic: scorer-only
  in **18 of 26 swept archetypes**. Mechanism (tracked in
  idea-hate-coverability-overvalues-defense-grid): `_hate` coverage applies no impact/symmetry
  factor, and Grid's tax hits OUR own instant-speed game.
- **1 Damping Sphere — 3.0%.** Scorer-only in 6 archetypes (ramp cluster); shares the
  symmetric-self-cost representability gap (idea-damping-sphere-base-model-near-miss).

These stay diagnostic overrides, not score edits — the pure-mechanics guardrail.

## 4. What the engine still dissents on (documented, not blindly followed)

- **Surgical Extraction (55.9% of winners, mode 2)**: excluded — the local room's graveyard
  share is thin (Doomsday piles use the yard lightly; no Reanimator at the venue). The winners'
  number is inflated by field-scope's tolerance (in-field tournaments can still contain graveyard
  decks). Watch item: if Grixis Reanimator (now #5 in the refreshed global regime, 157 decks)
  reaches the local meta, Surgical is the first add (owns 3).
- **Grafdigger's Cage (51.3%)**: same axis, same call; also anti-synergistic with our own
  Murktide/delve angle at the margin.
- **Feed the Cycle (20.2%, always 1-of)**: new-card watch item (owns 1). Not yet in the hoser
  catalog (part of the sweep's unclassified-cluster catalog gap, idea-hoser-catalog-new-card-gap).
- **Barrowgoyf SB copies**: winners' mode is 2 in the SB — but Build B mains 2, so our 1 SB copy
  (3rd overall) is the same total exposure. Engine edge, documented since session 1.

## 5. Online-lens variant (venue divergence — reported as a diff, never blended)

Solve vs the online field (`provenance='online'`, current regime; Tron 11.7% #1, Izzet 8.1%,
Show&Tell 7.2%, Energy 6.5%, Grixis Reanimator 6.4%): the raw engine board is **card-identical**
to the the local meta solve — but the dedicated core deepens (natural budget 9/15 vs 6/15; the online
field is more concentrated, so more slots clear the τ floor). After the same overrides, the same
15 stands. Two online-specific notes: Consign's stock rises further (Tron #1 = colorless triggers
everywhere), and Surgical's case is materially stronger online (Reanimator 6.4% + Doomsday 5.1%)
— an online grinder would run Board A −1 Toxic +1 Surgical.

## 6. Board B (owned-constrained) + acquisition list

**Board B converges to Board A.** The unconstrained solve's only unowned picks were 2 Defense
Grid + 1 Blue Elemental Blast — the two overridden false positives and a functional twin of owned
Hydroblast. After the judgment layer, every card is collection-covered (binder minus maindeck
usage). **Acquisition list: EMPTY.** No purchases needed for this board.

Audit trail of the raw owned-constrained solve (mechanism: catalog filtered to spares; NOT a
native solver mode): dropped BEB (unowned, entered via the promoted-pool path that bypasses the
catalog), repaired in Long Goodbye (residual 0.0040); its hedge filled Mystical Dispute 2 /
Damping Sphere / 4th Push — all displaced by the same judgment layer (adoption 14.8% / 3.0% /
6.1%).

**Collection honesty note**: `decks/binder.txt` (the current collection) contains NO Flusterstorm
or Echoing Truth — the 2026-06-27 buy list was not executed, so the "current" sideboard listed in
`dimir-tempo-current.txt` (2 Flusterstorm, 1 Echoing Truth, 2 Hurkyl's, 2 Massacre...) is
partially aspirational. This refreshed board requires none of those cards, and winners agree
(Flusterstorm 1.1%, Hurkyl's 0.4%, Massacre 10.3%). The sleeved-today gap to Board A is a
straight swap of the old 15 for the new 15, all owned.

## 7. Honest tiers

Winner sample ESTABLISHED (n=263) — first time this analysis clears the top tier. Per-matchup
impact factors remain speculative-tier (per-card matchup cells are thin; the engine labels each).
Field = the maintainer's 107-player post-ban the local meta table snapshot; that field file predates the corpus
refresh and is the next thing to re-derive if the venue shifts (regime window unchanged).
