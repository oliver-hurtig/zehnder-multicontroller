import pytest
from homeassistant.components.climate import HVACMode


@pytest.mark.asyncio
async def test_initialize_fan_names_and_modes(DummyCoordinator):
    # No fan_speed -> default names
    data = {"node1": {"temp": {"value": 20}}}
    coord = DummyCoordinator(data)
    from custom_components.zehnder_multicontroller.climate import (
        ZehnderClimate,
        DEFAULT_FAN_NAMES,
    )

    c = ZehnderClimate(coord, "entry1", "node1", "Node 1")
    assert c.fan_modes == DEFAULT_FAN_NAMES

    # Custom bounds that produce numeric names
    data = {
        "node2": {
            "temp": {"value": 21},
            "fan_speed": {"bounds": {"min": 0, "max": 2}, "value": 1},
        }
    }
    coord2 = DummyCoordinator(data)
    c2 = ZehnderClimate(coord2, "entry1", "node2", "Node 2")
    assert c2.fan_modes == ["0", "1", "2"]
    # fan_mode picks correct name
    assert c2.fan_mode == "1"


@pytest.mark.asyncio
async def test_hvac_mode_and_temperatures(DummyCoordinator):
    data = {
        "n": {
            "temp": {"value": 19},
            "temp_setpoint": {"value": 22},
            "radiant_enabled": {"value": False},
        }
    }
    coord = DummyCoordinator(data)
    from custom_components.zehnder_multicontroller.climate import ZehnderClimate

    c = ZehnderClimate(coord, "eid", "n", "Node")
    assert c.current_temperature == 19
    assert c.target_temperature == 22
    assert c.hvac_mode == HVACMode.OFF

    # Radiant enabled and season->HEAT/COOL/None
    data2 = {
        "n2": {
            "temp": {"value": 18},
            "radiant_enabled": {"value": True},
            "season": {"value": 1},
        }
    }
    c2 = ZehnderClimate(DummyCoordinator(data2), "eid", "n2", "N2")
    assert c2.hvac_mode == HVACMode.HEAT

    data3 = {
        "n3": {
            "temp": {"value": 18},
            "radiant_enabled": {"value": True},
            "season": {"value": 2},
        }
    }
    c3 = ZehnderClimate(DummyCoordinator(data3), "eid", "n3", "N3")
    assert c3.hvac_mode == HVACMode.COOL

    data4 = {
        "n4": {
            "temp": {"value": 18},
            "radiant_enabled": {"value": True},
            "season": {"value": 99},
        }
    }
    c4 = ZehnderClimate(DummyCoordinator(data4), "eid", "n4", "N4")
    assert c4.hvac_mode is None


@pytest.mark.asyncio
async def test_supported_features_and_setters(DummyCoordinator, DummyAPI):
    # Setup coordinator and API
    data = {
        "n": {
            "temp": {"value": 18},
            "temp_setpoint": {"value": 20, "properties": ["write"]},
            "fan_speed": {
                "value": 0,
                "properties": ["write"],
                "bounds": {"min": 0, "max": 3},
            },
            "radiant_enabled": {"value": True},
        }
    }
    coord = DummyCoordinator(data)
    api = DummyAPI(nodes=None)
    coord.api = api

    from custom_components.zehnder_multicontroller.climate import ZehnderClimate

    c = ZehnderClimate(coord, "eid", "n", "Node")
    features = c.get_supported_features()
    # Should include both temperature and fan
    assert features

    # Test async_set_temperature triggers api and refresh
    await c.async_set_temperature(temperature=21)
    api.async_set_param.assert_called_with("n", "temp_setpoint", 21)
    coord.async_request_refresh.assert_awaited()

    # Test async_set_hvac_mode transitions
    api.async_set_param.reset_mock()
    await c.async_set_hvac_mode(HVACMode.OFF.value)
    api.async_set_param.assert_called()
    api.async_set_param.reset_mock()
    await c.async_set_hvac_mode(HVACMode.HEAT.value)
    # Should set season then radiant
    assert any(call.args[1] == "season" for call in api.async_set_param.mock_calls)
    api.async_set_param.reset_mock()
    await c.async_set_hvac_mode(HVACMode.COOL.value)
    assert any(call.args[1] == "season" for call in api.async_set_param.mock_calls)

    # Test async_set_fan_mode unknown does nothing
    api.async_set_param.reset_mock()
    await c.async_set_fan_mode("NotARealMode")
    api.async_set_param.assert_not_called()


