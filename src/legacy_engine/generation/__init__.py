"""Deck Generation — consensus, tuning, and export.

Net-new module composing ``analytics/`` (meta-share + deck-card aggregates) and
``ingestion/banlist`` to produce decklists.  Pure, offline, reproducible — zero
network calls.

Public API surfaces:

* ``generation.models``  — ``GeneratedDeck`` result type
* ``generation.consensus`` — ``build_consensus`` / ``card_frequencies``
* ``generation.export``   — ``format_decklist`` / ``moxfield_import_block``
"""

from legacy_engine.generation.models import GeneratedDeck

__all__ = ["GeneratedDeck"]
