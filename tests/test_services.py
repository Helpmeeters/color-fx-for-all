"""The color_fx.* actions and how they pick Hubs."""

import pytest

from custom_components.color_fx.const import BUILTIN_SEQUENCES, DOMAIN, MEDIA_ART_SEQUENCE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from .conftest import COLOR_BULB, GROUP, coordinator_for


async def test_start_with_sequence(hass: HomeAssistant, setup_hub, turn_on_calls) -> None:
    """color_fx.start can pick the sequence it starts with."""
    entry = await setup_hub()

    await hass.services.async_call(
        DOMAIN,
        "start",
        {"entity_id": "switch.color_fx_living_room", "sequence": "Ocean Waves"},
        blocking=True,
    )
    await hass.async_block_till_done()

    coordinator = coordinator_for(hass, entry)
    assert coordinator.is_running
    assert coordinator.current_sequence == "Ocean Waves"
    assert turn_on_calls[0].data["rgb_color"] == [0, 60, 190]

    await hass.services.async_call(
        DOMAIN, "stop", {"entity_id": "switch.color_fx_living_room"}, blocking=True
    )
    assert not coordinator.is_running


async def test_targets_only_the_named_hub(hass: HomeAssistant, setup_hub) -> None:
    """Naming one Hub's switch leaves other Hubs alone."""
    living = await setup_hub()
    porch = await setup_hub("Porch")

    await hass.services.async_call(
        DOMAIN, "start", {"entity_id": "switch.color_fx_porch"}, blocking=True
    )

    assert coordinator_for(hass, porch).is_running
    assert not coordinator_for(hass, living).is_running


async def test_target_light_selects_its_hub(hass: HomeAssistant, setup_hub) -> None:
    """Naming a light a Hub targets acts on that Hub."""
    living = await setup_hub()
    porch = await setup_hub("Porch", target_light=[COLOR_BULB])

    await hass.services.async_call(DOMAIN, "start", {"entity_id": GROUP}, blocking=True)

    assert coordinator_for(hass, living).is_running
    assert not coordinator_for(hass, porch).is_running


async def test_no_target_means_every_hub(hass: HomeAssistant, setup_hub) -> None:
    """Leaving out entity_id acts on every Hub."""
    living = await setup_hub()
    porch = await setup_hub("Porch")

    await hass.services.async_call(DOMAIN, "set_sequence", {"sequence": "Rainbow"}, blocking=True)

    assert coordinator_for(hass, living).current_sequence == "Rainbow"
    assert coordinator_for(hass, porch).current_sequence == "Rainbow"


async def test_next_sequence_cycles_and_wraps(hass: HomeAssistant, setup_hub) -> None:
    """next_sequence walks the built-ins, then Media Art, then wraps to the first."""
    entry = await setup_hub()
    coordinator = coordinator_for(hass, entry)
    order = [*BUILTIN_SEQUENCES, MEDIA_ART_SEQUENCE]

    seen = []
    for _ in order:
        await hass.services.async_call(
            DOMAIN, "next_sequence", {"entity_id": "switch.color_fx_living_room"}, blocking=True
        )
        seen.append(coordinator.current_sequence)

    assert seen == [*order[1:], order[0]]


async def test_set_sequence_accepts_old_name(hass: HomeAssistant, setup_hub) -> None:
    """Automations written for "Music Art" keep working."""
    entry = await setup_hub()

    await hass.services.async_call(
        DOMAIN,
        "set_sequence",
        {"entity_id": "switch.color_fx_living_room", "sequence": "Music Art"},
        blocking=True,
    )

    assert coordinator_for(hass, entry).current_sequence == MEDIA_ART_SEQUENCE


async def test_set_unknown_sequence_errors(hass: HomeAssistant, setup_hub) -> None:
    """An unknown sequence name is reported to the caller."""
    await setup_hub()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "set_sequence",
            {"entity_id": "switch.color_fx_living_room", "sequence": "Disco"},
            blocking=True,
        )
