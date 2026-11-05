"""Zehnder Multicontroller integration (custom_component for HACS)."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .const import PLATFORMS
from .helpers import is_climate_node
from .helpers import is_climate_param
from .helpers import use_climate_entity

_LOGGER = logging.getLogger(__name__)


def _async_remove_unused_entities(
    hass: HomeAssistant, entry: ConfigEntry, data: dict | None
) -> None:
    """Remove registry entries for entities the current mode doesn't create.

    With the climate entity enabled, the individual entities for the params
    it covers are not created; with it disabled, the climate entity is not
    created. Leaving their registry entries behind would show them as
    "unavailable", so remove them.
    """
    if not data:
        return

    use_climate = use_climate_entity(entry)
    unused: set[str] = set()
    for node_id, params in data.items():
        if not is_climate_node(params):
            continue
        if use_climate:
            unused.update(
                f"{entry.entry_id}_{node_id}_{param}"
                for param in params
                if is_climate_param(param)
            )
        else:
            unused.add(f"{entry.entry_id}_{node_id}_climate")

    if not unused:
        return

    registry = er.async_get(hass)
    for reg_entry in list(registry.entities.values()):
        if (
            reg_entry.config_entry_id == entry.entry_id
            and reg_entry.unique_id in unused
        ):
            _LOGGER.info(
                "Removing %s: not used with use_climate_entity=%s",
                reg_entry.entity_id,
                use_climate,
            )
            registry.async_remove(reg_entry.entity_id)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change so entities are recreated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Zehnder Multicontroller config entry.

    Creates the API object, data coordinator and forwards platform setups.
    """
    _LOGGER.info(
        "Setting up Zehnder Multicontroller integration for entry %s",
        entry.entry_id,
    )

    data = entry.data
    host = data.get("host")
    username = data.get("username")
    password = data.get("password")

    # Import API and coordinator lazily to avoid requiring optional
    # dependencies (like `rainmaker-http`) at import time when the
    # config flow UI is loaded
    from .api import RainmakerAPI
    from .coordinator import RainmakerCoordinator

    api = RainmakerAPI(hass, host, username, password)
    try:
        _LOGGER.debug("Attempting to connect to Rainmaker API...")
        await api.async_connect()
        _LOGGER.info("Successfully connected to Rainmaker API")
    except Exception as err:
        _LOGGER.error("Failed to connect to Rainmaker: %s", err)
        raise ConfigEntryNotReady from err

    coordinator = RainmakerCoordinator(hass, api, entry)
    # Fetch initial data so platforms have data when they are first added
    _LOGGER.debug("Fetching initial data from coordinator...")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("Initial data fetched: %d nodes found", len(coordinator.data))

    # Store runtime-only references
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    _async_remove_unused_entities(hass, entry, coordinator.data)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info("Forwarding setup to platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Platform setup completed for entry %s", entry.entry_id)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and its platforms."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Remove runtime references if they exist
        domain_data = hass.data.get(DOMAIN)
        if domain_data and entry.entry_id in domain_data:
            domain_data.pop(entry.entry_id)
    return unload_ok
