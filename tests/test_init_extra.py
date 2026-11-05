"""Tests for integration setup/unload flows."""

from __future__ import annotations

import importlib

import pytest
from custom_components.zehnder_multicontroller.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

integ = importlib.import_module("custom_components.zehnder_multicontroller")


@pytest.mark.asyncio
async def test_async_setup_and_unload(monkeypatch):
    # Prepare a fake RainmakerAPI that connects and a simple coordinator
    class FakeAPI:
        def __init__(self, *args, **kwargs):
            pass

        async def async_connect(self):
            return None

    class FakeCoordinator:
        def __init__(self, hass, api, entry):
            self.data = {}

        async def async_config_entry_first_refresh(self):
            return None

    # The async_setup_entry performs local imports; insert fake submodules
    import sys
    import types

    api_mod = types.ModuleType("custom_components.zehnder_multicontroller.api")
    api_mod.RainmakerAPI = FakeAPI
    coord_mod = types.ModuleType(
        "custom_components.zehnder_multicontroller.coordinator"
    )
    coord_mod.RainmakerCoordinator = FakeCoordinator
    # monkeypatch restores the real modules afterwards so other tests aren't
    # affected
    monkeypatch.setitem(
        sys.modules, "custom_components.zehnder_multicontroller.api", api_mod
    )
    monkeypatch.setitem(
        sys.modules, "custom_components.zehnder_multicontroller.coordinator", coord_mod
    )

    class DummyHass:
        def __init__(self):
            self.data = {}
            self.config_entries = type("C", (), {})()

        async def async_forward(self, entry, platforms):
            return None

    hass = DummyHass()

    # stub config_entries behaviors used in async_setup_entry/unload
    async def _forward(entry, platforms):
        return None

    async def _unload(entry, platforms):
        return True

    hass.config_entries.async_forward_entry_setups = _forward
    hass.config_entries.async_unload_platforms = _unload

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "h"}, entry_id="e1")

    result = await integ.async_setup_entry(hass, entry)
    assert result is True
    assert DOMAIN in hass.data

    unloaded = await integ.async_unload_entry(hass, entry)
    assert unloaded is True
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
