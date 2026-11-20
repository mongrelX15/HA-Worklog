"""Config flow for Steuertage."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.selector import NumberSelectorMode

from .const import (
    CONF_DEVICE_TRACKER,
    CONF_HA_USER_ID,
    CONF_HOME_OFFICE_ENABLED,
    CONF_HOME_ZONE,
    CONF_OFFICE_ZONE,
    CONF_PERSON,
    CONF_THRESHOLD_HOURS,
    CONF_THRESHOLD_MINUTES,
    CONF_WORK_CALENDAR,
    CONF_WORK_CALENDAR_ENABLED,
    CONF_WORK_SIGNAL,
    DEFAULT_THRESHOLD_HOURS,
    DEFAULT_THRESHOLD_MINUTES,
    DOMAIN,
)
from .logic import find_person_configuration_conflicts


def _base_schema(
    defaults: dict[str, Any] | None = None, *, include_person: bool = True
) -> vol.Schema:
    """Build the first setup/options step with feature toggles."""
    defaults = defaults or {}
    fields: dict[Any, Any] = {}
    if include_person:
        fields[vol.Required(CONF_PERSON)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="person")
        )

    fields[vol.Required(
        CONF_HOME_OFFICE_ENABLED,
        default=bool(defaults.get(CONF_HOME_OFFICE_ENABLED, True)),
    )] = selector.BooleanSelector()

    fields[vol.Required(
        CONF_OFFICE_ZONE,
        default=defaults.get(CONF_OFFICE_ZONE) or "",
    )] = selector.EntitySelector(selector.EntitySelectorConfig(domain="zone"))

    calendar_enabled = defaults.get(
        CONF_WORK_CALENDAR_ENABLED,
        bool(defaults.get(CONF_WORK_CALENDAR)),
    )
    fields[vol.Required(
        CONF_WORK_CALENDAR_ENABLED,
        default=bool(calendar_enabled),
    )] = selector.BooleanSelector()

    legacy_minutes = defaults.get(CONF_THRESHOLD_MINUTES)
    default_hours = defaults.get(
        CONF_THRESHOLD_HOURS,
        float(legacy_minutes) / 60 if legacy_minutes is not None else DEFAULT_THRESHOLD_HOURS,
    )
    fields[vol.Required(
        CONF_THRESHOLD_HOURS,
        default=float(default_hours),
    )] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0.5,
            max=24,
            step=0.5,
            mode=NumberSelectorMode.BOX,
        )
    )
    return vol.Schema(fields)


def _homeoffice_schema(
    defaults: dict[str, Any] | None = None,
    *,
    include_legacy_signal: bool = False,
) -> vol.Schema:
    """Build the conditional Homeoffice source step."""
    defaults = defaults or {}
    fields: dict[Any, Any] = {
        vol.Required(
            CONF_HOME_ZONE,
            default=defaults.get(CONF_HOME_ZONE) or "zone.home",
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="zone")),
        (
            vol.Optional(
                CONF_DEVICE_TRACKER,
                default=defaults.get(CONF_DEVICE_TRACKER) or "",
            )
            if include_legacy_signal
            else vol.Required(
                CONF_DEVICE_TRACKER,
                default=defaults.get(CONF_DEVICE_TRACKER) or "",
            )
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="device_tracker")
        ),
    }
    if include_legacy_signal:
        fields[vol.Optional(
            CONF_WORK_SIGNAL,
            default=defaults.get(CONF_WORK_SIGNAL) or "",
        )] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor")
        )
    return vol.Schema(fields)


def _work_calendar_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the conditional work-calendar step."""
    defaults = defaults or {}
    return vol.Schema({
        vol.Required(
            CONF_WORK_CALENDAR,
            default=defaults.get(CONF_WORK_CALENDAR) or "",
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar"))
    })


def _configuration(entry) -> dict[str, Any]:
    """Return one entry's effective configuration."""
    return {**entry.data, **entry.options}


def _normalize_base(values: dict[str, Any]) -> dict[str, Any]:
    """Normalize the always-visible setup fields and legacy options."""
    legacy_minutes = values.pop(CONF_THRESHOLD_MINUTES, None)
    if CONF_THRESHOLD_HOURS not in values:
        values[CONF_THRESHOLD_HOURS] = (
            float(legacy_minutes) / 60
            if legacy_minutes is not None
            else DEFAULT_THRESHOLD_HOURS
        )
    values[CONF_THRESHOLD_HOURS] = max(
        0.5,
        min(24.0, round(float(values[CONF_THRESHOLD_HOURS]) * 2) / 2),
    )
    values[CONF_HOME_OFFICE_ENABLED] = bool(
        values.get(CONF_HOME_OFFICE_ENABLED, True)
    )
    values[CONF_OFFICE_ZONE] = values.get(CONF_OFFICE_ZONE) or None
    values[CONF_WORK_CALENDAR_ENABLED] = bool(
        values.get(
            CONF_WORK_CALENDAR_ENABLED,
            bool(values.get(CONF_WORK_CALENDAR)),
        )
    )
    # Legacy installations may still contain the old explicit user mapping.
    # New selection is inferred from the HA user linked to the Person entity.
    values[CONF_HA_USER_ID] = None
    for key in (CONF_DEVICE_TRACKER, CONF_HOME_ZONE, CONF_WORK_SIGNAL, CONF_WORK_CALENDAR):
        values[key] = values.get(key) or None
    return values


def _base_errors(values: dict[str, Any]) -> dict[str, str]:
    """Validate values required before optional source steps."""
    if values.get(CONF_OFFICE_ZONE):
        return {}
    return {CONF_OFFICE_ZONE: "office_zone_required"}


def _homeoffice_errors(values: dict[str, Any]) -> dict[str, str]:
    """Require an enabled Homeoffice source."""
    if not values.get(CONF_HOME_ZONE):
        return {CONF_HOME_ZONE: "home_zone_required"}
    if not (values.get(CONF_DEVICE_TRACKER) or values.get(CONF_WORK_SIGNAL)):
        return {CONF_DEVICE_TRACKER: "homeoffice_device_required"}
    return {}


def _find_conflicts(
    hass,
    values: dict[str, Any],
    *,
    exclude_entry_id: str | None = None,
) -> set[str]:
    """Prevent ambiguous person and tracker assignments."""
    configurations = [
        {"entry_id": entry.entry_id, "values": _configuration(entry)}
        for entry in hass.config_entries.async_entries(DOMAIN)
    ]
    return find_person_configuration_conflicts(
        values,
        configurations,
        exclude_entry_id=exclude_entry_id,
    )


class WorklogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up one independently tracked person."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Set up a person and choose which optional steps to show."""
        errors: dict[str, str] = {}
        if user_input is not None:
            values = _normalize_base(dict(user_input))
            errors = _base_errors(values)
            if not errors:
                self._person_entity = values[CONF_PERSON]
                await self.async_set_unique_id(self._person_entity)
                self._abort_if_unique_id_configured()
                errors = {
                    key: key
                    for key in _find_conflicts(self.hass, values)
                }
            if not errors:
                self._draft_config = values
                return await self._next_setup_step()

        return self.async_show_form(
            step_id="user",
            data_schema=_base_schema(user_input),
            errors=errors,
        )

    async def async_step_homeoffice(self, user_input: dict[str, Any] | None = None):
        """Collect Homeoffice details only when enabled."""
        errors: dict[str, str] = {}
        if user_input is not None:
            values = {
                **self._draft_config,
                **{key: value or None for key, value in user_input.items()},
            }
            errors = _homeoffice_errors(values)
            if not errors:
                self._draft_config.update({
                    CONF_HOME_ZONE: values.get(CONF_HOME_ZONE),
                    CONF_DEVICE_TRACKER: values.get(CONF_DEVICE_TRACKER),
                    CONF_WORK_SIGNAL: values.get(CONF_WORK_SIGNAL),
                })
                errors = {
                    key: key
                    for key in _find_conflicts(self.hass, self._draft_config)
                }
            if not errors:
                return await self._next_calendar_setup_step()

        return self.async_show_form(
            step_id="homeoffice",
            data_schema=_homeoffice_schema(user_input),
            errors=errors,
        )

    async def async_step_work_calendar(
        self, user_input: dict[str, Any] | None = None
    ):
        """Collect a calendar only when enabled."""
        errors: dict[str, str] = {}
        if user_input is not None:
            calendar_entity = user_input.get(CONF_WORK_CALENDAR) or None
            if not calendar_entity:
                errors[CONF_WORK_CALENDAR] = "work_calendar_required"
            else:
                self._draft_config[CONF_WORK_CALENDAR] = calendar_entity
                return self._create_entry()
        return self.async_show_form(
            step_id="work_calendar",
            data_schema=_work_calendar_schema(user_input),
            errors=errors,
        )

    async def _next_setup_step(self):
        if self._draft_config.get(CONF_HOME_OFFICE_ENABLED):
            return self.async_step_homeoffice()
        self._clear_homeoffice_sources()
        return await self._next_calendar_setup_step()

    async def _next_calendar_setup_step(self):
        if self._draft_config.get(CONF_WORK_CALENDAR_ENABLED):
            return self.async_step_work_calendar()
        self._draft_config[CONF_WORK_CALENDAR] = None
        return self._create_entry()

    def _clear_homeoffice_sources(self):
        self._draft_config[CONF_HOME_ZONE] = None
        self._draft_config[CONF_DEVICE_TRACKER] = None
        self._draft_config[CONF_WORK_SIGNAL] = None

    def _create_entry(self):
        state = self.hass.states.get(self._person_entity)
        title = (
            state.attributes.get("friendly_name", self._person_entity)
            if state
            else self._person_entity
        )
        return self.async_create_entry(
            title=f"Steuertage – {title}",
            data=self._draft_config,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return WorklogOptionsFlow()


class WorklogOptionsFlow(config_entries.OptionsFlow):
    """Update person, source and threshold settings."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Update always-visible settings and choose conditional steps."""
        current = _configuration(self.config_entry)
        if user_input is not None:
            values = _normalize_base({**current, **user_input})
            errors = _base_errors(values)
            if errors:
                return self.async_show_form(
                    step_id="init",
                    data_schema=_base_schema(values, include_person=False),
                    errors=errors,
                )
            self._draft_config = values
            return await self._next_options_step()

        return self.async_show_form(
            step_id="init",
            data_schema=_base_schema(current, include_person=False),
        )

    async def async_step_homeoffice(self, user_input: dict[str, Any] | None = None):
        """Update Homeoffice sources only when enabled."""
        current = _configuration(self.config_entry)
        include_legacy = bool(current.get(CONF_WORK_SIGNAL))
        errors: dict[str, str] = {}
        if user_input is not None:
            values = {
                **self._draft_config,
                **{key: value or None for key, value in user_input.items()},
            }
            errors = _homeoffice_errors(values)
            if not errors:
                self._draft_config.update({
                    CONF_HOME_ZONE: values.get(CONF_HOME_ZONE),
                    CONF_DEVICE_TRACKER: values.get(CONF_DEVICE_TRACKER),
                    CONF_WORK_SIGNAL: values.get(CONF_WORK_SIGNAL),
                })
                errors = {
                    key: key
                    for key in _find_conflicts(
                        self.hass,
                        self._draft_config,
                        exclude_entry_id=self.config_entry.entry_id,
                    )
                }
            if not errors:
                return await self._next_calendar_options_step()

        return self.async_show_form(
            step_id="homeoffice",
            data_schema=_homeoffice_schema(
                {**self._draft_config, **(user_input or {})},
                include_legacy_signal=include_legacy,
            ),
            errors=errors,
        )

    async def async_step_work_calendar(
        self, user_input: dict[str, Any] | None = None
    ):
        """Update the calendar only when enabled."""
        errors: dict[str, str] = {}
        if user_input is not None:
            calendar_entity = user_input.get(CONF_WORK_CALENDAR) or None
            if not calendar_entity:
                errors[CONF_WORK_CALENDAR] = "work_calendar_required"
            else:
                self._draft_config[CONF_WORK_CALENDAR] = calendar_entity
                return self._create_options_entry()
        return self.async_show_form(
            step_id="work_calendar",
            data_schema=_work_calendar_schema(
                {**self._draft_config, **(user_input or {})}
            ),
            errors=errors,
        )

    async def _next_options_step(self):
        if self._draft_config.get(CONF_HOME_OFFICE_ENABLED):
            return self.async_step_homeoffice()
        self._clear_homeoffice_sources()
        return await self._next_calendar_options_step()

    async def _next_calendar_options_step(self):
        if self._draft_config.get(CONF_WORK_CALENDAR_ENABLED):
            return self.async_step_work_calendar()
        self._draft_config[CONF_WORK_CALENDAR] = None
        return self._create_options_entry()

    def _clear_homeoffice_sources(self):
        self._draft_config[CONF_HOME_ZONE] = None
        self._draft_config[CONF_DEVICE_TRACKER] = None
        self._draft_config[CONF_WORK_SIGNAL] = None

    def _create_options_entry(self):
        errors = {
            key: key
            for key in _find_conflicts(
                self.hass,
                self._draft_config,
                exclude_entry_id=self.config_entry.entry_id,
            )
        }
        if errors:
            return self.async_show_form(
                step_id="init",
                data_schema=_base_schema(
                    self._draft_config,
                    include_person=False,
                ),
                errors=errors,
            )
        values = dict(self._draft_config)
        values.pop(CONF_PERSON, None)
        return self.async_create_entry(title="", data=values)
