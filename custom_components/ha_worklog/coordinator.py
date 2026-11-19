"""Coordinator that measures the current day's work signal."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MINIMUM_HOURS,
    CONF_OFFICE_ZONE,
    CONF_PERSON,
    CONF_WORK_SIGNAL,
    DOMAIN,
)
from .logic import classify_day

_LOGGER = logging.getLogger(__name__)

class WorklogCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Track overlap between a work signal and configured presence."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, logger=_LOGGER, name=DOMAIN, update_interval=None)
        config = {**entry.data, **entry.options}
        self.person_entity = config[CONF_PERSON]
        self.signal_entity = config[CONF_WORK_SIGNAL]
        self.office_zone_entity = config.get(CONF_OFFICE_ZONE) or None
        self.minimum_hours = float(config[CONF_MINIMUM_HOURS])
        self.store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
        self._seconds = 0.0
        self._last_update: datetime | None = None
        self._active = False
        self._location: str | None = None
        self._valid = False

    async def async_initialize(self) -> None:
        """Restore today's accumulated time without counting HA downtime."""
        saved = await self.store.async_load()
        today = dt_util.now().date().isoformat()
        if saved and saved.get("date") == today:
            self._seconds = float(saved.get("seconds", 0))
        self._last_update = dt_util.utcnow()
        self.data = self._snapshot()

    def _presence(self) -> tuple[str | None, bool]:
        person = self.hass.states.get(self.person_entity)
        signal = self.hass.states.get(self.signal_entity)
        zone = self.hass.states.get(self.office_zone_entity) if self.office_zone_entity else None
        if (
            person is None
            or signal is None
            or person.state in ("unknown", "unavailable")
            or signal.state in ("unknown", "unavailable")
        ):
            return None, False
        person_state = person.state.casefold()
        office_name = (zone.attributes.get("friendly_name", "") if zone else "").casefold()
        if person_state == "home":
            location = "home"
        elif office_name and person_state in (office_name, office_name.replace(" ", "_")):
            location = "office"
        else:
            location = "other"
        return location, signal.state == "on"

    async def _async_update_data(self) -> dict[str, Any]:
        """Accumulate elapsed seconds only while both configured signals are active."""
        now = dt_util.utcnow()
        current_date = dt_util.now().date().isoformat()
        if not hasattr(self, "_date"):
            self._date = current_date
        if current_date != self._date:
            self._date = current_date
            self._seconds = 0.0
        location, signal_on = self._presence()
        self._valid = location is not None
        active = signal_on and location in ("home", "office")
        if self._last_update is not None and self._active and self._valid:
            elapsed = max(0.0, (now - self._last_update).total_seconds())
            # A missed timer or restart must not create a long unobserved work interval.
            self._seconds += min(elapsed, 90.0)
        self._last_update = now
        self._active = active
        self._location = location
        self.data = self._snapshot()
        await self.store.async_save({
            "date": self._date,
            "seconds": self._seconds,
        })
        return self.data

    def _snapshot(self) -> dict[str, Any]:
        day_type = classify_day(
            self._seconds, self.minimum_hours, self._location, self._active, self._valid
        )
        return {
            "date": getattr(self, "_date", dt_util.now().date().isoformat()),
            "seconds": round(self._seconds),
            "hours": round(self._seconds / 3600, 2),
            "active": self._active,
            "location": self._location,
            "minimum_hours": self.minimum_hours,
            "day_type": day_type,
            "valid": self._valid,
        }
