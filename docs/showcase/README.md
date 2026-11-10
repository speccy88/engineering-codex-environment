# Showcase image provenance

The [main README](../../README.md) uses actual engineering renders and plots. Images illustrate particular projects; they are not evidence that every future design will pass electrical, mechanical or fabrication checks. Click an image in the README to view its full resolution.

## Existing 555 timer project

Six images were reused with the project owner's permission from the **555 LED Fader Design Files** and **555 LED Fader Enclosure** pages, both updated on 2026-11-09. They were retrieved on 2026-11-10. The public repository contains these previews, not a copy of the original project's complete design archive.

| Asset | Subject | Source project |
| --- | --- | --- |
| [555-assembly.jpg](555-assembly.jpg) | Assembled six-LED timer PCB | Design Files |
| [555-schematic.png](555-schematic.png) | KiCad schematic | Design Files |
| [555-pcb.png](555-pcb.png) | Routed top and bottom copper | Design Files |
| [555-simulation.png](555-simulation.png) | ngspice timing-voltage and current predictions | Design Files |
| [555-enclosure.jpg](555-enclosure.jpg) | Assembled enclosure | Enclosure |
| [555-exploded.jpg](555-exploded.jpg) | Lid, PCB and enclosure assembly | Enclosure |

The circuit was a functional reconstruction from photographs, with assumed values and dimensions. Source-page validation reported KiCad 9.0.2 ERC 0, DRC 0, unconnected 0, parity 0 and a check of all 49 component pins. The nominal functional SPICE model predicted a 7.46 s cycle and a 3.57 mA peak through one LED at 5 V and 25 °C. A transistor-gain stress case with BF = 100 stalled. These are model results, not hardware measurements.

The enclosure was modeled around the reconstructed 70 × 54 mm PCB. Source-page results reported valid base/lid solids, watertight print meshes, successful STEP roundtrips and zero PCB/base/lid intersections. Fit to the original physical board was not tested. The images and earlier reported results were reused; the original project validations were not rerun for this README update.

Assembly/enclosure renders were resized to fit 1280 × 1000 pixels and saved as JPEGs. Schematic, PCB and waveform PNGs retain their original bytes. No CAD geometry, diagram content or waveform data was altered. [555-provenance.json](555-provenance.json) records source and published hashes, sizes and transformations. Private page identifiers and download links are intentionally omitted.

## Newly generated examples

| Asset | Native source | Evidence |
| --- | --- | --- |
| [mechanical.png](mechanical.png) | FreeCAD bracket from [acceptance.py](../../tests/test_freecad/acceptance.py), tessellated and rendered in Blender | [CAD provenance](cad-provenance.json): three constrained sketches, valid solid, native reopen and export checks |
| [technical-drawing.png](technical-drawing.png) | Native TechDraw PDF from the same acceptance fixture | [Drawing provenance](drawing-provenance.json): geometry-linked dimensions and inspected export |
| [simulation.png](simulation.png) | Native ngspice [RC netlist](../../tests/test_ngspice/rc.cir) and [acceptance checks](../../tests/test_ngspice/acceptance.py) | [Simulation provenance](eda-provenance.json): 573 samples; maximum analytic residual 13.37 µV |

These showcase runs do not constitute a rerun of the entire workbench acceptance suite. The baseline test history remains in the [test matrix](../../setup/test-matrix.md). In this documentation session, the initial quick probe found the separate engineering/IPC virtual environments and some retained assets absent from the checkout; the selected native showcase workflows were run independently.

### Regenerate the bracket render

In a prepared environment, from the repository root:

```sh
WB_ARTIFACTS="$PWD/artifacts/showcase" \
  scripts/run-freecad.sh --gui tests/test_freecad/acceptance.py
ENGINEERING_THREADS=8 scripts/run-blender.sh scripts/showcase-cad.py \
  --input artifacts/showcase/freecad/bracket-wider.stl \
  --output docs/showcase/mechanical.png \
  --scene artifacts/showcase/mechanical.blend
magick docs/showcase/mechanical.png -strip -dither None -colors 256 \
  docs/showcase/mechanical.png
```

The blue display material and lighting are presentation choices, not material specifications. The mesh geometry is unchanged. See the drawing provenance for the exact TechDraw export and rasterization commands used in this session.

### Regenerate the RC plot

With native ngspice and Python NumPy/Matplotlib/Pillow available:

```sh
python3 tests/test_ngspice/acceptance.py artifacts/showcase/eda/simulation
python3 docs/showcase/render-simulation.py
```

The plotting script reads the solver's generated CSV and compares it with the analytic RC response; it does not invent waveform samples. Native files and execution evidence stay under ignored `artifacts/`.

## Fritzing example

The three Fritzing images are reused directly from [examples/fritzing/verified](../../examples/fritzing/verified/). That directory also contains the editable project, custom-part and output bundle, and its [verification record](../../examples/fritzing/verified/verification.json). See [the example instructions](../../examples/fritzing/README.md) and [workflow documentation](../fritzing.md) for reproduction and limitations.
