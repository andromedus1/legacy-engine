---
source_handle: card-semantics-ir-scryfall-tagger
fetched: 2026-07-31
source_url: https://scryfall.com/docs/syntax
provenance: source-direct
source_class: standard
---

# Scryfall search syntax — Tagger tags (`otag:` / `function:`)

## Summary

Scryfall's official search-syntax reference documents the access path to Scryfall Tagger's
community-maintained functional tags: the `function:`, `otag:`, and `oracletag:` search
keywords "find 'Oracle' tags which describe the function of the card," and the docs state
the data comes from the Tagger project. Access is therefore per-tag set-membership queries
through the ordinary public search API (`/cards/search?q=otag:<tag>`), not a per-card field —
card objects returned by the API carry no tag list (verified separately: the Force of
Negation card object has no tag field). A live check confirmed the search path works
end-to-end: querying `otag:removal name:"Swords to Plowshares"` against
`api.scryfall.com/cards/search` returns Swords to Plowshares. Practical consequence: Tagger
data is reachable for audit-style cross-validation (enumerate members of a chosen tag) but is
crowd-sourced, has no documented bulk export in the card objects, and its tags are not
versioned data-contract artifacts — suitable as a divergence-diagnostic oracle, not as ground
truth.

## Key passages

> You can use function:, otag:, or oracletag: to find "Oracle" tags which describe the
> function of the card. Data for these two features comes from the Tagger project.
> — § Tagger Tags

> function:removal — Cards that cause removal — § Tagger Tags (example row)

> Live API check (2026-07-31): GET
> https://api.scryfall.com/cards/search?q=otag%3Aremoval+name%3A%22Swords+to+Plowshares%22
> returned object=list with "Swords to Plowshares" among the results — the `otag:` keyword is
> honored by the public REST search endpoint. — api.scryfall.com observation

## Structural metadata

HTML search-syntax reference (fetched with a browser user agent); Tagger Tags is a named
section alongside art-tag syntax (`art:`/`atag:`). The Tagger project itself lives at
tagger.scryfall.com (interactive, account-based tagging UI).
