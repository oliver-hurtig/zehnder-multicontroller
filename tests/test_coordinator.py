"""Unit tests for RainmakerCoordinator."""

from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.coordinator import RainmakerCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed


@pytest.mark.asyncio
async def test_coordinator_success(hass, DummyAPI):
    nodes = {
        "node_details": [
            {
                "id": "n1",
                "params": {"multicontrol": {"p1": 1}},
                "config": {"devices": [{"params": [{"name": "p1"}]}]},
            }
        ]
    }

    api = DummyAPI(nodes=nodes)
    # Avoid calling the DataUpdateCoordinator __init__ which tries to
    # inspect the current frame for a config entry. Create the instance
    # without running __init__ and set the needed attributes manually.
    coord = object.__new__(RainmakerCoordinator)
    coord.api = api
    coord.entry = None

    data = await RainmakerCoordinator._async_update_data(coord)
    assert "n1" in data
    assert data["n1"]["p1"]["value"] == 1


@pytest.mark.asyncio
async def test_coordinator_missing_node_details(hass, DummyAPI):
    api = DummyAPI(nodes={"unexpected": []})
    coord = object.__new__(RainmakerCoordinator)
    coord.api = api
    coord.entry = None

    with pytest.raises(UpdateFailed):
        await RainmakerCoordinator._async_update_data(coord)
