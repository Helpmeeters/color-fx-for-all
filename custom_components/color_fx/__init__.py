"""The Color FX for All integration."""

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import (
    CONF_CUSTOM_SEQUENCES,
    CONF_INTERVAL,
    CONF_MEDIA_PLAYERS,
    CONF_RESTORE_STATE,
    CONF_ROTATE,
    CONF_SEQUENCE,
    CONF_TARGET_LIGHT,
    CONF_TRANSITION,
    DEFAULT_INTERVAL,
    DEFAULT_RESTORE_STATE,
    DEFAULT_ROTATE,
    DEFAULT_SEQUENCE,
    DEFAULT_TRANSITION,
    DOMAIN,
)
from .coordinator import ColorFXCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH, Platform.SELECT]
CARD_URL = f"/{DOMAIN}/color-fx-card.js"
CARD_PATH = Path(__file__).parent / "frontend" / "color-fx-card.js"

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
    await _async_register_card(hass)
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the Color FX dashboard card and load it on every dashboard."""
    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Color FX from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("coordinators", {})

    data = entry.data
    options = entry.options or {}
    targets = options.get(CONF_TARGET_LIGHT, data[CONF_TARGET_LIGHT])

    coordinator = ColorFXCoordinator(
        hass=hass,
        entry_id=entry.entry_id,
        name=entry.title,
        target_lights=[targets] if isinstance(targets, str) else list(targets),
        initial_sequence=options.get(CONF_SEQUENCE, data.get(CONF_SEQUENCE, DEFAULT_SEQUENCE)),
        interval=options.get(CONF_INTERVAL, data.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        transition=options.get(CONF_TRANSITION, data.get(CONF_TRANSITION, DEFAULT_TRANSITION)),
        restore_state=options.get(
            CONF_RESTORE_STATE, data.get(CONF_RESTORE_STATE, DEFAULT_RESTORE_STATE)
        ),
        media_players=options.get(CONF_MEDIA_PLAYERS, data.get(CONF_MEDIA_PLAYERS, [])),
        rotate=options.get(CONF_ROTATE, data.get(CONF_ROTATE, DEFAULT_ROTATE)),
    )

    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator
    coordinator.sync_media_art()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: ColorFXCoordinator | None = hass.data[DOMAIN]["coordinators"].get(entry.entry_id)
    if coordinator:
        await coordinator.async_stop()
        coordinator.sync_media_art(enabled=False)
        hass.data[DOMAIN]["coordinators"].pop(entry.entry_id, None)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
