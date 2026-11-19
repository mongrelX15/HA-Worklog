"""HA Work-Log integration."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .const import DOMAIN
from .coordinator import DAY_TYPES, WorklogCoordinator

PLATFORMS = ["sensor", "calendar"]
PANEL_PATH = "ha-worklog"
PANEL_MODULE = "/ha_worklog_static/ha_worklog_panel.js"
PANEL_STATIC_URL = "/ha_worklog_static"
PANEL_SERVICE = "set_day_override"
MANUAL_DAY_TYPES = set(DAY_TYPES) | {"vacation", "sick_leave"}


async def _async_setup_panel(hass: HomeAssistant) -> None:
    """Register the bundled sidebar panel and manual correction service."""
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
            """Set or clear a calendar day override."""
            day = call.data["date"]
            day_type = call.data["day_type"]
            if day_type != "automatic" and day_type not in MANUAL_DAY_TYPES:
                raise vol.Invalid(f"Unsupported day type: {day_type}")
            for coordinator in hass.data.get(DOMAIN, {}).values():
                await coordinator.async_set_day_override(day, day_type)

        hass.services.async_register(
            DOMAIN,
            PANEL_SERVICE,
            handle_day_override,
            schema=vol.Schema(
                {
                    vol.Required("date"): str,
                    vol.Required("day_type"): str,
                }
            ),
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a configured work log."""
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

    tracked = [coordinator.person_entity, coordinator.signal_entity]
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
    """Reload the integration after an options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a work log."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
            hass.services.async_remove(DOMAIN, PANEL_SERVICE)
        return True
    return False
