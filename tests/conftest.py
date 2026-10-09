"""Shared fixtures: a room of lights, recorded light calls, and a Hub that drives them."""

from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.color_fx.const import (
    CONF_INTERVAL,
    CONF_ROTATE,
    CONF_SEQUENCE,
    CONF_TARGET_LIGHT,
    CONF_TRANSITION,
    DOMAIN,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er

GROUP = "light.living_room"
COLOR_BULB = "light.lamp"
COLOR_TEMP_BULB = "light.ceiling"
DIMMER = "light.dimmer"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    return


@pytest.fixture(autouse=True)
def frontend_stub(hass: HomeAssistant):
    """Stand in for frontend and http, which the card registration needs."""
    hass.config.components.update({"frontend", "http"})
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    with patch("custom_components.color_fx.add_extra_js_url") as add_js:
        yield add_js


@pytest.fixture
def lights(hass: HomeAssistant) -> None:
    """A light group of two color bulbs and a dimmer that can't do color."""
    hass.states.async_set(
        GROUP,
        "on",
        {"entity_id": [COLOR_BULB, COLOR_TEMP_BULB, DIMMER], "supported_color_modes": ["xy"]},
    )
    hass.states.async_set(
        COLOR_BULB,
        "on",
        {"supported_color_modes": ["xy"], "brightness": 200, "rgb_color": (10, 20, 30)},
    )
    hass.states.async_set(
        COLOR_TEMP_BULB,
        "on",
        {"supported_color_modes": ["color_temp"], "brightness": 90, "color_temp_kelvin": 2700},
    )
    hass.states.async_set(DIMMER, "off", {"supported_color_modes": ["brightness"]})


@pytest.fixture
def turn_on_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Recorded light.turn_on calls."""
    return async_mock_service(hass, "light", "turn_on")


@pytest.fixture
def turn_off_calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Recorded light.turn_off calls."""
    return async_mock_service(hass, "light", "turn_off")


@pytest.fixture
def setup_hub(
    hass: HomeAssistant, lights, turn_on_calls, turn_off_calls
) -> Callable[..., Awaitable[MockConfigEntry]]:
    """Add and set up a Hub entry; keyword arguments override its data."""

    async def _setup(title: str = "Living Room", **data: Any) -> MockConfigEntry:
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=title,
            data={
                "name": title,
                CONF_TARGET_LIGHT: [GROUP],
                CONF_SEQUENCE: "Sunset",
                CONF_ROTATE: True,
                CONF_INTERVAL: 4.0,
                CONF_TRANSITION: 2.0,
                **data,
            },
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup


def entity_id_for(hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str) -> str:
    """Look up a Hub entity's id by its unique id."""
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
    assert entity_id
    return entity_id


def coordinator_for(hass: HomeAssistant, entry: MockConfigEntry):
    """Return a Hub's coordinator."""
    return hass.data[DOMAIN]["coordinators"][entry.entry_id]
