"""HA Work-Log integration."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .const import DOMAIN
from .coordinator import WorklogCoordinator
from .sensor import WorklogDaySensor, WorklogDurationSensor

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a configured work log."""
    coordinator = WorklogCoordinator(hass, entry)
    await coordinator.async_initialize()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
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
        return True
    return False
