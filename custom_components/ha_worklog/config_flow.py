"""Config flow for HA Work-Log."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_MINIMUM_HOURS,
    CONF_OFFICE_ZONE,
    CONF_PERSON,
    CONF_WORK_SIGNAL,
    DEFAULT_MINIMUM_HOURS,
    DOMAIN,
)

def _schema(defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    fields = {}
    for key, domain in ((CONF_PERSON, "person"), (CONF_WORK_SIGNAL, "binary_sensor")):
        field = selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))
        fields[vol.Required(key, default=defaults[key]) if key in defaults else vol.Required(key)] = field

    zone_field = selector.EntitySelector(selector.EntitySelectorConfig(domain="zone"))
    fields[vol.Optional(CONF_OFFICE_ZONE, default=defaults[CONF_OFFICE_ZONE]) if defaults.get(CONF_OFFICE_ZONE) else vol.Optional(CONF_OFFICE_ZONE)] = zone_field

    min_hours = defaults.get(CONF_MINIMUM_HOURS, DEFAULT_MINIMUM_HOURS)
    fields[vol.Required(CONF_MINIMUM_HOURS, default=min_hours)] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0.5, max=12, step=0.5, unit_of_measurement="h",
            mode=selector.NumberSelectorMode.BOX
        )
    )
    return vol.Schema(fields)

class WorklogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up one work log."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_PERSON])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="HA Work-Log", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    def async_get_options_flow(config_entry):
        return WorklogOptionsFlow(config_entry)

class WorklogOptionsFlow(config_entries.OptionsFlow):
    """Allow changing tracking options after setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(current))
