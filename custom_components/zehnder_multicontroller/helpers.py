"""Shared helpers for deciding which entities to create."""

from __future__ import annotations

from typing import Any

from .const import CLIMATE_PARAMS
from .const import CONF_USE_CLIMATE
from .const import DEFAULT_USE_CLIMATE


def use_climate_entity(entry: Any) -> bool:
    """Return True if the climate entity should be used for climate nodes."""
    options = getattr(entry, "options", None) or {}
    return bool(options.get(CONF_USE_CLIMATE, DEFAULT_USE_CLIMATE))


def is_climate_node(params: dict[str, Any]) -> bool:
    """Return True if a node exposes enough data for a climate entity."""
    return "temp" in params


def is_climate_param(param: str) -> bool:
    """Return True if the parameter is represented by the climate entity."""
    return param.lower() in CLIMATE_PARAMS


def handled_by_climate(entry: Any, params: dict[str, Any], param: str) -> bool:
    """Return True if `param` is covered by the climate entity for this node.

    Platforms use this to avoid creating duplicate individual entities for
    values the climate entity already shows and controls.
    """
    return (
        use_climate_entity(entry)
        and is_climate_node(params)
        and is_climate_param(param)
    )
