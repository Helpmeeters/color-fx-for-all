"""Config flow for Color FX for All."""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .const import (
    BUILTIN_SEQUENCES,
    CONF_INTERVAL,
    CONF_MEDIA_PLAYERS,
    CONF_RESTORE_STATE,
    CONF_ROTATE,
    CONF_SEQUENCE,
    CONF_TARGET_LIGHT,
    CONF_TRANSITION,
    DEFAULT_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_RESTORE_STATE,
    DEFAULT_ROTATE,
    DEFAULT_SEQUENCE,
    DEFAULT_TRANSITION,
    DOMAIN,
    MEDIA_ART_SEQUENCE,
    RENAMED_SEQUENCES,
)

LIGHTS_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="light", multiple=True)
)
SEQUENCE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=[*BUILTIN_SEQUENCES, MEDIA_ART_SEQUENCE],
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)
MEDIA_PLAYERS_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="media_player", multiple=True)
)


ROTATION_SECTION = "rotation"


def _rotation_section(current: Mapping[str, Any]) -> dict[Any, Any]:
    """Return the collapsible section for the settings that only matter while colors rotate."""
    schema = vol.Schema(
        {
            vol.Required(
                CONF_INTERVAL, default=current.get(CONF_INTERVAL, DEFAULT_INTERVAL)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1.0, max=60.0, step=0.5, unit_of_measurement="s")
            ),
            vol.Required(
                CONF_TRANSITION, default=current.get(CONF_TRANSITION, DEFAULT_TRANSITION)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.5, max=30.0, step=0.5, unit_of_measurement="s")
            ),
        }
    )
    collapsed = not current.get(CONF_ROTATE, DEFAULT_ROTATE)
    return {vol.Required(ROTATION_SECTION): section(schema, {"collapsed": collapsed})}


def _flatten(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Lift the rotation section's fields to the top level, where the entry stores them."""
    data = dict(user_input)
    data.update(data.pop(ROTATION_SECTION, {}))
    return data


class ColorFXConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Color FX."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            data = _flatten(user_input)
            return self.async_create_entry(title=data.get("name", DEFAULT_NAME), data=data)

        schema = vol.Schema(
            {
                vol.Required("name", default=DEFAULT_NAME): selector.TextSelector(),
                vol.Optional(CONF_MEDIA_PLAYERS, default=[]): MEDIA_PLAYERS_SELECTOR,
                vol.Required(CONF_TARGET_LIGHT): LIGHTS_SELECTOR,
                vol.Required(CONF_SEQUENCE, default=DEFAULT_SEQUENCE): SEQUENCE_SELECTOR,
                vol.Optional(
                    CONF_RESTORE_STATE, default=DEFAULT_RESTORE_STATE
                ): selector.BooleanSelector(),
                vol.Required(CONF_ROTATE, default=DEFAULT_ROTATE): selector.BooleanSelector(),
                **_rotation_section({}),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get options flow handler."""
        return ColorFXOptionsFlow()


class ColorFXOptionsFlow(OptionsFlow):
    """Handle options flow for Color FX."""

    @property
    def _current(self) -> dict[str, Any]:
        return {**self.config_entry.data, **(self.config_entry.options or {})}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        current = self._current
        if user_input is not None:
            user_input = dict(user_input)
            name = user_input.pop("name").strip()
            if name and name != self.config_entry.title:
                self.hass.config_entries.async_update_entry(self.config_entry, title=name)
            return self.async_create_entry(
                title="", data={CONF_MEDIA_PLAYERS: [], **_flatten(user_input)}
            )

        targets = current.get(CONF_TARGET_LIGHT, [])
        sequence = current.get(CONF_SEQUENCE, DEFAULT_SEQUENCE)
        schema = vol.Schema(
            {
                vol.Required("name", default=self.config_entry.title): selector.TextSelector(),
                vol.Optional(
                    CONF_MEDIA_PLAYERS,
                    description={"suggested_value": current.get(CONF_MEDIA_PLAYERS, [])},
                ): MEDIA_PLAYERS_SELECTOR,
                vol.Required(
                    CONF_TARGET_LIGHT,
                    default=[targets] if isinstance(targets, str) else targets,
                ): LIGHTS_SELECTOR,
                vol.Required(
                    CONF_SEQUENCE, default=RENAMED_SEQUENCES.get(sequence, sequence)
                ): SEQUENCE_SELECTOR,
                vol.Optional(
                    CONF_RESTORE_STATE,
                    default=current.get(CONF_RESTORE_STATE, DEFAULT_RESTORE_STATE),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ROTATE, default=current.get(CONF_ROTATE, DEFAULT_ROTATE)
                ): selector.BooleanSelector(),
                **_rotation_section(current),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
