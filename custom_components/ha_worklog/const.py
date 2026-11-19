"""Constants for HA Work-Log."""
from typing import Final

DOMAIN: Final = "ha_worklog"
CONF_PERSON: Final = "person_entity"
CONF_WORK_SIGNAL: Final = "work_signal"
CONF_OFFICE_ZONE: Final = "office_zone"
# Kept so existing options can be read safely; Beta uses a fixed threshold.
CONF_MINIMUM_HOURS: Final = "minimum_hours"
BETA_THRESHOLD_SECONDS: Final = 30 * 60
DEFAULT_MINIMUM_HOURS: Final = 2.0
