"""Unit tests for sensor platform."""

from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.const import DOMAIN
from custom_components.zehnder_multicontroller.sensor import async_setup_entry
from custom_components.zehnder_multicontroller.sensor import RainmakerParamSensor
from homeassistant.components.sensor import SensorDeviceClass
from pytest_homeassistant_custom_component.common import MockConfigEntry


def test_sensor_entity_properties(DummyCoordinator):
    data = {
        "n1": {
            "Name": {"value": "Node One"},
            "TempSensor": {"data_type": "string", "value": 21.5},
            "humidity_level": {"data_type": "string", "value": 55},
        }
    }

    coord = DummyCoordinator(data)
    ent = RainmakerParamSensor(coord, "entry1", "n1", "Node One", "TempSensor")

    assert ent.name == "Node One TempSensor"
    assert ent.unique_id == "entry1_n1_TempSensor"
    # native_value is taken straight from data
    assert ent.native_value == 21.5


@pytest.mark.asyncio
async def test_async_setup_entry_assigns_device_class_and_unit(DummyCoordinator):
    data = {
        "n1": {
            "Name": {"value": "Node One"},
            "temperature": {"data_type": "string", "value": 22.0},
            "humidity": {"data_type": "string", "value": 45},
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

    # two sensor entities should be added
    assert len(added) == 2
    # find the temperature sensor and verify properties
    temp = next(e for e in added if "temperature" in e.unique_id)
    assert temp._attr_device_class == SensorDeviceClass.TEMPERATURE
    assert temp._attr_native_unit_of_measurement == "°C"
