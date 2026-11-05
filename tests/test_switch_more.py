import pytest


@pytest.mark.asyncio
async def test_switch_setup_and_operations(DummyCoordinator, DummyAPI):
    data = {
        "node": {
            "Name": {"value": "SwitchNode"},
            "power": {"value": False, "data_type": "bool", "properties": ["write"]},
            "other": {"value": None, "data_type": "bool", "properties": ["write"]},
        }
    }
    coord = DummyCoordinator(data)
    api = DummyAPI()
    coord.api = api

    from custom_components.zehnder_multicontroller.switch import async_setup_entry

    # Use minimal fake hass object
    class FakeHass:
        pass

    fake = FakeHass()
    fake.data = {}
    fake.data.setdefault("zehnder_multicontroller", {})["eid"] = {"coordinator": coord}

    added = []

    def add(entities, update_before_add):
        added.extend(entities)

    await async_setup_entry(fake, type("E", (), {"entry_id": "eid"})(), add)
    # Should create a switch for 'power' but skip 'other' with None value for is_on calculations
    sw = next(e for e in added if e.unique_id.endswith("_power"))
    assert sw.is_on is False

    # Ensure entity has a hass reference so async_turn_on can access hass.data
    sw.hass = fake

    # Turn on -> should call api and request refresh
    await sw.async_turn_on()
    api.async_set_param.assert_called_with("node", "power", True)
    coord.async_request_refresh.assert_awaited()

    # Turn off -> should call api and request refresh
    api.async_set_param.reset_mock()
    await sw.async_turn_off()
    api.async_set_param.assert_called_with("node", "power", False)

    # There should also be an entity for 'other' whose value is None -> is_on is None
    other = next(e for e in added if e.unique_id.endswith("_other"))
    assert other.is_on is None

    # device_info is available and contains identifiers
    di = sw.device_info
    assert ("zehnder_multicontroller", "eid_node") in di["identifiers"]
