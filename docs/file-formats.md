# Editable sources and exchange formats

Keep native sources and derived outputs together when delivering a project,
with separate directories so an export cannot overwrite its source. Record
units, coordinate axes/origin, revision and the tool/runtime used. Exact
geometry, mesh geometry and editable feature histories carry different
information.

## Native source of truth

| Format | Preserve for continued editing |
| --- | --- |
| `.FCStd` | FreeCAD document, sketches/constraints, feature history, assembly links and TechDraw pages/dimensions. Include externally linked source files. |
| CadQuery/build123d `.py` | Parametric modeling source, input parameters and compatible dependency lock. Include referenced data. |
| `.scad` | OpenSCAD parametric source and included libraries/data. |
| `.kicad_sch` | Editable KiCad schematic and connectivity. Keep local symbols if used. |
| `.kicad_pcb` | Editable KiCad board, placements, pads, tracks/vias and outlines. Keep local footprints/models if used. |
| `.kicad_pro` | KiCad project settings/rules. Deliver with schematic and board when applicable. |
| `.blend` | Editable Blender scene, geometry, camera, lighting and materials. Include or pack external assets when required. |
| `.cir` / `.sp` | SPICE circuit/netlist source with model/include files, solver settings and units. |

A STEP model cannot replace parametric `.FCStd` or Python source when future
parameter editing is required. Blender `.blend` geometry imported from STL does
not restore CAD constraints. A Gerber set cannot replace a native PCB project.
Preserve the schematic when its relationship to a PCB must remain editable.

## Neutral and derived outputs

| Format | Purpose and checks |
| --- | --- |
| STEP (`.step`, `.stp`) | Exact solid/assembly exchange. Check every solid's validity, units, component count, dimensions and volume after reimport; PCB STEP must include component models when requested. Tested. |
| BREP (`.brep`) | OCCT shape exchange without parametric feature history. Available through the CAD kernels; not a separate acceptance fixture. |
| STL (`.stl`) | Tessellated manufacturing/preview mesh; units are implicit. State units and mesh tolerance, check watertightness/volume when relevant. Tested. |
| DXF (`.dxf`) | 2D geometry exchange. Confirm units, layers and critical dimensions; basic generation tested with ezdxf. |
| SVG / PDF | Drawings and visual review. Check page content, dimensions, scale and clipping. TechDraw dimensioned exports and general document generation tested. |
| Gerber / Excellon | PCB copper/mask/silkscreen plots and drill data. Generate after actual design-rule checks and retain fabrication layer/drill mapping. Tested export. |
| DSN / SES | Routing interchange. DSN is routing input; import SES into its matching source board and run DRC/parity afterwards. Tested roundtrip. |
| XML netlist / BOM CSV | Connectivity and component procurement data. Crosscheck pin/net assignments and references against native sources. Tested export. |
| MSH / VTU | Simulation/analysis meshes. Preserve physical groups/boundary metadata where needed; tested tetrahedral mesh/VTU connectivity roundtrip does not preserve Gmsh boundary entity sets. |
| CSV | Numerical results, with column names, units, tolerances and simulation settings. Divider and RC simulation CSVs tested. |
| PNG | Raster preview or plot. Check image dimensions, nonblank pixels and framing. Tested. |
| GLB | Portable visual 3D scene/mesh. Supported by suitable exporters, but no dedicated GLB acceptance run is claimed. Preserve CAD sources separately. |
| MP4 | Encoded video derivative. FFmpeg is installed; animation/video encoding has not been acceptance tested. |

Read [toolchain.md](toolchain.md) for runtime selection and the focused tool
documents for commands. Select formats based on the task; no project must
produce every format.

## Downloadable bundles

`scripts/export-project.sh PROJECT_DIRECTORY OUTPUT.zip` packages files without
modifying the source directory. The output must be a new ZIP outside the source
directory. It omits common caches, runtime directories, Git metadata, symlinks
and `.env` files; inspect the actual ZIP contents before sharing because an
arbitrary filename can still contain private data. Include a small manifest
with the native source revision, units, interfaces, validation evidence and
derived-file list. Keep large workbench runtimes/installers out of project
deliverables.
