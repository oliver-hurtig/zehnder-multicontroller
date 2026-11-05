"""Unit tests for binary sensor platform."""
from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.binary_sensor import async_setup_entry
from custom_components.zehnder_multicontroller.binary_sensor import (
    RainmakerParamBinarySensor,
)
from custom_components.zehnder_multicontroller.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry


def test_binary_sensor_entity_properties(DummyCoordinator):
    data = {
        "n1": {
            "Name": {"value": "Node One"},
            "is_active": {"data_type": "bool", "properties": ["read"], "value": 1},
        }
    }

    coord = DummyCoordinator(data)

    ent = RainmakerParamBinarySensor(coord, "entry1", "n1", "Node One", "is_active")

    assert ent.name == "Node One is_active"
    assert ent.unique_id == "entry1_n1_is_active"
    # boolean value of 1 -> True
    assert ent.is_on is True
    dev = ent.device_info
    # DeviceInfo may be a DeviceInfo object or a dict depending on HA helpers
    if isinstance(dev, dict):
        ids = dev.get("identifiers")
    else:
        ids = dev.identifiers
    assert (DOMAIN, "entry1_n1") in ids


@pytest.mark.asyncio
async def test_async_setup_entry_creates_entities(DummyCoordinator):
    data = {
        "n1": {
            "Name": {"value": "Node One"},
            # include a boolean read-only param and a non-bool param
            "is_active": {"data_type": "bool", "properties": ["read"], "value": 0},
            "config": {"value": "ignore"},
        }
    }

    coord = DummyCoordinator(data)
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="e1")

    class DummyHass:
        def __init__(self):
            self.data = {}

    hass = DummyHass()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coord}

    added = []

    def add(entities, update_before):
        added.extend(entities)

    await async_setup_entry(hass, entry, add)

    assert len(added) == 1
    ent = added[0]
    # value 0 -> False
    assert ent.is_on is False
