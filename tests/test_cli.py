"""CLI skeleton — groups are discoverable; leaf stubs fail loudly with 'not implemented'."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_top_level_help_lists_groups(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    for group in ("seed", "refresh", "label", "report", "advise"):
        assert group in result.output


@pytest.mark.parametrize(
    "group,subcommands",
    [
        ("seed", ("cards", "cache", "rules", "banlist")),
        ("report", ("meta", "matchups", "tiers")),
        ("advise", ("positioning", "sideboard", "whattoplay", "report")),
    ],
)
def test_group_help_lists_subcommands(runner, group, subcommands):
    result = runner.invoke(main, [group, "--help"])
    assert result.exit_code == 0
    for sub in subcommands:
        assert sub in result.output


@pytest.mark.parametrize(
    "args,label",
    [
        # seed cards/cache/rules/banlist, label, report matchups, report meta, and report tiers are implemented.
        # advise positioning/sideboard/whattoplay/report are also implemented (no longer stubs).
        (["refresh"], "refresh"),
    ],
)
def test_leaf_stubs_not_implemented(runner, args, label):
    result = runner.invoke(main, args)
    assert result.exit_code != 0
    assert f"not implemented: {label}" in result.output


def test_advise_subcommands_require_deck(runner):
    """Implemented advise commands require --deck; missing → non-zero exit + usage error."""
    for sub in ("positioning", "sideboard", "whattoplay", "report"):
        result = runner.invoke(main, ["advise", sub])
        assert result.exit_code != 0, f"advise {sub} should fail without --deck"
