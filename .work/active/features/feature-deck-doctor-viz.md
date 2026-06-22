---
id: feature-deck-doctor-viz
kind: feature
stage: drafting
tags: [viz, advisory]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-22
updated: 2026-06-22
---

# Deck-doctor consensus-diff visualization

## Brief
Add an HTML/PNG **visualization** of the deck-doctor consensus diff: overlay a
specific 75 (maindeck + sideboard) against a cohort's per-card copy-count
distribution. For each card, render the user's count against the field's
0x/1x/2x/3x/4x histogram, with inclusion%, average-when-played, and
on-mode / off-distribution / not-in-list tags — grouped by card type,
alphabetical within type.

The **data and diff layer already ship** (v0.1.0): `card_count_distributions`
and `diff_deck_vs_field` in `generation/card_distribution.py`, surfaced today as
the text command `generate doctor` (`generate_doctor` / `_render_deck_doctor` in
cli.py). This feature is purely the *rendering* layer on top of the existing
`DeckDoctorReport` — it does not re-derive any analytics.

**Why:** during the Dimir Tempo / Flow State analysis session (2026-06-22) this
exact view was built by hand repeatedly in throwaway scripts. The text
`generate doctor` report exists, but copy-count *distributions* are inherently
visual — a segmented bar communicates "Nethergoyf is binary: 0x or 3-4x, never
1-2x" or "you run 3 Scalding Tarn but no field deck runs more than 2" far faster
than a table. A working standalone HTML prototype lives at
`decks/dimir-tempo-vs-cohort.html` (generated this session) and demonstrates the
target output: per-type sections, distribution bars in the engine's Okabe-Ito
theme, the user's count outlined, and an EVOLVING/confidence banner.

## Recommended framing (for feature-design to confirm)
A **new `viz` leaf** (working name `viz doctor`) that consumes the shipped
`DeckDoctorReport` and renders via the existing viz **spec → render → write**
tail — mirroring the five existing leaves (`viz deck|meta|matchups|trends|tiers`).
This is preferred over bolting `--html/--png` output onto `generate doctor`,
because every other chart in the system lives under `viz` and follows the
`spec_*` + `render_html_tile`/`render_png` pattern (the `viz-spec-render-write-tail`
project pattern, 4 sites in cli.py). Keeping `generate doctor` as the text
surface and `viz doctor` as the rendered surface matches the established split.

## Reuse (do not re-implement)
- `generation/card_distribution.py::card_count_distributions` + `diff_deck_vs_field`
  — the windowed per-card histogram + outlier diff (shipped).
- `generation/consensus.py::_latest_regime_window` — current ban-regime window SSOT.
- `viz/render.py::render_html_tile` / `render_png`, `viz/specs.py` (`spec_*`),
  `viz/theme.py` (Okabe-Ito palette, dark theme), `viz/models.py`.
- The viz-spec-render-write-tail CLI pattern (build spec only after `con.close()`;
  wrap render `ValueError` as `click.ClickException("Render failed: …")`).

## New work (rough)
- A viz model adapter (`DeckDoctorReport` → a chart model in `viz/models.py`).
- A `spec_deck_doctor` (or `spec_consensus_diff`) in `viz/specs.py` producing the
  segmented per-card distribution bars, grouped by card type, with the user-count
  overlay and the confidence-tier banner.
- A new `viz doctor` CLI leaf wiring decklist input + archetype + regime window
  to the model + spec + render/write tail.

## Honest-degrade requirement
The confidence tier (speculative / evolving / established, from the cohort's
`decks_total`) MUST surface as a visible banner in the rendered output — the same
honesty the text deck-doctor carries (`honest-degrade-marker` pattern). A small
cohort (e.g. the exact-3-Nethergoyf subset at n=32) must render EVOLVING, not be
presented as settled.

## Open questions for feature-design
- **Sub-cohort filtering.** The hand prototype filtered to an arbitrary
  sub-cohort (Flow State decks running exactly 3 Nethergoyf). Does v1 expose
  cohort sub-filters (e.g. `--require "Nethergoyf=3"`), or just archetype + board +
  regime window, deferring sub-filters to a later iteration?
- **Sideboard.** One combined file (main + side sections) or separate renders?
- **Command name.** `viz doctor` (ties to the shipped `generate doctor` lineage)
  vs `viz consensus-diff` (the originally-parked idea name).

## Related
- Pairs with the parked `idea-granular-effect-tagging` — better tags → richer
  cohort/consensus nuance feeds this view.
- Lineage: extends the shipped `feature-card-count-outlier-advisor`
  (released in v0.1.0).
