"""Tests for the climate-entity vs individual-entities option."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from custom_components.zehnder_multicontroller import _async_remove_unused_entities
from custom_components.zehnder_multicontroller.climate import (
    async_setup_entry as climate_setup,
)
from custom_components.zehnder_multicontroller.const import CONF_USE_CLIMATE
from custom_components.zehnder_multicontroller.const import DOMAIN
from custom_components.zehnder_multicontroller.helpers import handled_by_climate
from custom_components.zehnder_multicontroller.number import (
    async_setup_entry as number_setup,
)
from custom_components.zehnder_multicontroller.sensor import (
    async_setup_entry as sensor_setup,
)
from custom_components.zehnder_multicontroller.switch import (
    async_setup_entry as switch_setup,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

NODE = {
    "Name": {"value": "Living"},
    "temp": {"value": 21, "properties": ["read"], "data_type": "float"},
    "humidity": {"value": 40, "properties": ["read"], "data_type": "float"},
    "temp_setpoint": {
        "value": 22,
        "properties": ["read", "write"],
        "data_type": "float",
        "bounds": {"min": 18, "max": 28, "step": 0.5},
    },
    "season": {"value": 1, "properties": ["read", "write"], "data_type": "int"},
    "fan_speed": {
        "value": 1,
        "properties": ["read", "write"],
        "data_type": "int",
        "bounds": {"min": 0, "max": 3},
    },
    "radiant_enabled": {
        "value": True,
        "properties": ["read", "write"],
        "data_type": "bool",
    },
    "boost": {"value": False, "properties": ["read", "write"], "data_type": "bool"},
}


def _entry(use_climate: bool | None):
    options = {} if use_climate is None else {CONF_USE_CLIMATE: use_climate}
    return MockConfigEntry(domain=DOMAIN, data={}, options=options, entry_id="e1")


async def _setup_all(DummyCoordinator, entry):
    coord = DummyCoordinator({"n1": NODE})
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: {"coordinator": coord}}})
    added: dict[str, list] = {}
    for name, setup in (
        ("climate", climate_setup),
        ("sensor", sensor_setup),
        ("number", number_setup),
        ("switch", switch_setup),
    ):
        items: list = []
        await setup(hass, entry, lambda ents, _u, items=items: items.extend(ents))
        added[name] = items
    return added


def _params(entities):
    return sorted(e._param for e in entities if not _is_stats(e))


def _stats_params(entities):
    return sorted(e._param for e in entities if _is_stats(e))


def _is_stats(entity):
    return entity.unique_id.endswith("_stats")


# Statistics mirrors don't depend on the climate option
EXPECTED_STATS = ["boost", "fan_speed", "radiant_enabled", "temp_setpoint"]


def test_handled_by_climate_helper():
    entry = _entry(None)
    assert handled_by_climate(entry, NODE, "temp_setpoint")
    assert handled_by_climate(entry, NODE, "Fan_Speed")
    # The read-only temperature sensor is kept in both modes
    assert not handled_by_climate(entry, NODE, "temp")
    assert not handled_by_climate(entry, NODE, "humidity")
    # Node without temp -> no climate entity -> nothing is covered
    assert not handled_by_climate(entry, {"fan_speed": {}}, "fan_speed")
    assert not handled_by_climate(_entry(False), NODE, "temp_setpoint")
    # Entries without an options attribute default to climate mode
    assert handled_by_climate(SimpleNamespace(entry_id="x"), NODE, "season")


@pytest.mark.asyncio
async def test_climate_mode_hides_duplicates(DummyCoordinator):
    added = await _setup_all(DummyCoordinator, _entry(None))
    assert len(added["climate"]) == 1
    assert _params(added["sensor"]) == ["humidity", "temp"]
    assert _stats_params(added["sensor"]) == EXPECTED_STATS
    assert _params(added["number"]) == []
    assert _params(added["switch"]) == ["boost"]


@pytest.mark.asyncio
async def test_individual_mode_creates_all_and_no_climate(DummyCoordinator):
    added = await _setup_all(DummyCoordinator, _entry(False))
    assert added["climate"] == []
    assert _params(added["sensor"]) == ["humidity", "temp"]
    assert _stats_params(added["sensor"]) == EXPECTED_STATS
    assert _params(added["number"]) == ["fan_speed", "season", "temp_setpoint"]
    assert _params(added["switch"]) == ["boost", "radiant_enabled"]


class _Registry:
    def __init__(self, entries):
        self.entities = {e.entity_id: e for e in entries}
        self.removed: list[str] = []

    def async_remove(self, entity_id):
        self.removed.append(entity_id)
        self.entities.pop(entity_id)


def _reg_entries():
    def item(entity_id, unique_id, config_entry_id="e1"):
        return SimpleNamespace(
            entity_id=entity_id, unique_id=unique_id, config_entry_id=config_entry_id
        )

    return [
        item("climate.living", "e1_n1_climate"),
        item("sensor.living_temp", "e1_n1_temp"),
        item("sensor.living_humidity", "e1_n1_humidity"),
        item("number.living_temp_setpoint", "e1_n1_temp_setpoint"),
        item("switch.living_radiant_enabled", "e1_n1_radiant_enabled"),
        item("switch.living_boost", "e1_n1_boost"),
        # Same unique_id pattern but another config entry -> untouched
        item("sensor.other_temp", "e1_n1_temp", config_entry_id="other"),
    ]


@pytest.mark.parametrize(
    ("use_climate", "expected_removed"),
    [
        (
            True,
            [
                "number.living_temp_setpoint",
                "switch.living_radiant_enabled",
            ],
        ),
        (False, ["climate.living"]),
    ],
)
def test_remove_unused_entities(monkeypatch, use_climate, expected_removed):
    registry = _Registry(_reg_entries())
    monkeypatch.setattr(
        "custom_components.zehnder_multicontroller.er.async_get",
        lambda hass: registry,
    )
    _async_remove_unused_entities(None, _entry(use_climate), {"n1": NODE})
    assert sorted(registry.removed) == sorted(expected_removed)


def test_remove_unused_entities_no_data(monkeypatch):
    def fail(hass):
        raise AssertionError("registry should not be accessed")

    monkeypatch.setattr("custom_components.zehnder_multicontroller.er.async_get", fail)
    _async_remove_unused_entities(None, _entry(True), None)


@pytest.mark.asyncio
async def test_options_flow(monkeypatch):
    from custom_components.zehnder_multicontroller.config_flow import (
        ZehnderMulticontrollerFlowHandler,
        ZehnderMulticontrollerOptionsFlow,
    )

    entry = _entry(None)
    flow = ZehnderMulticontrollerFlowHandler.async_get_options_flow(entry)
    assert isinstance(flow, ZehnderMulticontrollerOptionsFlow)
    monkeypatch.setattr(
        ZehnderMulticontrollerOptionsFlow,
        "config_entry",
        property(lambda self: entry),
    )

    result = await flow.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"
    schema_keys = {str(k): k for k in result["data_schema"].schema}
    # Defaults to the climate entity
    assert schema_keys[CONF_USE_CLIMATE].default() is True

    result = await flow.async_step_init({CONF_USE_CLIMATE: False})
    assert result["type"] == "create_entry"
    assert result["data"] == {CONF_USE_CLIMATE: False}


@pytest.mark.asyncio
async def test_fan_mode_respects_lower_bound(DummyCoordinator):
    from unittest.mock import AsyncMock

    from custom_components.zehnder_multicontroller.climate import ZehnderClimate
    from custom_components.zehnder_multicontroller.climate import DEFAULT_FAN_NAMES

    data = {
        "n1": {
            "temp": {"value": 20},
            "fan_speed": {
                "value": 1,
                "properties": ["read", "write"],
                "bounds": {"min": 1, "max": 4},
            },
        }
    }
    coord = DummyCoordinator(data)
    coord.api = type("A", (), {"async_set_param": AsyncMock()})()
    ent = ZehnderClimate(coord, "e1", "n1", "Node")

    assert ent.fan_modes == DEFAULT_FAN_NAMES
    # value == min -> first mode
    assert ent.fan_mode == DEFAULT_FAN_NAMES[0]
    data["n1"]["fan_speed"]["value"] = 4
    assert ent.fan_mode == DEFAULT_FAN_NAMES[3]

    await ent.async_set_fan_mode(DEFAULT_FAN_NAMES[3])
    coord.api.async_set_param.assert_awaited_with("n1", "fan_speed", 4)
    await ent.async_set_fan_mode(DEFAULT_FAN_NAMES[0])
    coord.api.async_set_param.assert_awaited_with("n1", "fan_speed", 1)


def test_setpoint_bounds_exposed(DummyCoordinator):
    from custom_components.zehnder_multicontroller.climate import ZehnderClimate

    ent = ZehnderClimate(DummyCoordinator({"n1": NODE}), "e1", "n1", "Node")
    assert ent.min_temp == 18.0
    assert ent.max_temp == 28.0
    assert ent.target_temperature_step == 0.5


@pytest.mark.asyncio
async def test_statistics_sensors(DummyCoordinator):
    from homeassistant.components.sensor import SensorDeviceClass
    from homeassistant.components.sensor import SensorStateClass
    from homeassistant.const import EntityCategory

    node = dict(NODE)
    node["mode_name"] = {
        "value": "eco",
        "properties": ["read"],
        "data_type": "string",
    }
    node["filter_alarm"] = {
        "value": None,
        "properties": ["read"],
        "data_type": "bool",
    }
    coord = DummyCoordinator({"n1": node})
    entry = _entry(None)
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: {"coordinator": coord}}})
    added: list = []
    await sensor_setup(hass, entry, lambda ents, _u: added.extend(ents))
    by_uid = {e.unique_id: e for e in added}

    # Read-only numeric sensors get a state_class -> long-term statistics
    temp = by_uid["e1_n1_temp"]
    assert temp._attr_state_class == SensorStateClass.MEASUREMENT
    assert temp._attr_device_class == SensorDeviceClass.TEMPERATURE
    humidity = by_uid["e1_n1_humidity"]
    assert humidity._attr_state_class == SensorStateClass.MEASUREMENT
    assert humidity._attr_native_unit_of_measurement == "%"
    # Non-numeric read-only sensor: no state_class (would make HA error)
    assert getattr(by_uid["e1_n1_mode_name"], "_attr_state_class", None) is None
    # No statistics for season or read-only numeric params (already covered)
    assert "e1_n1_season_stats" not in by_uid
    assert "e1_n1_temp_stats" not in by_uid
    assert "e1_n1_humidity_stats" not in by_uid

    setpoint = by_uid["e1_n1_temp_setpoint_stats"]
    assert setpoint.state_class == SensorStateClass.MEASUREMENT
    assert setpoint.entity_category == EntityCategory.DIAGNOSTIC
    assert setpoint._attr_native_unit_of_measurement == "°C"
    assert setpoint.native_value == 22
    assert setpoint.name == "Living temp_setpoint statistics"

    fan = by_uid["e1_n1_fan_speed_stats"]
    assert fan.native_value == 1

    radiant = by_uid["e1_n1_radiant_enabled_stats"]
    assert radiant._attr_native_unit_of_measurement == "%"
    assert radiant.native_value == 100
    node["radiant_enabled"] = {**node["radiant_enabled"], "value": False}
    assert radiant.native_value == 0

    # Read-only bools are mirrored too; unknown value -> None
    assert by_uid["e1_n1_filter_alarm_stats"].native_value is None
