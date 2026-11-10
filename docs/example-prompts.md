# Additional engineering prompt examples

The [README showcase](../README.md#example-prompts-by-workflow) includes complete prompts for new circuits, Fritzing, brackets, enclosures, drawings, simulation and rendering. These examples cover existing designs and other tools. Replace the example dimensions and limits with your project requirements, and attach the referenced files.

## Review and repair an existing KiCad PCB

```text
Review the attached KiCad project. Reproduce its ERC, DRC, net-parity and
unconnected-item results before making changes. Preserve the board outline,
mounting holes, connector positions and fabrication rules. Fix the routing
and clearance issues you can resolve without changing the circuit; explain
any electrical ambiguity first. If using Freerouting, import the SES into
the matching board and rerun the checks. Return the edited native project,
a before/after report, board previews and updated Gerber/drill files.
```

## Create a script-driven enclosure with OpenSCAD

```text
Create an OpenSCAD enclosure with an 80 × 50 × 25 mm internal cavity,
2.4 mm walls and a removable screw lid. Expose dimensions, wall thickness,
mounting-hole spacing and fit allowance as named parameters. State the
chosen screw and insert assumptions. Export base and lid separately in
print orientation, check watertightness and overall dimensions, and return
the SCAD source, STLs and assembly preview.
```

## Compare parametric mechanical variants

```text
Use CadQuery or build123d to generate three versions of a 70 × 40 mm
mounting plate with 3, 4 and 5 mm thickness. Keep the same four 5 mm holes
on a 50 × 20 mm center rectangle. Check all solids and exports. Tabulate
bounding dimensions, volume and calculated mass using my supplied density
of 2.70 g/cm³. Return the parameterized Python source, STEP/STL variants,
a CSV comparison and a labeled preview. Do not infer strength from volume.
```

## Generate and inspect an analysis mesh

```text
Generate a tetrahedral volume mesh of the attached STEP solid using Gmsh.
Confirm its units, validity and dimensions first. Compare nominal element
sizes of 1, 2 and 4 mm, report node/element counts and signed cell volumes,
and flag inverted or degenerate cells. Return the script, MSH and VTU files,
a mesh preview and a CSV summary. Identify boundary groups and any metadata
lost in conversion. This task is meshing only; do not claim a stress result.
```

## Check and visualize experimental data

```text
Analyze the attached circuit measurements using Python. Validate column
names, units, timestamps and missing samples. Overlay the measured LED
current with the supplied ngspice prediction, align time only using the
method you describe, and report cycle time, peak-current error and RMS
residual. Return the analysis script, cleaned CSV, plots and a short report
that separates measurements, predictions and assumptions.
```

## Continue a design from supplied sources

```text
Open the attached enclosure FCStd and matching PCB STEP. Increase the lid
clearance by 0.5 mm while preserving the external mounting interface and
connector locations. Recompute, reopen the saved document and check solid
validity, critical dimensions and board/component interference. Return a
new revision with FCStd, STEP, print-oriented STLs, a comparison image and
a list of changed dimensions. Keep the supplied originals unchanged.
```

## Prepare a project handoff

```text
Package this project's final revision into a ZIP containing editable native
sources, local symbols/models, generator scripts, neutral exports, previews
and actual check results. Include a manifest with units, origin, source
revision, tool versions and known limitations. Verify that the native files
reopen and that the archive contains all required dependencies. Exclude
caches, installations and temporary files, then list the delivered files.
```

For a larger project, define a shared interface first: units, origin, board outline, mounting-hole coordinates, component height limits, connector access, keepouts and revision. That lets separate PCB, enclosure and visualization tasks exchange compatible files. See [independent workflows](project-workflows.md).
