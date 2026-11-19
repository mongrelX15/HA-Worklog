from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType

logic_path = Path(__file__).parents[1] / "custom_components" / "ha_worklog" / "logic.py"
package_name = "ha_worklog_test_package"
package = ModuleType(package_name)
package.__path__ = [str(logic_path.parent)]
sys.modules[package_name] = package

spec = spec_from_file_location(f"{package_name}.logic", logic_path)
logic = module_from_spec(spec)
sys.modules[spec.name] = logic
spec.loader.exec_module(logic)
classify_day = logic.classify_day


def test_below_threshold_is_tracking():
    assert classify_day(1799, 0, False, False, True, True) == "tracking"


def test_threshold_classifies_home_office():
    assert classify_day(0, 1800, False, False, True, True) == "home_office"


def test_threshold_classifies_office():
    assert classify_day(1800, 0, False, False, True, True) == "office"


def test_missing_office_data_needs_review():
    assert classify_day(0, 0, False, False, False, True) == "needs_review"


def test_missing_data_needs_review():
    assert classify_day(0, 0, False, False, False, False) == "needs_review"


def test_inactive_empty_day():
    assert classify_day(0, 0, False, False, True, True) == "no_work"
