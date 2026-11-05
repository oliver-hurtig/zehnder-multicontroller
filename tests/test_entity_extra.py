"""Tests for ZehnderMulticontrollerEntity helpers."""

from __future__ import annotations

from custom_components.zehnder_multicontroller.entity import (
    ZehnderMulticontrollerEntity,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry


def test_entity_properties(DummyCoordinator):
    data = {"id": 123}
    coord = DummyCoordinator(data)
    entry = MockConfigEntry(domain="z", data={}, entry_id="e1")

    ent = ZehnderMulticontrollerEntity(coord, entry)
    assert ent.unique_id == entry.entry_id

    dev = ent.device_info
    assert ("zehnder_multicontroller", entry.entry_id) in dev["identifiers"] or (
        "zehnder_multicontroller",
        entry.entry_id,
    ) in dev.identifiers

    attrs = ent.device_state_attributes
    assert attrs["integration"] == "zehnder_multicontroller"
    assert "attribution" in attrs
