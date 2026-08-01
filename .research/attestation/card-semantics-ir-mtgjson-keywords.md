---
source_handle: card-semantics-ir-mtgjson-keywords
fetched: 2026-07-31
source_url: https://mtgjson.com/api/v5/Keywords.json
provenance: source-direct
source_class: standard
version: 5.3.0+20260731
---

# MTGJSON Keywords.json (v5.3.0+20260731)

## Summary

MTGJSON ships the game's keyword vocabulary as a standalone JSON enumeration, split into three
lists: `abilityWords` (69 entries — italicized flavor labels like Adamant/Addendum that have
no rules meaning), `keywordAbilities` (220 entries — Absorb, Affinity, Afflict, ...), and
`keywordActions` (78 entries — Abandon, Activate, Adapt, ...). Downloaded and counted
mechanically on 2026-07-31 (build meta: version 5.3.0+20260731). These counts are larger than
the current Comprehensive Rules 702/701 subsection counts (194/69) because MTGJSON includes
funny-set and variant keywords beyond the CR's tournament-legal enumeration. Value to the IR:
a machine-readable closed keyword vocabulary to validate a `keywords`-derived IR facet
against, available as versioned data rather than by parsing the CR text file.

## Key passages

> meta: {"date": "2026-07-31", "version": "5.3.0+20260731"} — file header

> data.abilityWords — 69 entries; first five: "Adamant", "Addendum", "Alliance", "Battalion",
> "Bloodrush" — counted from the downloaded file

> data.keywordAbilities — 220 entries; first five: "Absorb", "Affinity", "Afflict",
> "Afterlife", "Aftermath" — counted from the downloaded file

> data.keywordActions — 78 entries; first five: "Abandon", "Activate", "Adapt", "Airbend",
> "Amass" — counted from the downloaded file

## Structural metadata

Single JSON object: `{meta: {date, version}, data: {abilityWords, keywordAbilities,
keywordActions}}`. Counts computed with `len()` over each list after download; no
transformation applied.
