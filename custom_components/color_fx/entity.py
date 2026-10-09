"""Base entity for Color FX for All."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import ColorFXCoordinator


class ColorFXEntity(Entity):
    """An entity of a Color FX Hub, updated by its coordinator."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: ColorFXCoordinator,
        entry: ConfigEntry,
        platform: str,
        key: str,
        object_suffix: str = "",
    ) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )
        self.entity_id = f"{platform}.{DOMAIN}_{slugify(entry.title)}{object_suffix}"

    async def async_added_to_hass(self) -> None:
        """Follow coordinator updates."""
        self.async_on_remove(self.coordinator.register_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        """Update entity state from coordinator."""
        self.async_write_ha_state()
