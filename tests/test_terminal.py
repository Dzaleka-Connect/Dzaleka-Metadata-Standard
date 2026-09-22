"""Headless tests for the full-screen terminal workspace."""

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("textual")

from unittest.mock import patch

from dms.services import normalize_collection
from dms.terminal import DMSApp

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


async def _wait_until(predicate, timeout=5.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("timed out waiting for terminal workspace")


def test_workspace_loads_examples_and_switches_modes():
    async def scenario():
        app = DMSApp(EXAMPLES_DIR)
        async with app.run_test(size=(120, 40)) as pilot:
            await _wait_until(lambda: not app.loading_records)
            assert app.workspace_mode == "records"
            assert any(entry.key == "story.json" for entry in app.entries)
            assert "story.json" in app.catalog
            await pilot.press("ctrl+3")
            await pilot.pause()
            assert app.workspace_mode == "vocabulary"
            assert app.catalog
            await pilot.press("ctrl+4")
            await pilot.pause()
            assert app.workspace_mode == "schema"
            assert "title" in app.catalog
            await pilot.press("/")
            await pilot.pause()
            assert app.focused.id == "search"
            await pilot.press("escape")
            await pilot.pause()
            assert app.focused.id == "items"

    asyncio.run(scenario())


def test_search_filters_records_and_escape_clears():
    async def scenario():
        app = DMSApp(EXAMPLES_DIR)
        async with app.run_test(size=(120, 40)) as pilot:
            await _wait_until(lambda: not app.loading_records)
            await pilot.press("/")
            await pilot.press(*list("poem"))
            await pilot.pause()
            assert "poem.json" in app.catalog
            assert "story.json" not in app.catalog
            await pilot.press("escape")
            await pilot.pause()
            assert app.query_one("#search").value == ""
            assert "story.json" in app.catalog

    asyncio.run(scenario())


def test_theme_toggle_and_light_start():
    async def scenario():
        app = DMSApp(EXAMPLES_DIR, light=True)
        async with app.run_test(size=(100, 36)) as pilot:
            await _wait_until(lambda: not app.loading_records)
            assert app.theme == "dms-day"
            app.action_toggle_theme()
            await pilot.pause()
            assert app.theme == "dms-night"
            svg = app.export_screenshot()
            assert "Records" in svg
            assert "DMS" in svg

    asyncio.run(scenario())


def test_help_screen_opens_and_closes():
    async def scenario():
        app = DMSApp(EXAMPLES_DIR)
        async with app.run_test(size=(100, 36)) as pilot:
            await _wait_until(lambda: not app.loading_records)
            await pilot.press("f1")
            await pilot.pause()
            assert app.screen.__class__.__name__ == "HelpScreen"
            await pilot.press("escape")
            await pilot.pause()
            assert type(app.screen).__name__ != "HelpScreen"

    asyncio.run(scenario())


def test_jump_copy_and_overview_keys():
    async def scenario():
        app = DMSApp(EXAMPLES_DIR)
        async with app.run_test(size=(120, 40)) as pilot:
            await _wait_until(lambda: not app.loading_records)
            first = next(iter(app.catalog))
            await pilot.press("G")
            await pilot.pause()
            last = list(app.catalog)[-1]
            assert app.selected_key == last
            await pilot.press("g")
            await pilot.pause()
            assert app.selected_key == first
            app.action_copy_json()
            assert '"title"' in app._clipboard
            await pilot.press("ctrl+j")
            await pilot.pause()
            assert app.query_one("#details").active == "json"
            await pilot.press("ctrl+o")
            await pilot.pause()
            assert app.query_one("#details").active == "overview"

    asyncio.run(scenario())


def test_sources_stay_idle_until_reload():
    async def scenario():
        with patch("dms.terminal.ServicesClient") as client:
            app = DMSApp(EXAMPLES_DIR)
            async with app.run_test(size=(120, 40)) as pilot:
                await _wait_until(lambda: not app.loading_records)
                await pilot.press("ctrl+5")
                await pilot.pause()
                assert app.workspace_mode == "sources"
                assert app.source_items == []
                assert app.query_one("#category").value == "encyclopedia"
                client.assert_not_called()
                payload = {"data": {"entries": [{"id": "angela-abizera", "title": "Angela Abizera",
                                                 "summary": "A poet.", "entryType": "person"}]}}
                client.return_value.fetch.return_value = (normalize_collection("encyclopedia", payload), False)
                await pilot.press("ctrl+r")
                await _wait_until(lambda: not app.loading_sources)
                assert "angela-abizera" in app.catalog
                client.return_value.fetch.assert_called_once()
                assert app.selected_key == "angela-abizera"

    asyncio.run(scenario())


def test_loaded_source_survives_leaving_the_workspace():
    async def scenario():
        with patch("dms.terminal.ServicesClient") as client:
            payload = {"data": {"poets": [{"id": "amissi", "title": "Amissi", "description": "A poet."}]}}
            client.return_value.fetch.return_value = (normalize_collection("poets", payload), False)
            app = DMSApp(EXAMPLES_DIR)
            async with app.run_test(size=(120, 40)) as pilot:
                await _wait_until(lambda: not app.loading_records)
                await pilot.pause()
                await pilot.press("ctrl+5")
                await pilot.pause()
                app.query_one("#category").value = "poets"
                await pilot.pause()
                await pilot.press("ctrl+r")
                await _wait_until(lambda: not app.loading_sources and "amissi" in app.catalog)
                await pilot.press("ctrl+1")
                await pilot.pause()
                await pilot.press("ctrl+5")
                await pilot.pause()
                assert app.query_one("#category").value == "poets"
                assert "amissi" in app.catalog

    asyncio.run(scenario())


def test_compact_layout_on_narrow_terminal():
    async def scenario():
        app = DMSApp(EXAMPLES_DIR)
        async with app.run_test(size=(80, 24)) as pilot:
            await _wait_until(lambda: not app.loading_records)
            assert app.has_class("compact")
            assert app.has_class("short")
            await pilot.resize_terminal(140, 40)
            assert not app.has_class("compact")

    asyncio.run(scenario())
