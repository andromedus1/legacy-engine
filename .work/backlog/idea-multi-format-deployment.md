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

## Current decision — architecture target only

The Modern deployment is intentionally deferred while Legacy is changing quickly. Do not extract
a shared core, introduce a `FormatProfile` abstraction, create a Modern database/configuration,
or stand up a second deployment yet: those would create a second maintenance surface before the
Legacy contracts settle.

Keep portability as a constraint on new boundaries, then revisit implementation only after the
Legacy decision benchmark is evaluable and the local refresh/format-monitoring path is operating
reliably. The eventual port should consume stable seams proved by Legacy rather than trying to
predict them during the current high-velocity phase.
