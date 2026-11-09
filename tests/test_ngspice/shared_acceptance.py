"""Real PySpice operating point using the wrapper's native shared-library prefix."""

import json
from pathlib import Path

from PySpice.Spice.Netlist import Circuit

circuit = Circuit("Shared ngspice divider")
circuit.V(1, "input", circuit.gnd, 5)
circuit.R(1, "input", "output", 10000)
circuit.R(2, "output", circuit.gnd, 10000)
analysis = circuit.simulator().operating_point()
voltage = float(analysis["output"][0])
assert abs(voltage - 2.5) < 1e-8, voltage
result = {
    "status": "passed",
    "backend": "ngspice-shared",
    "output_V": voltage,
    "expected_V": 2.5,
    "tolerance_V": 1e-8,
    "limitation": "PySpice warns ngspice44 is not a recognized version; basic DC verified, advanced code models untested.",
}
out = (
    Path(__file__).resolve().parents[2] / "artifacts/ngspice/pyspice-shared-result.json"
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
