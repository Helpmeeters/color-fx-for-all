"""The Color FX for All integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_CUSTOM_SEQUENCES,
    CONF_INTERVAL,
    CONF_RESTORE_STATE,
    CONF_SEQUENCE,
    CONF_TARGET_LIGHT,
    CONF_TRANSITION,
    DEFAULT_INTERVAL,
    DEFAULT_RESTORE_STATE,
    DEFAULT_SEQUENCE,
    DEFAULT_TRANSITION,
    DOMAIN,
)
from .coordinator import ColorFXCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH, Platform.SELECT]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Color FX component via YAML."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("coordinators", {})
    hass.data[DOMAIN].setdefault("custom_sequences", {})

    if DOMAIN in config:
        conf = config[DOMAIN]
        if CONF_CUSTOM_SEQUENCES in conf:
            hass.data[DOMAIN]["custom_sequences"] = conf[CONF_CUSTOM_SEQUENCES]

    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Color FX from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("coordinators", {})

    data = entry.data
    options = entry.options or {}

    coordinator = ColorFXCoordinator(
        hass=hass,
        entry_id=entry.entry_id,
        name=entry.title,
        target_light=data[CONF_TARGET_LIGHT],
        initial_sequence=options.get(CONF_SEQUENCE, data.get(CONF_SEQUENCE, DEFAULT_SEQUENCE)),
        interval=options.get(CONF_INTERVAL, data.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        transition=options.get(CONF_TRANSITION, data.get(CONF_TRANSITION, DEFAULT_TRANSITION)),
        restore_state=options.get(
            CONF_RESTORE_STATE, data.get(CONF_RESTORE_STATE, DEFAULT_RESTORE_STATE)
        ),
    )

    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: ColorFXCoordinator | None = hass.data[DOMAIN]["coordinators"].get(entry.entry_id)
    if coordinator:
        await coordinator.async_stop()
        hass.data[DOMAIN]["coordinators"].pop(entry.entry_id, None)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
