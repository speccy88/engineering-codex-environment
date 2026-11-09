# Optional 5 V resistor-divider example

This is a small acceptance fixture, not a required circuit or component catalog.
The editable KiCad sources are in `native/`. Open `divider.kicad_pro` in KiCad9.
R1 and R2 are 10 kΩ. Apply 5 V between J1 pins1(VIN) and2(GND); unloaded pin3(VOUT)
is2.5 V. Pin polarity/net connectivity is independently checked against the
exported schematic XML netlist.

```sh
scripts/run-kicad.sh python tests/test_kicad/board.py
scripts/run-python.sh tests/test_kicad/step_geometry.py
```

This regenerates schematic, board, routing, ERC/DRC reports, BOM, copper Gerbers,
Excellon drill, STEP assembly and SVG previews under `artifacts/eda/`.
No existing user project is overwritten. Native example sources committed here
are a tested checkpoint; generated artifacts are excluded from Git.

Electrical interface:

|J1 pin|Signal|Role|
|---|---|---|
|1|VIN|5 V external source|
|2|GND|Source return|
|3|VOUT|Unloaded divider output|

Mechanical interface: rectangular40×25 mm PCB, thickness1.6 mm, no mounting
holes. Native board XY runs(0,0)–(40,25)mm. STEP reverses the Y axis; exported
assembled bounds measured x0–40,y−25–0,z−1.405–10.135mm, including header.
The example does not imply loading, power dissipation, EMC or manufacturing
qualification beyond its documented ERC/DRC/net connectivity and geometry tests.
