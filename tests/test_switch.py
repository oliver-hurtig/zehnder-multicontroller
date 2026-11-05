"""Tests for switch platform entity behaviour."""

from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.const import DOMAIN
from custom_components.zehnder_multicontroller.switch import RainmakerParamSwitch


@pytest.mark.asyncio
async def test_switch_is_on_and_service_calls(monkeypatch, DummyCoordinator, DummyAPI):
    coordinator = DummyCoordinator()
    coordinator.data = {
        "node1": {
            "param1": {"value": 1, "data_type": "bool", "properties": ["write"]},
            "Name": {"value": "Node 1"},
        }
    }

    api = DummyAPI()

    # Create the entity
    switch = RainmakerParamSwitch(coordinator, "entry1", "node1", "Node 1", "param1")

    # Provide hass.data structure expected by the entity methods
    class DummyHass:
        def __init__(self):
            self.data = {DOMAIN: {"entry1": {"coordinator": coordinator, "api": api}}}

    switch.hass = DummyHass()

    assert switch.is_on is True

    # Turn off
    coordinator.api = api
    await switch.async_turn_off()
    api.async_set_param.assert_called_with("node1", "param1", False)
    coordinator.async_request_refresh.assert_awaited()

    # Turn on
    await switch.async_turn_on()
    api.async_set_param.assert_called_with("node1", "param1", True)
    coordinator.async_request_refresh.assert_awaited()
