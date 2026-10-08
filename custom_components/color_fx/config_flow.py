"""Config flow for Color FX for All."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    BUILTIN_SEQUENCES,
    CONF_INTERVAL,
    CONF_RESTORE_STATE,
    CONF_SEQUENCE,
    CONF_TARGET_LIGHT,
    CONF_TRANSITION,
    DEFAULT_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_RESTORE_STATE,
    DEFAULT_SEQUENCE,
    DEFAULT_TRANSITION,
    DOMAIN,
)


class ColorFXConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Color FX."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            title = user_input.get("name", DEFAULT_NAME)
            return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required("name", default=DEFAULT_NAME): selector.TextSelector(),
                vol.Required(CONF_TARGET_LIGHT): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light")
                ),
                vol.Required(
                    CONF_SEQUENCE, default=DEFAULT_SEQUENCE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(BUILTIN_SEQUENCES.keys()),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_INTERVAL, default=DEFAULT_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0, max=60.0, step=0.5, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_TRANSITION, default=DEFAULT_TRANSITION
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5, max=30.0, step=0.5, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_RESTORE_STATE, default=DEFAULT_RESTORE_STATE
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get options flow handler."""
        return ColorFXOptionsFlow(config_entry)


class ColorFXOptionsFlow(OptionsFlow):
    """Handle options flow for Color FX."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options or {}
        data = self.config_entry.data

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SEQUENCE,
                    default=options.get(CONF_SEQUENCE, data.get(CONF_SEQUENCE, DEFAULT_SEQUENCE)),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(BUILTIN_SEQUENCES.keys()),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_INTERVAL,
                    default=options.get(CONF_INTERVAL, data.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0, max=60.0, step=0.5, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_TRANSITION,
                    default=options.get(CONF_TRANSITION, data.get(CONF_TRANSITION, DEFAULT_TRANSITION)),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5, max=30.0, step=0.5, unit_of_measurement="s"
                    )
                ),
                vol.Optional(
                    CONF_RESTORE_STATE,
                    default=options.get(
                        CONF_RESTORE_STATE, data.get(CONF_RESTORE_STATE, DEFAULT_RESTORE_STATE)
                    ),
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
