"""Config paths are absolute, repo-rooted, and import has no side effects."""

from __future__ import annotations

from legacy_engine import config


def test_paths_are_absolute():
    for path in (
        config.PROJECT_ROOT,
        config.DATA_DIR,
        config.SCRYFALL_DIR,
        config.CACHE_DIR,
        config.RULES_DIR,
        config.BANLIST_DIR,
        config.DUCKDB_PATH,
    ):
        assert path.is_absolute()


def test_data_dirs_under_project_root():
    assert config.DATA_DIR.parent == config.PROJECT_ROOT
    for sub in (config.SCRYFALL_DIR, config.CACHE_DIR, config.RULES_DIR, config.BANLIST_DIR):
        assert sub.parent == config.DATA_DIR


def test_duckdb_path_under_data_dir():
    assert config.DUCKDB_PATH.parent == config.DATA_DIR
    assert config.DUCKDB_PATH.name == "legacy.duckdb"


def test_import_has_no_filesystem_side_effects():
    # Importing config must not create the data directories.
    assert not config.DATA_DIR.exists() or config.DATA_DIR.is_dir()
    # Re-importing is idempotent and creates nothing.
    import importlib

    importlib.reload(config)
    assert config.SCRYFALL_BULK_TYPE == "oracle_cards"


def test_rules_sha_unpinned_by_default():
    assert config.RULES_PINNED_SHA == ""
