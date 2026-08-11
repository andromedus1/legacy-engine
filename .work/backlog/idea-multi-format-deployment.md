---
id: idea-multi-format-deployment
created: 2026-08-11
updated: 2026-08-11
tags: [architecture, analytics]
---

# Multi-format deployment from the 1v1 engine

Eventually make another deployment of legacy-engine for other competitive 1v1 Magic formats,
starting with Modern. Preserve the current Legacy deployment while determining which analytics,
ingestion, ranking, validation, player, and observed-deck-choice capabilities can be shared and
which knowledge/configuration must remain format-specific.

Current feasibility evidence from the repository: the mirrored tournament cache already contains
3,435 Modern event files, and the vendored MTGOFormatData tree already contains 141 Modern rule
files. The core question is whether to extract a shared format-aware engine with isolated per-format
data/configuration and deployments after the best-deck decision-trust work proves the ranking
contract. Do not pull goldfish/rules simulation or modeled sideboard recommendation into the
portability prerequisite; both are already deferred.
