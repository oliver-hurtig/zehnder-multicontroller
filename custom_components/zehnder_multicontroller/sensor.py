"""Sensor platform for Zehnder Multicontroller."""
from __future__ import annotations

import logging
from functools import cached_property
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.const import EntityCategory
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .const import NUMERIC_DATA_TYPES
from .const import STATISTICS_EXCLUDED_PARAMS
from .helpers import handled_by_climate

_LOGGER = logging.getLogger(__name__)


class RainmakerParamSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str,
        node_id: str,
        node_name: str,
        param: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._node_id = node_id
        self._node_name = node_name
        self._param = param
        self._attr_name = f"{node_name} {param}"
        self._unique_id = f"{entry_id}_{node_id}_{param}"

    @cached_property
    def name(self) -> str | None:
        return self._attr_name

    @cached_property
    def unique_id(self) -> str | None:
        return self._unique_id

    @property
    def native_value(self) -> Any:
        # Do not cache this value — it must reflect the latest
        # coordinator data on every state update.
        params = self.coordinator.data.get(self._node_id, {})
        return params.get(self._param, {}).get("value")

    @cached_property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_{self._node_id}" )},
            name=self._node_name,
            manufacturer="ESP RainMaker",
        )


class RainmakerStatisticsSensor(RainmakerParamSensor):
    """Read-only numeric mirror of a parameter, for long-term statistics.

    Home Assistant only compiles long-term statistics for sensor entities
    with a state_class. Controls (number/switch/climate) and binary sensors
    never get them, so writable and boolean parameters are mirrored here.
    Booleans are recorded as 0/100 % so the hourly mean is the share of
    time the parameter was on.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str,
        node_id: str,
        node_name: str,
        param: str,
        is_bool: bool,
    ) -> None:
        super().__init__(coordinator, entry_id, node_id, node_name, param)
        self._is_bool = is_bool
        self._attr_name = f"{node_name} {param} statistics"
        self._unique_id = f"{entry_id}_{node_id}_{param}_stats"
        if is_bool:
            self._attr_native_unit_of_measurement = PERCENTAGE
        else:
            _apply_unit_and_device_class(self, param)

    @property
    def native_value(self) -> Any:
        value = super().native_value
        if value is None:
            return None
        if self._is_bool:
            return 100 if value else 0
        return value if isinstance(value, (int, float)) else None


def _apply_unit_and_device_class(entity: SensorEntity, param: str) -> None:
    lowered = param.lower()
    if "temp" in lowered:
        entity._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        entity._attr_device_class = SensorDeviceClass.TEMPERATURE
    elif "humidity" in lowered:
        entity._attr_native_unit_of_measurement = PERCENTAGE
        entity._attr_device_class = SensorDeviceClass.HUMIDITY


def _wants_statistics_mirror(param: str, meta: dict[str, Any]) -> bool:
    """Return True if `param` needs a separate statistics sensor.

    Read-only numeric params already get a regular sensor with a
    state_class; everything else that is numeric or boolean is mirrored.
    """
    if param.lower() in STATISTICS_EXCLUDED_PARAMS:
        return False
    dtype = str(meta.get("data_type", "")).lower()
    writable = "write" in meta.get("properties", [])
    if dtype == "bool":
        return True
    return dtype in NUMERIC_DATA_TYPES and writable


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not entry_data:
        _LOGGER.debug("No entry data for %s, skipping sensor setup", entry.entry_id)
        return

    coordinator: DataUpdateCoordinator = entry_data["coordinator"]

    entities: list[RainmakerParamSensor] = []
    for node_id, params in coordinator.data.items():
        node_name = params.get("Name", {}).get("value", node_id)
        for param, meta in params.items():
            # Skip schedules, config, and Name parameters
            if param == "Name" or param == "config" or "schedule" in param.lower():
                continue
            # Statistics mirrors are independent of the climate option, so
            # their entities never appear/disappear when it is toggled.
            if _wants_statistics_mirror(param, meta):
                entities.append(
                    RainmakerStatisticsSensor(
                        coordinator,
                        entry.entry_id,
                        node_id,
                        node_name,
                        param,
                        is_bool=str(meta.get("data_type", "")).lower() == "bool",
                    )
                )
            # Covered by the climate entity -> don't duplicate it
            if handled_by_climate(entry, params, param):
                continue
            dtype = meta.get("data_type", "").lower()
            if "write" not in meta.get("properties", []) and dtype != "bool":
                entity = RainmakerParamSensor(
                    coordinator, entry.entry_id, node_id, node_name, param
                )
                # Attach simple metadata-driven attributes
                _apply_unit_and_device_class(entity, param)
                if dtype in NUMERIC_DATA_TYPES:
                    # Enables long-term statistics
                    entity._attr_state_class = SensorStateClass.MEASUREMENT

                entities.append(entity)

    async_add_entities(entities, True)
