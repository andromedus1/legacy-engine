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
