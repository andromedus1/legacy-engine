---
id: epic-sb-advisor-correctness-matchup-plan-flex
kind: feature
stage: drafting
tags: [advisory]
parent: epic-sb-advisor-correctness
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Matchup-plan flex — unlock the OUT side, gate the IN side on axis relevance

## Brief

`_plan_matchups` (`src/legacy_engine/advisory/sideboard.py:2576`) builds the per-opponent OUT/IN
swap plans, and both sides are broken for a consensus-tight deck. The OUT side locks every maindeck
card at `lock_threshold = 0.65` archetype adoption (`:2584`, `:2640-2642`), which for Dimir Tempo
leaves FETCHLANDS as the only flex — so the data-driven plans proposed cutting 2-3 lands (Scalding
Tarn, Bloodstained Mire) for spells vs Izzet / Jeskai / the mirror. Cutting lands is not a
sideboarding decision a real pilot makes; it is what an unconstrained optimizer does when the only
unlocked slots happen to be lands. The IN side is gated on correlational card value alone
(`:2700-2708`: gate tier + `lift > 0`), with no check that the card's answer axis is even present
in the matchup — which is how the mirror plan boarded Hydroblast into a UB deck.

This feature fixes both sides. OUT: hard-exempt lands from the flex/OUT pool and degrade honestly
when no legal non-land flex remains — say "no flex slots at this consensus level" rather than
manufacturing land cuts. IN: gate candidates on the coverage model's axis relevance (a `plays-red`
answer needs a red target in the matchup) in addition to lift, so correlational noise cannot
promote an inert card. Both changes are subtractive on the recommendation side and additive on the
audit side; the honest-degrade path is a first-class output, not a failure.

Does NOT cover: lowering `lock_threshold` globally (rejected — see inherited decisions); the
coverage model / element weights (`per-deck-castability`, `hate-self-cost`); the composition of the
15 itself; measuring whether a given slot actually pulls weight in its matchup (that is
`epic-sb-config-evaluation-matchup-slot-test`'s territory — this feature only decides which cards
are ELIGIBLE to swap, never how much a swap is worth empirically).

## Epic context

- Parent epic: `epic-sb-advisor-correctness`
- Position in epic: independent capability — `_plan_matchups` output is not part of the backtest's
  recommended-board partition, so this feature neither depends on nor perturbs the divergence
  ratchet. Fully parallelizable with the coverage-model arc.

## Inherited design decisions

- **Calibration philosophy** (epic): mechanism fixes only; observed adoption stays a diagnostic and
  is NEVER blended into scores. Note the subtlety: the `lock_threshold` IS an adoption reading, but
  it is a legality/identity constraint on which cards may be cut, not a score input — this feature
  keeps it in that role and does not let adoption reach the ranking.
- **OUT-side form** (epic `## Design decisions`): hard-exempt lands and degrade honestly, rather
  than lowering `lock_threshold`. Lowering the threshold would unlock spells indiscriminately
  across every archetype; the land exemption is targeted at the verified failure and preserves the
  consensus-core protection the threshold exists for.

## Research briefs

- `docs/briefs/advisory-methods.md` — advisory surface conventions and the per-matchup plan
  contract.
- `docs/briefs/sideboard-core-and-hedge.md` — how the chosen 15 reaches `_plan_matchups`.
- Audit trail for the finding: the Dimir primer session (2026-07-04) used judgment plans with the
  engine's signals cited and explicitly rejected — the IN side had real signal (Consign vs Izzet
  n=71, Hydroblast vs Doomsday n=30 corroborated judgment), the OUT side did not.

## Foundation references

- `docs/ARCHITECTURE.md` — the `sideboard.py` row's per-matchup OUT/IN plan description
  (post-board exactly-60, copy-capped, locked-core protected).
- `docs/SPEC.md` — Pillar 4 + the HONEST-DEGRADE NFR.
- Patterns: `.agents/skills/patterns/honest-degrade-marker.md` (the no-legal-flex path must carry a
  named reason and suppress the magnitude, matching the existing `MatchupPlan.degraded=True` note
  shape at `sideboard.py:2666-2675`); `.agents/skills/patterns/audit-echo-comment-lines.md` (any new
  provenance line uses the `// ...` prefix);
  `.agents/skills/patterns/divergence-as-diagnostic-surface.md` (where the engine declines to
  recommend a swap the correlational signal favors, say so — do not silently drop it).

<!-- The /feature-design pass will fill in interfaces, signatures, and implementation units. -->
