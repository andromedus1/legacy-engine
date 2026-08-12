---
id: feature-ranking-credible-window-utility-horizon-clamp
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: feature-ranking-credible-window-utility
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Confirmed-ban lower bound for entity horizons

## Brief

Implement Unit 1 of the parent feature: combine stored/detected entity eras with confirmed direct
ban affectedness so the later boundary wins, while unaffected entities retain admissible history.
