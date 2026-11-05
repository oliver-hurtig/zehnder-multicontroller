"""Additional tests for climate platform to increase coverage."""
from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.climate import async_setup_entry
from custom_components.zehnder_multicontroller.climate import DEFAULT_FAN_NAMES
from custom_components.zehnder_multicontroller.climate import ZehnderClimate
from custom_components.zehnder_multicontroller.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry


def test_hvac_mode_variants(DummyCoordinator):
    # radiant disabled -> OFF
    data = {
        "n1": {
            "Name": {"value": "Node"},
            "temp": {"value": 20},
            "radiant_enabled": {"value": False},
        }
    }
    coord = DummyCoordinator(data)
    ent = ZehnderClimate(coord, "e1", "n1", "Node")
    assert ent.hvac_mode is not None
    assert ent.hvac_mode.value == "off"

    # season heat
    data = {
        "n1": {
            "Name": {"value": "Node"},
            "temp": {"value": 20},
            "radiant_enabled": {"value": True},
            "season": {"value": 1},
        }
    }
    coord = DummyCoordinator(data)
    ent = ZehnderClimate(coord, "e1", "n1", "Node")
    assert ent.hvac_mode.value == "heat"

    # season cool
    data = {
        "n1": {
            "Name": {"value": "Node"},
            "temp": {"value": 20},
            "radiant_enabled": {"value": True},
            "season": {"value": 2},
        }
    }
    coord = DummyCoordinator(data)
    ent = ZehnderClimate(coord, "e1", "n1", "Node")
    assert ent.hvac_mode.value == "cool"


def test_fan_mode_edge_cases(DummyCoordinator):
    # no fan_speed -> fan_mode None
    data = {"n1": {"Name": {"value": "Node"}, "temp": {"value": 20}}}
    coord = DummyCoordinator(data)
    ent = ZehnderClimate(coord, "e1", "n1", "Node")
    assert ent.fan_mode is None

    # fan_speed value None -> None
    data = {
        "n1": {
            "Name": {"value": "Node"},
            "temp": {"value": 20},
            "fan_speed": {"value": None, "bounds": {"min": 0, "max": 3}},
        }
    }
    coord = DummyCoordinator(data)
    ent = ZehnderClimate(coord, "e1", "n1", "Node")
    assert ent.fan_mode is None

    # out of range -> None
    data = {
        "n1": {
            "Name": {"value": "Node"},
            "temp": {"value": 20},
            "fan_speed": {"value": 99, "bounds": {"min": 0, "max": 3}},
        }
    }
    coord = DummyCoordinator(data)
    ent = ZehnderClimate(coord, "e1", "n1", "Node")
    assert ent.fan_mode is None

    # valid value -> name
    data = {
        "n1": {
            "Name": {"value": "Node"},
            "temp": {"value": 20},
            "fan_speed": {"value": 2, "bounds": {"min": 0, "max": 3}},
        }
    }
    coord = DummyCoordinator(data)
    ent = ZehnderClimate(coord, "e1", "n1", "Node")
    assert ent.fan_mode == DEFAULT_FAN_NAMES[2]


def test_initialize_fan_names_count_matches_default(DummyCoordinator):
    # bounds that produce num_levels == len(DEFAULT_FAN_NAMES)
    data = {
        "n1": {"Name": {"value": "Node"}, "fan_speed": {"bounds": {"min": 0, "max": 3}}}
    }
    coord = DummyCoordinator(data)
    ent = ZehnderClimate(coord, "e1", "n1", "Node")
    assert ent.fan_modes == DEFAULT_FAN_NAMES


def test_get_supported_features_none(DummyCoordinator):
    data = {"n1": {"Name": {"value": "Node"}, "temp": {"value": 20}}}
    coord = DummyCoordinator(data)
    ent = ZehnderClimate(coord, "e1", "n1", "Node")
    features = ent.get_supported_features()
    assert features == 0


def test_handle_coordinator_update_exception(DummyCoordinator, monkeypatch):
    data = {"n1": {"Name": {"value": "Node"}, "temp": {"value": 20}}}
    coord = DummyCoordinator(data)
    ent = ZehnderClimate(coord, "e1", "n1", "Node")

    def bad():
        raise RuntimeError("fail")

    ent.get_supported_features = bad
    # Prevent the base class implementation from writing state during test
    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    monkeypatch.setattr(
        CoordinatorEntity, "_handle_coordinator_update", lambda self: None
    )

    # Should not raise when get_supported_features raises
    ent._handle_coordinator_update()


@pytest.mark.asyncio
async def test_async_setters_and_features(DummyCoordinator, DummyAPI):
    data = {
        "n1": {
            "Name": {"value": "Node"},
            "temp": {"value": 21.0},
            "temp_setpoint": {"value": 22.0, "properties": ["write"]},
            "fan_speed": {
                "value": 1,
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

    ent = ZehnderClimate(coord, "e1", "n1", "Node")

    # features should include temperature and fan
    features = ent.get_supported_features()
    assert features

    # async_set_temperature should call API and request refresh
    await ent.async_set_temperature(temperature=24.0)
    api.async_set_param.assert_any_call("n1", "temp_setpoint", 24.0)
    coord.async_request_refresh.assert_awaited()

    # async_set_hvac_mode transitions
    await ent.async_set_hvac_mode("off")
    await ent.async_set_hvac_mode("heat")
    await ent.async_set_hvac_mode("cool")
    coord.async_request_refresh.assert_awaited()

    # async_set_fan_mode invalid then valid
    await ent.async_set_fan_mode("invalid")
    await ent.async_set_fan_mode(ent.fan_modes[0])
    coord.async_request_refresh.assert_awaited()


@pytest.mark.asyncio
async def test_async_setup_entry_registry_behavior(DummyCoordinator, monkeypatch):
    data = {"n1": {"Name": {"value": "Node"}, "temp": {"value": 20}}}
    coord = DummyCoordinator(data)

    class DummyHass:
        def __init__(self):
            self.data = {}

    hass = DummyHass()
    entry = MockConfigEntry(domain=DOMAIN, data={}, entry_id="e1")
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coord}

    added = []

    def add(entities, update_before):
        added.extend(entities)

    # Entity must be created on every setup, even when its unique_id is
    # already in the entity registry (e.g. after a restart or reload).
    await async_setup_entry(hass, entry, add)
    assert len(added) == 1

    added.clear()
    await async_setup_entry(hass, entry, add)
    assert len(added) == 1
