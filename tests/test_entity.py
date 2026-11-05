"""Tests for ZehnderMulticontrollerEntity helpers."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.zehnder_multicontroller.entity import (
    ZehnderMulticontrollerEntity,
)


def test_entity_device_info_and_unique_id():
    coordinator = SimpleNamespace(data={})
    entry = SimpleNamespace(entry_id="entry123")

    ent = ZehnderMulticontrollerEntity(coordinator, entry)

    assert ent.unique_id == "entry123"
    dev_info = ent.device_info
    assert ("zehnder_multicontroller", "entry123") in dev_info["identifiers"]
    assert dev_info["name"]


def test_device_state_attributes():
    coordinator = SimpleNamespace(data={"id": 5})
    entry = SimpleNamespace(entry_id="e2")
    ent = ZehnderMulticontrollerEntity(coordinator, entry)

    attrs = ent.device_state_attributes
    assert "id" in attrs
    assert attrs["integration"] == "zehnder_multicontroller"
