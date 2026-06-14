---
id: idea-build-group-doc-drift-and-polish
created: 2026-06-13
tags: [documentation, advisory]
---

Non-blocking findings from the Phase 8 final completion review of the 8-feature dogfooding build
group (all `done`, suite green at 1548). None blocking; queued for the docs gate / update-documentation
at release-deploy time, per the rolling-foundation principle.

1. **(Low) docs/ARCHITECTURE.md module-map + CLI-surface drift.** The build group added ~10 modules not
   listed in the Module Map: `interaction_facts.py`, `generation/card_distribution.py`,
   `analytics/subgroup.py`, `archetype/variants.py`, `analytics/venue.py`, the `analytics/players/`
   subpackage, `advisory/primer.py`, `advisory/refresh.py`, `models/variant.py`. The CLI diagram +
   Conventions omit `report subgroup|variants`, `generate doctor`, `advise refresh`, the `identify`
   group, and the `--strong/--players/--variant/--venues` flags. Roll ARCHITECTURE.md forward to list
   them. (Also: frontmatter `updated: 2026-06-01` vs body "2026-05-31" mismatch — fix.)
2. **(Low) docs/SPEC.md domain-entity drift.** Add the new entities: Variant, Player (+strength/history),
   Venue, Subgroup, InteractionFacts. (Inventory/UserDeck roll-forward already present + coherent.)
3. **(Low) `report meta --venues <bad-key>` raises a raw `ValueError` traceback** from
   `analytics/venue.py:86` instead of a clean `click.ClickException` (every other cli.py input-error path
   wraps it). Wrap the `resolve_venues` ValueError at `cli.py:~316` for consistency. Valid keys work.
   **RESOLVED (2026-06-14):** Both `report meta --venues` and `advise report --venues` now wrap
   `resolve_venues` ValueError in a `click.ClickException`. Tests added in `TestBadVenueKeyCleanError`
   (test_cli_venues.py).
4. **(Trivial) `generate consensus` help** doesn't state that `--variant` and `--players` combine
   (AND-filter); add a one-line note.
   **RESOLVED (2026-06-14):** Both `--variant` and `--players` option help strings now state they
   combine as an AND-filter.

Cross-feature seams reviewed and judged defensible-by-design (not bugs): the empirical sideboard pool is
anchored to the current-regime uniform window while per-opponent adaptive windows pool back to
max(valid_since) — degrades safely (pool=None when thin); `--players` precedence over `--strong` is
implemented and documented.
