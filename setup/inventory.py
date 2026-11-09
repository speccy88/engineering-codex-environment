"""Capture exact installed versions without reading credentials or the environment."""

import datetime
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command):
    result = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, check=False
    )
    return {
        "command": command,
        "exit_code": result.returncode,
        "output": (result.stdout + result.stderr).strip(),
    }


def main():
    packages = run(
        ["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\t${db:Status-Status}\n"]
    )
    prefixes = (
        "freecad",
        "libfreecad",
        "kicad",
        "blender",
        "openscad",
        "libocct",
        "python3-pyside2",
        "python3-pivy",
        "libgl",
        "libegl",
        "openjdk-21",
        "git",
        "gh",
        "ffmpeg",
        "imagemagick",
    )
    native = []
    for row in packages["output"].splitlines():
        fields = row.split("\t")
        if (
            len(fields) == 3
            and fields[2] == "installed"
            and fields[0].startswith(prefixes)
        ):
            native.append({"package": fields[0], "version": fields[1]})
    code = 'import importlib.metadata as m,json,sys; print(json.dumps({"python":sys.version,"packages":{d.metadata["Name"]:d.version for d in m.distributions()}},sort_keys=True))'
    runtimes = {}
    for name in ["engineering", "kicad-ipc"]:
        result = run([str(ROOT / ".venvs" / name / "bin/python"), "-c", code])
        assert result["exit_code"] == 0, result
        runtimes[name] = json.loads(result["output"])
    commands = [
        ["/usr/bin/python3", "--version"],
        ["uv", "--version"],
        ["git", "--version"],
        ["gh", "--version"],
        ["scripts/run-kicad.sh", "cli", "version"],
        ["/usr/bin/blender", "--version"],
        ["openscad", "--version"],
        ["scripts/run-ngspice.sh", "--version"],
        ["java", "-version"],
        ["ffmpeg", "-version"],
        ["magick", "-version"],
    ]
    extras = json.loads((ROOT / "setup/native-extras.json").read_text())["packages"]
    optional = ROOT / "setup/pyspice-native.json"
    if optional.exists():
        extras += json.loads(optional.read_text())["packages"]
    report = {
        "schema_version": 1,
        "captured_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "platform": "Debian 13 trixie, amd64",
        "native_system_packages": native,
        "workspace_prefix_packages": extras,
        "freerouting": json.loads((ROOT / "setup/freerouting.json").read_text()),
        "python_runtimes": runtimes,
        "version_commands": [run(c) for c in commands],
    }
    assert all(c["exit_code"] == 0 for c in report["version_commands"])
    (ROOT / "setup/versions.lock").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"Captured {len(native)} native packages and {sum(len(v['packages']) for v in runtimes.values())} Python distributions."
    )


if __name__ == "__main__":
    main()
