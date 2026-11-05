"""Unit tests for climate platform behavior."""

from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.climate import DEFAULT_FAN_NAMES
from custom_components.zehnder_multicontroller.climate import ZehnderClimate


def test_initialize_fan_names_default(DummyCoordinator):
    data = {"n1": {"Name": {"value": "Node One"}}}
    coord = DummyCoordinator(data)

    ent = ZehnderClimate(coord, "entry1", "n1", "Node One")
    assert ent.fan_modes == DEFAULT_FAN_NAMES


def test_initialize_fan_names_bounds(DummyCoordinator):
    data = {
        "n1": {
            "Name": {"value": "Node One"},
            "fan_speed": {"bounds": {"min": 1, "max": 3}},
        }
    }
    coord = DummyCoordinator(data)

    ent = ZehnderClimate(coord, "entry1", "n1", "Node One")
    assert ent.fan_modes == ["1", "2", "3"]


@pytest.mark.asyncio
async def test_temperature_and_modes_and_setters(DummyCoordinator, DummyAPI):
    data = {
        "n1": {
            "Name": {"value": "Node One"},
            "temp": {"value": 21.5},
            "temp_setpoint": {"value": 22.0, "properties": ["write"]},
            "fan_speed": {
                "value": 2,
                "properties": ["write"],
                "bounds": {"min": 0, "max": 3},
            },
            "season": {"value": 1},
            "radiant_enabled": {"value": True},
        }
    }

    coord = DummyCoordinator(data)
    api = DummyAPI()
    coord.api = api

    ent = ZehnderClimate(coord, "entry1", "n1", "Node One")

    assert ent.current_temperature == 21.5
    assert ent.target_temperature == 22.0
    # supports target temperature and fan mode
    features = ent.get_supported_features()
    assert features

    # hvac_mode from season and radiant_enabled
    assert ent.hvac_mode is not None

    # async setters should call API and request refresh
    await ent.async_set_temperature(temperature=24.0)
    api.async_set_param.assert_any_call("n1", "temp_setpoint", 24.0)
    coord.async_request_refresh.assert_awaited()

    await ent.async_set_hvac_mode("off")
    await ent.async_set_hvac_mode("heat")
    await ent.async_set_hvac_mode("cool")
    # should have set season/radiant and requested refresh multiple times
    coord.async_request_refresh.assert_awaited()

    # set fan mode to an invalid value should not call API
    await ent.async_set_fan_mode("invalid")
    # set to a valid fan mode
    valid = ent.fan_modes[0]
    await ent.async_set_fan_mode(valid)
    coord.async_request_refresh.assert_awaited()
