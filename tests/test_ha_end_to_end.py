"""End-to-end tests that load the integration in a real Home Assistant core."""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from custom_components.zehnder_multicontroller.const import CONF_USE_CLIMATE
from custom_components.zehnder_multicontroller.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry

PARAMS = [
    {"name": "Name", "data_type": "string", "properties": ["read"]},
    {"name": "temp", "data_type": "float", "properties": ["read"]},
    {"name": "humidity", "data_type": "float", "properties": ["read"]},
    {
        "name": "temp_setpoint",
        "data_type": "float",
        "properties": ["read", "write"],
        "bounds": {"min": 18, "max": 28, "step": 0.5},
    },
    {"name": "season", "data_type": "int", "properties": ["read", "write"]},
    {
        "name": "fan_speed",
        "data_type": "int",
        "properties": ["read", "write"],
        "bounds": {"min": 0, "max": 3},
    },
    {"name": "radiant_enabled", "data_type": "bool", "properties": ["read", "write"]},
    {"name": "boost", "data_type": "bool", "properties": ["read", "write"]},
    {"name": "filter_alarm", "data_type": "bool", "properties": ["read"]},
]
VALUES = {
    "Name": "Living",
    "temp": 21.0,
    "humidity": 40.0,
    "temp_setpoint": 22.0,
    "season": 1,
    "fan_speed": 1,
    "radiant_enabled": True,
    "boost": False,
    "filter_alarm": False,
}
NODES = {
    "node_details": [
        {
            "id": "n1",
            "config": {"devices": [{"params": PARAMS}]},
            "params": {"multicontrol": VALUES},
        }
    ]
}


class FakeAPI:
    """Stands in for the cloud API only; everything above it is real."""

    instances: list = []

    def __init__(self, *args, **kwargs):
        self.is_connected = False
        self.async_set_param = AsyncMock()
        FakeAPI.instances.append(self)

    async def async_connect(self):
        self.is_connected = True

    async def async_close(self):
        self.is_connected = False

    async def async_get_nodes(self):
        return deepcopy(NODES)


@pytest.fixture
async def loaded_entry(hass, enable_custom_integrations, monkeypatch):
    FakeAPI.instances = []
    monkeypatch.setattr(
        "custom_components.zehnder_multicontroller.api.RainmakerAPI", FakeAPI
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "https://h/", "username": "u", "password": "p"},
        entry_id="e1",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


def _entity_id(hass, platform, suffix):
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"e1_n1_{suffix}")


def _available_state(hass, platform, suffix):
    entity_id = _entity_id(hass, platform, suffix)
    assert entity_id is not None, f"{platform} {suffix} is not registered"
    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} has no state"
    assert state.state != STATE_UNAVAILABLE, f"{entity_id} is unavailable"
    return state


async def test_climate_works_in_real_core(hass, loaded_entry):
    state = _available_state(hass, "climate", "climate")
    assert state.state == "heat"
    assert state.attributes["current_temperature"] == 21.0
    assert state.attributes["temperature"] == 22.0
    assert state.attributes["fan_mode"] == "Low"
    assert state.attributes["min_temp"] == 18.0
    assert state.attributes["max_temp"] == 28.0
    assert state.attributes["target_temp_step"] == 0.5


async def test_climate_logs_no_temperature_deprecations(hass, loaded_entry, caplog):
    """Reading the state must not use the climate names deprecated in 2026.11."""
    _available_state(hass, "climate", "climate")
    assert "deprecated" not in caplog.text


@pytest.fixture
def fahrenheit_hass(hass):
    hass.config.units = US_CUSTOMARY_SYSTEM


async def test_climate_converts_from_celsius_when_ha_uses_fahrenheit(
    hass, fahrenheit_hass, loaded_entry
):
    """Regression: device °C values were treated as °F on Fahrenheit systems."""
    state = _available_state(hass, "climate", "climate")
    assert state.attributes["current_temperature"] == 70  # 21 °C
    assert state.attributes["temperature"] == 72  # 22 °C
    assert state.attributes["min_temp"] == 64  # 18 °C
    assert state.attributes["max_temp"] == 82  # 28 °C

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": state.entity_id, "temperature": 73.4},
        blocking=True,
    )
    node, param, value = FakeAPI.instances[-1].async_set_param.await_args.args
    assert (node, param) == ("n1", "temp_setpoint")
    assert value == pytest.approx(23.0)


@pytest.mark.parametrize("cycles", [1, 3])
async def test_climate_stays_available_after_reload(hass, loaded_entry, cycles):
    """Regression: the climate entity went unavailable after a reload/restart."""
    for _ in range(cycles):
        assert await hass.config_entries.async_reload(loaded_entry.entry_id)
        await hass.async_block_till_done()
        assert _available_state(hass, "climate", "climate").state == "heat"


async def test_climate_services_reach_the_api(hass, loaded_entry):
    entity_id = _entity_id(hass, "climate", "climate")
    api = FakeAPI.instances[-1]

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": entity_id, "temperature": 23},
        blocking=True,
    )
    api.async_set_param.assert_awaited_with("n1", "temp_setpoint", 23)

    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": entity_id, "fan_mode": "High"},
        blocking=True,
    )
    api.async_set_param.assert_awaited_with("n1", "fan_speed", 3)

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": "off"},
        blocking=True,
    )
    api.async_set_param.assert_awaited_with("n1", "radiant_enabled", False)


async def test_statistics_and_either_or_in_climate_mode(hass, loaded_entry):
    # Controls are only in the climate entity...
    assert _entity_id(hass, "number", "temp_setpoint") is None
    assert _entity_id(hass, "switch", "radiant_enabled") is None
    # ...others stay separate...
    assert _available_state(hass, "switch", "boost").state == "off"
    # ...and read-only numbers record long-term statistics
    temp = _available_state(hass, "sensor", "temp")
    assert temp.attributes["state_class"] == "measurement"
    assert temp.attributes["unit_of_measurement"] == "°C"

    setpoint = _available_state(hass, "sensor", "temp_setpoint_stats")
    assert float(setpoint.state) == 22.0
    assert setpoint.attributes["state_class"] == "measurement"
    radiant = _available_state(hass, "sensor", "radiant_enabled_stats")
    assert float(radiant.state) == 100
    assert radiant.attributes["unit_of_measurement"] == "%"
    assert _entity_id(hass, "sensor", "season_stats") is None


async def test_options_flow_switches_modes(hass, loaded_entry):
    registry = er.async_get(hass)

    async def set_use_climate(value):
        flow = await hass.config_entries.options.async_init(loaded_entry.entry_id)
        assert flow["step_id"] == "init"
        result = await hass.config_entries.options.async_configure(
            flow["flow_id"], user_input={CONF_USE_CLIMATE: value}
        )
        assert result["type"] == "create_entry"
        await hass.async_block_till_done()
        assert loaded_entry.state is ConfigEntryState.LOADED

    await set_use_climate(False)
    assert _entity_id(hass, "climate", "climate") is None
    assert _available_state(hass, "number", "temp_setpoint")
    assert _available_state(hass, "switch", "radiant_enabled")
    assert _available_state(hass, "sensor", "temp_setpoint_stats")

    await set_use_climate(True)
    assert _available_state(hass, "climate", "climate")
    assert _entity_id(hass, "number", "temp_setpoint") is None

    # Nothing is left behind as unavailable
    for reg_entry in er.async_entries_for_config_entry(registry, "e1"):
        state = hass.states.get(reg_entry.entity_id)
        assert state is not None and state.state != STATE_UNAVAILABLE, reg_entry
