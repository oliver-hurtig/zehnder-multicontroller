"""Extra unit tests for the Rainmaker API adapter."""
from __future__ import annotations

import pytest
from aiohttp import ClientError
from custom_components.zehnder_multicontroller import api as api_mod
from custom_components.zehnder_multicontroller.api import RainmakerAPI
from custom_components.zehnder_multicontroller.api import RainmakerAuthError
from custom_components.zehnder_multicontroller.api import RainmakerConnectionError
from custom_components.zehnder_multicontroller.api import RainmakerError


@pytest.mark.asyncio
async def test_async_connect_success(monkeypatch):
    class DummyClient:
        def __init__(self, host):
            self.host = host

        async def async_login(self, username, password):
            return None

    monkeypatch.setattr(api_mod, "RainmakerClient", DummyClient)

    api = RainmakerAPI(None, "http://h", "u", "p")
    await api.async_connect()
    assert api.is_connected


@pytest.mark.asyncio
async def test_async_connect_network_error(monkeypatch):
    class DummyClient:
        def __init__(self, host):
            pass

        async def async_login(self, username, password):
            raise ClientError("network")

    monkeypatch.setattr(api_mod, "RainmakerClient", DummyClient)

    api = RainmakerAPI(None, "h", "u", "p")
    with pytest.raises(RainmakerConnectionError):
        await api.async_connect()


@pytest.mark.asyncio
async def test_async_connect_auth_error(monkeypatch):
    class DummyClient:
        def __init__(self, host):
            pass

        async def async_login(self, username, password):
            raise ValueError("bad creds")

    monkeypatch.setattr(api_mod, "RainmakerClient", DummyClient)

    api = RainmakerAPI(None, "h", "u", "p")
    with pytest.raises(RainmakerAuthError):
        await api.async_connect()


@pytest.mark.asyncio
async def test_async_get_nodes_success():
    class GoodClient:
        async def async_get_nodes(self, node_details=True):
            return {"node_details": [{"id": "n1"}]}

    api = RainmakerAPI(None, "h", "u", "p")
    api._client = GoodClient()
    api._connected = True

    data = await api.async_get_nodes()
    assert "node_details" in data


@pytest.mark.asyncio
async def test_async_get_nodes_reconnect(monkeypatch):
    class BadClient:
        async def async_get_nodes(self, node_details=True):
            raise RuntimeError("boom")

    class GoodClient:
        async def async_get_nodes(self, node_details=True):
            return {"node_details": [{"id": "n1"}]}

    api = RainmakerAPI(None, "h", "u", "p")
    api._client = BadClient()
    api._connected = True

    async def fake_reconnect():
        api._client = GoodClient()
        api._connected = True

    monkeypatch.setattr(api, "_reconnect", fake_reconnect)

    data = await api.async_get_nodes()
    assert "node_details" in data


@pytest.mark.asyncio
async def test_async_get_nodes_missing_node_details():
    class Client:
        async def async_get_nodes(self, node_details=True):
            return {}

    api = RainmakerAPI(None, "h", "u", "p")
    api._client = Client()
    api._connected = True

    with pytest.raises(RainmakerError):
        await api.async_get_nodes()


@pytest.mark.asyncio
async def test_async_set_param_success():
    class Client:
        async def async_set_params(self, batch):
            return [
                {
                    "node_id": batch[0]["node_id"] if False else batch[0]["node_id"],
                    "status": "success",
                }
            ]

    api = RainmakerAPI(None, "h", "u", "p")
    api._client = Client()
    api._connected = True

    # Should not raise
    await api.async_set_param("n1", "p", 1)


@pytest.mark.asyncio
async def test_async_set_param_failure_status():
    class Client:
        async def async_set_params(self, batch):
            return [{"node_id": "n1", "status": "failure"}]

    api = RainmakerAPI(None, "h", "u", "p")
    api._client = Client()
    api._connected = True

    with pytest.raises(RainmakerError):
        await api.async_set_param("n1", "p", 1)


@pytest.mark.asyncio
async def test_async_set_param_client_raises():
    class Client:
        async def async_set_params(self, batch):
            raise RuntimeError("boom")

    api = RainmakerAPI(None, "h", "u", "p")
    api._client = Client()
    api._connected = True
    reconnects = []

    async def fake_reconnect():
        reconnects.append(1)

    api._reconnect = fake_reconnect

    with pytest.raises(RainmakerError):
        await api.async_set_param("n1", "p", 1)
    # One reconnect attempt before giving up
    assert len(reconnects) == 1


@pytest.mark.asyncio
async def test_async_set_param_reconnects_on_expired_session():
    calls = []

    class Client:
        async def async_set_params(self, batch):
            calls.append(batch)
            if len(calls) == 1:
                raise RuntimeError("token expired")
            return [{"node_id": "n1", "status": "success"}]

    api = RainmakerAPI(None, "h", "u", "p")
    api._client = Client()
    api._connected = True
    reconnects = []

    async def fake_reconnect():
        reconnects.append(1)

    api._reconnect = fake_reconnect

    await api.async_set_param("n1", "p", 1)
    assert len(calls) == 2
    assert len(reconnects) == 1


@pytest.mark.asyncio
async def test_async_close_handles_error():
    class Client:
        async def async_close(self):
            raise ClientError("close fail")

    api = RainmakerAPI(None, "h", "u", "p")
    api._client = Client()
    api._connected = True

    # Should not raise
    await api.async_close()
    assert api._client is None
    assert api.is_connected is False
