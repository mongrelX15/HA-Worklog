"""Config flow for HA Work-Log."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import CONF_OFFICE_ZONE, CONF_PERSON, CONF_WORK_SIGNAL, DOMAIN


def _schema(defaults: dict | None = None) -> vol.Schema:
    """Create the setup and options form."""
    defaults = defaults or {}
    fields = {}
    for key, domain in ((CONF_PERSON, "person"), (CONF_WORK_SIGNAL, "binary_sensor")):
        field = selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))
        fields[vol.Required(key, default=defaults[key]) if key in defaults else vol.Required(key)] = field

    zone_field = selector.EntitySelector(selector.EntitySelectorConfig(domain="zone"))
    if defaults.get(CONF_OFFICE_ZONE):
        fields[vol.Optional(CONF_OFFICE_ZONE, default=defaults[CONF_OFFICE_ZONE])] = zone_field
    else:
        fields[vol.Optional(CONF_OFFICE_ZONE)] = zone_field
    return vol.Schema(fields)


class WorklogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up one work log."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Set up the integration."""
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_PERSON])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="HA Work-Log", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return WorklogOptionsFlow()


class WorklogOptionsFlow(config_entries.OptionsFlow):
    """Allow changing the person and tracking sensors after setup."""

    async def async_step_init(self, user_input: dict | None = None):
        """Update the integration configuration."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(current))
