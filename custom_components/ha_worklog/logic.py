"""Pure classification helpers used by HA Work-Log."""
from __future__ import annotations

def classify_day(
    worked_seconds: float,
    minimum_hours: float,
    location: str | None,
    active: bool,
    valid: bool = True,
) -> str:
    """Return an explainable daily work classification."""
    if not valid or location is None:
        return "needs_review"
    if worked_seconds >= minimum_hours * 3600:
        if location == "home":
            return "home_office"
        if location == "office":
            return "office"
        return "needs_review"
    if active or worked_seconds > 0:
        return "tracking"
    return "no_work"
