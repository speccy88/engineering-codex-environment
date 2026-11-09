"""Run both simulations in an isolated directory, retaining native solver checks."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def test_native_divider_and_rc(tmp_path):
    spec = spec_from_file_location(
        "ngspice_acceptance", Path(__file__).with_name("acceptance.py")
    )
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run_acceptance(tmp_path)
    assert result["checks_executed"] == 2
