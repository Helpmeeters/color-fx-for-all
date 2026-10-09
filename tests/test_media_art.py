"""Turning media artwork into a palette and following the player that's playing."""

import io
from unittest.mock import AsyncMock, MagicMock

from PIL import Image
import pytest

from custom_components.color_fx.media_art import extract_palette
from homeassistant.components.media_player import DATA_COMPONENT
from homeassistant.core import HomeAssistant

from .conftest import coordinator_for

SWITCH = "switch.color_fx_living_room"


async def _settle(hass: HomeAssistant) -> None:
    """Wait for artwork fetches, which run as background tasks."""
    await hass.async_block_till_done(wait_background_tasks=True)


def _image(*bands: tuple[tuple[int, int, int], int]) -> bytes:
    """A PNG of vertical color bands, each (rgb, width)."""
    img = Image.new("RGB", (sum(width for _, width in bands), 20))
    x = 0
    for rgb, width in bands:
        img.paste(rgb, (x, 0, x + width, 20))
        x += width
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


RED_BLUE = _image(((200, 30, 30), 60), ((30, 30, 200), 30), ((0, 0, 0), 10))
GREEN = _image(((30, 200, 30), 100))


def test_palette_is_dominant_first_without_black() -> None:
    """Colors come out most common first, saturated to full brightness, with black dropped."""
    assert extract_palette(RED_BLUE) == [[255, 0, 0], [0, 0, 255]]


def test_near_duplicate_hues_are_merged() -> None:
    """Two shades of the same hue become one light color."""
    image = _image(((200, 30, 30), 50), ((220, 50, 40), 50))
    assert len(extract_palette(image)) == 1


def test_grays_become_white() -> None:
    """Unsaturated artwork gives white rather than a tinted color."""
    assert extract_palette(_image(((128, 128, 128), 100))) == [[255, 255, 255]]


@pytest.fixture
def players(hass: HomeAssistant) -> dict[str, MagicMock]:
    """Fake media player entities whose artwork the tracker can fetch."""
    entities = {
        "media_player.speaker": MagicMock(
            async_get_media_image=AsyncMock(return_value=(RED_BLUE, "image/png"))
        ),
        "media_player.tv": MagicMock(
            async_get_media_image=AsyncMock(return_value=(GREEN, "image/png"))
        ),
    }
    hass.data[DATA_COMPONENT] = MagicMock(get_entity=entities.get)
    return entities


async def test_follows_artwork_while_off(hass: HomeAssistant, setup_hub, players) -> None:
    """With Media Art selected, the palette follows the playing player even while the Hub is off."""
    hass.states.async_set("media_player.speaker", "playing", {"entity_picture": "/art/1"})
    await setup_hub(sequence="Media Art")
    await _settle(hass)

    switch = hass.states.get(SWITCH)
    assert switch.state == "off"
    assert switch.attributes["palette"] == ["#ff0000", "#0000ff"]
    assert switch.attributes["palette_source"] == "media_player.speaker"


async def test_switches_to_player_that_starts_playing(
    hass: HomeAssistant, setup_hub, players, turn_on_calls
) -> None:
    """When another player starts new artwork, a running Hub restarts on its colors."""
    hass.states.async_set("media_player.speaker", "playing", {"entity_picture": "/art/1"})
    await setup_hub(sequence="Media Art", rotate=False)
    await _settle(hass)
    await hass.services.async_call("switch", "turn_on", {"entity_id": SWITCH}, blocking=True)
    await _settle(hass)
    assert turn_on_calls[0].data["rgb_color"] == [255, 0, 0]

    hass.states.async_set("media_player.tv", "playing", {"entity_picture": "/art/2"})
    await _settle(hass)

    switch = hass.states.get(SWITCH)
    assert switch.attributes["palette_source"] == "media_player.tv"
    assert switch.attributes["palette"] == ["#00ff00"]
    assert turn_on_calls[-1].data["rgb_color"] == [0, 255, 0]


async def test_only_follows_chosen_players(hass: HomeAssistant, setup_hub, players) -> None:
    """A Hub limited to some players ignores the others."""
    hass.states.async_set("media_player.speaker", "playing", {"entity_picture": "/art/1"})
    await setup_hub(sequence="Media Art", media_players=["media_player.tv"])
    await _settle(hass)
    assert hass.states.get(SWITCH).attributes["palette"] == []

    hass.states.async_set("media_player.tv", "playing", {"entity_picture": "/art/2"})
    await _settle(hass)

    assert hass.states.get(SWITCH).attributes["palette_source"] == "media_player.tv"


async def test_paused_or_same_art_is_ignored(hass: HomeAssistant, setup_hub, players) -> None:
    """Pausing, or a state change with the same artwork, doesn't refetch the image."""
    hass.states.async_set("media_player.speaker", "playing", {"entity_picture": "/art/1"})
    await setup_hub(sequence="Media Art")
    await _settle(hass)
    fetch = players["media_player.speaker"].async_get_media_image

    hass.states.async_set(
        "media_player.speaker", "playing", {"entity_picture": "/art/1", "volume_level": 0.3}
    )
    hass.states.async_set("media_player.speaker", "paused", {"entity_picture": "/art/1"})
    await _settle(hass)

    assert fetch.await_count == 1


async def test_stops_following_when_another_sequence_is_picked(
    hass: HomeAssistant, setup_hub, players
) -> None:
    """Choosing a built-in sequence stops watching players."""
    hass.states.async_set("media_player.speaker", "playing", {"entity_picture": "/art/1"})
    entry = await setup_hub(sequence="Media Art")
    await _settle(hass)

    await coordinator_for(hass, entry).async_set_sequence("Sunset")
    hass.states.async_set("media_player.tv", "playing", {"entity_picture": "/art/2"})
    await _settle(hass)

    players["media_player.tv"].async_get_media_image.assert_not_awaited()
    assert hass.states.get(SWITCH).attributes["palette_source"] is None


async def test_unreadable_artwork_keeps_last_palette(
    hass: HomeAssistant, setup_hub, players, caplog
) -> None:
    """Artwork that can't be decoded is logged and the previous palette stays."""
    hass.states.async_set("media_player.speaker", "playing", {"entity_picture": "/art/1"})
    await setup_hub(sequence="Media Art")
    await _settle(hass)
    players["media_player.tv"].async_get_media_image.return_value = (b"not an image", "image/png")

    hass.states.async_set("media_player.tv", "playing", {"entity_picture": "/art/2"})
    await _settle(hass)

    assert hass.states.get(SWITCH).attributes["palette_source"] == "media_player.speaker"
    assert "Failed extracting artwork colors from media_player.tv" in caplog.text
