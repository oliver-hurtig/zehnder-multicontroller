"""Additional sensor tests for edge cases."""

from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.const import DOMAIN
from custom_components.zehnder_multicontroller.sensor import async_setup_entry
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_async_setup_entry_no_entry_data():
    class DummyHass:
        def __init__(self):
            self.data = {}

    hass = DummyHass()
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="e1")
    added = []

    def add(entities, update_before):
        added.extend(entities)

    # Should simply return without raising and not add entities
    await async_setup_entry(hass, entry, add)
    assert len(added) == 0


@pytest.mark.asyncio
async def test_async_setup_entry_skips_types_and_schedule(DummyCoordinator):
    data = {
        "n1": {
            "Name": {"value": "Node One"},
            "temp_sensor": {"data_type": "int", "value": 5},
            "schedule_1": {"data_type": "string", "value": "skip"},
        }
    }

    coord = DummyCoordinator(data)

    class DummyHass:
        def __init__(self):
            self.data = {}

    hass = DummyHass()
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="e1")
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coord}

    added = []

    def add(entities, update_before):
        added.extend(entities)

    await async_setup_entry(hass, entry, add)
    # numeric read-only params are now exposed as sensors
    assert len(added) == 1
    ent = added[0]
    assert ent.native_value == 5
