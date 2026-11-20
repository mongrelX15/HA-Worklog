"""Config flow for HA Work-Log."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.selector import SelectSelectorMode

from .const import (
    CONF_DEVICE_TRACKER,
    CONF_HA_USER_ID,
    CONF_HOME_ZONE,
    CONF_OFFICE_ZONE,
    CONF_PERSON,
    CONF_WORK_SIGNAL,
    DOMAIN,
)


def _schema(
    defaults: dict[str, Any] | None = None,
    *,
    include_person: bool = True,
    include_legacy_signal: bool = False,
    user_options: list[dict[str, str]] | None = None,
) -> vol.Schema:
    """Build setup or options form while keeping Beta 7 entries editable."""
    defaults = defaults or {}
    fields: dict[Any, Any] = {}

    if include_person:
        fields[vol.Required(CONF_PERSON)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="person")
        )

    fields[vol.Required(
        CONF_HOME_ZONE,
        default=defaults.get(CONF_HOME_ZONE) or "zone.home",
    )] = selector.EntitySelector(selector.EntitySelectorConfig(domain="zone"))

    tracker_key = (
        vol.Required(CONF_DEVICE_TRACKER)
        if include_person
        else vol.Optional(CONF_DEVICE_TRACKER, default=defaults.get(CONF_DEVICE_TRACKER) or "")
    )
    fields[tracker_key] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="device_tracker")
    )

    if include_legacy_signal:
        fields[vol.Optional(CONF_WORK_SIGNAL)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor")
        )

    fields[vol.Optional(CONF_OFFICE_ZONE)] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="zone")
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


def _find_conflicts(
    hass,
    values: dict[str, Any],
    *,
    exclude_entry_id: str | None = None,
) -> set[str]:
    """Prevent ambiguous person, tracker, and default-user assignments."""
    errors: set[str] = set()
    person = values.get(CONF_PERSON)
    tracker = values.get(CONF_DEVICE_TRACKER)
    user_id = values.get(CONF_HA_USER_ID) or None

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == exclude_entry_id:
            continue
        current = _configuration(entry)
        if person and current.get(CONF_PERSON) == person:
            errors.add("already_configured")
        if tracker and current.get(CONF_DEVICE_TRACKER) == tracker:
            errors.add("device_already_configured")
        if user_id and current.get(CONF_HA_USER_ID) == user_id:
            errors.add("user_already_configured")
    return errors


class WorklogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up one independently tracked person."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Set up the integration."""
        errors: dict[str, str] = {}
        users = await _user_options(self.hass)

        if user_input is not None:
            values = dict(user_input)
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
                    title=f"HA Work-Log – {title}",
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
    """Update sensors and user mapping without changing the stored person key."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Update an existing person setup."""
        current = _configuration(self.config_entry)
        users = await _user_options(self.hass)
        errors: dict[str, str] = {}

        if user_input is not None:
            values = dict(user_input)
            values[CONF_HA_USER_ID] = values.get(CONF_HA_USER_ID) or None
            # Older entries keep their existing work_signal until a device tracker
            # has been configured. It is not used once the new tracker is selected.
            conflicts = _find_conflicts(
                self.hass,
                {
                    **current,
                    **values,
                    CONF_PERSON: current.get(CONF_PERSON),
                },
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
