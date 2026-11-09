---
name: technical-drawings
description: Generate or revise dimensioned engineering drawings from native FreeCAD models or imported STEP geometry using the workbench's offscreen TechDraw runtime, preserving drawing sources and validating exports.
---

# Technical drawings

Read `AGENTS.md` and `docs/freecad.md`. Use the existing checkout without
creating a Git worktree unless requested. Drawings can be produced independently
of EDA, simulation or rendering workflows.

1. Locate and preserve the native model and drawing source. Confirm units,
   revision, intended manufacturing process, projection convention and required
   dimensions from the task. A STEP input may supply geometry but does not
   contain an editable parametric FreeCAD feature history.
2. Run a Python script with
   `scripts/run-freecad.sh --gui path/to/drawing.py [arguments...]`.
   TechDraw PDF/SVG export requires GUI-backed modules despite running
   headlessly; the wrapper starts a private Xvfb display when needed with the
   compatible Debian Python and FreeCAD libraries. The tested GUI path uses
   Qt xcb and software graphics; pure Qt offscreen did not provide working
   TechDraw PDF/SVG exports. Do not force the scientific venv into it.
3. Create a `TechDraw::DrawPage` with a `TechDraw::DrawSVGTemplate` and appropriate
   `TechDraw::DrawViewPart` projections. Reuse distribution templates from
   `/usr/share/freecad/Mod/TechDraw/Templates/` or version a custom template.
   Set explicit view direction, position and scale. Recompute and process Qt
   events so projection workers finish before adding dimensions/exporting.
4. Add useful `TechDraw::DrawViewDimension` objects referencing real projected
   geometry. Identify edges by measured geometry rather than assuming stable
   edge numbers across revisions. Verify references and numeric values against
   the source shape. Model dimensions, tolerances, datums and manufacturing
   notes must come from requirements or explicit engineering assumptions.
5. Export using `TechDrawGui.exportPageAsPdf(page, path)` and
   `TechDrawGui.exportPageAsSvg(page, path)` after recompute/event processing.
   Save the native `.FCStd` containing the drawing page and dimensions. Never
   substitute a manually painted illustration for a checked technical drawing.
6. Open or render the PDF/SVG and inspect page bounds, clipping, overlap,
   labels, scale and dimension values. Verify the native document can be
   reopened and edited. Record actual export status and remaining limitations;
   file existence alone is insufficient.

`tests/test_freecad/acceptance.py` includes a dimensioned bracket example.
Its template, dimensions and geometry are optional examples. Check its current
test evidence before representing PDF/SVG generation as verified.
