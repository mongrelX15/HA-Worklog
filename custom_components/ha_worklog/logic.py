"""Pure classification helpers used by HA Work-Log."""
from __future__ import annotations

from .const import BETA_THRESHOLD_SECONDS, DOMAIN


def classify_day(
    office_seconds: float,
    homeoffice_seconds: float,
    office_active: bool,
    homeoffice_active: bool,
    office_source_valid: bool,
    homeoffice_source_valid: bool,
) -> str:
    """Classify a day from either independent 30-minute signal."""
    office_qualifies = office_seconds >= BETA_THRESHOLD_SECONDS
    homeoffice_qualifies = homeoffice_seconds >= BETA_THRESHOLD_SECONDS

    if office_qualifies and homeoffice_qualifies:
        return "office_and_home_office"
    if office_qualifies:
        return "office"
    if homeoffice_qualifies:
        return "home_office"
    if office_active or homeoffice_active or office_seconds > 0 or homeoffice_seconds > 0:
        return "tracking"
    if not office_source_valid or not homeoffice_source_valid:
        return "needs_review"
    return "no_work"


def detect_homeoffice(
    person_valid: bool,
    home_zone_valid: bool,
    device_valid: bool,
    person_home: bool,
    device_home: bool,
) -> tuple[bool, str]:
    """Return a fail-closed Homeoffice result and a diagnostic reason."""
    if not person_valid:
        return False, "person_unavailable"
    if not home_zone_valid:
        return False, "home_zone_unavailable"
    if not person_home:
        return False, "person_outside_home_zone"
    if not device_valid:
        return False, "device_unavailable"
    if not device_home:
        return False, "device_outside_home_zone"
    return True, "person_and_device_in_home_zone"


def append_manual_change(
    history: list[dict],
    *,
    person_id: str,
    changed_by: str,
    timestamp: str,
    old_value: str,
    new_value: str,
    reason: str | None,
) -> list[dict]:
    """Append one audit entry without replacing earlier changes."""
    safe_history = [item for item in history if isinstance(item, dict)]
    safe_history.append({
        "person_id": person_id,
        "changed_by": changed_by,
        "timestamp": timestamp,
        "old_value": old_value,
        "new_value": new_value,
        "reason": (reason or "").strip() or None,
    })
    return safe_history


def make_storage_key(entry_id: str) -> str:
    """Return isolated persistent storage for a single config entry/person."""
    return f"{DOMAIN}_{entry_id}"


def normalize_day_record(
    record: dict,
    *,
    day_types: tuple[str, ...],
    override_types: tuple[str, ...],
) -> dict:
    """Normalize old daily records while keeping valid manual audit history."""
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
    if day_type not in day_types:
        day_type = "needs_review"
    automatic_day_type = record.get("automatic_day_type", day_type)
    if automatic_day_type not in day_types:
        automatic_day_type = day_type
    manual_override = record.get("manual_override")
    if manual_override not in override_types:
        manual_override = None
    change_history = record.get("change_history", [])
    if not isinstance(change_history, list):
        change_history = []
    return {
        "day_type": manual_override or day_type,
        "automatic_day_type": automatic_day_type,
        "manual_override": manual_override,
        "office_seconds": round(office_seconds),
        "homeoffice_seconds": round(homeoffice_seconds),
        "change_history": [item for item in change_history if isinstance(item, dict)],
    }
