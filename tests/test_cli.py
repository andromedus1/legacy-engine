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
        ("advise", ("positioning", "sideboard", "whattoplay")),
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
        # ("seed", "cards") is implemented (see test_scryfall); the rest remain stubs.
        (["seed", "cache"], "seed cache"),
        (["seed", "rules"], "seed rules"),
        (["seed", "banlist"], "seed banlist"),
        (["refresh"], "refresh"),
        (["label"], "label"),
        (["report", "meta"], "report meta"),
        (["report", "matchups"], "report matchups"),
        (["report", "tiers"], "report tiers"),
        (["advise", "positioning"], "advise positioning"),
        (["advise", "sideboard"], "advise sideboard"),
        (["advise", "whattoplay"], "advise whattoplay"),
    ],
)
def test_leaf_stubs_not_implemented(runner, args, label):
    result = runner.invoke(main, args)
    assert result.exit_code != 0
    assert f"not implemented: {label}" in result.output
