---
source_handle: data-autonomy-topdeck-api-docs
fetched: 2026-07-31
source_url: https://topdeck.gg/docs/tournaments-v2
provenance: source-direct
source_class: api-docs
---

# TopDeck.gg — Tournaments V2 API documentation

## Summary

Topdeck.gg exposes an official, documented tournament API: keys are free via a
developer portal, every request sends the key in an Authorization header, most
endpoints allow 100 requests/minute (bulk endpoints lower; 429 on excess). Endpoints:
`POST /v2/tournaments` (search completed tournaments by game/format/date range,
returning standings and decklists), `GET /v2/tournaments/{TID}` (full tournament),
`GET /v2/tournaments/{TID}/standings`. Decklists appear when the tournament has ended
or the organizer enabled deck visibility. This is the one upstream source with a
sanctioned API — the hot-spare's Topdeck leg is fully legitimate, just needs a free key.

## Key passages

> Keys are free — create one from the developer portal. — API key

> "Authorization": "YOUR_API_KEY" — required header

> Most endpoints allow 100 requests per minute. — rate limits (heavier bulk endpoints lower; 429 when exceeded)

> POST /v2/tournaments — Query completed tournaments by game, format, and date range; returns standings and decklists. — endpoint

> Decklists included in standings responses when "tournament has ended OR organizer enabled 'Show Decks'." — visibility rule

## Structural metadata

Official docs page fetched 2026-07-31 via WebFetch. Covers 30+ games including Magic:
The Gathering with per-game format options.
