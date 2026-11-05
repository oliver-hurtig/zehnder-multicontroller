"""API adapter for Rainmaker cloud API."""
from __future__ import annotations

import logging
from typing import Any
from typing import cast

from aiohttp import ClientError
from rainmaker_http.client import RainmakerClient

_LOGGER = logging.getLogger(__name__)


class RainmakerError(Exception):
    """Base exception for Rainmaker adapter."""


class RainmakerAuthError(RainmakerError):
    """Raised for authentication related failures."""


class RainmakerConnectionError(RainmakerError, RuntimeError):
    """Raised for network/connectivity failures.

    Subclasses RuntimeError so callers that catch RuntimeError (legacy
    code paths in the config flow) will correctly treat connection
    failures as connectivity errors.
    """


class RainmakerAPI:
    """HTTP adapter for Rainmaker cloud API using `rainmaker-http`.

    This adapter implements the minimal operations used by the
    integration: login, nodes listing, params/config retrieval and batch set.
    """

    def __init__(
        self, hass: Any | None, host: Any, username: Any, password: Any
    ) -> None:
        """Initialize adapter with Home Assistant `hass`, host and creds."""
        self._hass = hass
        self.host = str(host).rstrip("/") + "/" if host is not None else ""
        self.username = str(username) if username is not None else ""
        self.password = str(password) if password is not None else ""
        self._client: RainmakerClient | None = None
        self._connected = False
        # currently, we only support the multicontrol service
        self._service_name: str = "multicontrol"

    async def async_close(self) -> None:
        """Close any resources held by the adapter."""
        if self._client is not None:
            try:
                await self._client.async_close()
            except (
                ClientError,
                RuntimeError,
            ) as err:  # pragma: no cover - defensive cleanup
                _LOGGER.debug("Error closing rainmaker_http client: %s", err)

        self._client = None
        self._connected = False

    async def async_connect(self) -> None:
        """Authenticate against Rainmaker using the PyPI client."""
        try:
            _LOGGER.debug("Initializing RainmakerClient with host: %s", self.host)
            client = RainmakerClient(self.host)
            self._client = client
            _LOGGER.debug("Attempting login with username: %s", self.username)
            await client.async_login(self.username, self.password)
        except ClientError as err:
            _LOGGER.error("Network error during rainmaker login: %s", err)
            raise RainmakerConnectionError("Network error") from err
        except Exception as err:
            _LOGGER.error(
                "Authentication/login failed: %s (type: %s)", err, type(err).__name__
            )
            raise RainmakerAuthError("Authentication failed") from err

        self._connected = True
        _LOGGER.info("Rainmaker HTTP client login successful (host=%s)", self.host)

    async def _ensure_connection(self) -> None:
        if self._client is None or not self._connected:
            _LOGGER.debug("Rainmaker client not connected; reconnecting")
            await self._reconnect()

    async def _reconnect(self) -> None:
        self._connected = False
        await self.async_close()
        await self.async_connect()

    async def async_get_nodes(self) -> dict[str, Any]:
        """Return a list of normalized nodes with params and params_meta."""
        await self._ensure_connection()

        data: dict[str, Any] | None = None
        for attempt in (1, 2):
            try:
                assert self._client is not None
                _LOGGER.debug(
                    "Fetching nodes from Rainmaker API (attempt %d)...", attempt
                )
                data = cast(
                    dict[str, Any],
                    await self._client.async_get_nodes(node_details=True),
                )
                _LOGGER.debug("Successfully fetched nodes data")
                break
            except Exception as err:  # pragma: no cover - network resilience
                _LOGGER.warning(
                    "Failed to fetch nodes on attempt %d: %s (type: %s)",
                    attempt,
                    err,
                    type(err).__name__,
                )
                if attempt == 1:
                    await self._reconnect()
                    continue
                _LOGGER.error("Exhausted retries fetching nodes after reconnect")
                raise RainmakerConnectionError(f"Failed to fetch nodes: {err}") from err

        if data is None:  # pragma: no cover - defensive safety
            raise RainmakerConnectionError("Failed to fetch nodes: no data returned")
        if "node_details" not in data:
            _LOGGER.error(
                "API response missing node_details. Keys present: %s",
                list(data.keys()) if isinstance(data, dict) else type(data),
            )
            raise RainmakerError(f"Wrong data format for nodes: {data}")

        _LOGGER.debug("Found %d node(s) in response", len(data.get("node_details", [])))
        return data

    async def async_set_param(self, node_id: str, param: str, value: Any) -> None:
        try:
            await self._ensure_connection()
        except RainmakerError:
            raise
        except Exception as err:  # pragma: no cover - defensive
            raise RainmakerConnectionError("Not connected") from err

        payload = {self._service_name: {param: value}}

        batch = [{"node_id": node_id, "payload": payload}]
        result: Any = None
        for attempt in (1, 2):
            try:
                assert self._client is not None
                result = await self._client.async_set_params(batch)
                break
            except Exception as err:
                _LOGGER.debug(
                    "Failed to set param via rainmaker client (attempt %d): %s",
                    attempt,
                    err,
                )
                if attempt == 1:
                    # Most likely an expired session token: log in again and
                    # retry once, mirroring async_get_nodes.
                    try:
                        await self._reconnect()
                    except RainmakerError as reconnect_err:
                        raise RainmakerError(
                            "Failed to set param: reconnect failed"
                        ) from reconnect_err
                    continue
                raise RainmakerError("Failed to set param") from err

        if isinstance(result, list):
            for res in result:
                if res.get("node_id") == node_id and res.get("status") != "success":
                    raise RainmakerError(f"Failed to set param: {res}")

    @property
    def is_connected(self) -> bool:
        return bool(self._connected)
