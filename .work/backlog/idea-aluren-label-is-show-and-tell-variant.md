---
id: idea-aluren-label-is-show-and-tell-variant
created: 2026-07-31
tags: [archetype, analytics]
---

The `Aluren` archetype label is a misnomer for what the deck now is: a **UG Show and Tell shell**.
Andrew's read while studying it (2026-07-31): "seems like it's just a subarchetype of the show and
tell archetype" — the composition data agrees.

Measured (maindeck inclusion ≥50% = "core", since 2026-05-11):
- `Aluren [Acererak the Archlich]` n=47 vs `Show and Tell` n=334 → **core Jaccard 0.54**, 15 shared
  core cards covering the entire engine (Show and Tell, Omniscience, Emrakul, Atraxa, Ancient Tomb,
  City of Traitors, Lotus Petal, Force of Will, Brainstorm, Ponder, Stock Up)
- the difference is one interchangeable package: Aluren+Acererak in UG (Trop/Forest/Hedge Maze/
  Boseiju/Veil) vs Sneak Attack at 77% in UR (Volcanic/Mountain/Scalding Tarn/Thundering Falls)
- `Show and Tell`'s own camps are already `Sneak Attack` (252) / `non-Sneak Attack` (44) — the
  Aluren build is functionally a third camp that landed under a different PARENT

Root cause to verify: the rule-based archetype parser (vendored MTGOFormatData rules) almost
certainly keys the `Aluren` label on the presence of the card Aluren. That rule dates from when
Aluren meant the creature-chain combo deck (Cavern Harpy / Parasitic Strix / Recruiter loops); it
now fires on a Show and Tell deck that happens to run Aluren as a cheat target. Note the corpus
still holds the older generations under the same parent — a dead `Baleful Strix` camp (nothing
since 2026-01-31) plus `Formidable Speaker` — so the parent label mixes eras AND strategies.

Why it matters: the split starves both labels of matchup data (every Aluren cell is n<30), it
makes the parent-label marginal misleading (parent 50.8% n=427 vs Acererak camp 57.3% n=185), and
it means "Aluren vs Show and Tell" reads as a real matchup edge (73.9%, n=23) when it is really an
intra-family cell.

Options to weigh at scope time (not decided): reclassify in the vendored rules vs. handle it purely
at the superarchetype layer ([[idea-superarchetype-matchup-aggregation]]) vs. leave labels alone and
surface the family relationship as a diagnostic. Relates to the era/generation-mixing theme in
[[idea-camp-incremental-assignment]] and the discovery temporal gate.
