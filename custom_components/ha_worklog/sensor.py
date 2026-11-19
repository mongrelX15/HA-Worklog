"""Sensors exposed by HA Work-Log."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DAY_TYPES, WorklogCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create work-log sensors."""
    coordinator: WorklogCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        WorklogDurationSensor(coordinator, entry),
        WorklogDaySensor(coordinator, entry),
    ])


class WorklogDurationSensor(CoordinatorEntity[WorklogCoordinator], SensorEntity):
    """Internal diagnostic duration; the dashboard does not use this sensor."""

    _attr_has_entity_name = True
    _attr_name = "Erkennungszeit heute"
    _attr_native_unit_of_measurement = "h"
    _attr_native_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: WorklogCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_work_duration"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "HA Work-Log",
            "manufacturer": "HA Work-Log",
            "model": "Beta",
        }

    @property
    def native_value(self):
        return self.coordinator.data["hours"]

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            "datum": data["date"],
            "arbeitszone_sekunden": data["office_seconds"],
            "homeoffice_sensor_sekunden": data["homeoffice_seconds"],
            "schwellwert_minuten": data["threshold_minutes"],
        }


class WorklogDaySensor(CoordinatorEntity[WorklogCoordinator], SensorEntity):
    """Expose the automatically detected kind of work day."""

    _attr_has_entity_name = True
    _attr_name = "Tagestyp"
    _attr_icon = "mdi:briefcase-clock"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = DAY_TYPES

    def __init__(self, coordinator: WorklogCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_day_type"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "HA Work-Log",
            "manufacturer": "HA Work-Log",
            "model": "Beta",
        }

    @property
    def native_value(self):
        return self.coordinator.data["day_type"]

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            "datum": data["date"],
            "schwellwert_minuten": data["threshold_minutes"],
            "arbeitszone_erreichbar": data["office_source_valid"],
            "homeoffice_sensor_erreichbar": data["homeoffice_source_valid"],
            "arbeitszone_aktiv": data["office_active"],
            "homeoffice_sensor_aktiv": data["homeoffice_active"],
        }