def test_handle_coordinator_update_exception(DummyCoordinator, monkeypatch):
    # Create a coordinator and climate then make get_supported_features raise
    data = {"n": {"temp": {"value": 20}}}
    coord = DummyCoordinator(data)
    from custom_components.zehnder_multicontroller.climate import ZehnderClimate

    c = ZehnderClimate(coord, "eid", "n", "Node")

    def bad_features():
        raise RuntimeError("boom")

    monkeypatch.setattr(c, "get_supported_features", bad_features)

    def _noop_write():
        return None

    monkeypatch.setattr(c, "async_write_ha_state", _noop_write)
    # Should not raise (async_write_ha_state is stubbed)
    c._handle_coordinator_update()


def test_fan_mode_out_of_range(DummyCoordinator):
    data = {
        "n": {
            "temp": {"value": 20},
            "fan_speed": {"value": 99, "bounds": {"min": 0, "max": 3}},
        }
    }
    c = __import__(
        "custom_components.zehnder_multicontroller.climate", fromlist=["ZehnderClimate"]
    ).ZehnderClimate(DummyCoordinator(data), "eid", "n", "Node")
    assert c.fan_mode is None


def test_unique_name_deviceinfo_and_setters_none(DummyCoordinator, DummyAPI):
    data = {
        "n": {
            "temp": {"value": 20},
            "temp_setpoint": {"value": 21, "properties": ["write"]},
        }
    }
    coord = DummyCoordinator(data)
    api = DummyAPI()
    coord.api = api
    from custom_components.zehnder_multicontroller.climate import ZehnderClimate

    c = ZehnderClimate(coord, "eid", "n", "NodeName")
    assert c.unique_id == "eid_n_climate"
    assert c.name == "NodeName"
    di = c.device_info
    assert ("zehnder_multicontroller", "eid_n") in di["identifiers"]

    # Calling async_set_temperature with no temperature should be a no-op
    import asyncio

    asyncio.get_event_loop().run_until_complete(c.async_set_temperature())
    api.async_set_param.assert_not_called()


def test_async_setup_entry_skips_node_without_temp(monkeypatch, DummyCoordinator):
    data = {"a": {"Name": {"value": "A"}}, "b": {"temp": {"value": 10}}}
    coord = DummyCoordinator(data)

    class FakeHass:
        pass

    fake = FakeHass()
    fake.data = {"zehnder_multicontroller": {"eid": {"coordinator": coord}}}

    added = []

    def add(entities, update_before_add):
        added.extend(entities)

    import asyncio

    awaitable = __import__(
        "custom_components.zehnder_multicontroller.climate",
        fromlist=["async_setup_entry"],
    ).async_setup_entry
    asyncio.get_event_loop().run_until_complete(
        awaitable(fake, type("E", (), {"entry_id": "eid"})(), add)
    )
    # Only node 'b' has temp -> one entity created
    assert len(added) == 1


def test_async_set_fan_mode_valid(DummyCoordinator, DummyAPI):
    data = {
        "n": {
            "temp": {"value": 20},
            "fan_speed": {
                "value": 2,
                "properties": ["write"],
                "bounds": {"min": 0, "max": 3},
            },
        }
    }
    coord = DummyCoordinator(data)
    api = DummyAPI()
    coord.api = api
    from custom_components.zehnder_multicontroller.climate import ZehnderClimate

    c = ZehnderClimate(coord, "eid", "n", "N")
    # pick a valid fan mode name
    valid = c.fan_modes[2]
    import asyncio

    asyncio.get_event_loop().run_until_complete(c.async_set_fan_mode(valid))
    api.async_set_param.assert_called()


