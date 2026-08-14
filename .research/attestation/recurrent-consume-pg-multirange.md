---
source_handle: recurrent-consume-pg-multirange
fetched: 2026-08-13
source_url: https://www.postgresql.org/docs/18/functions-range.html
provenance: source-direct
substrate_confidence: source-direct
source_class: official-documentation
---

# PostgreSQL 18 range and multirange operators

## Summary

The PostgreSQL documentation defines multiranges as a representation that can preserve disjoint
subranges and supplies closed operations for their union, intersection, and difference. It also
defines empty-range behavior.

## Key passages

1. Table 9.59 defines `anymultirange + anymultirange` as a union whose inputs need not overlap or
   be adjacent; its example preserves `[5,10)` and `[15,20)` as two components (lines 68–68).
2. The same table defines `anymultirange * anymultirange` as intersection, with the example
   `{[5,15)} * {[10,20)} = {[10,15)}` (line 69).
3. The difference operator can return two disjoint components, and the documentation advises
   multiranges when a range operation may yield disjoint output (lines 70–73).
4. Empty ranges and multiranges act as the union identity; intersection-relevant ordering
   predicates involving empty values are false (lines 71–72).

## Structural metadata

PostgreSQL 18 official manual, section 9.20, “Range/Multirange Functions and Operators,” Table
9.59.
