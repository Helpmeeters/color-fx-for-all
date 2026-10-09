"""Services for Color FX for All."""

import logging

import voluptuous as vol

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .const import (
    CONF_SEQUENCE,
    DOMAIN,
    SERVICE_NEXT_SEQUENCE,
    SERVICE_SET_SEQUENCE,
    SERVICE_START,
    SERVICE_STOP,
)
from .coordinator import ColorFXCoordinator

_LOGGER = logging.getLogger(__name__)

START_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(CONF_SEQUENCE): cv.string,
    }
)

STOP_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)

SET_SEQUENCE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(CONF_SEQUENCE): cv.string,
    }
)

NEXT_SEQUENCE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)


def _get_coordinators_for_call(hass: HomeAssistant, call: ServiceCall) -> list[ColorFXCoordinator]:
    """Find matching coordinators based on targeted entity_id or return all."""
    coordinators_map: dict[str, ColorFXCoordinator] = hass.data.get(DOMAIN, {}).get(
        "coordinators", {}
    )
    all_coords = list(coordinators_map.values())

    entity_ids = call.data.get(ATTR_ENTITY_ID)
    if not entity_ids:
        return all_coords

    if isinstance(entity_ids, str):
        entity_ids = [entity_ids]

    registry = er.async_get(hass)
    entry_ids = set()
    for entity_id in entity_ids:
        entity = registry.async_get(entity_id)
        if entity and entity.platform == DOMAIN:
            entry_ids.add(entity.config_entry_id)

    return [
        coord
        for coord in all_coords
        if coord.entry_id in entry_ids
        or any(target in coord.target_lights for target in entity_ids)
    ]


async def async_handle_start(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle start service."""
    sequence = call.data.get(CONF_SEQUENCE)
    for coord in _get_coordinators_for_call(hass, call):
        await coord.async_start(sequence=sequence)


async def async_handle_stop(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle stop service."""
    for coord in _get_coordinators_for_call(hass, call):
        await coord.async_stop()


async def async_handle_next_sequence(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle next_sequence service."""
    for coord in _get_coordinators_for_call(hass, call):
        await coord.async_next_sequence()


async def async_handle_set_sequence(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle set_sequence service."""
    sequence = call.data[CONF_SEQUENCE]
    for coord in _get_coordinators_for_call(hass, call):
        await coord.async_set_sequence(sequence)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register Color FX services."""

    async def _start(call: ServiceCall) -> None:
        await async_handle_start(hass, call)

    async def _stop(call: ServiceCall) -> None:
        await async_handle_stop(hass, call)

    async def _next_seq(call: ServiceCall) -> None:
        await async_handle_next_sequence(hass, call)

    async def _set_seq(call: ServiceCall) -> None:
        await async_handle_set_sequence(hass, call)

    hass.services.async_register(DOMAIN, SERVICE_START, _start, schema=START_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_STOP, _stop, schema=STOP_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_NEXT_SEQUENCE, _next_seq, schema=NEXT_SEQUENCE_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_SET_SEQUENCE, _set_seq, schema=SET_SEQUENCE_SCHEMA)
