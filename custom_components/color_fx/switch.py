"""Switch platform for Color FX for All."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_AVAILABLE_SEQUENCES,
    ATTR_CURRENT_SEQUENCE,
    ATTR_TARGET_LIGHT,
    DOMAIN,
)
from .coordinator import ColorFXCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Color FX switch entity from a config entry."""
    coordinator: ColorFXCoordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    async_add_entities([ColorFXSwitch(coordinator, entry)])


class ColorFXSwitch(SwitchEntity):
    """Switch representation of a Color FX Zone."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:shimmer"

    def __init__(self, coordinator: ColorFXCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_switch"
        self._attr_name = "Color FX"
        self._unregister_listener = None

    async def async_added_to_hass(self) -> None:
        """Register coordinator update listener."""
        self._unregister_listener = self.coordinator.register_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister coordinator listener."""
        if self._unregister_listener:
            self._unregister_listener()

    @callback
    def _handle_update(self) -> None:
        """Update entity state from coordinator."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if the effect loop is currently active."""
        return self.coordinator.is_running

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return dynamic attributes."""
        return {
            ATTR_CURRENT_SEQUENCE: self.coordinator.current_sequence,
            ATTR_TARGET_LIGHT: self.coordinator.target_light,
            ATTR_AVAILABLE_SEQUENCES: self.coordinator.available_sequences,
            "interval": self.coordinator.interval,
            "transition": self.coordinator.transition,
            "restore_state": self.coordinator.restore_state,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the color sequence animation."""
        await self.coordinator.async_start()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the color sequence animation and restore original lighting."""
        await self.coordinator.async_stop()
