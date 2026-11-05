"""Constants for Zehnder Multicontroller."""
from __future__ import annotations

from homeassistant.const import Platform

# Base component constants
NAME = "Zehnder Multicontroller"
DOMAIN = "zehnder_multicontroller"
VERSION = "0.2.4"
ATTRIBUTION = "Data provided by Zehnder Multicontroller Integration"

# Platforms
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Default polling interval in seconds
DEFAULT_SCAN_INTERVAL = 120

# Options
CONF_USE_CLIMATE = "use_climate_entity"
DEFAULT_USE_CLIMATE = True

# Node parameters that are controlled through the climate entity. When the
# climate entity is enabled these are not also exposed as individual
# number/switch entities. The read-only "temp" sensor is kept in both modes
# because it carries the temperature's long-term statistics.
CLIMATE_PARAMS = frozenset({"temp_setpoint", "season", "radiant_enabled", "fan_speed"})

# RainMaker data types that are numeric (eligible for a state_class)
NUMERIC_DATA_TYPES = frozenset({"int", "float"})

# Numeric params whose average is meaningless (modes/enums), so no
# statistics sensor is created for them.
STATISTICS_EXCLUDED_PARAMS = frozenset({"season"})