def test_fan_mode_none_when_value_missing(DummyCoordinator):
    data = {
        "n": {
            "temp": {"value": 20},
            "fan_speed": {"value": None, "bounds": {"min": 0, "max": 3}},
        }
    }
    c = __import__(
        "custom_components.zehnder_multicontroller.climate", fromlist=["ZehnderClimate"]
    ).ZehnderClimate(DummyCoordinator(data), "eid", "n", "Node")
    assert c.fan_mode is None


def test_get_supported_features_variants(DummyCoordinator):
    mod = __import__(
        "custom_components.zehnder_multicontroller.climate", fromlist=["ZehnderClimate"]
    )
    ZehnderClimate = mod.ZehnderClimate

    # Only temp_setpoint with write
    data1 = {"n1": {"temp": {"value": 1}, "temp_setpoint": {"properties": ["write"]}}}
    c1 = ZehnderClimate(DummyCoordinator(data1), "eid", "n1", "N1")
    f1 = c1.get_supported_features()
    assert f1 & mod.ClimateEntityFeature.TARGET_TEMPERATURE

    # Only fan write
    data2 = {"n2": {"temp": {"value": 1}, "fan_speed": {"properties": ["write"]}}}
    c2 = ZehnderClimate(DummyCoordinator(data2), "eid", "n2", "N2")
    f2 = c2.get_supported_features()
    assert f2 & mod.ClimateEntityFeature.FAN_MODE

    # Neither
    data3 = {"n3": {"temp": {"value": 1}}}
    c3 = ZehnderClimate(DummyCoordinator(data3), "eid", "n3", "N3")
    f3 = c3.get_supported_features()
    assert f3 == mod.ClimateEntityFeature(0)


def test_current_and_target_none_and_hvac_modes(DummyCoordinator):
    # Empty data -> no temps
    c = __import__(
        "custom_components.zehnder_multicontroller.climate", fromlist=["ZehnderClimate"]
    ).ZehnderClimate(DummyCoordinator({}), "eid", "n", "N")
    assert c.current_temperature is None
    assert c.target_temperature is None
    assert isinstance(c.hvac_modes, list)


def test_async_setup_entry_no_entry_data_climate():
    mod = __import__(
        "custom_components.zehnder_multicontroller.climate",
        fromlist=["async_setup_entry"],
    )
    awaitable = mod.async_setup_entry

    class FakeHass:
        pass

    fake = FakeHass()
    fake.data = {}

    def add(entities, update_before_add):
        raise AssertionError("Should not be called")

    import asyncio

    asyncio.get_event_loop().run_until_complete(
        awaitable(fake, type("E", (), {"entry_id": "eid"})(), add)
    )


def test_async_setup_entry_creates_on_every_setup(monkeypatch, DummyCoordinator):
    # Prepare coordinator with one node that has temp
    data = {"nodea": {"temp": {"value": 21}, "Name": {"value": "NA"}}}
    coord = DummyCoordinator(data)

    # Fake hass with data
    class FakeHass:
        pass

    fake = FakeHass()
    fake.data = {"zehnder_multicontroller": {"eid": {"coordinator": coord}}}

    added = []

    def add(entities, update_before_add):
        added.extend(entities)

    awaitable = __import__(
        "custom_components.zehnder_multicontroller.climate",
        fromlist=["async_setup_entry"],
    ).async_setup_entry
    # Call sync (it's async) via running it
    import asyncio

    asyncio.get_event_loop().run_until_complete(
        awaitable(fake, type("E", (), {"entry_id": "eid"})(), add)
    )
    assert any(e for e in added if isinstance(e.__class__.__name__, str))

    # A second setup (restart/reload) must create the entity again so the
    # existing registry entry gets reattached instead of going unavailable.
    added.clear()
    asyncio.get_event_loop().run_until_complete(
        awaitable(fake, type("E", (), {"entry_id": "eid"})(), add)
    )
    assert len(added) == 1
