"""Diagnose optional PySpice backends without patching installed dependencies.

A completed probe does not mean that either PySpice simulator backend passed.
Native ngspice remains independently tested by acceptance.py.
"""

from __future__ import annotations

import importlib.metadata
import json
import logging
import subprocess
import traceback
from pathlib import Path

import numpy as np
from PySpice.Spice.Netlist import Circuit
from PySpice.Spice.NgSpice.Shared import NgSpiceShared

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    output = ROOT / "artifacts" / "ngspice"
    output.mkdir(parents=True, exist_ok=True)
    shared_library = ROOT / ".local/sysroot/usr/lib/x86_64-linux-gnu/libngspice.so"
    if shared_library.is_file():
        # Public class configuration selects the isolated native library explicitly.
        NgSpiceShared.LIBRARY_PATH = str(shared_library.resolve())
    logging.basicConfig(
        filename=output / "pyspice-runtime.log", level=logging.WARNING, force=True
    )
    circuit = Circuit("PySpice 5 V divider")
    circuit.V(1, "input", circuit.gnd, 5)
    circuit.R(1, "input", "output", 10000)
    circuit.R(2, "output", circuit.gnd, 10000)
    evidence = {
        "pyspice_version": importlib.metadata.version("PySpice"),
        "backends": {},
    }
    for mode in ("ngspice-shared", "ngspice-subprocess"):
        try:
            kwargs = {"simulator": mode}
            if mode.endswith("subprocess"):
                kwargs["spice_command"] = str(ROOT / "scripts" / "run-ngspice.sh")
            simulation = circuit.simulator(**kwargs)
            analysis = simulation.operating_point()
            voltage = float(analysis["output"][0])
            assert abs(voltage - 2.5) < 1e-8, voltage
            evidence["backends"][mode] = {
                "status": "passed",
                "output_V": voltage,
                "tolerance_V": 1e-8,
                "shared_library": str(shared_library.resolve())
                if mode.endswith("shared")
                else None,
            }
            (output / f"pyspice-{mode}.log").unlink(missing_ok=True)
        except (OSError, NameError, AssertionError) as exc:
            (output / f"pyspice-{mode}.log").write_text(traceback.format_exc())
            evidence["backends"][mode] = {
                "status": "blocked",
                "exception": type(exc).__name__,
                "reason": str(exc),
                "log": str(output / f"pyspice-{mode}.log"),
            }

    # PySpice's circuit builder is independently usable: run the exported native netlist.
    netlist = output / "pyspice-divider.cir"
    netlist.write_text(
        str(circuit) + "\n.control\nset wr_singlescale\nset wr_vecnames\nop\n"
        "wrdata pyspice-divider.dat v(output)\nquit\n.endc\n.end\n"
    )
    data_file = output / "pyspice-divider.dat"
    data_file.unlink(missing_ok=True)
    command = [str(ROOT / "scripts" / "run-ngspice.sh"), "-b", netlist.name]
    result = subprocess.run(
        command, cwd=output, capture_output=True, text=True, timeout=60, check=False
    )
    (output / "pyspice-builder-native.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0
    voltage = float(np.loadtxt(data_file, skiprows=1, ndmin=2)[0, -1])
    assert abs(voltage - 2.5) < 1e-8
    evidence["netlist_builder_native_solver"] = {
        "status": "passed",
        "output_V": voltage,
        "tolerance_V": 1e-8,
        "command": command,
        "exit_code": result.returncode,
        "scope": "PySpice netlist generation plus native ngspice; not a PySpice simulator backend",
    }
    evidence["compatibility_notes"] = [
        "PySpice 1.5 warns Unsupported Ngspice version 44; the shared backend divider is tested explicitly.",
        "The basic shared solver runs without the system spinit; optional XSPICE/OSDI code models are not validated.",
    ]
    evidence["status"] = (
        "partial"
        if any(item["status"] == "blocked" for item in evidence["backends"].values())
        else "passed"
    )
    destination = output / "pyspice-status.json"
    destination.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
