---
source_handle: recurrent-consume-w3c-prov
fetched: 2026-08-13
source_url: https://www.w3.org/TR/prov-o/
provenance: source-direct
substrate_confidence: source-direct
source_class: standard
---

# W3C PROV-O Recommendation

## Summary

PROV-O is the W3C Recommendation for exchanging provenance descriptions. It distinguishes
entities, activities, and agents and provides relations and timestamps for generation, use,
derivation, revision, and primary sources.

## Key passages

1. The W3C identifies PROV-O as a Recommendation mapping the PROV data model to OWL2 and describes
   the PROV family as supporting interoperable provenance exchange (lines 39–55).
2. The expanded vocabulary includes `prov:wasRevisionOf` for a derived entity containing
   substantial content from an earlier entity and `prov:hadPrimarySource` for a preceding entity
   with direct knowledge (lines 321–321).
3. `prov:specializationOf` relates a more specific entity to a general one, illustrated by a web
   page on a particular date versus that page in general (lines 322–324).
4. The Recommendation defines `prov:generatedAtTime` for the completion time of an entity's
   generation, `prov:used` from an activity to an entity it used, and `prov:wasDerivedFrom` for a
   transformation or construction of one entity from another. — sections 3.1, property
   `prov:wasDerivedFrom`; 4.4, property `prov:generatedAtTime`; and the qualified-usage discussion
   and example in section 4.

## Structural metadata

W3C Recommendation published by the Provenance Working Group; official PROV family document.
