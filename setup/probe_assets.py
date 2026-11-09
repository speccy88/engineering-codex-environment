"""Check retained assets needed by future tasks without starting applications."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
router = json.loads((ROOT / "setup/freerouting.json").read_text())
jar = ROOT / router["path"]
assert jar.is_file(), f"Missing Freerouting JAR: {jar}"
assert hashlib.file_digest(jar.open("rb"), "sha256").hexdigest() == router["sha256"], (
    "Freerouting checksum mismatch"
)
for filename in ["native-extras.json", "pyspice-native.json"]:
    for package in json.loads((ROOT / "setup" / filename).read_text())["packages"]:
        sentinel = ROOT / ".local/sysroot" / package["sentinel"]
        marker = ROOT / ".local/sysroot" / f".{package['name']}.sha256"
        assert sentinel.exists(), f"Missing installed asset: {sentinel}"
        assert marker.read_text().strip() == package["sha256"], (
            f"Wrong installed package marker: {marker}"
        )
assert (ROOT / ".local/ngspice/scripts/spinit").is_file(), (
    "Missing relocated ngspice configuration"
)
assert Path("/usr/share/kicad/symbols/Device.kicad_sym").is_file()
assert Path(
    "/usr/share/kicad/footprints/Resistor_SMD.pretty/R_0805_2012Metric.kicad_mod"
).is_file()
print(
    "Retained Freerouting, native package assets, ngspice configuration and KiCad libraries available."
)
