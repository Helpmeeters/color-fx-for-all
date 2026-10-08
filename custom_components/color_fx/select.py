"""Select platform for choosing Color FX sequences."""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ColorFXCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Color FX select entity from a config entry."""
    coordinator: ColorFXCoordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    async_add_entities([ColorFXSequenceSelect(coordinator, entry)])


class ColorFXSequenceSelect(SelectEntity):
    """Select entity for choosing the active Color FX sequence."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:palette-swatch"

    def __init__(self, coordinator: ColorFXCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sequence"
        self._attr_name = "Sequence"
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
