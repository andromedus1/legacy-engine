---
source_handle: ddx-construction-registry
fetched: 2026-08-20
source_path: decks/doomsday-variants/manifest.json
provenance: source-direct
substrate_confidence: source-direct
---

# Doomsday construction registry

The machine-readable manifest registers the canonical candidate identities, deck paths, evidence
postures, hashes, and legality-check dates used by the construction experiment.

## Key passages

1. **Registry shape.** The `candidates` array has 14 rows and the root declares 15 artifacts / 14 unique candidates.
  Every candidate row has an `id`, `path`, `status`, `evidence_posture`, and
  `canonical_deck_sha256`.
2. **Evidence posture.** The current Dimir, Esper, light green-white, and four-color lists are exact registrations;
  Personal Tutor and Wasteland/Murktide are exact published registrations.
  BUG, Moonshadow, and Cori-Steel Cutter are inferred reconstructions. Grixis, Paradigm Shift,
  Emrakul/Shelldock, Chancellor, and the value-threat list are observed-historical rather than
  observed-current.
3. **Legality and coverage.** The manifest pins a 2026-08-10 ban-list snapshot and records a 2026-08-20 legality check.
  The registered canonical paths cover the principal Dimir, Esper, BUG, Grixis, green-white,
  four-color, and Wasteland branches plus six alternate-module branches.

## Revisions

- 2026-08-20: Added stable numbered passages separating registry shape, evidence posture, and
  legality/coverage after the full-rigor adversarial review found absent ordinals.
