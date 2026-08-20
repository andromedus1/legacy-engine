---
source_handle: ddp-registered-candidates
fetched: 2026-08-20
source_path: decks/doomsday-variants/manifest.json
provenance: source-direct
substrate_confidence: source-direct
---

# Registered candidate artifact

The manifest root has schema `doomsday-variant-candidates`, a 14-entry `candidates` array, and a separate `artifact_aliases` array. The alias row maps `tamiyo-bilbo-unearth-value` to `current-esper-teferi-swords` and carries the same canonical deck hash.

## Key passages

- JSON root keys `schema`, `compatibility_baseline_id`, `candidates`, and `artifact_aliases`.
- Candidate fields include `id`, `path`, `status`, `evidence_posture`, `family`, and `canonical_deck_sha256`.
- The current Dimir row is the compatibility baseline.
- The alias row's `canonical_id` is `current-esper-teferi-swords`; its path is `decks/doomsday-tamiyo-bilbo-unearth-value-75.txt`; its hash equals the canonical Esper row.
- The candidate paths resolve to parser-valid 60-card maindecks plus 15-card sideboards. The alias file parses to the same board tuple as the canonical Esper file.
- The current Dimir, Esper, light green-white, four-color, Personal Tutor, and Wasteland/Murktide
  entries are exact registrations or exact published registrations. The BUG entry is an
  `inferred-reconstruction`; Grixis is `observed-historical` and marked legal at the cutoff rather
  than observed-current.
- Moonshadow and Cori-Steel Cutter are `inferred-reconstruction` entries whose linked deck headers
  identify Fantasticar-era sources. Their headers disclose maindeck substitutions of four and three
  Fantasticars respectively for the same number of Personal Tutors. The emitted candidates contain
  no Fantasticar.
- Every canonical candidate has a registered version-to-hash mapping. The manifest records an
  August 10 ban-list snapshot and an August 20 legality check date; those fields register the check
  posture but do not turn historical or inferred candidates into observed-current lists.

## Revisions

- 2026-08-20 — Extended the attestation from manifest shape to the per-candidate status,
  reconstruction header, version/hash, and legality-posture specifics used by the matchup design.
