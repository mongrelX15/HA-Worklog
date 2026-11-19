"""Coordinator that recognizes qualifying work days and stores history."""
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
    BETA_THRESHOLD_SECONDS,
    CONF_OFFICE_ZONE,
    CONF_PERSON,
    CONF_WORK_SIGNAL,
    DOMAIN,
)
from .logic import classify_day

_LOGGER = logging.getLogger(__name__)
DAY_TYPES = (
    "no_work",
    "tracking",
    "home_office",
    "office",
    "office_and_home_office",
    "needs_review",
)


class WorklogCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Track office-zone and home-office sensor time independently."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, logger=_LOGGER, name=DOMAIN, update_interval=None)
        config = {**entry.data, **entry.options}
        self.person_entity = config[CONF_PERSON]
        self.signal_entity = config[CONF_WORK_SIGNAL]
        self.office_zone_entity = config.get(CONF_OFFICE_ZONE) or None
        self.threshold_seconds = BETA_THRESHOLD_SECONDS
        self.store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
        self._office_seconds = 0.0
        self._homeoffice_seconds = 0.0
        self._last_update: datetime | None = None
        self._office_active = False
        self._homeoffice_active = False
        self._location: str | None = None
        self._office_source_valid = not bool(self.office_zone_entity)
        self._homeoffice_source_valid = False
        self._history: dict[str, dict[str, Any]] = {}
        self._date = dt_util.now().date().isoformat()

    async def async_initialize(self) -> None:
        """Restore today's totals and migrate the previous Beta history."""
        saved = await self.store.async_load()
        today = dt_util.now().date().isoformat()
        self._date = today

        if saved:
            history = saved.get("history", {})
            if isinstance(history, dict):
                self._history = {
                    day: self._normalize_record(record)
                    for day, record in history.items()
                    if isinstance(day, str) and isinstance(record, dict)
                }

            saved_date = saved.get("date")
            if saved_date == today:
                if "office_seconds" in saved or "homeoffice_seconds" in saved:
                    self._office_seconds = float(saved.get("office_seconds", 0))
                    self._homeoffice_seconds = float(saved.get("homeoffice_seconds", 0))
                else:
                    # Beta 0.1.0-beta.3 kept one combined counter. Preserve it
                    # under the last known location until the new model takes over.
                    legacy_seconds = float(saved.get("seconds", 0))
                    legacy_type = saved.get("day_type")
                    if legacy_type == "office" or saved.get("location") == "office":
                        self._office_seconds = legacy_seconds
                    elif legacy_type == "home_office" or saved.get("location") == "home":
                        self._homeoffice_seconds = legacy_seconds
            elif isinstance(saved_date, str) and saved_date < today:
                self._history[saved_date] = self._normalize_record(saved)

        self._last_update = dt_util.utcnow()
        self.data = self._snapshot()
        self._history[today] = self._history_record()
        await self._async_save()

    @staticmethod
    def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
        """Migrate an older saved daily record without exposing durations."""
        office_seconds = float(record.get("office_seconds", 0))
        homeoffice_seconds = float(record.get("homeoffice_seconds", 0))
        legacy_seconds = float(record.get("seconds", 0))
        legacy_type = record.get("day_type")
        if not office_seconds and not homeoffice_seconds and legacy_seconds:
            if legacy_type == "office" or record.get("location") == "office":
                office_seconds = legacy_seconds
            elif legacy_type == "home_office" or record.get("location") == "home":
                homeoffice_seconds = legacy_seconds
        day_type = record.get("day_type", "needs_review")
        if day_type not in DAY_TYPES:
            day_type = "needs_review"
        return {
            "day_type": day_type,
            "office_seconds": round(office_seconds),
            "homeoffice_seconds": round(homeoffice_seconds),
        }

    def _history_record(self) -> dict[str, Any]:
        """Return the persisted classification for the current date."""
        return {
            "day_type": self.data["day_type"],
            "office_seconds": round(self._office_seconds),
            "homeoffice_seconds": round(self._homeoffice_seconds),
        }

    async def _async_save(self) -> None:
        """Persist the current day and history locally."""
        await self.store.async_save({
            "date": self._date,
            "office_seconds": self._office_seconds,
            "homeoffice_seconds": self._homeoffice_seconds,
            "day_type": self.data["day_type"],
            "location": self._location,
            "history": self._history,
        })

    def _presence(self) -> tuple[str | None, bool, bool]:
        """Return location and validity of the person and home-office sensor."""
        person = self.hass.states.get(self.person_entity)
        signal = self.hass.states.get(self.signal_entity)
        zone = self.hass.states.get(self.office_zone_entity) if self.office_zone_entity else None

        person_valid = person is not None and person.state not in ("unknown", "unavailable")
        signal_valid = signal is not None and signal.state not in ("unknown", "unavailable")
        if not person_valid:
            location = None
        else:
            person_state = person.state.casefold()
            office_name = (zone.attributes.get("friendly_name", "") if zone else "").casefold()
            office_entity_state = self.office_zone_entity.split(".", 1)[-1].casefold() if self.office_zone_entity else ""
            if person_state == "home":
                location = "home"
            elif office_name and person_state in (office_name, office_name.replace(" ", "_")):
                location = "office"
            elif office_entity_state and person_state == office_entity_state:
                location = "office"
            else:
                location = "other"
        homeoffice_on = signal_valid and signal.state == "on"
        return location, person_valid, bool(homeoffice_on)

    async def _async_update_data(self) -> dict[str, Any]:
        """Accumulate each configured signal independently."""
        now = dt_util.utcnow()
        current_date = dt_util.now().date().isoformat()
        same_date = current_date == self._date
        if not same_date:
            self._history[self._date] = self._history_record()
            self._date = current_date
            self._office_seconds = 0.0
            self._homeoffice_seconds = 0.0

        if same_date and self._last_update is not None:
            elapsed = min(max(0.0, (now - self._last_update).total_seconds()), 90.0)
            if self._office_active:
                self._office_seconds += elapsed
            if self._homeoffice_active:
                self._homeoffice_seconds += elapsed

        location, person_valid, homeoffice_active = self._presence()
        self._location = location
        self._office_active = bool(
            self.office_zone_entity and person_valid and location == "office"
        )
        self._homeoffice_active = homeoffice_active
        self._office_source_valid = not self.office_zone_entity or person_valid
        signal = self.hass.states.get(self.signal_entity)
        self._homeoffice_source_valid = (
            signal is not None and signal.state not in ("unknown", "unavailable")
        )
        self._last_update = now
        self.data = self._snapshot()
        self._history[self._date] = self._history_record()
        await self._async_save()
        return self.data

    def _snapshot(self) -> dict[str, Any]:
        """Return the current day classification and source status."""
        day_type = classify_day(
            self._office_seconds,
            self._homeoffice_seconds,
            self._office_active,
            self._homeoffice_active,
            self._office_source_valid,
            self._homeoffice_source_valid,
        )
        seconds = round(self._office_seconds + self._homeoffice_seconds)
        return {
            "date": self._date,
            "office_seconds": round(self._office_seconds),
            "homeoffice_seconds": round(self._homeoffice_seconds),
            "seconds": seconds,
            "hours": round(seconds / 3600, 2),
            "office_active": self._office_active,
            "homeoffice_active": self._homeoffice_active,
            "location": self._location,
            "threshold_minutes": self.threshold_seconds // 60,
            "day_type": day_type,
            "office_source_valid": self._office_source_valid,
            "homeoffice_source_valid": self._homeoffice_source_valid,
        }
