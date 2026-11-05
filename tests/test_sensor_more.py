import pytest


@pytest.mark.asyncio
async def test_sensor_setup_and_attributes(DummyCoordinator):
    # Node contains multiple params, some skipped (Name/config/schedule)
    data = {
        "node": {
            "Name": {"value": "My Node"},
            "temp": {"value": 23, "data_type": "float"},
            "humidity": {"value": 55, "data_type": "int"},
            "config": {"value": {}},
            "schedule_week": {"value": {}},
            "writable_bool": {
                "value": True,
                "data_type": "bool",
                "properties": ["write"],
            },
        }
    }
    coord = DummyCoordinator(data)

    from custom_components.zehnder_multicontroller.sensor import async_setup_entry

    added = []

    def add(entities, update_before_add):
        added.extend(entities)

    # Use a minimal fake hass object with a data dict
    class FakeHass:
        pass

    fake = FakeHass()
    fake.data = {}

    # Individual-entity mode: the climate entity is disabled, so 'temp' is
    # exposed as its own sensor.
    entry = type(
        "E", (), {"entry_id": "eid", "options": {"use_climate_entity": False}}
    )()

    # No entry data -> should early return without error
    await async_setup_entry(fake, entry, add)

    # Attach coordinator into hass.data and run setup
    fake.data.setdefault("zehnder_multicontroller", {})["eid"] = {"coordinator": coord}
    added.clear()
    await async_setup_entry(fake, entry, add)

    # We should have sensors for temp and humidity, but not Name/config/schedule or writable bool
    names = [e.name for e in added]
    assert any("temp" in n.lower() for n in names)
    assert any("humidity" in n.lower() for n in names)

    temp_entity = next(e for e in added if "temp" in e.unique_id)
    assert temp_entity.native_value == 23
    # device class/unit for temp should be set
    assert getattr(temp_entity, "_attr_device_class") is not None
    assert getattr(temp_entity, "_attr_native_unit_of_measurement") == "°C"


@pytest.mark.asyncio
async def test_sensor_excludes_bool_and_none_value(DummyCoordinator):
    data = {
        "node": {
            "Name": {"value": "My Node"},
            "boolparam": {"data_type": "Bool"},
            "novalue": {"data_type": "float"},
        }
    }
    coord = DummyCoordinator(data)

    from custom_components.zehnder_multicontroller.sensor import async_setup_entry

    added = []

    def add(entities, update_before_add):
        added.extend(entities)

    class FakeHass:
        pass

    fake = FakeHass()
    fake.data = {"zehnder_multicontroller": {"eid": {"coordinator": coord}}}

    await async_setup_entry(fake, type("E", (), {"entry_id": "eid"})(), add)

    # boolparam should be excluded because dtype bool, novalue should create entity with native_value None
    assert any("novalue" in e.unique_id for e in added)
    nov = next(e for e in added if "novalue" in e.unique_id)
    assert nov.native_value is None


@pytest.mark.asyncio
async def test_sensor_device_info_and_unique_id(DummyCoordinator):
    data = {
        "node": {"Name": {"value": "N"}, "param1": {"value": 1, "data_type": "float"}}
    }
    coord = DummyCoordinator(data)

    from custom_components.zehnder_multicontroller.sensor import async_setup_entry

    added = []

    def add(entities, update_before_add):
        added.extend(entities)

    class FakeHass:
        pass

    fake = FakeHass()
    fake.data = {"zehnder_multicontroller": {"eid": {"coordinator": coord}}}

    await async_setup_entry(fake, type("E", (), {"entry_id": "eid"})(), add)
    s = next(e for e in added if e.unique_id.endswith("_param1"))
    di = s.device_info
    assert ("zehnder_multicontroller", "node") in di["identifiers"]
    assert s.unique_id.endswith("_param1")


def test_sensor_direct_properties(DummyCoordinator):
    data = {"node": {"Name": {"value": "N"}, "p": {"value": 5, "data_type": "float"}}}
    coord = DummyCoordinator(data)
    from custom_components.zehnder_multicontroller.sensor import RainmakerParamSensor

    s = RainmakerParamSensor(coord, "eid", "node", "N", "p")
    assert s.name == "N p"
    assert s.unique_id == "eid_node_p"
    assert s.native_value == 5
    di = s.device_info
    assert ("zehnder_multicontroller", "node") in di["identifiers"]


@pytest.mark.asyncio
async def test_async_setup_entry_no_data_does_nothing():
    from custom_components.zehnder_multicontroller.sensor import async_setup_entry

    class FakeHass:
        pass

    fake = FakeHass()
    fake.data = {}

    def add(entities, update_before_add):
        raise AssertionError("Should not be called")

    await async_setup_entry(fake, type("E", (), {"entry_id": "eid"})(), add)
