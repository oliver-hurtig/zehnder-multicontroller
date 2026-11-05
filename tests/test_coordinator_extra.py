"""Extra tests for coordinator to cover connect and error paths."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from custom_components.zehnder_multicontroller.coordinator import RainmakerCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed


@pytest.mark.asyncio
async def test_ensure_connected_calls_connect():
    api = type("A", (), {})()
    api.is_connected = False
    api.async_connect = AsyncMock()

    coord = object.__new__(RainmakerCoordinator)
    coord.api = api

    await RainmakerCoordinator._ensure_connected(coord)
    api.async_connect.assert_awaited()


@pytest.mark.asyncio
async def test_update_data_raises_on_api_error(DummyAPI):
    api = DummyAPI()

    async def _bad():
        raise RuntimeError("boom")

    api.async_get_nodes = _bad

    coord = object.__new__(RainmakerCoordinator)
    coord.api = api
    coord.entry = None

    with pytest.raises(UpdateFailed):
        await RainmakerCoordinator._async_update_data(coord)


@pytest.mark.asyncio
async def test_update_data_no_valid_nodes(DummyAPI):
    # node_details exists but entries are malformed so processing fails
    nodes = {"node_details": [{"id": "n1", "params": {}, "config": {}}]}
    api = DummyAPI(nodes=nodes)

    coord = object.__new__(RainmakerCoordinator)
    coord.api = api
    coord.entry = None

    with pytest.raises(UpdateFailed):
        await RainmakerCoordinator._async_update_data(coord)


def test_coordinator_init_with_hass(hass, DummyAPI, monkeypatch):
    # Prevent frame helper errors by silencing report_usage
    import homeassistant.helpers.frame as _frame

    monkeypatch.setattr(_frame, "report_usage", lambda *a, **k: None)

    api = DummyAPI()
    coord = RainmakerCoordinator(hass, api)
    assert coord.api is api
