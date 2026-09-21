"""CLI entry-point tests for the terminal workspace and restyled commands."""

import builtins

import click
import pytest
from click.testing import CliRunner

from dms.cli import launch_workspace, main


def test_tui_requires_an_interactive_terminal():
    result = CliRunner().invoke(main, ["tui"])
    assert result.exit_code != 0
    assert "interactive terminal" in result.output


def test_bare_dms_on_non_tty_prints_help():
    result = CliRunner().invoke(main, [])
    assert result.exit_code == 0
    assert "tui" in result.output
    assert "validate" in result.output


def test_missing_textual_explains_the_extra(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "dms.terminal":
            raise ModuleNotFoundError("textual", name="textual")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("dms.cli.sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("dms.cli.sys.stdout.isatty", lambda: True)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(click.ClickException) as error:
        launch_workspace()
    assert "dzaleka-metadata-standard[tui]" in str(error.value)


def test_module_entrypoint_runs_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "tui" in result.output


def test_info_and_validate_use_sparse_output():
    runner = CliRunner()
    info = runner.invoke(main, ["info"])
    assert info.exit_code == 0
    assert "DMS" in info.output
    assert "Schema" in info.output
    assert "╔" not in info.output

    valid = runner.invoke(main, ["validate", "examples/story.json"])
    assert valid.exit_code == 0
    assert "✓" in valid.output
    assert "story.json" in valid.output
