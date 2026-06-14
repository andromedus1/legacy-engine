---
name: principles-legacy-engine
description: Read when making a design or modeling trade-off — the decision heuristics specific to legacy-engine (beyond generic best practice).
type: principles
kind: planning
summary: |
  Project-specific decision heuristics for legacy-engine. Inherits edh-engine's analytics principles
  (analytics is the product, data-driven over vibes, rules-correct at the fidelity claimed, knowledge
  compiled not re-derived) and adds Legacy-specific ones: legality is live data, always label the
  meta-% definition and online/paper basis, confidence-gate every stat, and treat the advisory layer
  as a first-class product.
decisions:
  - "Analytics is the product — infrastructure is justified only by the analytical questions it unlocks."
  - "Data-driven over vibes — every claim backed by tournament data, simulation, or both; build a pipeline wherever there's a data source."
  - "Rules-correct at the fidelity claimed — the goldfish track simplifies transparently and carries confidence metadata; never wrong-but-fast."
  - "Legality is live data — validate against a dated BanListSnapshot; the banned list changes ~quarterly and history must stay correct."
  - "Never an unlabeled meta-% — always state the definition (raw/top-cut/winrate-weighted) and the online/paper/blend basis; they diverge materially."
  - "Confidence-gate every derived stat — sample size + CI on matchup cells; low-n flagged, not silently shown."
  - "Advisory is first-class — 'how to attack the field' is a headline product surface, not a footnote to descriptive stats."
  - "Ban-regime-aware windowing is the default, and the window is always stated — adaptive for matrix-backed surfaces, uniform for explicit --regime/--since windows, full for deck-based descriptive surfaces; a thin window may never silently claim depth it doesn't have."
created: 2026-05-29
updated: 2026-06-13
related:
  - {slug: docs/VISION.md, relationship: depends-on}
  - {slug: docs/ARCHITECTURE.md, relationship: parallel-to}
---

# Principles: legacy-engine

Decision heuristics specific to this project. Generic best practices (tests, types, clean code) are
assumed, not listed. The first four are inherited from edh-engine (sibling consistency); the rest are
Legacy-specific, drawn directly from the research findings.

### 1. Analytics is the product
The ingestion pipelines, archetype parser, and (later) simulation engine are infrastructure. Their
value is the analytical questions they unlock. Every piece of infrastructure must produce usable
analytical output, not just feed a future phase.

### 2. Data-driven over vibes
Measure, don't assume. Every metagame or deckbuilding claim is backed by tournament data, simulation,
or both. Where there's a data source, build a pipeline — don't hand-curate what can be automated.

### 3. Rules-correct at the fidelity claimed
The goldfish track intentionally simplifies (no opponent in the simplest model, simplified stack) for
speed and **carries confidence metadata** so consumers know the fidelity. Simplified-but-transparent is
useful; wrong-but-fast is poison. Mana payment, summoning sickness, sorcery-speed gating, and
state-based actions must be modeled correctly at the level the sim claims.

### 4. Knowledge is compiled, not re-derived
Meta-knowledge (archetypes, combos, card roles, hosers, matchup reads) is compiled once into structured
form, maintained as data changes, and queried by analysis — not re-derived per question. The archetype
taxonomy is the canonical example: ported from a maintained community ruleset so it stays aligned and
auditable.

### 5. Legality is live data
Legacy is a blacklist format whose banned list changes ~quarterly. Always validate against a **dated
`BanListSnapshot`** with `banned_date` + `ban_reason`, so historical decks validate against the
legality that applied then (a 2024 Psychic Frog deck was legal). Card roles and archetypes are
**version-stamped** where bans changed them (e.g. pre/post-Entomb Reanimator is the same name, different clock).

### 6. Never an unlabeled meta-%
Meta share is computed three genuinely different ways — raw entry count, top-cut presence,
win-rate-weighted — and **online and paper metagames diverge materially**. Every reported number states
its definition and its online/paper/blend basis. Compute % ourselves from raw finishes; never trust a
single aggregator's headline number.

### 7. Confidence-gate every derived stat
Matchup cells and aggregates carry sample size and a confidence interval. Low-sample cells (n<100) are
flagged, not silently presented as fact. Reuses edh-engine's `established | evolving | speculative`
confidence-metadata pattern.

### 8. Advisory is first-class
"How to attack the field" — positioning score, sideboard recommendation, what-to-play — is a headline
product surface. Model the hoser→target graph and its anti-hate second order explicitly; let the user
supply their *expected local field*, because the best metagame call is field-dependent.

### 9. Sibling-consistent, divergence-justified
Mirror edh-engine's architecture, conventions, and code wherever the domain overlaps (Scryfall layer,
deck-as-data, mana solver, mulligan, confidence metadata, CLI shape). Diverge only where Legacy demands
it — the archetype parser, the advisory pillar, 1v1/sideboard semantics, straight London (no free mull) —
and say why in the doc.

### 10. Ban-regime-aware windowing, always labeled
Every analytical surface defaults to ban-regime-aware windowing so tuning reflects the **current**
meta, not a stale pre-ban field. Three modes — **adaptive** (per-cell/per-opponent ban-aware, the
default for matrix-backed surfaces: matchups, positioning, gaps, sideboard plans), **uniform**
(an explicit `--regime`/`--since` window, degraded to full corpus + banner when thin), and **full**
(`--all-time`, or deck-based descriptive surfaces whose thinness shows via confidence tiers). A
surface MUST echo its resolved window and thinness; a thin window may never silently claim depth it
doesn't have. Where two surfaces legitimately use different windows (a current-regime consensus list
read alongside an adaptive matchup matrix), the divergence is stated, never silent. New surfaces are
audited against this checklist before they ship.
