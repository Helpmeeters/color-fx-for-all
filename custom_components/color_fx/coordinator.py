"""Coordinator for driving Color FX animations on light targets."""

import asyncio
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ATTR_XY_COLOR,
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError

from .const import (
    BUILTIN_SEQUENCES,
    DEFAULT_INTERVAL,
    DEFAULT_SEQUENCE,
    DEFAULT_TRANSITION,
    DOMAIN,
    MEDIA_ART_SEQUENCE,
    RENAMED_SEQUENCES,
)
from .media_art import MediaArtTracker

_LOGGER = logging.getLogger(__name__)

COLOR_MODES = {"xy", "rgb", "hs", "rgbw", "rgbww", "color_temp"}


class ColorFXCoordinator:
    """Controls the background sequence loop for a single Color FX hub."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        target_lights: list[str],
        initial_sequence: str = DEFAULT_SEQUENCE,
        interval: float = DEFAULT_INTERVAL,
        transition: float = DEFAULT_TRANSITION,
        restore_state: bool = True,
        media_players: list[str] | None = None,
        rotate: bool = True,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry_id = entry_id
        self.name = name
        self.target_lights = target_lights
        initial_sequence = RENAMED_SEQUENCES.get(initial_sequence, initial_sequence)
        self.current_sequence = (
            initial_sequence if initial_sequence in self.available_sequences else DEFAULT_SEQUENCE
        )
        self.interval = float(interval)
        self.transition = float(transition)
        self.restore_state = restore_state
        self.rotate = rotate

        self.is_running = False
        self._task: asyncio.Task[None] | None = None
        self._current_step = 0
        self._saved_states: dict[str, dict[str, Any]] = {}
        self._listeners: list[callback] = []
        self._media_art = MediaArtTracker(hass, media_players or [], self._handle_media_art)

    @property
    def media_players(self) -> list[str]:
        """Return the media players Media Art follows; empty means all of them."""
        return self._media_art.players

    @property
    def available_sequences(self) -> list[str]:
        """Return list of available sequence names (builtins + Media Art + custom)."""
        custom = self.hass.data.get(DOMAIN, {}).get("custom_sequences", {})
        combined = [*BUILTIN_SEQUENCES, MEDIA_ART_SEQUENCE]
        for name in custom:
            if name not in combined:
                combined.append(name)
        return combined

    def get_palette(self, sequence_name: str | None = None) -> list[list[int]]:
        """Return the RGB colors the hub shows; only the first, most dominant, without rotation."""
        name = sequence_name or self.current_sequence
        custom = self.hass.data.get(DOMAIN, {}).get("custom_sequences", {})
        if name in custom:
            palette = custom[name]
        elif name == MEDIA_ART_SEQUENCE:
            palette = self._media_art.palette
        else:
            palette = BUILTIN_SEQUENCES.get(name, BUILTIN_SEQUENCES[DEFAULT_SEQUENCE])
        return palette if self.rotate else palette[:1]

    @property
    def palette_source(self) -> str | None:
        """Return the media player supplying the palette, when following Media Art."""
        if self.current_sequence != MEDIA_ART_SEQUENCE:
            return None
        return self._media_art.source

    def register_listener(self, update_callback: callback) -> callback:
        """Register a callback for state changes."""
        self._listeners.append(update_callback)

        def unregister() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return unregister

    def _notify_listeners(self) -> None:
        """Sync the Media Art subscription and notify all registered entity listeners."""
        self.sync_media_art()
        for cb in self._listeners:
            try:
                cb()
            except Exception as err:
                _LOGGER.error("Error in ColorFX listener: %s", err)

    def sync_media_art(self, enabled: bool = True) -> None:
        """Follow media artwork whenever Media Art is selected, running or not."""
        wants = enabled and self.current_sequence == MEDIA_ART_SEQUENCE
        if wants and not self._media_art.active:
            self._media_art.async_start()
        elif not wants and self._media_art.active:
            self._media_art.async_stop()

    @callback
    def _handle_media_art(self) -> None:
        """Publish the new artwork palette and restart the animation from its first color."""
        self._notify_listeners()
        if not self.is_running:
            return
        self._current_step = 0
        self.hass.async_create_task(self._apply_step())

    def _resolve_target_lights(self) -> list[str]:
        """Resolve member lights and filter to color-capable entities."""
        candidates: list[str] = []
        for target in self.target_lights:
            state = self.hass.states.get(target)
            if not state:
                continue

            # If it's a light group, expand member entities
            member_ids = state.attributes.get(ATTR_ENTITY_ID)
            candidates.extend(member_ids if isinstance(member_ids, list) else [target])

        color_lights: list[str] = []
        for eid in dict.fromkeys(candidates):
            st = self.hass.states.get(eid)
            if not st:
                continue
            modes = st.attributes.get("supported_color_modes") or []
            if any(m in COLOR_MODES for m in modes):
                color_lights.append(eid)

        return color_lights

    def _snapshot_lights(self, entity_ids: list[str]) -> None:
        """Snapshot current state and color of bulbs before effect starts."""
        self._saved_states.clear()
        for eid in entity_ids:
            st = self.hass.states.get(eid)
            if not st:
                continue
            attrs = st.attributes
            snap: dict[str, Any] = {"is_on": st.state == STATE_ON}
            if st.state == STATE_ON:
                if ATTR_BRIGHTNESS in attrs:
                    snap[ATTR_BRIGHTNESS] = attrs[ATTR_BRIGHTNESS]
                if ATTR_RGB_COLOR in attrs:
                    snap[ATTR_RGB_COLOR] = attrs[ATTR_RGB_COLOR]
                elif ATTR_COLOR_TEMP_KELVIN in attrs:
                    snap[ATTR_COLOR_TEMP_KELVIN] = attrs[ATTR_COLOR_TEMP_KELVIN]
                elif ATTR_HS_COLOR in attrs:
                    snap[ATTR_HS_COLOR] = attrs[ATTR_HS_COLOR]
                elif ATTR_XY_COLOR in attrs:
                    snap[ATTR_XY_COLOR] = attrs[ATTR_XY_COLOR]
            self._saved_states[eid] = snap

    async def _restore_lights(self) -> None:
        """Restore previous state and colors of bulbs."""
        if not self.restore_state or not self._saved_states:
            return

        for eid, snap in self._saved_states.items():
            try:
                if not snap.get("is_on"):
                    await self.hass.services.async_call(
                        LIGHT_DOMAIN,
                        SERVICE_TURN_OFF,
                        {ATTR_ENTITY_ID: eid, ATTR_TRANSITION: 1.0},
                        blocking=False,
                    )
                else:
                    restore_data: dict[str, Any] = {
                        ATTR_ENTITY_ID: eid,
                        ATTR_TRANSITION: 1.0,
                    }
                    for key in (
                        ATTR_BRIGHTNESS,
                        ATTR_RGB_COLOR,
                        ATTR_COLOR_TEMP_KELVIN,
                        ATTR_HS_COLOR,
                        ATTR_XY_COLOR,
                    ):
                        if key in snap:
                            restore_data[key] = snap[key]
                    await self.hass.services.async_call(
                        LIGHT_DOMAIN,
                        SERVICE_TURN_ON,
                        restore_data,
                        blocking=False,
                    )
            except Exception as err:
                _LOGGER.warning("Failed restoring state for %s: %s", eid, err)

    async def async_start(self, sequence: str | None = None) -> None:
        """Start the Color FX animation loop."""
        sequence = RENAMED_SEQUENCES.get(sequence, sequence)
        if sequence and sequence in self.available_sequences:
            self.current_sequence = sequence

        if self.is_running:
            self._notify_listeners()
            return

        target_bulbs = self._resolve_target_lights()
        if not target_bulbs:
            _LOGGER.warning(
                "No color-capable lights found for targets %s", ", ".join(self.target_lights)
            )
            return

        self._snapshot_lights(target_bulbs)
        self.is_running = True
        self._current_step = 0
        self._task = self.hass.async_create_background_task(
            self._animation_loop(), f"color_fx_{self.entry_id}"
        )
        self._notify_listeners()
        _LOGGER.info("Color FX '%s' started with sequence '%s'", self.name, self.current_sequence)

    async def async_stop(self) -> None:
        """Stop the Color FX animation loop."""
        if not self.is_running:
            return

        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        await self._restore_lights()
        self._notify_listeners()
        _LOGGER.info("Color FX '%s' stopped", self.name)

    async def async_next_sequence(self) -> str:
        """Advance to the next available sequence."""
        seqs = self.available_sequences
        try:
            curr_idx = seqs.index(self.current_sequence)
            next_idx = (curr_idx + 1) % len(seqs)
        except ValueError:
            next_idx = 0

        self.current_sequence = seqs[next_idx]
        self._current_step = 0
        self._notify_listeners()

        # If currently running, apply immediately
        if self.is_running:
            await self._apply_step()

        _LOGGER.info("Color FX '%s' switched to sequence '%s'", self.name, self.current_sequence)
        return self.current_sequence

    async def async_set_sequence(self, sequence: str) -> None:
        """Set the active sequence."""
        sequence = RENAMED_SEQUENCES.get(sequence, sequence)
        if sequence not in self.available_sequences:
            raise ServiceValidationError(f"Unknown sequence: {sequence}")

        self.current_sequence = sequence
        self._current_step = 0
        self._notify_listeners()

        if self.is_running:
            await self._apply_step()

    async def _apply_step(self) -> None:
        """Apply current animation step colors to the targeted lights."""
        target_bulbs = self._resolve_target_lights()
        if not target_bulbs:
            return

        palette = self.get_palette()
        if not palette:
            return

        # If single bulb or all synced:
        color = palette[self._current_step % len(palette)]

        try:
            await self.hass.services.async_call(
                LIGHT_DOMAIN,
                SERVICE_TURN_ON,
                {
                    ATTR_ENTITY_ID: target_bulbs,
                    ATTR_RGB_COLOR: color,
                    ATTR_TRANSITION: (
                        min(self.transition, self.interval) if self.rotate else self.transition
                    ),
                },
                blocking=False,
            )
        except Exception as err:
            _LOGGER.error("Failed applying Color FX step: %s", err)

    async def _animation_loop(self) -> None:
        """Background loop stepping through the sequence palette."""
        try:
            while self.is_running:
                await self._apply_step()
                if not self.rotate:
                    return
                self._current_step += 1
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            pass
        except Exception:
            _LOGGER.exception("Unexpected error in Color FX loop")
            self.is_running = False
            self._notify_listeners()
