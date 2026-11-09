---
name: circuit-simulation
description: Run and validate electronic-circuit simulations with native ngspice, including operating points and transient response, and produce inspectable data and graphs.
---

1. Inspect the supplied netlist, models, units, source definitions, initial
   conditions and requested operating conditions. A simulation request does not
   require a new schematic or PCB. Preserve user files and use a separate output
   directory. Use trusted device-model sources and record their versions.
2. Invoke native ngspice independently:
   `scripts/run-ngspice.sh -b -o artifacts/simulation.log circuit.cir`.
   Do not force simulator execution through FreeCAD, Blender or pcbnew Python.
   For CSV processing, plotting and numerical checks use `scripts/run-python.sh`.
3. Choose analysis appropriate to the question: operating point, DC sweep, AC,
   transient or model corner/tolerance sweep. Inspect convergence and warnings,
   verify actual analysis ran, and fail if simulation outputs are missing,
   nonfinite or inconsistent. A process exit code alone does not prove validity.
4. Check numerical expectations with explicit tolerances and physical units;
   compare analytical values or independent invariants when available. For a
   divider compare unloaded output with Vin*Rbottom/(Rtop+Rbottom). For RC
   charging compare samples/time constant with the analytical exponential.
   These are examples, not constraints on supported circuits.
5. Save the original/edited netlist and model references, raw simulator output,
   CSV data, graph and machine-readable assertions. Report operating assumptions,
   tolerances, executed commands and limitations of the selected model.

`tests/test_ngspice/acceptance.py` is the optional real divider and RC test;
`tests/test_ngspice/divider.cir` and `rc.cir` are reusable examples. Native CLI
simulation is validated separately from optional PySpice. A PySpice import alone
must not be reported as a verified shared-library simulation.
