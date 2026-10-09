"""Starting, animating, and stopping a Hub's lights."""

import asyncio

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from .conftest import COLOR_BULB, COLOR_TEMP_BULB, DIMMER, GROUP, coordinator_for

SWITCH = "switch.color_fx_living_room"
SUNSET = [[255, 75, 45], [255, 160, 20], [180, 50, 180], [70, 50, 160]]


async def _turn_on(hass: HomeAssistant) -> None:
    await hass.services.async_call("switch", "turn_on", {"entity_id": SWITCH}, blocking=True)
    await hass.async_block_till_done()


async def _turn_off(hass: HomeAssistant) -> None:
    await hass.services.async_call("switch", "turn_off", {"entity_id": SWITCH}, blocking=True)
    await hass.async_block_till_done()


async def test_start_colors_only_color_capable_members(
    hass: HomeAssistant, setup_hub, turn_on_calls
) -> None:
    """A light group is expanded, and lights that can't show color are left alone."""
    await setup_hub()

    await _turn_on(hass)

    assert hass.states.get(SWITCH).state == "on"
    first = turn_on_calls[0].data
    assert first["entity_id"] == [COLOR_BULB, COLOR_TEMP_BULB]
    assert first["rgb_color"] == SUNSET[0]
    assert first["transition"] == 2.0


async def test_rotation_steps_through_palette(
    hass: HomeAssistant, setup_hub, turn_on_calls
) -> None:
    """With rotation on, each interval moves to the next color and wraps around."""
    await setup_hub(interval=0.01, transition=5.0)

    await _turn_on(hass)
    while len(turn_on_calls) < 6:
        await asyncio.sleep(0.01)
    await _turn_off(hass)

    colors = [call.data["rgb_color"] for call in turn_on_calls[:6]]
    assert colors == [*SUNSET, *SUNSET[:2]]
    assert turn_on_calls[0].data["transition"] == 0.01


async def test_without_rotation_holds_dominant_color(
    hass: HomeAssistant, setup_hub, turn_on_calls
) -> None:
    """With rotation off, the lights hold the first color and the full transition is used."""
    entry = await setup_hub(rotate=False, interval=0.01, transition=3.0)

    await _turn_on(hass)
    await asyncio.sleep(0.05)

    assert [call.data["rgb_color"] for call in turn_on_calls] == [SUNSET[0]]
    assert turn_on_calls[0].data["transition"] == 3.0
    assert hass.states.get(SWITCH).attributes["palette"] == ["#ff4b2d"]
    assert coordinator_for(hass, entry).is_running


async def test_stop_restores_previous_state(
    hass: HomeAssistant, setup_hub, turn_on_calls, turn_off_calls
) -> None:
    """Stopping restores each bulb's brightness and color, and turns off bulbs that were off."""
    hass.states.async_set(COLOR_TEMP_BULB, "off", {"supported_color_modes": ["color_temp"]})
    await setup_hub()
    await _turn_on(hass)
    turn_on_calls.clear()

    await _turn_off(hass)

    assert hass.states.get(SWITCH).state == "off"
    assert [call.data for call in turn_on_calls] == [
        {"entity_id": COLOR_BULB, "transition": 1.0, "brightness": 200, "rgb_color": (10, 20, 30)}
    ]
    assert [call.data["entity_id"] for call in turn_off_calls] == [COLOR_TEMP_BULB]
    assert DIMMER not in {call.data["entity_id"] for call in turn_on_calls + turn_off_calls}


async def test_stop_restores_color_temperature(
    hass: HomeAssistant, setup_hub, turn_on_calls
) -> None:
    """A bulb showing white light gets its color temperature back."""
    await setup_hub()
    await _turn_on(hass)
    turn_on_calls.clear()

    await _turn_off(hass)

    restored = {call.data["entity_id"]: call.data for call in turn_on_calls}
    assert restored[COLOR_TEMP_BULB]["color_temp_kelvin"] == 2700
    assert restored[COLOR_TEMP_BULB]["brightness"] == 90


async def test_stop_without_restore_leaves_lights(
    hass: HomeAssistant, setup_hub, turn_on_calls, turn_off_calls
) -> None:
    """With restore off, stopping leaves the lights on their last color."""
    await setup_hub(restore_state=False)
    await _turn_on(hass)
    turn_on_calls.clear()

    await _turn_off(hass)

    assert turn_on_calls == []
    assert turn_off_calls == []


async def test_no_color_lights_does_not_start(
    hass: HomeAssistant, setup_hub, turn_on_calls, caplog
) -> None:
    """A Hub aimed only at lights without color stays off and says why."""
    await setup_hub(target_light=[DIMMER])

    await _turn_on(hass)

    assert hass.states.get(SWITCH).state == "off"
    assert turn_on_calls == []
    assert "No color-capable lights found" in caplog.text


async def test_select_changes_running_sequence(
    hass: HomeAssistant, setup_hub, turn_on_calls
) -> None:
    """Picking a sequence while running applies its first color right away."""
    await setup_hub()
    await _turn_on(hass)

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.color_fx_living_room_sequence", "option": "Christmas"},
        blocking=True,
    )

    assert turn_on_calls[-1].data["rgb_color"] == [255, 15, 15]
    assert hass.states.get(SWITCH).attributes["current_sequence"] == "Christmas"


async def test_unknown_sequence_is_rejected(hass: HomeAssistant, setup_hub) -> None:
    """Setting a sequence that doesn't exist is a validation error, not a crash."""
    entry = await setup_hub()

    with pytest.raises(ServiceValidationError):
        await coordinator_for(hass, entry).async_set_sequence("Disco")


async def test_single_light_target(hass: HomeAssistant, setup_hub, turn_on_calls) -> None:
    """A target that is one light rather than a group is used directly."""
    await setup_hub(target_light=COLOR_BULB)

    await _turn_on(hass)

    assert turn_on_calls[0].data["entity_id"] == [COLOR_BULB]
    assert hass.states.get(SWITCH).attributes["target_light"] == [COLOR_BULB]


async def test_group_members_are_deduplicated(
    hass: HomeAssistant, setup_hub, turn_on_calls
) -> None:
    """A light listed both directly and through its group is sent one command."""
    await setup_hub(target_light=[GROUP, COLOR_BULB])

    await _turn_on(hass)

    assert turn_on_calls[0].data["entity_id"] == [COLOR_BULB, COLOR_TEMP_BULB]
