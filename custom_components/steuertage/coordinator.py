"""Coordinator that recognizes qualifying work days and stores per-person history."""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    BETA_THRESHOLD_SECONDS,
    CONF_DEVICE_TRACKER,
    CONF_HA_USER_ID,
    CONF_HOME_ZONE,
    CONF_OFFICE_ZONE,
    CONF_PERSON,
    CONF_WORK_SIGNAL,
    DOMAIN,
)
from .logic import (
    append_manual_change,
    classify_day,
    detect_homeoffice,
    make_storage_key,
    normalize_day_record,
)

_LOGGER = logging.getLogger(__name__)
DAY_TYPES = (
    "no_work",
    "tracking",
    "home_office",
    "office",
    "office_and_home_office",
    "needs_review",
    "vacation",
    "sick_leave",
)
OVERRIDE_TYPES = (*DAY_TYPES,)


class WorklogCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Track one person's office and home-office signals independently."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, logger=_LOGGER, name=f"{DOMAIN}_{entry.entry_id}", update_interval=None)
        config = {**entry.data, **entry.options}
        self.entry_id = entry.entry_id
        self.person_entity = config[CONF_PERSON]
        person_state = hass.states.get(self.person_entity)
        self.person_name = (
            person_state.attributes.get("friendly_name", self.person_entity)
            if person_state
            else self.person_entity
        )
        self.ha_user_id = config.get(CONF_HA_USER_ID)
        self.home_zone_entity = config.get(CONF_HOME_ZONE) or "zone.home"
        self.homeoffice_device_entity = config.get(CONF_DEVICE_TRACKER)
        self.legacy_signal_entity = config.get(CONF_WORK_SIGNAL)
        self.legacy_mode = bool(
            not self.homeoffice_device_entity and self.legacy_signal_entity
        )
        self.office_zone_entity = config.get(CONF_OFFICE_ZONE) or None
        self.threshold_seconds = BETA_THRESHOLD_SECONDS
        self.store = Store(hass, 1, make_storage_key(entry.entry_id))
        self._office_seconds = 0.0
        self._homeoffice_seconds = 0.0
        self._last_update: datetime | None = None
        self._office_active = False
        self._homeoffice_active = False
        self._location: str | None = None
        self._office_source_valid = not bool(self.office_zone_entity)
        self._homeoffice_source_valid = False
        self._person_source_valid = False
        self._device_source_valid = False
        self._person_status = "unknown"
        self._device_status = "unknown"
        self._homeoffice_reason = "not_evaluated"
        self._history: dict[str, dict[str, Any]] = {}
        self._date = dt_util.now().date().isoformat()

    async def async_initialize(self) -> None:
        """Restore today's totals and preserve previously stored history."""
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
                    # Beta 0.1.0-beta.3 stored one combined counter.
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
        """Migrate older daily records without dropping manual audit entries."""
        return normalize_day_record(
            record,
            day_types=DAY_TYPES,
            override_types=OVERRIDE_TYPES,
        )

    def _history_record(self) -> dict[str, Any]:
        """Return the current record while preserving its manual change history."""
        previous = self._history.get(self._date, {})
        return {
            "day_type": self.data["day_type"],
            "automatic_day_type": self.data["automatic_day_type"],
            "manual_override": self.data["manual_override"],
            "office_seconds": round(self._office_seconds),
            "homeoffice_seconds": round(self._homeoffice_seconds),
            "change_history": list(previous.get("change_history", [])),
        }

    async def async_set_day_override(
        self,
        day_string: str,
        day_type: str,
        *,
        changed_by: str,
        changed_by_name: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Persist a manual correction and append an authenticated audit record."""
        day = date.fromisoformat(day_string)
        key = day.isoformat()
        existing = self._history.get(key, {})
        if key == self._date:
            automatic = self.data.get("automatic_day_type", self.data["day_type"])
            office_seconds = round(self._office_seconds)
            homeoffice_seconds = round(self._homeoffice_seconds)
        else:
            automatic = existing.get(
                "automatic_day_type", existing.get("day_type", "no_work")
            )
            office_seconds = int(existing.get("office_seconds", 0))
            homeoffice_seconds = int(existing.get("homeoffice_seconds", 0))

        old_value = existing.get("manual_override") or automatic
        override = None if day_type == "automatic" else day_type
        new_value = override or automatic
        change_history = append_manual_change(
            list(existing.get("change_history", [])),
            person_id=self.person_entity,
            changed_by=changed_by,
            timestamp=dt_util.utcnow().isoformat(),
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        )
        change_history[-1]["changed_by_name"] = changed_by_name
        self._history[key] = {
            "day_type": new_value,
            "automatic_day_type": automatic,
            "manual_override": override,
            "office_seconds": office_seconds,
            "homeoffice_seconds": homeoffice_seconds,
            "change_history": change_history,
        }
        if key == self._date:
            self.data = self._snapshot()
        await self._async_save()
        self.async_set_updated_data(self._snapshot())

    async def _async_save(self) -> None:
        """Persist this person's counters and history under their own key."""
        await self.store.async_save({
            "date": self._date,
            "office_seconds": self._office_seconds,
            "homeoffice_seconds": self._homeoffice_seconds,
            "day_type": self.data["day_type"],
            "location": self._location,
            "history": self._history,
        })

    @staticmethod
    def _zone_tokens(zone_entity: str, zone_state) -> set[str]:
        """Return Home Assistant state forms that identify a selected zone."""
        tokens = {zone_entity.split(".", 1)[-1].casefold()}
        if zone_state is not None:
            friendly_name = str(zone_state.attributes.get("friendly_name", "")).strip()
            if friendly_name:
                tokens.add(friendly_name.casefold())
                tokens.add(re.sub(r"[^a-z0-9]+", "_", friendly_name.casefold()).strip("_"))
        if zone_entity == "zone.home":
            tokens.add("home")
        return {token for token in tokens if token}

    def _is_in_zone(self, entity_state, zone_entity: str | None) -> bool:
        """Check an entity against Home Assistant's zone state."""
        if entity_state is None or zone_entity is None:
            return False
        if entity_state.state in ("unknown", "unavailable", ""):
            return False
        if zone_entity in entity_state.attributes.get("in_zones", []):
            return True
        zone_state = self.hass.states.get(zone_entity)
        if zone_state is None or zone_state.state in ("unknown", "unavailable"):
            return False
        return entity_state.state.casefold() in self._zone_tokens(zone_entity, zone_state)

    def _presence(self) -> tuple[str | None, bool, bool]:
        """Update signal diagnostics and return location and valid home-office state."""
        person = self.hass.states.get(self.person_entity)
        home_zone = self.hass.states.get(self.home_zone_entity)
        person_valid = person is not None and person.state not in ("unknown", "unavailable")
        self._person_status = person.state if person else "unavailable"
        home_zone_valid = bool(
            home_zone is not None and home_zone.state not in ("unknown", "unavailable")
        )
        self._person_source_valid = bool(person_valid and home_zone_valid)

        office_zone = (
            self.hass.states.get(self.office_zone_entity)
            if self.office_zone_entity
            else None
        )
        office_zone_valid = bool(
            not self.office_zone_entity
            or (office_zone is not None and office_zone.state not in ("unknown", "unavailable"))
        )
        if not person_valid:
            location = None
        elif self._is_in_zone(person, self.home_zone_entity):
            location = "home"
        elif self.office_zone_entity and self._is_in_zone(person, self.office_zone_entity):
            location = "office"
        else:
            location = "other"

        if self.legacy_mode:
            signal = self.hass.states.get(self.legacy_signal_entity)
            signal_valid = signal is not None and signal.state not in ("unknown", "unavailable")
            self._device_status = signal.state if signal else "unavailable"
            self._device_source_valid = bool(signal_valid)
            self._homeoffice_source_valid = bool(signal_valid)
            homeoffice_active = bool(signal_valid and signal.state == "on")
            self._homeoffice_reason = (
                "legacy_signal_active" if homeoffice_active
                else "legacy_signal_inactive" if signal_valid
                else "legacy_signal_unavailable"
            )
        else:
            device = self.hass.states.get(self.homeoffice_device_entity) if self.homeoffice_device_entity else None
            device_valid = device is not None and device.state not in ("unknown", "unavailable")
            self._device_status = device.state if device else "unavailable"
            self._device_source_valid = bool(device_valid)
            person_home = self._is_in_zone(person, self.home_zone_entity)
            device_home = self._is_in_zone(device, self.home_zone_entity)
            self._homeoffice_source_valid = bool(
                person_valid and home_zone_valid and device_valid
            )
            homeoffice_active = bool(
                self._homeoffice_source_valid and person_home and device_home
            )
            homeoffice_active, self._homeoffice_reason = detect_homeoffice(
                person_valid,
                home_zone_valid,
                device_valid,
                person_home,
                device_home,
            )

        self._office_source_valid = bool(person_valid and office_zone_valid)
        return location, bool(person_valid), homeoffice_active

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
        self._last_update = now
        self.data = self._snapshot()
        self._history[self._date] = self._history_record()
        await self._async_save()
        return self.data

    def _snapshot(self) -> dict[str, Any]:
        """Return the current day classification and source diagnostics."""
        automatic_day_type = classify_day(
            self._office_seconds,
            self._homeoffice_seconds,
            self._office_active,
            self._homeoffice_active,
            self._office_source_valid,
            self._homeoffice_source_valid,
        )
        saved_record = self._history.get(self._date, {})
        manual_override = saved_record.get("manual_override")
        if manual_override not in OVERRIDE_TYPES:
            manual_override = None
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
            "day_type": manual_override or automatic_day_type,
            "automatic_day_type": automatic_day_type,
            "manual_override": manual_override,
            "office_source_valid": self._office_source_valid,
            "homeoffice_source_valid": self._homeoffice_source_valid,
            "person_source_valid": self._person_source_valid,
            "device_source_valid": self._device_source_valid,
            "person_status": self._person_status,
            "device_status": self._device_status,
            "homeoffice_reason": self._homeoffice_reason,
        }
