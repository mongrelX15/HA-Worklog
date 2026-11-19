"""Read-only daily history calendar for HA Work-Log."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import WorklogCoordinator

DAY_LABELS = {
    "no_work": "Kein Arbeitstag",
    "tracking": "Arbeit erfasst",
    "home_office": "Homeoffice",
    "office": "Büro",
    "needs_review": "Prüfung erforderlich",
}
LOCATION_LABELS = {
    "home": "Homeoffice",
    "office": "Büro",
    "other": "anderer Ort",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the daily history calendar."""
    coordinator: WorklogCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WorklogCalendar(coordinator, entry)])


class WorklogCalendar(CoordinatorEntity[WorklogCoordinator], CalendarEntity):
    """Expose one all-day event per recorded date."""

    _attr_has_entity_name = True
    _attr_name = "Arbeitskalender"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: WorklogCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_work_calendar"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "HA Work-Log",
            "manufacturer": "HA Work-Log",
            "model": "Beta",
        }

    @property
    def event(self) -> CalendarEvent | None:
        """Return today's all-day event for the calendar state."""
        today = dt_util.now().date()
        record = self._record_for_day(today)
        if record is None:
            return None
        return self._event_for_day(today, record)

    def _record_for_day(self, day: date) -> dict[str, Any] | None:
        """Return live data for today and the stored record for older days."""
        if day.isoformat() == self.coordinator.data["date"]:
            return {
                "seconds": self.coordinator.data["seconds"],
                "hours": self.coordinator.data["hours"],
                "location": self.coordinator.data["location"],
                "day_type": self.coordinator.data["day_type"],
            }
        return self.coordinator._history.get(day.isoformat())

    @staticmethod
    def _event_for_day(day: date, record: dict[str, Any]) -> CalendarEvent:
        """Create a localized all-day calendar event."""
        day_type = record.get("day_type", "needs_review")
        label = DAY_LABELS.get(day_type, DAY_LABELS["needs_review"])
        hours = float(record.get("hours", 0))
        hours_text = f"{hours:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        summary = f"{label} · {hours_text} h"
        location = LOCATION_LABELS.get(record.get("location"), "nicht erkannt")
        description = (
            f"Erfasste Arbeitszeit: {hours_text} Stunden. "
            f"Arbeitsort: {location}."
        )
        return CalendarEvent(
            start=day,
            end=day + timedelta(days=1),
            summary=summary,
            description=description,
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return saved daily events overlapping the requested date range."""
        records = dict(self.coordinator._history)
        today = dt_util.now().date()
        current = self._record_for_day(today)
        if current is not None:
            records[today.isoformat()] = current

        events: list[CalendarEvent] = []
        for day_string, record in records.items():
            try:
                day = date.fromisoformat(day_string)
            except ValueError:
                continue
            local_start = datetime.combine(day, time.min, tzinfo=start_date.tzinfo)
            local_end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=start_date.tzinfo)
            if local_end > start_date and local_start < end_date:
                events.append(self._event_for_day(day, record))
        return sorted(events, key=lambda item: item.start)
