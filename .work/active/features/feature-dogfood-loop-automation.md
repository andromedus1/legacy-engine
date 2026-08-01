---
id: feature-dogfood-loop-automation
kind: feature
stage: drafting
tags: [infra]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-31
---

# Dogfooding session workflow as an autonomous idea-processing loop


# Dogfooding session workflow as an autonomous idea-processing loop

Andrew's observation (2026-07-04, mid sweep-arc build): our typical dogfooding session
already follows a repeatable loop — pick a deck, start an idea about it, investigate using
the data, output analysis, maybe test more, then find ideas for improvements to the engine,
build those, and end the loop (with the option to loop again). We could use this same loop
as a way to process general ideas more autonomously — codify the session shape into an
autonomous process rather than an ad-hoc pattern.

## Design decisions
<!-- captured 2026-07-31 via feature-design --only-questions; treat as fixed inputs -->
- **Loop driver**: scheduled headless Claude session (launchd/cron → headless invocation of
  a dogfood-loop skill against this repo), consistent with epic-data-autonomy's launchd
  scheduling decision.
- **Output contract**: each run parks ideas to .work/backlog/ and writes its analysis under
  docs/analysis/ (or decks/); nothing is auto-promoted — Andrew reviews and scopes, exactly
  like today's manual sessions.
