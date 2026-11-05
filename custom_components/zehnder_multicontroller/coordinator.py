"""Data coordinator for Zehnder Multicontroller."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import RainmakerAPI
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class RainmakerCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Rainmaker nodes and params."""

    def __init__(
        self, hass: HomeAssistant, api: RainmakerAPI, entry: object | None = None
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="zehnder_multicontroller",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.entry = entry

    async def _ensure_connected(self):
        # Ensure API is connected
        if not getattr(self.api, "is_connected", False):
            _LOGGER.debug("API not connected, attempting reconnect")
            await self.api.async_connect()

    async def _async_update_data(self):
        await self._ensure_connected()
        try:
            nodes = await self.api.async_get_nodes()
        except Exception as err:
            _LOGGER.error("Failed to fetch nodes: %s", err)
            raise UpdateFailed(f"Failed to fetch nodes: {err}") from err

        if "node_details" not in nodes:
            _LOGGER.error("API response missing node_details: %s", nodes)
            raise UpdateFailed(f"API response not in the expected format: {nodes}")

        nodes_dict = {}
        for nd in nodes["node_details"]:
            try:
                node_id = nd["id"]
                # params is an array in config.devices[0].params
                config_params_list = nd["config"]["devices"][0]["params"]
                param_vals = nd["params"]["multicontrol"]

                transformed_params = {}
                # Convert the params list to a dict keyed by param name
                for param_meta in config_params_list:
                    param_name = param_meta["name"]
                    transformed_params[param_name] = param_meta.copy()
                    transformed_params[param_name]["value"] = param_vals.get(param_name)

                nodes_dict[node_id] = transformed_params
                _LOGGER.debug(
                    "Processed node %s with %d params", node_id, len(transformed_params)
                )
            except (KeyError, IndexError, TypeError) as err:
                _LOGGER.warning(
                    "Failed to process node %s: %s", nd.get("id", "unknown"), err
                )
                continue
        if not nodes_dict:
            raise UpdateFailed("No valid nodes found in API response")

        return nodes_dict
