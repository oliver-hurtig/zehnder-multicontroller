"""Global fixtures for Zehnder Multicontroller integration."""

from unittest.mock import patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with (
        patch("homeassistant.components.persistent_notification.async_create"),
        patch("homeassistant.components.persistent_notification.async_dismiss"),
    ):
        yield


# This fixture, when used, will result in calls to async_get_data to return None. To have the call
# return a value, we would add the `return_value=<VALUE_TO_RETURN>` parameter to the patch call.
@pytest.fixture(name="bypass_get_data")
def bypass_get_data_fixture():
    """Skip calls to get data from API."""
    # Patch the RainmakerAPI connect and the coordinator's initial refresh so
    # integration setup does not perform network calls.
    with (
        patch(
            "custom_components.zehnder_multicontroller.api.RainmakerAPI.async_connect",
            return_value=None,
        ),
        patch(
            "custom_components.zehnder_multicontroller.coordinator.RainmakerCoordinator.async_config_entry_first_refresh",
            return_value=None,
        ),
    ):
        yield


# In this fixture, we are forcing calls to async_get_data to raise an Exception. This is useful
# for exception handling.
@pytest.fixture(name="error_on_get_data")
def error_get_data_fixture():
    """Simulate error when retrieving data from API."""
    # Force coordinator initial refresh to raise to simulate setup failure
    with (
        patch(
            "custom_components.zehnder_multicontroller.api.RainmakerAPI.async_connect",
            return_value=None,
        ),
        patch(
            "custom_components.zehnder_multicontroller.coordinator.RainmakerCoordinator.async_config_entry_first_refresh",
            side_effect=Exception,
        ),
    ):
        yield


@pytest.fixture(name="DummyAPI")
def fixture_dummy_api():
    """Provide a simple DummyAPI class for tests.

    The class accepts an optional `nodes` kwarg to control what
    `async_get_nodes` returns. It also exposes `async_set_param` as an
    AsyncMock to make assertions about calls.
    """
    from unittest.mock import AsyncMock

    class _DummyAPI:
        def __init__(self, *args, nodes=None, **kwargs):
            self._nodes = nodes if nodes is not None else {"node_details": []}
            self.is_connected = False
            self.async_set_param = AsyncMock()

        async def async_connect(self):
            self.is_connected = True

        async def async_get_nodes(self):
            return self._nodes

        async def async_close(self):
            self.is_connected = False

    return _DummyAPI


@pytest.fixture(name="DummyCoordinator")
def fixture_dummy_coordinator():
    """Provide a simple DummyCoordinator class for tests.

    Instances have a `data` dict, an `api` attribute, and an
    `async_request_refresh` AsyncMock so platform entities can call it.
    """
    from unittest.mock import AsyncMock

    class _DummyCoordinator:
        def __init__(self, *args, data=None, **kwargs):
            # Accept either a data dict directly (positional) or the usual
            # (hass, api, entry) constructor signature so the class can be
            # used both as a lightweight test coordinator and as a
            # replacement for the actual RainmakerCoordinator during
            # integration setup.
            if data is None and args:
                # If the first positional arg is a dict, treat it as data
                first = args[0]
                if isinstance(first, dict):
                    data = first
            self.data = data or {}
            self.async_request_refresh = AsyncMock()
            self.api = None

        async def async_config_entry_first_refresh(self):
            return None

    return _DummyCoordinator
