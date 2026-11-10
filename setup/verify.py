"""Record real subprocess outcomes without hiding failures or reusing old evidence."""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--fritzing", action="store_true", help="Only Fritzing runtime and functional acceptance")
    args = parser.parse_args()
    if sum((args.quick, args.full, args.fritzing)) > 1:
        parser.error("Choose only one of --quick, --full or --fritzing")
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "artifacts" / "verification" / stamp
    out.mkdir(parents=True)
    commands = [
        ("fritzing", ["scripts/run-fritzing.sh", "--version"]),
        (
            "python",
            [
                "scripts/run-python.sh",
                "-c",
                'import cadquery,build123d,OCP,gmsh,meshio,trimesh,shapely,numpy,scipy,sympy,pandas,pint,matplotlib,pymupdf,svgwrite,ezdxf,pytest; print("engineering imports OK")',
            ],
        ),
        (
            "freecad",
            ["scripts/run-freecad.sh", str(ROOT / "setup" / "probe_freecad.py")],
        ),
        (
            "kicad",
            [
                "scripts/run-kicad.sh",
                "python",
                "-c",
                "import pcbnew; print(pcbnew.Version())",
            ],
        ),
        ("kicad-cli", ["scripts/run-kicad.sh", "cli", "version"]),
        ("blender", ["/usr/bin/blender", "--version"]),
        ("ngspice", ["scripts/run-ngspice.sh", "--version"]),
        ("java", ["java", "-version"]),
        ("openscad", ["openscad", "--version"]),
        ("ffmpeg", ["ffmpeg", "-version"]),
        ("imagemagick", ["magick", "-version"]),
        ("retained-assets", ["python3", "setup/probe_assets.py"]),
        (
            "kicad-ipc-client",
            [
                "scripts/run-kicad-ipc.sh",
                "-c",
                'import importlib.metadata as m, kipy; print(m.version("kicad-python"))',
            ],
        ),
    ]
    if args.fritzing:
        commands = [
            ("fritzing", ["scripts/run-fritzing.sh", "--version"]),
            ("fritzing-regression", ["python3", "-m", "unittest", "discover", "-s", "tests/test_fritzing", "-p", "test_*.py", "-v"]),
            ("fritzing-acceptance", ["python3", "tests/test_fritzing/acceptance.py"]),
        ]
    if args.full:
        # Each acceptance script asserts engineering behavior and creates fresh outputs.
        commands.extend(
            [
                ("fritzing-regression", ["python3", "-m", "unittest", "discover", "-s", "tests/test_fritzing", "-p", "test_*.py", "-v"]),
                ("fritzing-acceptance", ["python3", "tests/test_fritzing/acceptance.py"]),
                (
                    "freecad-acceptance",
                    [
                        "scripts/run-freecad.sh",
                        "--gui",
                        "tests/test_freecad/acceptance.py",
                    ],
                ),
                (
                    "freecad-joint-acceptance",
                    [
                        "scripts/run-freecad.sh",
                        "tests/test_freecad/joint_acceptance.py",
                    ],
                ),
                (
                    "cadquery-acceptance",
                    ["scripts/run-python.sh", "tests/test_cadquery/acceptance.py"],
                ),
                (
                    "build123d-acceptance",
                    ["scripts/run-python.sh", "tests/test_build123d/acceptance.py"],
                ),
                (
                    "geometry-acceptance",
                    ["scripts/run-python.sh", "tests/test_geometry/acceptance.py"],
                ),
                (
                    "openscad-acceptance",
                    [
                        "scripts/run-python.sh",
                        "tests/test_geometry/openscad_acceptance.py",
                    ],
                ),
                (
                    "skidl-acceptance",
                    [
                        "scripts/run-python.sh",
                        "tests/test_geometry/skidl_acceptance.py",
                    ],
                ),
                (
                    "ngspice-acceptance",
                    ["scripts/run-python.sh", "tests/test_ngspice/acceptance.py"],
                ),
                (
                    "pyspice-shared-acceptance",
                    [
                        "scripts/run-python.sh",
                        "tests/test_ngspice/shared_acceptance.py",
                    ],
                ),
                (
                    "eda-acceptance",
                    ["scripts/run-kicad.sh", "python", "tests/test_kicad/board.py"],
                ),
                (
                    "kicad-live-ipc-acceptance",
                    ["scripts/run-kicad-ipc.sh", "tests/test_kicad/ipc_acceptance.py"],
                ),
                (
                    "pcb-step-acceptance",
                    ["scripts/run-python.sh", "tests/test_kicad/step_geometry.py"],
                ),
                (
                    "assembly-acceptance",
                    [
                        "scripts/run-freecad.sh",
                        "tests/test_freecad/assembly.py",
                        "artifacts/eda/divider.step",
                    ],
                ),
                (
                    "blender-acceptance",
                    [
                        "scripts/run-blender.sh",
                        "tests/test_blender/render_acceptance.py",
                        "--output",
                        "artifacts/blender-cad",
                        "--stl",
                        "artifacts/freecad/bracket.stl",
                    ],
                ),
                (
                    "media-acceptance",
                    [
                        "bash",
                        "tests/test_blender/check_media.sh",
                        "artifacts/blender-cad",
                    ],
                ),
                (
                    "assembly-render-acceptance",
                    [
                        "scripts/run-blender.sh",
                        "tests/test_blender/render_acceptance.py",
                        "--output",
                        "artifacts/assembly-preview",
                        "--stl",
                        "artifacts/assembly/pcb-enclosure.stl",
                        "--import-only",
                    ],
                ),
                (
                    "animation-acceptance",
                    [
                        "scripts/run-blender.sh",
                        "tests/test_blender/animation_acceptance.py",
                    ],
                ),
                (
                    "video-acceptance",
                    [
                        "bash",
                        "tests/test_blender/check_video.sh",
                        "artifacts/animation",
                    ],
                ),
            ]
        )
    results = []
    for name, command in commands:
        started = datetime.datetime.now(datetime.UTC).isoformat()
        print(f"Running {name}", flush=True)
        with (out / f"{name}.log").open("w") as log:
            try:
                process = subprocess.run(
                    command,
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=900,
                    env=os.environ.copy(),
                )
                code = process.returncode
            except (OSError, subprocess.TimeoutExpired) as error:
                log.write(str(error))
                code = 124 if isinstance(error, subprocess.TimeoutExpired) else 127
        result = {
            "name": name,
            "command": command,
            "cwd": str(ROOT),
            "started_at": started,
            "exit_code": code,
            "status": "passed" if code == 0 else "failed",
            "log": str((out / f"{name}.log").relative_to(ROOT)),
        }
        results.append(result)
        (out / "commands.json").write_text(json.dumps(results, indent=2) + "\n")
        print(f"{name}: {result['status']} ({code})", flush=True)
    summary = {
        "mode": "fritzing" if args.fritzing else "full" if args.full else "quick",
        "run": stamp,
        "passed": sum(x["exit_code"] == 0 for x in results),
        "failed": sum(x["exit_code"] != 0 for x in results),
        "commands": results,
    }
    (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    (ROOT / "artifacts" / "verification" / "latest.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(f"Results: {out}/result.json", flush=True)
    return int(summary["failed"] != 0)


if __name__ == "__main__":
    sys.exit(main())
