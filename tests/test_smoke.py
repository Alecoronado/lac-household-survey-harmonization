"""Smoke tests: the package imports and the CLI is wired up."""

import pytest

import lacharm
from lacharm.cli import main


def test_package_has_version():
    assert lacharm.__version__


def test_cli_runs_without_arguments():
    assert main([]) == 0


def test_cli_prints_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert lacharm.__version__ in capsys.readouterr().out
