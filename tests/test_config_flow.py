"""Adding and configuring a Hub."""

from custom_components.color_fx.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .conftest import COLOR_BULB, GROUP


async def test_user_flow_creates_hub(hass: HomeAssistant, lights) -> None:
    """The setup form stores the rotation section's fields at the top level."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Living Room",
            "media_players": [],
            "target_light": [GROUP],
            "sequence": "Halloween",
            "restore_state": True,
            "rotate": True,
            "rotation": {"interval": 6.0, "transition": 1.5},
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living Room"
    assert result["data"] == {
        "name": "Living Room",
        "media_players": [],
        "target_light": [GROUP],
        "sequence": "Halloween",
        "restore_state": True,
        "rotate": True,
        "interval": 6.0,
        "transition": 1.5,
    }
    assert hass.states.get("switch.color_fx_living_room")


async def test_options_flow_updates_and_renames(hass: HomeAssistant, setup_hub) -> None:
    """Options change the Hub's settings, and a new name retitles it."""
    entry = await setup_hub()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "  Den  ",
            "target_light": [COLOR_BULB],
            "sequence": "Media Art",
            "restore_state": False,
            "rotate": False,
            "rotation": {"interval": 4.0, "transition": 2.0},
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.title == "Den"
    entity = er.async_get(hass).async_get("switch.color_fx_living_room")
    assert dr.async_get(hass).async_get(entity.device_id).name == "Den"
    assert entry.options == {
        "media_players": [],
        "target_light": [COLOR_BULB],
        "sequence": "Media Art",
        "restore_state": False,
        "rotate": False,
        "interval": 4.0,
        "transition": 2.0,
    }
    switch = hass.states.get("switch.color_fx_living_room")
    assert switch.attributes["current_sequence"] == "Media Art"
    assert switch.attributes["target_light"] == [COLOR_BULB]
    assert switch.attributes["rotate"] is False


async def test_options_flow_keeps_name_when_blank(hass: HomeAssistant, setup_hub) -> None:
    """Clearing the name field keeps the current name."""
    entry = await setup_hub()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": " ",
            "target_light": [GROUP],
            "sequence": "Sunset",
            "rotate": True,
            "rotation": {"interval": 4.0, "transition": 2.0},
        },
    )
    await hass.async_block_till_done()

    assert entry.title == "Living Room"
