"""Additional switch tests for edge cases."""

from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.const import DOMAIN
from custom_components.zehnder_multicontroller.switch import async_setup_entry
from custom_components.zehnder_multicontroller.switch import RainmakerParamSwitch
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_switch_setup_no_entry_data():
    class DummyHass:
        def __init__(self):
            self.data = {}

    hass = DummyHass()
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="e1")
    added = []

    def add(entities, update_before):
        added.extend(entities)

    await async_setup_entry(hass, entry, add)
    assert len(added) == 0


def test_switch_is_on_none(DummyCoordinator):
    data = {"n1": {"Name": {"value": "Node One"}, "param": {"data_type": "bool"}}}
    coord = DummyCoordinator(data)
    ent = RainmakerParamSwitch(coord, "entry1", "n1", "Node One", "param")
    # coordinator has param but no value -> is_on is None
    assert ent.is_on is None
