"""Extra tests for config flow handler."""

from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.api import RainmakerAuthError
from custom_components.zehnder_multicontroller.api import RainmakerConnectionError
from custom_components.zehnder_multicontroller.config_flow import (
    ZehnderMulticontrollerFlowHandler,
)


@pytest.mark.asyncio
async def test_async_step_user_show_form():
    handler = ZehnderMulticontrollerFlowHandler()
    res = await handler.async_step_user(None)
    assert res["type"] == "form"


@pytest.mark.asyncio
async def test_async_step_user_auth_error(monkeypatch):
    handler = ZehnderMulticontrollerFlowHandler()

    async def _bad(hass, user_input):
        raise RainmakerAuthError()

    monkeypatch.setattr(
        "custom_components.zehnder_multicontroller.config_flow.validate_input", _bad
    )

    res = await handler.async_step_user({"host": "h", "username": "u", "password": "p"})
    assert res["type"] == "form"
    assert res["errors"]["base"] == "auth"


@pytest.mark.asyncio
async def test_async_step_user_cannot_connect(monkeypatch):
    handler = ZehnderMulticontrollerFlowHandler()

    async def _bad(hass, user_input):
        raise RainmakerConnectionError()

    monkeypatch.setattr(
        "custom_components.zehnder_multicontroller.config_flow.validate_input", _bad
    )

    res = await handler.async_step_user({"host": "h", "username": "u", "password": "p"})
    assert res["type"] == "form"
    assert res["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_async_step_user_success(monkeypatch):
    handler = ZehnderMulticontrollerFlowHandler()

    async def _good(hass, user_input):
        return {"title": "Zehnder Multicontroller"}

    monkeypatch.setattr(
        "custom_components.zehnder_multicontroller.config_flow.validate_input", _good
    )
    # prevent unique id collision checks and skip framework unique id logic
    handler._abort_if_unique_id_configured = lambda: None

    async def _noop_set_unique_id(uid):
        return None

    handler.async_set_unique_id = _noop_set_unique_id

    res = await handler.async_step_user({"host": "h", "username": "u", "password": "p"})
    assert res["type"] == "create_entry"
