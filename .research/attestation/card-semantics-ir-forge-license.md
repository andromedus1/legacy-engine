---
source_handle: card-semantics-ir-forge-license
fetched: 2026-07-31
source_url: https://api.github.com/repos/Card-Forge/forge/license
provenance: source-direct
source_class: standard
---

# Card-Forge/forge repository license (GitHub license API)

## Summary

GitHub's license-detection API for the Card-Forge/forge repository reports the project's
license as GPL-3.0. Consequence for legacy-engine: Forge's card-script corpus (the
`res/cardsfolder/` per-card DSL files) is copyleft — usable as read-only prior art and as an
external divergence-diagnostic oracle, but bulk-importing script content or deriving data
tables directly from it would pull GPL obligations into a non-GPL codebase and needs an
explicit licensing decision.

## Key passages

> "license": {"key": "gpl-3.0", ... "spdx_id": "GPL-3.0"} — GET
> /repos/Card-Forge/forge/license (license object)

> "html_url": "https://github.com/Card-Forge/forge/blob/master/LICENSE" — GET
> /repos/Card-Forge/forge/license (path to the license file in-repo)

## Structural metadata

JSON response from the GitHub REST API `GET /repos/{owner}/{repo}/license` endpoint,
2026-07-31. SPDX identifier quoted verbatim.
