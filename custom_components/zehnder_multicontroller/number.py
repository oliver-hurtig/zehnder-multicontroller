"""Number platform for Zehnder Multicontroller."""

from __future__ import annotations

import logging
from functools import cached_property

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .helpers import handled_by_climate

_LOGGER = logging.getLogger(__name__)


class RainmakerParamNumber(CoordinatorEntity, NumberEntity):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str,
        node_id: str,
        node_name: str,
        param: str,
        bounds: dict | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._node_id = node_id
        self._node_name = node_name
        self._param = param
        self._attr_name = f"{node_name} {param}"
        self._unique_id = f"{entry_id}_{node_id}_{param}"
        # Set bounds from metadata
        if bounds and isinstance(bounds, dict):
            if float(bounds.get("min")) == 20.0:
                bounds["min"] = 18.0  # adjust min temp to 18C
            self._attr_native_min_value = bounds.get("min")
            self._attr_native_max_value = bounds.get("max")
            self._attr_native_step = bounds.get("step", 1)

    @cached_property
    def name(self) -> str | None:
        return self._attr_name

    @cached_property
    def unique_id(self) -> str | None:
        return self._unique_id

    @property
    def native_value(self) -> float | None:
        params = self.coordinator.data.get(self._node_id, {})
        return params.get(self._param, {}).get("value")

    @cached_property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_{self._node_id}")},
            name=self._node_name,
            manufacturer="ESP RainMaker",
        )

    async def async_set_native_value(self, value: float) -> None:
        await self.hass.async_add_executor_job(lambda: None)
        try:
            await self.hass.data[DOMAIN][self._entry_id][
                "coordinator"
            ].api.async_set_param(self._node_id, self._param, value)
        except Exception:  # pragma: no cover - surface errors to logs
            _LOGGER.exception(
                "Error setting param %s on node %s", self._param, self._node_id
            )
        finally:
            await self.hass.data[DOMAIN][self._entry_id][
                "coordinator"
            ].async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not entry_data:
        _LOGGER.debug("No entry data for %s, skipping number setup", entry.entry_id)
        return

    coordinator: DataUpdateCoordinator = entry_data["coordinator"]

    entities: list[RainmakerParamNumber] = []
    for node_id, params in coordinator.data.items():
        node_name = params.get("Name", {}).get("value", node_id)
        for param, meta in params.items():
            # Skip schedules, config, and Name parameters
            if param == "Name" or param == "config" or "schedule" in param.lower():
                continue
            # Covered by the climate entity -> don't duplicate it
            if handled_by_climate(entry, params, param):
                continue
            if (
                "write" in meta.get("properties", [])
                and meta.get("data_type") != "bool"
            ):
                bounds = meta.get("bounds")
                entity = RainmakerParamNumber(
                    coordinator, entry.entry_id, node_id, node_name, param, bounds
                )
                entities.append(entity)

    async_add_entities(entities, True)
