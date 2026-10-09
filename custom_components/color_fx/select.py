"""Select platform for choosing Color FX sequences."""

from homeassistant.components.select import DOMAIN as SELECT_DOMAIN, SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ColorFXCoordinator
from .entity import ColorFXEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Color FX select entity from a config entry."""
    coordinator: ColorFXCoordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    async_add_entities([ColorFXSequenceSelect(coordinator, entry)])


class ColorFXSequenceSelect(ColorFXEntity, SelectEntity):
    """Select entity for choosing the active Color FX sequence."""

    _attr_icon = "mdi:palette-swatch"
    _attr_name = "Sequence"

    def __init__(self, coordinator: ColorFXCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entry, SELECT_DOMAIN, "sequence", "_sequence")

    @property
    def options(self) -> list[str]:
        """Return the list of available sequence names."""
        return self.coordinator.available_sequences

    @property
    def current_option(self) -> str | None:
        """Return the current active sequence."""
        return self.coordinator.current_sequence

    async def async_select_option(self, option: str) -> None:
        """Change the active sequence."""
        await self.coordinator.async_set_sequence(option)
