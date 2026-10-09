"""Setup, entities, the dashboard card, and unload."""

from custom_components.color_fx.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .conftest import GROUP, coordinator_for, entity_id_for


async def test_setup_creates_hub_entities(hass: HomeAssistant, setup_hub) -> None:
    """Each Hub gets a switch and a sequence select named after it, on its own device."""
    entry = await setup_hub()

    assert entity_id_for(hass, entry, "switch", "switch") == "switch.color_fx_living_room"
    assert (
        entity_id_for(hass, entry, "select", "sequence") == "select.color_fx_living_room_sequence"
    )

    switch = hass.states.get("switch.color_fx_living_room")
    assert switch.state == "off"
    assert switch.attributes["friendly_name"] == "Living Room Color FX"
    assert switch.attributes["current_sequence"] == "Sunset"
    assert switch.attributes["target_light"] == [GROUP]
    assert switch.attributes["palette"] == ["#ff4b2d", "#ffa014", "#b432b4", "#4632a0"]
    assert switch.attributes["palette_source"] is None
    assert "Media Art" in switch.attributes["available_sequences"]

    select = hass.states.get("select.color_fx_living_room_sequence")
    assert select.state == "Sunset"
    assert select.attributes["options"] == switch.attributes["available_sequences"]

    entity = er.async_get(hass).async_get("select.color_fx_living_room_sequence")
    device = dr.async_get(hass).async_get(entity.device_id)
    assert device.name == "Living Room"
    assert (DOMAIN, entry.entry_id) in device.identifiers


async def test_two_hubs_get_distinct_entity_ids(hass: HomeAssistant, setup_hub) -> None:
    """A second Hub doesn't fall back to generic ids like select.sequence."""
    await setup_hub()
    await setup_hub("Porch")

    assert hass.states.get("switch.color_fx_porch")
    assert hass.states.get("select.color_fx_porch_sequence")
    assert hass.states.get("select.sequence") is None


async def test_card_is_registered_once(hass: HomeAssistant, setup_hub, frontend_stub) -> None:
    """The dashboard card is served and loaded on every dashboard, cache-busted by version."""
    await setup_hub()
    await setup_hub("Porch")

    frontend_stub.assert_called_once()
    url = frontend_stub.call_args.args[1]
    assert url.startswith("/color_fx/color-fx-card.js?v=")
    (paths,) = hass.http.async_register_static_paths.call_args.args
    assert paths[0].url_path == "/color_fx/color-fx-card.js"
    assert paths[0].path.endswith("frontend/color-fx-card.js")


async def test_unload_stops_and_restores(
    hass: HomeAssistant, setup_hub, turn_on_calls, turn_off_calls
) -> None:
    """Unloading a running Hub stops the animation and restores the lights."""
    entry = await setup_hub()
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.color_fx_living_room"}, blocking=True
    )
    assert coordinator_for(hass, entry).is_running

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert entry.entry_id not in hass.data[DOMAIN]["coordinators"]
    assert any(call.data.get("brightness") == 200 for call in turn_on_calls)


async def test_options_change_reloads_hub(hass: HomeAssistant, setup_hub) -> None:
    """Changing options rebuilds the Hub with the new settings."""
    entry = await setup_hub()

    hass.config_entries.async_update_entry(entry, options={"sequence": "Halloween"})
    await hass.async_block_till_done()

    assert coordinator_for(hass, entry).current_sequence == "Halloween"
    assert hass.states.get("select.color_fx_living_room_sequence").state == "Halloween"


async def test_renamed_sequence_is_migrated(hass: HomeAssistant, setup_hub) -> None:
    """Entries saved with the old "Music Art" name open on Media Art."""
    entry = await setup_hub(sequence="Music Art")

    assert coordinator_for(hass, entry).current_sequence == "Media Art"


async def test_unknown_sequence_falls_back_to_default(hass: HomeAssistant, setup_hub) -> None:
    """A sequence that no longer exists falls back to Sunset instead of failing setup."""
    entry = await setup_hub(sequence="Disco")

    assert coordinator_for(hass, entry).current_sequence == "Sunset"
