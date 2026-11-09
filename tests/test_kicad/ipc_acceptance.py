#!/usr/bin/env python3
"""Exercise live KiCad IPC in a temporary Xvfb editor and isolated profile.

Invoke using scripts/run-kicad-ipc.sh. No persistent service or source edit.
"""

from __future__ import annotations

import argparse
import json
import os
import selectors
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from kipy import KiCad
from kipy.errors import ApiError
from kipy.errors import ConnectionError as KiCadConnectionError

ROOT = Path(__file__).resolve().parents[2]


def timestamp():
    return datetime.now(UTC).isoformat()


def check(output: Path):
    output = output.resolve()
    run = output / datetime.now(UTC).strftime("run-%Y%m%dT%H%M%S-%f")
    run.mkdir(parents=True)
    result = {
        "status": "running",
        "started_at": timestamp(),
        "commands": [],
        "run_directory": str(run),
    }
    processes = []
    logs = []
    try:
        xvfb = shutil.which("Xvfb") or str(ROOT / ".local/sysroot/usr/bin/Xvfb")
        assert Path(xvfb).is_file(), "Xvfb missing; run setup/install.sh"
        profile = run / "config/kicad/9.0"
        source_profile = ROOT / ".local/xdg/config/kicad/9.0"
        if source_profile.exists():
            shutil.copytree(source_profile, profile)
        else:
            profile.mkdir(parents=True)
        common_file = profile / "kicad_common.json"
        common = json.loads(common_file.read_text()) if common_file.exists() else {}
        common.setdefault("api", {})["enable_server"] = True
        common.setdefault("do_not_show_again", {})["data_collection_prompt"] = False
        common_file.write_text(json.dumps(common, indent=2) + "\n")
        for name in ["fp-lib-table", "sym-lib-table"]:
            target = profile / name
            if not target.exists():
                shutil.copyfile(Path("/usr/share/kicad/template") / name, target)
        work = run / "project"
        work.mkdir()
        for suffix in ["kicad_pcb", "kicad_sch", "kicad_pro"]:
            shutil.copyfile(
                ROOT / "examples/electronic-circuit/native" / f"divider.{suffix}",
                work / f"divider.{suffix}",
            )
        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        for key, folder in [
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_CACHE_HOME", "cache"),
            ("XDG_DATA_HOME", "data"),
            ("TMPDIR", "tmp"),
        ]:
            path = run / folder
            path.mkdir(exist_ok=True)
            env[key] = str(path)
        env["LIBGL_ALWAYS_SOFTWARE"] = "1"
        env["GDK_BACKEND"] = "x11"
        env["KICAD9_FOOTPRINT_DIR"] = "/usr/share/kicad/footprints"
        env["KICAD9_SYMBOL_DIR"] = "/usr/share/kicad/symbols"
        env["KICAD9_3DMODEL_DIR"] = str(
            ROOT / ".local/sysroot/usr/share/kicad/3dmodels"
        )
        xlog = (run / "xvfb.log").open("w")
        logs.append(xlog)
        command = [
            xvfb,
            "-displayfd",
            "1",
            "-screen",
            "0",
            "1280x800x24",
            "-nolisten",
            "tcp",
            "-noreset",
        ]
        server = subprocess.Popen(
            command, env=env, stdout=subprocess.PIPE, stderr=xlog, text=True
        )
        processes.append(server)
        result["commands"].append(
            {"command": command, "pid": server.pid, "started_at": timestamp()}
        )
        with selectors.DefaultSelector() as selector:
            selector.register(server.stdout, selectors.EVENT_READ)
            assert selector.select(timeout=10), "Xvfb did not assign a display"
        display = server.stdout.readline().strip()
        assert display.isdigit(), f"Invalid Xvfb display: {display!r}"
        env["DISPLAY"] = ":" + display
        gui_log = (run / "pcbnew.log").open("w")
        logs.append(gui_log)
        command = ["/usr/bin/pcbnew", str(work / "divider.kicad_pcb")]
        editor = subprocess.Popen(
            command, env=env, stdout=gui_log, stderr=subprocess.STDOUT
        )
        processes.append(editor)
        result["commands"].append(
            {
                "command": command,
                "pid": editor.pid,
                "started_at": timestamp(),
                "display": env["DISPLAY"],
            }
        )
        socket_path = run / "tmp/kicad/api.sock"
        endpoint = "ipc://" + str(socket_path)
        client = KiCad(
            socket_path=endpoint,
            client_name="engineering-workbench-acceptance",
            timeout_ms=500,
        )
        deadline = time.monotonic() + 50
        last_error = None
        while time.monotonic() < deadline:
            if editor.poll() is not None:
                raise RuntimeError(
                    f"pcbnew exited {editor.returncode}; see {run / 'pcbnew.log'}"
                )
            try:
                client.ping()
                board = client.get_board()
                footprints = board.get_footprints()
                break
            except (ApiError, KiCadConnectionError) as error:
                last_error = repr(error)
                time.sleep(0.5)
        else:
            raise RuntimeError(
                f"Live IPC connection failed: {last_error}; see {run / 'pcbnew.log'}"
            )
        assert len(footprints) == 3, len(footprints)
        positions = {
            fp.reference_field.text.value: [fp.position.x / 1e6, fp.position.y / 1e6]
            for fp in footprints
        }
        assert positions == {"R1": [16, 8], "R2": [26, 8], "J1": [5, 8]}, positions
        tracks, vias = board.get_tracks(), board.get_vias()
        assert len(tracks) > 0 and len(vias) > 0
        result.update(
            {
                "status": "passed",
                "server_version": str(client.get_version()),
                "client_api_version": str(client.get_api_version()),
                "footprints_read": len(footprints),
                "positions_mm": positions,
                "tracks_read": len(tracks),
                "vias_read": len(vias),
                "endpoint": endpoint,
                "operations": [
                    "Ping",
                    "GetVersion",
                    "GetOpenDocuments",
                    "GetItems(footprints)",
                    "GetItems(tracks)",
                    "GetItems(vias)",
                ],
            }
        )
        return result
    except Exception as error:
        result.update({"status": "failed", "error": repr(error)})
        raise
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            for command in result["commands"]:
                if command["pid"] == process.pid:
                    command["cleanup_exit_code"] = process.returncode
                    command["stopped_at"] = timestamp()
        for stream in logs:
            stream.close()
        result["finished_at"] = timestamp()
        (run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        output.mkdir(parents=True, exist_ok=True)
        (output / "latest-result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=ROOT / "artifacts/ipc")
    print(json.dumps(check(parser.parse_args().output), indent=2))
