# Parametric mounting-bracket example

This optional acceptance fixture demonstrates an independent mechanical task;
it imposes no architecture on future projects.

From the repository root run:

```bash
scripts/run-freecad.sh --gui tests/test_freecad/acceptance.py
```

The script is the editable modeling recipe. It produces
`artifacts/freecad/bracket.FCStd` (60 mm width) and
`artifacts/freecad/bracket-wider.FCStd` (70 mm width), plus STEP, closed STL,
and a linked TechDraw drawing in PDF and SVG. Open either `.FCStd` in desktop
FreeCAD and edit the constrained base sketch's named `Width` or `Depth`
dimensions. `FlangeSketch.Constraints.Width` and the right mounting-hole
position are expressions linked to the base sketch's width.

The analytic material-volume check accounts for flange overlap and both
cylindrical through holes. STEP is reimported and checked for a valid solid
with matching volume. STL is checked for closed geometry. The source,
reopened source, changed model, and technical drawing are all exercised.

Keep `.FCStd` as the parametric source. STEP/STL are exchange or manufacturing
derivatives, not replacements for the feature history. See `docs/freecad.md`
for exact runtime requirements and tested headless drawing behavior.
