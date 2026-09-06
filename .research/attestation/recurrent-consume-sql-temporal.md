---
source_handle: recurrent-consume-sql-temporal
fetched: 2026-08-13
source_url: https://learn.microsoft.com/en-us/sql/relational-databases/tables/querying-data-in-a-system-versioned-temporal-table?view=sql-server-ver17
provenance: source-direct
substrate_confidence: source-direct
source_class: official-documentation
---

# SQL Server system-time query documentation

## Summary

Microsoft's documentation separates current-state queries, point-in-time reconstruction, period
overlap, period containment, and unrestricted history. It also notes that applying one `AS OF`
clause to a view lets the database reconstruct the participating temporal tables at a common
point. This supplies concrete semantics for an “as of” data-state constraint, but it does not by
itself version code, model configuration, or facts first learned later.

## Key passages

1. `FOR SYSTEM_TIME` exposes `AS OF`, `FROM ... TO`, `BETWEEN`, `CONTAINED IN`, and `ALL` as
   distinct temporal subclauses (lines 33–40).
2. `AS OF` reconstructs the state of data at a specified past instant, interpreted in UTC (lines
   41–54).
3. Applying `AS OF` to a view reconstructs all temporal tables participating in that view at the
   same point, while leaving non-temporal tables unaffected (lines 76–103).
4. `FROM ... TO` and `BETWEEN` select row versions overlapping a period, while `CONTAINED IN`
   selects versions wholly within the period (lines 105–110).

## Structural metadata

Microsoft Learn documentation for SQL Server 2016 and later and related Azure/Fabric products;
page title “Query data in a system-versioned temporal table.”
