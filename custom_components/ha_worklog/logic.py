"""Pure classification helpers used by HA Work-Log."""
from __future__ import annotations

from .const import BETA_THRESHOLD_SECONDS


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
