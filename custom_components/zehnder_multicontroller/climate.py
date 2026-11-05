"""Climate platform for Zehnder Multicontroller."""

from __future__ import annotations

import logging
from functools import cached_property
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .helpers import is_climate_node
from .helpers import use_climate_entity

_LOGGER = logging.getLogger(__name__)

DEFAULT_FAN_NAMES = ["Away", "Low", "Medium", "High"]


class ZehnderClimate(CoordinatorEntity, ClimateEntity):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str,
        node_id: str,
        node_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._node_id = node_id
        self._node_name = node_name
        self._attr_name = node_name
        self._unique_id = f"{entry_id}_{node_id}_climate"
        self._fan_min = 0

        try:
            self._attr_temperature_unit = coordinator.hass.config.units.temperature_unit
        except AttributeError:
            self._attr_temperature_unit = "°C"

        # Initialize fan names based on fan_speed bounds
        self._fan_names = self._initialize_fan_names()

        _LOGGER.debug(
            "Creating ZehnderClimate for node %s with fan names: %s",
            node_id,
            self._fan_names,
        )

        self._attr_supported_features = self.get_supported_features()

    def _fan_bounds(self) -> tuple[int, int]:
        """Return the (min, max) fan_speed bounds as integers."""
        node_data = self.coordinator.data.get(self._node_id, {})
        bounds = node_data.get("fan_speed", {}).get("bounds") or {}
        try:
            min_val = int(bounds.get("min", 0))
            max_val = int(bounds.get("max", min_val + len(DEFAULT_FAN_NAMES) - 1))
        except (TypeError, ValueError):
            min_val, max_val = 0, len(DEFAULT_FAN_NAMES) - 1
        if max_val < min_val:
            max_val = min_val
        return min_val, max_val

    def _initialize_fan_names(self) -> list[str]:
        """Initialize fan mode names based on fan_speed bounds."""
        node_data = self.coordinator.data.get(self._node_id, {})

        if "fan_speed" not in node_data:
            self._fan_min = 0
            return DEFAULT_FAN_NAMES

        min_val, max_val = self._fan_bounds()
        # fan_speed values are offset by the lower bound: value == min_val
        # corresponds to the first fan mode name.
        self._fan_min = min_val

        # Calculate number of levels
        num_levels = max_val - min_val + 1

        # Check if default names match the number of levels
        if num_levels == len(DEFAULT_FAN_NAMES):
            return DEFAULT_FAN_NAMES

        # Generate numeric names if counts don't match
        return [str(i) for i in range(min_val, max_val + 1)]

    @cached_property
    def unique_id(self) -> str | None:
        return self._unique_id

    @cached_property
    def name(self) -> str | None:
        return self._attr_name

    @cached_property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_{self._node_id}")},
            name=self._node_name,
            manufacturer="ESP RainMaker",
        )

    @property
    def current_temperature(self) -> float | None:
        node_data = self.coordinator.data.get(self._node_id, {})
        for param, meta in node_data.items():
            if param.lower() == "temp":
                return meta.get("value")
        return None

    @property
    def target_temperature(self) -> float | None:
        node_data = self.coordinator.data.get(self._node_id, {})
        for param, meta in node_data.items():
            if param.lower() == "temp_setpoint":
                return meta.get("value")
        return None

    def _setpoint_bounds(self) -> dict[str, Any]:
        node_data = self.coordinator.data.get(self._node_id, {})
        bounds = node_data.get("temp_setpoint", {}).get("bounds")
        return bounds if isinstance(bounds, dict) else {}

    @property
    def min_temp(self) -> float:
        min_val = self._setpoint_bounds().get("min")
        if min_val is None:
            return super().min_temp
        min_val = float(min_val)
        # Same adjustment as the number platform: allow 18 °C when the
        # device reports 20 °C as its lower bound.
        return 18.0 if min_val == 20.0 else min_val

    @property
    def max_temp(self) -> float:
        max_val = self._setpoint_bounds().get("max")
        if max_val is None:
            return super().max_temp
        return float(max_val)

    @property
    def target_temperature_step(self) -> float | None:
        step = self._setpoint_bounds().get("step")
        return float(step) if step else None

    @cached_property
    def hvac_modes(self) -> list[HVACMode]:
        return [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode | None:
        node_data = self.coordinator.data.get(self._node_id, {})
        season = None
        enabled = None
        for param, meta in node_data.items():
            if param.lower() == "season":
                season = meta.get("value")
            elif param.lower() == "radiant_enabled":
                enabled = meta.get("value")
        if not enabled:
            return HVACMode.OFF
        if season == 1:
            return HVACMode.HEAT
        if season == 2:
            return HVACMode.COOL
        return None

    def get_supported_features(self) -> ClimateEntityFeature:
        features_flag = ClimateEntityFeature(0)
        node_data = self.coordinator.data.get(self._node_id, {})

        has_temp_setpoint = "temp_setpoint" in node_data and "write" in node_data[
            "temp_setpoint"
        ].get("properties", [])
        if has_temp_setpoint:
            features_flag |= ClimateEntityFeature.TARGET_TEMPERATURE

        has_fan = "fan_speed" in node_data and "write" in node_data["fan_speed"].get(
            "properties", []
        )
        if has_fan:
            features_flag |= ClimateEntityFeature.FAN_MODE

        _LOGGER.debug(
            "ZehnderClimate(%s) params keys=%s -> features=%s",
            self._node_id,
            list(node_data.keys()),
            features_flag,
        )

        return features_flag

    def _handle_coordinator_update(self) -> None:
        try:
            # Recompute any derived attributes that depend on coordinator data
            # so they reflect runtime changes (e.g. fan_speed bounds -> names).
            self._fan_names = self._initialize_fan_names()
            self._attr_supported_features = self.get_supported_features()
        except Exception:  # pragma: no cover - defensive
            _LOGGER.exception(
                "Failed to update supported features for %s", self._node_id
            )
        super()._handle_coordinator_update()

    @property
    def fan_modes(self) -> list[str] | None:
        return self._fan_names

    @property
    def fan_mode(self) -> str | None:
        node_data = self.coordinator.data.get(self._node_id, {})
        if "fan_speed" not in node_data:
            return None
        val = node_data["fan_speed"].get("value")
        if val is None:
            return None
        try:
            index = int(val) - self._fan_min
        except (TypeError, ValueError):
            return None

        if 0 <= index < len(self._fan_names):
            return self._fan_names[index]
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        try:
            await self.coordinator.api.async_set_param(
                self._node_id, "temp_setpoint", temperature
            )
            await self.coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - runtime dependent
            _LOGGER.exception("Failed to set temperature on %s", self._node_id)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        try:
            if hvac_mode == HVACMode.OFF.value:
                await self.coordinator.api.async_set_param(
                    self._node_id, "radiant_enabled", False
                )
            elif hvac_mode == HVACMode.HEAT.value:
                await self.coordinator.api.async_set_param(self._node_id, "season", 1)
                await self.coordinator.api.async_set_param(
                    self._node_id, "radiant_enabled", True
                )
            elif hvac_mode == HVACMode.COOL.value:
                await self.coordinator.api.async_set_param(self._node_id, "season", 2)
                await self.coordinator.api.async_set_param(
                    self._node_id, "radiant_enabled", True
                )
            await self.coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - runtime dependent
            _LOGGER.exception("Failed to set hvac mode on %s", self._node_id)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        try:
            if fan_mode not in self._fan_names:
                _LOGGER.warning("Unknown fan mode: %s", fan_mode)
                return
            level = self._fan_names.index(fan_mode) + self._fan_min
            await self.coordinator.api.async_set_param(
                self._node_id, "fan_speed", level
            )
            await self.coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - runtime dependent
            _LOGGER.exception("Failed to set fan mode on %s", self._node_id)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    _LOGGER.info("Setting up climate platform for entry %s", entry.entry_id)

    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not entry_data:
        _LOGGER.error(
            "No entry data found for %s, aborting climate setup", entry.entry_id
        )
        return

    if not use_climate_entity(entry):
        _LOGGER.info(
            "Climate entity disabled in options; using individual entities instead"
        )
        return

    coordinator = entry_data["coordinator"]
    _LOGGER.debug("Coordinator data contains %d nodes", len(coordinator.data))

    entities: list[ZehnderClimate] = []

    for node_id, params in coordinator.data.items():
        _LOGGER.debug("Checking node %s for climate entity creation", node_id)
        _LOGGER.debug("Node %s params: %s", node_id, list(params.keys()))

        if not is_climate_node(params):
            _LOGGER.debug("Node %s does not have 'temp' parameter, skipping", node_id)
            continue

        # Always (re)create the entity object. An existing entity registry
        # entry with the same unique_id is reattached automatically by HA;
        # skipping it here leaves the registry entry orphaned, which shows
        # up as "unavailable" after every restart or reload.
        node_name = params.get("Name", {}).get("value", node_id)
        _LOGGER.info(
            "Creating climate entity for node %s (name: %s)", node_id, node_name
        )
        entities.append(ZehnderClimate(coordinator, entry.entry_id, node_id, node_name))

    _LOGGER.info("Adding %d climate entities", len(entities))
    async_add_entities(entities, True)
    _LOGGER.info("Climate platform setup completed")
