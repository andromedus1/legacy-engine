"""User personal collection — inventory and decks.

A peer of ``ingestion/`` in the layer diagram (data-acquisition + persistence),
sitting beneath ``analytics/``/``advisory/``/``generation/``.

Raw JSON under ``data/collection/`` is the source of truth (user-authored,
precious, git-/hand-editable).  DuckDB tables are a rebuildable derived cache
for allocation/buildability joins — same SSOT split as ``ingestion/``.
"""
