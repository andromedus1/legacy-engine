"""DuckDB adapter for the outcome-free recurrent discovery corpus.

The implementation lives next to the frozen contracts in ``discovery.py`` so
the adapter and core share no duplicate schema.  This module is deliberately a
small import seam: consumers can depend on a source-specific path while the
core still receives only ``OutcomeFreeCorpus``.
"""

from legacy_engine.analytics.eras.discovery import load_outcome_free_corpus

__all__ = ["load_outcome_free_corpus"]
