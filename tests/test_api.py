"""Unit tests for the Rainmaker API adapter."""
from __future__ import annotations

import asyncio

import pytest
from custom_components.zehnder_multicontroller import api as api_module


class DummyClient:
    def __init__(self, host: str) -> None:
        self.host = host
        self._closed = False

    async def async_login(self, username: str, password: str) -> None:
        if username == "bad":
            raise Exception("auth failed")

    async def async_get_nodes(self, node_details: bool = False) -> dict:
        await asyncio.sleep(0)
        return {
            "node_details": [
                {
                    "id": "n1",
                    "params": {"multicontrol": {"p": 1}},
                    "config": {"devices": [{"params": [{"name": "p"}]}]},
                }
            ]
        }

    async def async_set_params(self, batch):
        return [{"node_id": batch[0]["node_id"], "status": "success"}]

    async def async_close(self):
        self._closed = True


@pytest.mark.asyncio
async def test_rainmaker_api_connect_and_get_nodes(monkeypatch):
    """Test that RainmakerAPI connects and fetches nodes using the internal client."""

    # Patch the external RainmakerClient to our dummy
    monkeypatch.setattr(api_module, "RainmakerClient", DummyClient)

    api = api_module.RainmakerAPI(None, "https://host/", "user", "pass")
    await api.async_connect()
    assert api.is_connected

    nodes = await api.async_get_nodes()
    assert "node_details" in nodes
    assert nodes["node_details"][0]["id"] == "n1"


@pytest.mark.asyncio
async def test_rainmaker_api_set_param_and_close(monkeypatch):
    monkeypatch.setattr(api_module, "RainmakerClient", DummyClient)

    api = api_module.RainmakerAPI(None, "https://host/", "user", "pass")
    await api.async_connect()
    await api.async_set_param("n1", "p", 2)
    await api.async_close()
    assert not api.is_connected


@pytest.mark.asyncio
async def test_async_get_nodes_wrong_format(monkeypatch):
    class BadClient:
        def __init__(self, host: str) -> None:
            self.host = host

        async def async_login(self, username: str, password: str) -> None:
            return None

        async def async_get_nodes(self, node_details: bool = False) -> dict:
            return {"unexpected": []}

        async def async_close(self):
            return None

    monkeypatch.setattr(api_module, "RainmakerClient", BadClient)

    api = api_module.RainmakerAPI(None, "https://host/", "user", "pass")
    await api.async_connect()
    with pytest.raises(api_module.RainmakerError):
        await api.async_get_nodes()


@pytest.mark.asyncio
async def test_async_set_param_not_connected_reconnect_fails():
    api = api_module.RainmakerAPI(None, "https://host/", "user", "pass")

    async def failing_reconnect():
        raise api_module.RainmakerConnectionError("Network error")

    api._reconnect = failing_reconnect
    with pytest.raises(api_module.RainmakerConnectionError):
        await api.async_set_param("n1", "p", 1)
