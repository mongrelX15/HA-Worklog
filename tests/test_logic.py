from custom_components.ha_worklog.logic import classify_day

def test_below_threshold_is_tracking():
    assert classify_day(3599, 1, "home", True) == "tracking"

def test_threshold_classifies_home_office():
    assert classify_day(3600, 1, "home", False) == "home_office"

def test_threshold_classifies_office():
    assert classify_day(7200, 2, "office", False) == "office"

def test_unknown_location_needs_review():
    assert classify_day(9000, 2, "other", False) == "needs_review"

def test_missing_data_needs_review():
    assert classify_day(0, 2, None, False, valid=False) == "needs_review"

def test_inactive_empty_day():
    assert classify_day(0, 2, "home", False) == "no_work"
