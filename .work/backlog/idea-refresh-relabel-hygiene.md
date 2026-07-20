---
id: idea-refresh-relabel-hygiene
created: 2026-07-12
tags: [ingestion, hygiene]
---

**`refresh all` can silently wipe the label layers.** The 2026-07-12 run did a full cache reload
(65,785 decks reloaded; archetype labels dropped to 3, decks.variant to 0) — everything downstream
(camps, eras consumption, split-variant reports) silently degraded to fallbacks until a manual
`label` + per-archetype `discover apply` (29 splits) + `eras run` recovery. Ideas: (a) `refresh all`
should detect a labels-wiped state and either auto-run `label` (+ re-apply staged splits + `eras
run`) or print a loud `// ⚠ labels wiped — run: label && discover apply … && eras run` checklist;
(b) make ingestion preserve labels for unchanged decks (keyed reload instead of full reload);
(c) at minimum an audit line in refresh output stating how many labeled rows were lost.
The staged-registry membership persistence made recovery lossless — keep that guarantee.

**Recurred 2026-07-13:** the wipe happens even on a NO-OP refresh — cache said "Already up to
date", zero new tournaments (deck count and max date unchanged), yet the reload still dropped
labels to 3 and variants to 0. Manual recovery (label + 29× discover apply + eras run) worked
again but took ~10 min of wall clock. This fires on every refresh, not just data-bearing ones —
raises the priority of option (b) (keyed reload preserving labels for unchanged decks).

**Recurred 2026-07-20:** third occurrence, again on a fully no-op refresh (upstream
fbettega/MTG_decklistcache stalled since 2026-07-02, so zero new data). Labels 65,785→3,
variants 21,484→0; recovered via label + 29× discover apply + eras run. Every single refresh
now costs a ~10-min manual recovery — this should be scoped, not re-parked.
