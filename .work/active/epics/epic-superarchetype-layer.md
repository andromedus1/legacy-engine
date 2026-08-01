---
id: epic-superarchetype-layer
kind: epic
stage: drafting
tags: [analytics, archetype, needs-brief]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Superarchetype layer — pool strategy clusters so every row gets signal

## Brief

**Thin data is the binding constraint on the engine's headline output.** On the
2026-07-31 best-call page, Cradle Control ranked #1 by adjusted field WR while having
**zero** matchup cells that clear the display threshold; Aluren's every cell is n<30;
Energy — the #5 deck in the format — has exactly two. Every honesty mechanism the project
has built (tier gates, grounded strata, honest-degrade banners) makes that thinness
*legible*; none of them make it *go away*.

This epic adds the one thing that raises effective sample: a **superarchetype** level above
parent archetype. Archetypes are clustered into strategy groups, and the matches of every
archetype in a cluster contribute to a win rate against that cluster — so a deck gets some
grounded signal against all the major strategies even when it has never played the specific
archetype in front of it.

**the maintainer's framing (2026-07-31, verbatim intent):** cluster the archetypes into
superarchetypes, then use archetypes within each superarchetype cluster to generate a win
rate against that superarchetype — getting signal against all the major strategies despite
perhaps not having all the data on the archetypes within it. The open work is the *method*:
how to derive the superarchetype matchup win rates from the data available.

**Worked evidence this is real, not theoretical (measured 2026-07-31):** `Aluren [Acererak
the Archlich]` (n=47) and `Show and Tell` (n=334) share 15 core cards and the entire engine
(Show and Tell, Omniscience, Emrakul, Atraxa, Ancient Tomb, City of Traitors, Lotus Petal,
Force of Will, Brainstorm, Ponder, Stock Up) at **core Jaccard 0.54** — one chassis with two
interchangeable second-engine packages (Aluren+Acererak in UG vs Sneak Attack 77% in UR).
They are separate parents only because the rules-based labeler keys on the card Aluren, a
rule written when that meant the creature-chain deck. Pooling them is exactly what a
superarchetype does, and it is the difference between n=47 and n=381 for that strategy.

Three separate label-pooling failures surfaced in one session (Cradle Control fragmented
across color-prefixed labels; Aluren's dead Baleful Strix generation; Aluren ≡ Show and
Tell), which is why this arc outranks the presentation-layer honesty work in the queue.

## Strategic decisions
<!-- captured 2026-07-31 at scope; downstream design treats these as fixed inputs -->
- **Derivation**: data-driven clustering of archetypes by card composition with a **curated
  override layer** — the hybrid-derived-curated-registry pattern. Reuse the discovery
  engine's machinery where it fits (it already clusters one level down); curated entries win
  by key, derived fills gaps.
- **Intra-cluster matches**: they **count** toward the superarchetype cell but carry an
  **intra-cluster flag** so surfaces can say "this edge is inside your own family" (the
  Aluren 73.9% vs Show and Tell case). Divergence-as-diagnostic, not silent exclusion.
- **Consumption on the best-call page**: **per-cell fallback, labeled** — use the archetype
  cell when it clears its tier gate, fall back to the superarchetype cell when it doesn't,
  with a provenance chip alongside the existing BA/FC/era chips. Every row gets coverage and
  every number stays auditable.
- **Foundation**: VISION rolled forward to a three-level taxonomy (superarchetype → parent
  archetype → camp) at scope time. SPEC/ARCHITECTURE roll forward during epic-design once
  the brief pins the method.

## Open method questions for the brief
- Clustering representation: full 75 vs maindeck-only vs the flex-band representation
  discovery already uses; distance metric; how to handle archetypes too small to cluster.
- Aggregation: how a subject's record against a cluster is computed from per-archetype cells
  — pooled raw counts vs a weighted mean of shrunk cells vs a hierarchical prior with the
  superarchetype as an intermediate shrinkage target (the existing chain is camp → parent′ →
  marginal′; this inserts a level).
- Uneven coverage inside a cluster: a cluster whose matches are 90% one member is not really
  a read on the cluster — needs a concentration/representativeness gate.
- Validation: how to know a superarchetype cell is *honest* (does pooling across genuinely
  different strategies smuggle in bias worse than the thin cell it replaced?).
- Interaction with stable eras: clusters shift over time; whether cluster membership is
  era-scoped like camps are.

## Member ideas (absorbed from backlog; full text below)

---

### idea-superarchetype-matchup-aggregation


**Thin data is the biggest problem to solve on the best-deck/best-call HTML.** the maintainer's
framing (2026-07-31): too many cells are unmeasured or speculative, so rows can't be
grounded and the page's honesty gates discard most of the field.

**The idea:** cluster archetypes into **superarchetypes**, then use the archetypes *within*
each superarchetype cluster to generate a win rate against that superarchetype. That way we
get some signal against all the major strategies even when we don't have full data on every
individual archetype inside the cluster.

**What still needs solving:** the method for deriving superarchetype win-rate matchups from
the data actually available — how to aggregate/pool the member archetypes' cells into one
superarchetype cell, and how to handle uneven coverage across members.

Context that makes this intelligible later: the engine already has a two-level taxonomy
(parent archetype → data-driven camp). This adds a level *above* archetype, which the current
matchup/window machinery has no concept of. Relates to [[idea-path-to-grounding]] (converting
discarded coverage into an agenda), [[idea-lean-view-toggle]] (soft-weighting instead of hard
gates), [[feature-ranking-honesty-guards]], and [[idea-adj-field-wr-recompute-divergence]].

## Worked example found 2026-07-31 (Aluren ≡ Show and Tell family)

Measured while building the Aluren primer — a concrete case the superarchetype layer would fix:

`Aluren [Acererak the Archlich]` (n=47, since 2026-05-11) vs `Show and Tell` (n=334), maindeck
inclusion ≥50% as the "core":
- **shared core = 15 cards**: Show and Tell, Omniscience, Emrakul, Atraxa, Ancient Tomb, City of
  Traitors, Lotus Petal, Force of Will, Brainstorm, Ponder, Stock Up, Island, Misty Rainforest,
  Polluted Delta, Flooded Strand — i.e. the whole engine
- **core Jaccard = 0.54**
- Aluren-only core: Aluren, Acererak, Boseiju, Forest, Hedge Maze, Tropical Island, Veil of Summer
  (the UG package)
- S&T-only core: Sneak Attack (77%), Volcanic Island, Mountain, Scalding Tarn, Thundering Falls
  (the UR package)

So they are one chassis with two interchangeable second-engine packages, and S&T's own camps are
already `Sneak Attack` (252) / `non-Sneak Attack` (44). A "cheat-into-play combo" superarchetype
would pool all of it — and the pooled opponent cells are exactly what both labels currently lack
(every Aluren cell is n<30).

Note the honesty consequence this cuts both ways: the Aluren build's best-looking cell is
**73.9% vs Show and Tell (n=23)**, which under a superarchetype view is an INTRA-family cell, not
an edge against a distinct strategy. Superarchetype aggregation needs a rule for whether
intra-cluster matches count toward a member's record against its own cluster. See
[[idea-aluren-label-is-show-and-tell-variant]] for the labeling half of this.

---

### idea-aluren-label-is-show-and-tell-variant


The `Aluren` archetype label is a misnomer for what the deck now is: a **UG Show and Tell shell**.
the maintainer's read while studying it (2026-07-31): "seems like it's just a subarchetype of the show and
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
