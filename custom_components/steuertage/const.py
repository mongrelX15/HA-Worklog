"""Constants for Steuertage."""
from typing import Final

DOMAIN: Final = "steuertage"
CONF_PERSON: Final = "person_entity"
CONF_WORK_SIGNAL: Final = "work_signal"  # Legacy Beta 7 binary sensor.
CONF_HOME_ZONE: Final = "home_zone"
CONF_DEVICE_TRACKER: Final = "homeoffice_device"
CONF_HA_USER_ID: Final = "ha_user_id"
CONF_OFFICE_ZONE: Final = "office_zone"
# Kept so existing options can be read safely; Beta uses a fixed threshold.
CONF_MINIMUM_HOURS: Final = "minimum_hours"
BETA_THRESHOLD_SECONDS: Final = 30 * 60
DEFAULT_MINIMUM_HOURS: Final = 2.0
