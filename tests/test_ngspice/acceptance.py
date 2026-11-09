"""Execute native ngspice; check physical results, retain native inputs and evidence.

Run: scripts/run-python.sh tests/test_ngspice/acceptance.py
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).parent


def run_acceptance(output: Path | None = None) -> dict:
    output = (output or ROOT / "artifacts" / "ngspice").resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").unlink(missing_ok=True)
    executable = ROOT / "scripts" / "run-ngspice.sh"
    version = subprocess.run(
        [str(executable), "--version"], capture_output=True, text=True, check=True
    )
    (output / "version.txt").write_text(version.stdout + version.stderr)
    commands = []
    for stem in ("divider", "rc"):
        shutil.copy2(SOURCE / f"{stem}.cir", output / f"{stem}.cir")
        # Remove prior result so successful status cannot reuse stale data.
        (output / f"{stem}.dat").unlink(missing_ok=True)
        command = [str(executable), "-b", f"{stem}.cir"]
        result = subprocess.run(
            command, cwd=output, capture_output=True, text=True, timeout=60, check=False
        )
        (output / f"{stem}.log").write_text(result.stdout + result.stderr)
        commands.append(
            {"argv": command, "cwd": str(output), "exit_code": result.returncode}
        )
        (output / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        assert result.returncode == 0, f"ngspice failed: {output / (stem + '.log')}"
        assert (output / f"{stem}.dat").is_file(), (
            "ngspice did not write fresh simulation data"
        )

    divider = np.loadtxt(output / "divider.dat", skiprows=1, ndmin=2)
    voltage = float(divider[0, -1])
    assert np.isfinite(voltage) and abs(voltage - 2.5) < 1e-8, voltage
    with (output / "divider.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["supply_V", "output_V", "expected_V"])
        writer.writerow([5.0, voltage, 2.5])
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.bar(["Supply", "Divider output"], [5, voltage], color=["#475569", "#0284c7"])
    ax.set(ylabel="Voltage (V)", title="ngspice: 10 kΩ / 10 kΩ divider", ylim=(0, 5.5))
    fig.tight_layout()
    fig.savefig(output / "divider.png", dpi=160)
    plt.close(fig)

    transient = np.loadtxt(output / "rc.dat", skiprows=1, ndmin=2)
    assert transient.shape[1] == 3, transient.shape
    time, supply, simulated = transient.T
    assert len(time) > 100 and time[-1] >= 0.00499, (
        "Transient did not reach the requested stop time"
    )
    assert np.all(np.isfinite(transient)), "Transient contains nonfinite values"
    expected = 5 * (1 - np.exp(-time / 0.001))
    error = np.abs(simulated - expected)
    max_error = float(np.max(error))
    assert max_error < 0.01, f"RC step response error {max_error} V"
    assert abs(simulated[-1] - 5 * (1 - np.exp(-5))) < 0.01
    assert np.min(np.diff(simulated)) >= -1e-6, (
        "Passive RC charging response is non-monotonic"
    )
    np.savetxt(
        output / "rc.csv",
        np.column_stack([time, supply, simulated, expected, error]),
        delimiter=",",
        header="time_s,input_V,output_V,analytic_V,absolute_error_V",
        comments="",
    )
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(time * 1000, simulated, label="ngspice")
    ax.plot(time * 1000, expected, "--", label="5(1−exp(−t/RC))")
    ax.set(
        xlabel="Time (ms)",
        ylabel="Voltage (V)",
        title="RC charging: R = 1 kΩ, C = 1 µF",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "rc.png", dpi=160)
    plt.close(fig)
    evidence = {
        "status": "passed",
        "checks_executed": 2,
        "divider_output_V": voltage,
        "divider_expected_V": 2.5,
        "divider_tolerance_V": 1e-8,
        "rc_rows": len(time),
        "rc_max_absolute_error_V": max_error,
        "rc_tolerance_V": 0.01,
        "commands": commands,
        "version_output": str(output / "version.txt"),
        "outputs": [
            str(p) for p in sorted(output.iterdir()) if p.name != "results.json"
        ],
    }
    (output / "results.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


if __name__ == "__main__":
    print(
        json.dumps(
            run_acceptance(Path(sys.argv[1]) if len(sys.argv) > 1 else None), indent=2
        )
    )
