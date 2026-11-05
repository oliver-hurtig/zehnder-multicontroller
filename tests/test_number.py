"""Unit tests for number platform."""

from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.const import DOMAIN
from custom_components.zehnder_multicontroller.number import async_setup_entry
from custom_components.zehnder_multicontroller.number import RainmakerParamNumber
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_number_async_set_native_value(DummyCoordinator, DummyAPI):
    data = {
        "n1": {
            "Name": {"value": "Node One"},
            "setpoint": {"data_type": "number", "properties": ["write"], "value": 2},
        }
    }

    coord = DummyCoordinator(data)
    api = DummyAPI()
    coord.api = api

    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="e1")

    class DummyHass:
        def __init__(self):
            self.data = {}

        async def async_add_executor_job(self, func, *args):
            return func()

    hass = DummyHass()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coord}

    ent = RainmakerParamNumber(
        coord,
        entry.entry_id,
        "n1",
        "Node One",
        "setpoint",
        bounds={"min": 0, "max": 10, "step": 0.5},
    )
    ent.hass = hass

    await ent.async_set_native_value(5.0)

    api.async_set_param.assert_called_with("n1", "setpoint", 5.0)
    coord.async_request_refresh.assert_awaited()


@pytest.mark.asyncio
async def test_async_setup_entry_creates_numbers(DummyCoordinator):
    data = {
        "n1": {
            "Name": {"value": "Node One"},
            "config": {"value": "ignore"},
            "num": {
                "data_type": "number",
                "properties": ["write"],
                "value": 1,
                "bounds": {"min": 0, "max": 5},
            },
            "schedule_1": {"data_type": "string", "value": "skip"},
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

    # Only the writeable non-bool parameter should be added
    assert len(added) == 1
    ent = added[0]
    assert ent.unique_id.endswith("_n1_num")
