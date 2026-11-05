"""Tests for the config flow validation logic."""

from __future__ import annotations

import pytest
from custom_components.zehnder_multicontroller.config_flow import validate_input


@pytest.mark.asyncio
async def test_validate_input_success(monkeypatch, hass, DummyAPI):
    """validate_input should return title when connection succeeds."""
    # Use shared DummyAPI test class
    monkeypatch.setattr(
        "custom_components.zehnder_multicontroller.api.RainmakerAPI", DummyAPI
    )

    info = await validate_input(hass, {"host": "h", "username": "u", "password": "p"})
    assert info["title"] == "Zehnder Multicontroller"


@pytest.mark.asyncio
async def test_validate_input_auth_error(monkeypatch, hass):
    class BadAPI:
        def __init__(self, hass, host, username, password):
            pass

        async def async_connect(self):
            raise Exception("auth")

    monkeypatch.setattr(
        "custom_components.zehnder_multicontroller.api.RainmakerAPI", BadAPI
    )

    with pytest.raises(Exception, match="auth"):
        await validate_input(hass, {"host": "h", "username": "bad", "password": "p"})


# The module-level config-flow validation tests are above. Additional
# integration-style config flow tests that exercise the full UI flow are
# intentionally omitted here — they require the Home Assistant config flow
# harness and more extensive fixtures. The `validate_input` unit tests
# above exercise the code path used to validate credentials.
