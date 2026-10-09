"""Follow artwork on media players and turn it into a light palette."""

import asyncio
from collections.abc import Callable
import colorsys
import io
import logging

from PIL import Image

from homeassistant.components.media_player import (
    DATA_COMPONENT as MEDIA_PLAYER_COMPONENT,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    MediaPlayerState,
)
from homeassistant.const import ATTR_ENTITY_PICTURE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.event import TrackStates, async_track_state_change_filtered

_LOGGER = logging.getLogger(__name__)

SWATCH_COUNT = 24
MIN_SHARE = 0.01
MIN_VALUE = 0.1
MIN_SATURATION = 0.06
MIN_BOOSTED_SATURATION = 0.85
MIN_HUE_GAP = 20.0


def extract_palette(image: bytes) -> list[list[int]]:
    """Return the distinct, light-friendly colors of an image, most dominant first."""
    with Image.open(io.BytesIO(image)) as img:
        small = img.convert("RGB")
    small.thumbnail((100, 100))
    quantized = small.quantize(colors=SWATCH_COUNT, method=Image.Quantize.MEDIANCUT)
    colors = quantized.getpalette() or []
    counts = sorted(quantized.getcolors() or [], reverse=True)
    total = sum(count for count, _ in counts)

    palette: list[list[int]] = []
    kept: list[tuple[float, float]] = []
    for count, index in counts:
        if count < total * MIN_SHARE:
            continue
        r, g, b = colors[index * 3 : index * 3 + 3]
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        # Lights can't show black, and brightness is controlled separately from color.
        if v < MIN_VALUE:
            continue
        s = 0.0 if s < MIN_SATURATION else min(1.0, max(MIN_BOOSTED_SATURATION, s * 1.5))
        hue = h * 360
        if any(
            (s == 0.0) == (ks == 0.0)
            and (s == 0.0 or min(abs(hue - kh), 360 - abs(hue - kh)) < MIN_HUE_GAP)
            for kh, ks in kept
        ):
            continue
        kept.append((hue, s))
        palette.append([round(c * 255) for c in colorsys.hsv_to_rgb(h, s, 1.0)])

    return palette


class MediaArtTracker:
    """Keeps a palette from the artwork of the watched player that most recently started playing.

    An empty player list watches every media player.
    """

    def __init__(
        self, hass: HomeAssistant, players: list[str], on_update: Callable[[], None]
    ) -> None:
        """Initialize the tracker."""
        self.hass = hass
        self.players = players
        self.palette: list[list[int]] = []
        self.source: str | None = None
        self._on_update = on_update
        self._art: str | None = None
        self._latest_player: str | None = None
        self._unsub: Callable[[], None] | None = None
        self._refresh_task: asyncio.Task[None] | None = None

    @property
    def active(self) -> bool:
        """Return True while watching players."""
        return self._unsub is not None

    @callback
    def async_start(self) -> None:
        """Start watching players and pick up whatever is already playing."""
        if self._unsub:
            return
        self._unsub = async_track_state_change_filtered(
            self.hass,
            TrackStates(False, set(self.players), set() if self.players else {MEDIA_PLAYER_DOMAIN}),
            self._handle_state_change,
        ).async_remove
        self._schedule_refresh()

    @callback
    def async_stop(self) -> None:
        """Stop watching players, keeping the last palette."""
        if self._unsub:
            self._unsub()
            self._unsub = None
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Note players that start playing new artwork."""
        new = event.data["new_state"]
        if new is None or new.state != MediaPlayerState.PLAYING:
            return
        art = new.attributes.get(ATTR_ENTITY_PICTURE)
        if not art:
            return
        old = event.data["old_state"]
        if (
            old is not None
            and old.state == MediaPlayerState.PLAYING
            and old.attributes.get(ATTR_ENTITY_PICTURE) == art
        ):
            return

        self._latest_player = new.entity_id
        self._schedule_refresh()

    @callback
    def _schedule_refresh(self) -> None:
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
        self._refresh_task = self.hass.async_create_background_task(
            self._async_refresh(), "color_fx_media_art"
        )

    def _pick_player(self) -> State | None:
        """Prefer the player that last started playing, else the most recently changed one."""
        states = (
            [st for eid in self.players if (st := self.hass.states.get(eid))]
            if self.players
            else self.hass.states.async_all(MEDIA_PLAYER_DOMAIN)
        )
        playing = [
            st
            for st in states
            if st.state == MediaPlayerState.PLAYING and st.attributes.get(ATTR_ENTITY_PICTURE)
        ]
        for st in playing:
            if st.entity_id == self._latest_player:
                return st
        return max(playing, key=lambda st: st.last_changed, default=None)

    async def _async_refresh(self) -> None:
        state = self._pick_player()
        if state is None:
            return
        art = state.attributes[ATTR_ENTITY_PICTURE]
        if art == self._art:
            return

        component = self.hass.data.get(MEDIA_PLAYER_COMPONENT)
        entity = component.get_entity(state.entity_id) if component else None
        if entity is None:
            return

        try:
            image, _ = await entity.async_get_media_image()
            if not image:
                return
            palette = await self.hass.async_add_executor_job(extract_palette, image)
        except Exception as err:
            _LOGGER.warning("Failed extracting artwork colors from %s: %s", state.entity_id, err)
            return
        if not palette:
            return

        self.palette = palette
        self.source = state.entity_id
        self._art = art
        _LOGGER.debug("Media Art palette from %s: %s", state.entity_id, palette)
        self._on_update()
