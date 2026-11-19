"""Read-only daily work-day history calendar."""
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
    "tracking": "Erkennung läuft",
    "home_office": "Homeoffice-Tag",
    "office": "Bürotag",
    "office_and_home_office": "Büro- und Homeoffice-Signale",
    "needs_review": "Bitte prüfen",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the daily history calendar."""
    coordinator: WorklogCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WorklogCalendar(coordinator, entry)])


class WorklogCalendar(CoordinatorEntity[WorklogCoordinator], CalendarEntity):
    """Expose one all-day event for every tracked date."""

    _attr_has_entity_name = True
    _attr_name = "Arbeitskalender"
    _attr_icon = "mdi:calendar-month"

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
        """Return today's all-day calendar event."""
        today = dt_util.now().date()
        record = self._record_for_day(today)
        if record is None:
            return None
        return self._event_for_day(today, record)

    def _record_for_day(self, day: date) -> dict[str, Any] | None:
        """Return live data for today and stored data for previous days."""
        if day.isoformat() == self.coordinator.data["date"]:
            return {"day_type": self.coordinator.data["day_type"]}
        return self.coordinator._history.get(day.isoformat())

    @staticmethod
    def _event_for_day(day: date, record: dict[str, Any]) -> CalendarEvent:
        """Create a calendar event without displaying measured time."""
        day_type = record.get("day_type", "needs_review")
        summary = DAY_LABELS.get(day_type, DAY_LABELS["needs_review"])
        return CalendarEvent(
            start=day,
            end=day + timedelta(days=1),
            summary=summary,
            description=f"Automatische Tageserkennung: {summary}.",
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return history events overlapping the requested range."""
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
