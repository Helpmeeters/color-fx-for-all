"""Switch platform for Color FX for All."""

from typing import Any

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_AVAILABLE_SEQUENCES,
    ATTR_CURRENT_SEQUENCE,
    ATTR_PALETTE,
    ATTR_PALETTE_SOURCE,
    ATTR_TARGET_LIGHT,
    DOMAIN,
)
from .coordinator import ColorFXCoordinator
from .entity import ColorFXEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Color FX switch entity from a config entry."""
    coordinator: ColorFXCoordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    async_add_entities([ColorFXSwitch(coordinator, entry)])


class ColorFXSwitch(ColorFXEntity, SwitchEntity):
    """Switch representation of a Color FX Hub."""

    _attr_icon = "mdi:shimmer"
    _attr_name = "Color FX"

    def __init__(self, coordinator: ColorFXCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, SWITCH_DOMAIN, "switch")

    @property
    def is_on(self) -> bool:
        """Return True if the effect loop is currently active."""
        return self.coordinator.is_running

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return dynamic attributes."""
        return {
            ATTR_CURRENT_SEQUENCE: self.coordinator.current_sequence,
            ATTR_TARGET_LIGHT: self.coordinator.target_lights,
            ATTR_AVAILABLE_SEQUENCES: self.coordinator.available_sequences,
            ATTR_PALETTE: [
                "#{:02x}{:02x}{:02x}".format(*rgb) for rgb in self.coordinator.get_palette()
            ],
            ATTR_PALETTE_SOURCE: self.coordinator.palette_source,
            "rotate": self.coordinator.rotate,
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
