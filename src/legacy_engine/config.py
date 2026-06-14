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

# Package-shipped (tracked in git) static data — hand-curated, version-stamped configs.
PACKAGE_DATA_DIR = Path(__file__).parent / "data"
VARIANTS_DIR = PACKAGE_DATA_DIR / "variants"
VARIANTS_REGISTRY_PATH = VARIANTS_DIR / "legacy.json"  # shipped variant registry
PLAYERS_DIR = PACKAGE_DATA_DIR / "players"
ALIASES_PATH = PLAYERS_DIR / "aliases.json"             # shipped player-alias map (curated SSOT)

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

# ── Collection (user's personal inventory + decks) ──
COLLECTION_DIR = DATA_DIR / "collection"
INVENTORY_PATH = COLLECTION_DIR / "inventory.json"
DECKS_DIR = COLLECTION_DIR / "decks"
LOCAL_OWNER = "local"  # single-user default; future multi-user: pass a real user id

# ── Visualization ──
VIZ_DIR = DATA_DIR / "viz"                 # default output dir; mkdir at write time, never on import
VIZ_PNG_SCALE = 2.0                        # vl_convert PNG scale multiplier (2x for crisp raster)
VIZ_VL_VERSION = "6.4"                     # vl_convert vl_version pin (bundled set tops out at 6.4)
VL_SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v6.json"  # spec "$schema" value
VIZ_CDN_VEGA = "https://cdn.jsdelivr.net/npm/vega@6"               # dashboard template (later feature)
VIZ_CDN_VEGA_LITE = "https://cdn.jsdelivr.net/npm/vega-lite@6"     # matches vl-convert's bundled JS
VIZ_CDN_VEGA_EMBED = "https://cdn.jsdelivr.net/npm/vega-embed@7"
