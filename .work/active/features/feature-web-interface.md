---
id: feature-web-interface
kind: feature
stage: drafting
tags: [interface, needs-research, hold-for-review, deferred]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-15
---

> **DEFERRED 2026-06-15** — parked by decision; not in scope for the current cycle. Revisit by
> lifting `deferred`/`hold-for-review` and running the research pass below.


Build a better way to interact with the engine than the CLI alone — most likely a **website / web
app**. Today every read (meta, trends, advise, tune, consensus, viz) is a CLI invocation; a hosted
UI would make the engine usable without a terminal and make outputs (field reads, dashboards, tuned
lists) shareable.

This is a **new research + engineering direction**, not a small feature: web hosting, an API/service
layer over the analytics core, a frontend, auth/deploy, and how the DuckDB corpus is served. Needs
its own research pass (`/research` or `/deep-research`) before architecture — don't design from
assumptions. Note there's already a static-HTML thread to fold in: [[idea-autorefresh-html-dashboard]]
and the existing `viz` deck-dashboard renderer are prior art for what a web surface could present.
