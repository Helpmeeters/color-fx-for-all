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

from .const import (
    BUILTIN_SEQUENCES,
    DEFAULT_INTERVAL,
    DEFAULT_SEQUENCE,
    DEFAULT_TRANSITION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

COLOR_MODES = {"xy", "rgb", "hs", "rgbw", "rgbww", "color_temp"}


class ColorFXCoordinator:
    """Controls the background sequence loop for a single Color FX zone."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        target_light: str,
        initial_sequence: str = DEFAULT_SEQUENCE,
        interval: float = DEFAULT_INTERVAL,
        transition: float = DEFAULT_TRANSITION,
        restore_state: bool = True,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry_id = entry_id
        self.name = name
        self.target_light = target_light
        self.current_sequence = (
            initial_sequence if initial_sequence in self.available_sequences else DEFAULT_SEQUENCE
        )
        self.interval = float(interval)
        self.transition = float(transition)
        self.restore_state = restore_state

        self.is_running = False
        self._task: asyncio.Task[None] | None = None
        self._current_step = 0
        self._saved_states: dict[str, dict[str, Any]] = {}
        self._listeners: list[callback] = []

    @property
    def available_sequences(self) -> list[str]:
        """Return list of available sequence names (builtins + custom)."""
        custom = self.hass.data.get(DOMAIN, {}).get("custom_sequences", {})
        combined = list(BUILTIN_SEQUENCES.keys())
        for name in custom:
            if name not in combined:
                combined.append(name)
        return combined

    def get_palette(self, sequence_name: str | None = None) -> list[list[int]]:
        """Return the list of RGB colors for a sequence."""
        name = sequence_name or self.current_sequence
        custom = self.hass.data.get(DOMAIN, {}).get("custom_sequences", {})
        if name in custom:
            return custom[name]
        return BUILTIN_SEQUENCES.get(name, BUILTIN_SEQUENCES[DEFAULT_SEQUENCE])

    def register_listener(self, update_callback: callback) -> callback:
        """Register a callback for state changes."""
        self._listeners.append(update_callback)

        def unregister() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return unregister

    def _notify_listeners(self) -> None:
        """Notify all registered entity listeners."""
        for cb in self._listeners:
            try:
                cb()
            except Exception as err:
                _LOGGER.error("Error in ColorFX listener: %s", err)

    def _resolve_target_lights(self) -> list[str]:
        """Resolve member lights and filter to color-capable entities."""
        state = self.hass.states.get(self.target_light)
        if not state:
            return []

        # If it's a light group, expand member entities
        member_ids = state.attributes.get(ATTR_ENTITY_ID)
        candidates = member_ids if isinstance(member_ids, list) else [self.target_light]

        color_lights: list[str] = []
        for eid in candidates:
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
        if sequence and sequence in self.available_sequences:
            self.current_sequence = sequence

        if self.is_running:
            self._notify_listeners()
            return

        target_bulbs = self._resolve_target_lights()
        if not target_bulbs:
            _LOGGER.warning("No color-capable lights found for target %s", self.target_light)
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
        if sequence not in self.available_sequences:
            raise ValueError(f"Unknown sequence: {sequence}")

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
                    ATTR_TRANSITION: min(self.transition, self.interval),
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
                self._current_step += 1
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            pass
        except Exception as err:
            _LOGGER.exception("Unexpected error in Color FX loop: %s", err)
            self.is_running = False
            self._notify_listeners()
