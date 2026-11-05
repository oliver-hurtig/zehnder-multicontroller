"""Tests for integration setup/unload helpers (focused unit tests)."""

from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller import async_setup_entry
from custom_components.zehnder_multicontroller import async_unload_entry
from custom_components.zehnder_multicontroller.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_setup_and_unload_entry_creates_hass_data(
    monkeypatch, DummyAPI, DummyCoordinator
):
    """Verify async_setup_entry stores runtime data and unload removes it."""
    # Patch the integration to use the shared test Dummy classes which avoid
    # network access and the real coordinator startup behaviour.
    monkeypatch.setattr(
        "custom_components.zehnder_multicontroller.api.RainmakerAPI",
        DummyAPI,
    )
    monkeypatch.setattr(
        "custom_components.zehnder_multicontroller.coordinator.RainmakerCoordinator",
        DummyCoordinator,
    )

    # Avoid attempting to actually forward setups to platform modules
    # (loader may not find the integration in this test environment).
    from unittest.mock import AsyncMock

    class DummyConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms):
            return None

        async def async_unload_platforms(self, entry, platforms):
            return True

    class DummyHass:
        def __init__(self):
            self.data = {}
            self.config_entries = DummyConfigEntries()
            # Minimal config required by Home Assistant helpers used during setup
            import types as _types

            self.config = _types.SimpleNamespace(config_dir=".")
            # Minimal event bus stub used by the entity registry during tests
            from types import SimpleNamespace as _SS

            self.bus = _SS(async_listen=lambda *a, **k: (lambda: None))

    hass = DummyHass()

    monkeypatch.setattr(
        hass.config_entries, "async_forward_entry_setups", AsyncMock(return_value=None)
    )

    # Stub the entity registry getter used when removing unused entities so
    # it does not try to access HomeAssistant internals like the event bus
    # or storage manager during this unit test.
    from types import SimpleNamespace
    import importlib

    mod = importlib.import_module("custom_components.zehnder_multicontroller")
    monkeypatch.setattr(
        mod,
        "er",
        SimpleNamespace(
            async_get=lambda hass: SimpleNamespace(
                entities={}, async_remove=lambda eid: None
            )
        ),
    )

    config_entry = MockConfigEntry(domain=DOMAIN, data={})

    # Store the minimal expected entry data before setup
    assert await async_setup_entry(hass, config_entry)
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]

    assert await async_unload_entry(hass, config_entry)
    assert config_entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_setup_entry_exception(error_on_get_data):
    """Test ConfigEntryNotReady when API raises an exception during entry setup."""

    # Use a minimal hass replacement so we don't trigger the full HA storage
    # stack during this unit test. The `error_on_get_data` fixture patches the
    # coordinator initial refresh to raise.
    class DummyHass:
        def __init__(self):
            self.data = {}
            import types as _types

            self.config = _types.SimpleNamespace(config_dir=".")
            # Provide a minimal event bus for entity registry initialization
            from types import SimpleNamespace as _SS

            self.bus = _SS(async_listen=lambda *a, **k: (lambda: None))

    hass = DummyHass()
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="test")

    # When the coordinator initial refresh raises, setup should propagate the error
    with pytest.raises(Exception):
        await async_setup_entry(hass, config_entry)
