"""Config flow for Steuertage."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.selector import NumberSelectorMode, SelectSelectorMode

from .const import (
    CONF_DEVICE_TRACKER,
    CONF_HA_USER_ID,
    CONF_HOME_OFFICE_ENABLED,
    CONF_HOME_ZONE,
    CONF_OFFICE_ZONE,
    CONF_PERSON,
    CONF_THRESHOLD_MINUTES,
    CONF_WORK_CALENDAR,
    CONF_WORK_SIGNAL,
    DEFAULT_THRESHOLD_MINUTES,
    DOMAIN,
)
from .logic import find_person_configuration_conflicts


def _schema(
    defaults: dict[str, Any] | None = None,
    *,
    include_person: bool = True,
    include_legacy_signal: bool = False,
    user_options: list[dict[str, str]] | None = None,
) -> vol.Schema:
    """Build setup or options form with optional Homeoffice recognition."""
    defaults = defaults or {}
    fields: dict[Any, Any] = {}

    if include_person:
        fields[vol.Required(CONF_PERSON)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="person")
        )

    fields[vol.Optional(
        CONF_HOME_OFFICE_ENABLED,
        default=bool(defaults.get(CONF_HOME_OFFICE_ENABLED, True)),
    )] = selector.BooleanSelector()

    fields[vol.Optional(
        CONF_HOME_ZONE,
        default=defaults.get(CONF_HOME_ZONE) or "zone.home",
    )] = selector.EntitySelector(selector.EntitySelectorConfig(domain="zone"))

    fields[vol.Optional(
        CONF_DEVICE_TRACKER,
        default=defaults.get(CONF_DEVICE_TRACKER) or "",
    )] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="device_tracker")
    )

    if include_legacy_signal:
        fields[vol.Optional(
            CONF_WORK_SIGNAL,
            default=defaults.get(CONF_WORK_SIGNAL) or "",
        )] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor")
        )

    fields[vol.Optional(
        CONF_OFFICE_ZONE,
        default=defaults.get(CONF_OFFICE_ZONE) or "",
    )] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="zone")
    )

    fields[vol.Optional(
        CONF_WORK_CALENDAR,
        default=defaults.get(CONF_WORK_CALENDAR) or "",
    )] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="calendar")
    )

    fields[vol.Optional(
        CONF_THRESHOLD_MINUTES,
        default=int(defaults.get(CONF_THRESHOLD_MINUTES, DEFAULT_THRESHOLD_MINUTES)),
    )] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1,
            max=1440,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    )

    options = [
        {"value": "", "label": "Keinem HA-Benutzer zugeordnet"},
        *(user_options or []),
    ]
    fields[vol.Optional(
        CONF_HA_USER_ID,
        default=defaults.get(CONF_HA_USER_ID) or "",
    )] = selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )
    return vol.Schema(fields)


async def _user_options(hass) -> list[dict[str, str]]:
    """Return Home Assistant users for the optional default-calendar mapping."""
    users = await hass.auth.async_get_users()
    return [
        {"value": str(user.id), "label": user.name or str(user.id)}
        for user in users
        if getattr(user, "is_active", True)
    ]


def _configuration(entry) -> dict[str, Any]:
    """Return one entry's effective configuration."""
    return {**entry.data, **entry.options}


def _homeoffice_errors(values: dict[str, Any]) -> dict[str, str]:
    """Require Home-zone and a source only when Homeoffice tracking is enabled."""
    if not values.get(CONF_HOME_OFFICE_ENABLED, True):
        return {}
    errors: dict[str, str] = {}
    if not values.get(CONF_HOME_ZONE):
        errors[CONF_HOME_ZONE] = "home_zone_required"
    if not (values.get(CONF_DEVICE_TRACKER) or values.get(CONF_WORK_SIGNAL)):
        errors[CONF_DEVICE_TRACKER] = "homeoffice_device_required"
    return errors


def _find_conflicts(
    hass,
    values: dict[str, Any],
    *,
    exclude_entry_id: str | None = None,
) -> set[str]:
    """Prevent ambiguous person, tracker, and default-user assignments."""
    configurations = [
        {"entry_id": entry.entry_id, "values": _configuration(entry)}
        for entry in hass.config_entries.async_entries(DOMAIN)
    ]
    return find_person_configuration_conflicts(
        values,
        configurations,
        exclude_entry_id=exclude_entry_id,
    )


def _normalize_values(values: dict[str, Any]) -> dict[str, Any]:
    """Normalize optional entity and user selections."""
    for key in (
        CONF_DEVICE_TRACKER,
        CONF_WORK_SIGNAL,
        CONF_OFFICE_ZONE,
        CONF_WORK_CALENDAR,
        CONF_HA_USER_ID,
    ):
        values[key] = values.get(key) or None
    values[CONF_THRESHOLD_MINUTES] = int(
        values.get(CONF_THRESHOLD_MINUTES, DEFAULT_THRESHOLD_MINUTES)
    )
    values[CONF_HOME_OFFICE_ENABLED] = bool(
        values.get(CONF_HOME_OFFICE_ENABLED, True)
    )
    return values


class WorklogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up one independently tracked person."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Set up the integration."""
        errors: dict[str, str] = {}
        users = await _user_options(self.hass)

        if user_input is not None:
            values = _normalize_values(dict(user_input))
            errors = _homeoffice_errors(values)
            if not errors:
                values[CONF_HA_USER_ID] = values.get(CONF_HA_USER_ID) or None
                self._person_entity = values[CONF_PERSON]
                await self.async_set_unique_id(self._person_entity)
                self._abort_if_unique_id_configured()
                errors = {key: key for key in _find_conflicts(self.hass, values)}

            if not errors:
                state = self.hass.states.get(self._person_entity)
                title = (
                    state.attributes.get("friendly_name", self._person_entity)
                    if state
                    else self._person_entity
                )
                return self.async_create_entry(
                    title=f"Steuertage – {title}",
                    data=values,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_options=users),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return WorklogOptionsFlow()


class WorklogOptionsFlow(config_entries.OptionsFlow):
    """Update person, source and threshold settings."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Update an existing person setup."""
        current = _configuration(self.config_entry)
        users = await _user_options(self.hass)
        errors: dict[str, str] = {}

        if user_input is not None:
            values = _normalize_values(dict(user_input))
            errors = _homeoffice_errors(values)
            if not errors:
                conflicts = _find_conflicts(
                    self.hass,
                    {**current, **values, CONF_PERSON: current.get(CONF_PERSON)},
                    exclude_entry_id=self.config_entry.entry_id,
                )
                errors = {key: key for key in conflicts}
            if not errors:
                return self.async_create_entry(title="", data=values)

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(
                current,
                include_person=False,
                include_legacy_signal=bool(current.get(CONF_WORK_SIGNAL)),
                user_options=users,
            ),
            errors=errors,
        )
