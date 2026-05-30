---
id: epic-advisory-report
kind: feature
stage: drafting
tags: [advisory]
parent: epic-advisory
depends_on: [epic-advisory-positioning, epic-advisory-whattoplay, epic-advisory-sideboard]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Field Read & Deck Recommendation Report (advise CLI surface)

## Brief
The advisor's terminal payoff: a coherent **"Field Read & Deck Recommendation"** report that composes the
three producers into one audit-trailed surface — field composition + derived **vulnerability profile** →
field-read narrative ("X% of the field is graveyard-reliant → graveyard hate is highest-equity") → decks
**ranked by positioning score**, each tagged proactive/reactive and best-deck/best-call → a recommended
**15-card sideboard package** → an **audit trail** (every number with its derivation, sample size, and a
heuristic-vs-data-driven label). Wires the **`advise` CLI group** — implements the `advise
positioning | sideboard | whattoplay` stubs to emit their individual reports, plus the combined field-read
report leaf (leaf name decided in feature-design). Each command loads a deck/field input and a `--field`
custom-field option (via `field-model`).

Pure composition + presentation: consumes `positioning` (S/ranking), `whattoplay` (proactivity, tags,
hate-equity, best-deck/best-call), and `sideboard` (`SideboardPackage`); recomputes nothing. Confidence is
per-component (not one global label); BEST-CALL recommendations gate on established/evolving matchup data.

Does NOT compute any advisory statistic (consumes all three); does NOT render charts (analytics `charts`
owns visual output) or cover simulation/generation.

## Epic context
- Parent epic: `epic-advisory`
- Position in epic: **terminal sink** — composes `positioning` + `whattoplay` + `sideboard` and wires the
  `advise` CLI surface. The epic's user-facing payoff.

## Inherited design decisions
- **Full Field-Read & Deck-Recommendation report** is the MVP surface (field composition + vulnerability
  profile + ranked decks + sideboard package + audit trail).
- **Audit trail mandatory**: every figure carries derivation + sample size + heuristic-vs-data-driven label.
- **Per-component confidence** (not one global label); **gate BEST-CALL on established/evolving data only**.
- **Custom field threads through** (`--field`) to positioning + sideboard + whattoplay via `field-model`.

## Research briefs
- `docs/briefs/advisory-methods.md` — §4 "the recommendation surface" (report structure + audit trail).

## Foundation references
- `docs/ARCHITECTURE.md` — `advisory/report.py`; the `advise positioning|sideboard|whattoplay` CLI group.
- `docs/SPEC.md` — the advisory MVP capabilities.
- `docs/PRINCIPLES.md` — advisory is first-class; confidence-gate the recommendation.

<!-- feature-design fills in: the report assembler, advise CLI wiring + deck/field input, test approach. -->
