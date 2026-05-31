"""Configuration for legacy-engine — paths, external sources, constants.

Importing this module has no filesystem side effects; directories are created
by the code that writes into them, not here.
"""

from __future__ import annotations

from pathlib import Path

# ── Paths ──
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCRYFALL_DIR = DATA_DIR / "scryfall"  # Scryfall oracle bulk + name index
CACHE_DIR = DATA_DIR / "cache"        # mirrored fbettega tournament JSON
RULES_DIR = DATA_DIR / "rules"        # vendored MTGOFormatData rules
BANLIST_DIR = DATA_DIR / "banlist"    # dated WotC B&R snapshots
DUCKDB_PATH = DATA_DIR / "legacy.duckdb"  # rebuildable analytical store

# ── Scryfall ──
SCRYFALL_API_BASE = "https://api.scryfall.com"
SCRYFALL_BULK_TYPE = "oracle_cards"
SCRYFALL_API_DELAY = 0.1  # seconds between REST requests (bulk has no limit)
USER_AGENT = "LegacyEngine/0.1.0"

# ── Vendored / mirrored external sources ──
FBETTEGA_CACHE_REPO = "https://github.com/fbettega/MTG_decklistcache"
MTGOFORMATDATA_REPO = "https://github.com/Badaro/MTGOFormatData"

# Pinned commit SHA of the vendored MTGOFormatData rules. Set by
# `legacy refresh rules`. Empty string means unpinned — the archetype layer
# treats that as fail-fast (it must classify against a known rules version).
RULES_PINNED_SHA = ""

# True pinned SHA for refresh_rules (finding #5). refresh_rules checks out this
# exact commit and raises if the post-checkout HEAD doesn't match, preventing
# silent drift when the upstream repo advances.
MTGOFORMATDATA_SHA = "e056bc7d63c0138091986ce1696c705bc7dee296"
