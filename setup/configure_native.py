"""Create user-owned configuration for relocated Debian native packages."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / ".local/sysroot/usr/share/ngspice/scripts/spinit"
destination = ROOT / ".local/ngspice/scripts/spinit"
destination.parent.mkdir(parents=True, exist_ok=True)
# Leave the hash-authenticated vendor artifact intact; create a runtime config.
text = source.read_text().replace(
    "/usr/lib/x86_64-linux-gnu/ngspice/",
    str(ROOT / ".local/sysroot/usr/lib/x86_64-linux-gnu/ngspice") + "/",
)
text = text.replace("set num_threads=8", "set num_threads=2")
destination.write_text(text)
print(f"Configured ngspice init: {destination}")
