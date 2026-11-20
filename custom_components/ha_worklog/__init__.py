"""HA Work-Log integration."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import (
    CONF_DEVICE_TRACKER,
    CONF_HOME_ZONE,
    CONF_OFFICE_ZONE,
    CONF_PERSON,
    CONF_WORK_SIGNAL,
    DOMAIN,
)
from .coordinator import DAY_TYPES, WorklogCoordinator

PLATFORMS = ["sensor", "calendar", "binary_sensor"]
PANEL_PATH = "ha-worklog"
PANEL_MODULE = "/ha_worklog_static/ha_worklog_panel.js?v=0.1.0-beta.9"
PANEL_STATIC_URL = "/ha_worklog_static"
PANEL_SERVICE = "set_day_override"
MANUAL_DAY_TYPES = set(DAY_TYPES) | {"automatic"}


async def _async_setup_panel(hass: HomeAssistant) -> None:
    """Register one shared sidebar panel and one targeted correction service."""
    panel_data = hass.data.setdefault(f"{DOMAIN}_panel", {})
    if not panel_data.get("static_registered"):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    PANEL_STATIC_URL,
                    str(Path(__file__).parent / "www"),
                    cache_headers=True,
                )
            ]
        )
        panel_data["static_registered"] = True

    if not frontend.async_panel_exists(hass, PANEL_PATH):
        await panel_custom.async_register_panel(
            hass=hass,
            frontend_url_path=PANEL_PATH,
            webcomponent_name="ha-worklog-panel",
            sidebar_title="HA Work-Log",
            sidebar_icon="mdi:calendar-check",
            module_url=PANEL_MODULE,
            config={},
        )

    if not hass.services.has_service(DOMAIN, PANEL_SERVICE):
        async def handle_day_override(call: ServiceCall) -> None:
            """Apply a correction only to the explicitly selected person."""
            person_entity = call.data["person_entity"]
            day = call.data["date"]
            day_type = call.data["day_type"]
            reason = call.data.get("reason", "")
            changed_by = call.context.user_id
            if not changed_by:
                raise ServiceValidationError(
                    "Für manuelle Änderungen wird ein angemeldeter HA-Benutzer benötigt."
                )
            if day_type not in MANUAL_DAY_TYPES:
                raise ServiceValidationError(f"Unbekannter Tagestyp: {day_type}")
            try:
                coordinator = next(
                    coordinator
                    for coordinator in hass.data.get(DOMAIN, {}).values()
                    if coordinator.person_entity == person_entity
                )
            except StopIteration as err:
                raise ServiceValidationError(
                    "Für diese Person ist kein HA Work-Log eingerichtet."
                ) from err
            try:
                user = await hass.auth.async_get_user(changed_by)
            except (AttributeError, ValueError, HomeAssistantError):
                user = None
            await coordinator.async_set_day_override(
                day,
                day_type,
                changed_by=str(changed_by),
                changed_by_name=user.name if user else None,
                reason=reason,
            )

        hass.services.async_register(
            DOMAIN,
            PANEL_SERVICE,
            handle_day_override,
            schema=vol.Schema(
                {
                    vol.Required("person_entity"): str,
                    vol.Required("date"): str,
                    vol.Required("day_type"): str,
                    vol.Optional("reason", default=""): vol.All(
                        str, vol.Length(max=500)
                    ),
                }
            ),
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one independently tracked person."""
    coordinator = WorklogCoordinator(hass, entry)
    await coordinator.async_initialize()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await _async_setup_panel(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def changed(_event) -> None:
        hass.async_create_task(coordinator.async_refresh())

    async def refresh_interval(_now) -> None:
        await coordinator.async_refresh()

    tracked = [
        coordinator.person_entity,
        coordinator.home_zone_entity,
    ]
    if coordinator.homeoffice_device_entity:
        tracked.append(coordinator.homeoffice_device_entity)
    if coordinator.legacy_signal_entity:
        tracked.append(coordinator.legacy_signal_entity)
    if coordinator.office_zone_entity:
        tracked.append(coordinator.office_zone_entity)
    remove_state_listener = async_track_state_change_event(hass, tracked, changed)
    remove_timer = async_track_time_interval(
        hass, refresh_interval, timedelta(minutes=1)
    )
    entry.async_on_unload(remove_state_listener)
    entry.async_on_unload(remove_timer)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await coordinator.async_refresh()
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration after options changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one person's entities and remove shared UI only for the last entry."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
            hass.services.async_remove(DOMAIN, PANEL_SERVICE)
        return True
    return False
