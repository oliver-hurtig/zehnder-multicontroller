"""Edge-case tests for setup, reconnects and entity properties."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import custom_components.zehnder_multicontroller as integ
import pytest
from custom_components.zehnder_multicontroller.api import RainmakerAPI
from custom_components.zehnder_multicontroller.api import RainmakerAuthError
from custom_components.zehnder_multicontroller.api import RainmakerError
from custom_components.zehnder_multicontroller.binary_sensor import (
    async_setup_entry as binary_sensor_setup,
)
from custom_components.zehnder_multicontroller.climate import DEFAULT_FAN_NAMES
from custom_components.zehnder_multicontroller.climate import ZehnderClimate
from custom_components.zehnder_multicontroller.const import CONF_USE_CLIMATE
from custom_components.zehnder_multicontroller.const import DOMAIN
from custom_components.zehnder_multicontroller.number import (
    async_setup_entry as number_setup,
)
from custom_components.zehnder_multicontroller.number import RainmakerParamNumber
from custom_components.zehnder_multicontroller.switch import RainmakerParamSwitch
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry


# --- integration setup -------------------------------------------------------


async def test_setup_raises_not_ready_when_connect_fails(monkeypatch):
    class FailingAPI:
        def __init__(self, *args, **kwargs):
            pass

        async def async_connect(self):
            raise RainmakerAuthError("nope")

    monkeypatch.setattr(
        "custom_components.zehnder_multicontroller.api.RainmakerAPI", FailingAPI
    )
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "h"}, entry_id="e1")
    with pytest.raises(ConfigEntryNotReady):
        await integ.async_setup_entry(SimpleNamespace(data={}), entry)


async def test_update_listener_reloads_entry():
    reload = AsyncMock()
    hass = SimpleNamespace(config_entries=SimpleNamespace(async_reload=reload))
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="e1")
    await integ._async_update_listener(hass, entry)
    reload.assert_awaited_once_with("e1")


def test_remove_unused_entities_ignores_non_climate_nodes(monkeypatch):
    def fail(hass):
        raise AssertionError("registry should not be accessed")

    monkeypatch.setattr("custom_components.zehnder_multicontroller.er.async_get", fail)
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="e1")
    # No node has 'temp' -> nothing to remove -> registry untouched
    integ._async_remove_unused_entities(
        None, entry, {"n1": {"fan_speed": {"value": 1}}}
    )


# --- API reconnects ----------------------------------------------------------


async def test_reconnect_closes_and_connects():
    api = RainmakerAPI(None, "h", "u", "p")
    calls = []

    async def close():
        calls.append("close")

    async def connect():
        calls.append("connect")

    api.async_close = close
    api.async_connect = connect
    api._connected = True
    await api._reconnect()
    assert calls == ["close", "connect"]


async def test_set_param_reconnect_failure_raises():
    class Client:
        async def async_set_params(self, batch):
            raise RuntimeError("token expired")

    api = RainmakerAPI(None, "h", "u", "p")
    api._client = Client()
    api._connected = True

    async def failing_reconnect():
        raise RainmakerAuthError("login failed")

    api._reconnect = failing_reconnect
    with pytest.raises(RainmakerError, match="reconnect failed"):
        await api.async_set_param("n1", "p", 1)


# --- climate -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("bounds", "expected"),
    [
        # Unparseable bounds -> default 4 levels
        ({"min": "x", "max": 3}, DEFAULT_FAN_NAMES),
        # max below min -> single level
        ({"min": 2, "max": 1}, ["2"]),
    ],
)
def test_fan_names_with_bad_bounds(DummyCoordinator, bounds, expected):
    data = {"n1": {"temp": {"value": 20}, "fan_speed": {"bounds": bounds}}}
    ent = ZehnderClimate(DummyCoordinator(data), "e1", "n1", "Node")
    assert ent.fan_modes == expected


def test_fan_mode_non_numeric_value(DummyCoordinator):
    data = {
        "n1": {
            "temp": {"value": 20},
            "fan_speed": {"value": "high", "bounds": {"min": 0, "max": 3}},
        }
    }
    ent = ZehnderClimate(DummyCoordinator(data), "e1", "n1", "Node")
    assert ent.fan_mode is None


def test_climate_temp_limits_without_bounds(DummyCoordinator):
    data = {"n1": {"temp": {"value": 20}, "temp_setpoint": {"value": 21}}}
    ent = ZehnderClimate(DummyCoordinator(data), "e1", "n1", "Node")
    # Falls back to the Home Assistant defaults
    assert ent.min_temp == 7
    assert ent.max_temp == 35
    assert ent.target_temperature_step is None


def test_climate_min_temp_adjusted_from_20(DummyCoordinator):
    data = {
        "n1": {
            "temp": {"value": 20},
            "temp_setpoint": {"value": 21, "bounds": {"min": 20, "max": 26}},
        }
    }
    ent = ZehnderClimate(DummyCoordinator(data), "e1", "n1", "Node")
    assert ent.min_temp == 18.0


# --- number / switch / binary_sensor -----------------------------------------


def test_number_properties_and_min_adjustment(DummyCoordinator):
    data = {"n1": {"temp_setpoint": {"value": 21.5}}}
    ent = RainmakerParamNumber(
        DummyCoordinator(data),
        "e1",
        "n1",
        "Node",
        "temp_setpoint",
        {"min": 20, "max": 26, "step": 0.5},
    )
    assert ent.name == "Node temp_setpoint"
    assert ent.native_value == 21.5
    assert ent.native_min_value == 18.0
    assert ent.native_max_value == 26
    assert ent.native_step == 0.5
    assert (DOMAIN, "e1_n1") in ent.device_info["identifiers"]


def test_switch_name(DummyCoordinator):
    ent = RainmakerParamSwitch(DummyCoordinator({}), "e1", "n1", "Node", "boost")
    assert ent.name == "Node boost"


@pytest.mark.parametrize("setup", [number_setup, binary_sensor_setup])
async def test_platform_setup_without_entry_data(setup):
    added: list = []
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="e1")
    await setup(SimpleNamespace(data={}), entry, lambda e, _u: added.extend(e))
    assert added == []


@pytest.mark.parametrize(("use_climate", "expected_count"), [(True, 0), (False, 1)])
async def test_binary_sensor_skips_params_covered_by_climate(
    DummyCoordinator, use_climate, expected_count
):
    # A read-only radiant_enabled is a binary sensor unless the climate
    # entity covers it.
    data = {
        "n1": {
            "temp": {"value": 20},
            "radiant_enabled": {
                "value": True,
                "data_type": "bool",
                "properties": ["read"],
            },
        }
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={CONF_USE_CLIMATE: use_climate},
        entry_id="e1",
    )
    hass = SimpleNamespace(
        data={DOMAIN: {"e1": {"coordinator": DummyCoordinator(data)}}}
    )
    added: list = []
    await binary_sensor_setup(hass, entry, lambda e, _u: added.extend(e))
    assert len(added) == expected_count
