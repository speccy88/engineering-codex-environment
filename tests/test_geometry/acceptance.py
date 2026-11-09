"""Numerical and geometry tool acceptance with a real tetrahedral mesh roundtrip."""

import json
from importlib import metadata
from pathlib import Path

import ezdxf
import gmsh
import meshio
import numpy as np
import pint
import pymupdf
import scipy.linalg
import shapely
import svgwrite
import sympy
from shapely.geometry import Polygon


def main(out=Path("artifacts/python/geometry")):
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").unlink(missing_ok=True)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.NumThreads", 2)
        gmsh.model.add("unit-cube")
        gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.25)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 0.25)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(out / "cube.msh"))
    finally:
        gmsh.finalize()
    mesh = meshio.read(out / "cube.msh")
    tetra = mesh.get_cells_type("tetra")
    assert tetra.shape[0] > 0
    p = mesh.points[tetra]
    volumes = (
        np.abs(
            np.linalg.det(
                np.stack(
                    (p[:, 1] - p[:, 0], p[:, 2] - p[:, 0], p[:, 3] - p[:, 0]), axis=1
                )
            )
        )
        / 6
    )
    assert np.all(volumes > 1e-12)
    assert abs(volumes.sum() - 1.0) < 1e-9
    # Preserve volume topology without Gmsh boundary entity sets unsupported by VTU.
    volume_mesh = meshio.Mesh(mesh.points, [("tetra", tetra)])
    meshio.write(out / "cube.vtu", volume_mesh)
    reread = meshio.read(out / "cube.vtu")
    assert len(reread.points) == len(mesh.points)
    assert np.array_equal(reread.get_cells_type("tetra"), tetra)
    units = pint.UnitRegistry()
    assert abs((1 * units.inch).to(units.mm).magnitude - 25.4) < 1e-12
    polygon = Polygon([(0, 0), (4, 0), (4, 2), (0, 2)])
    assert polygon.is_valid and polygon.area == 8
    assert shapely.from_wkt(polygon.wkt).equals(polygon)
    x = sympy.symbols("x")
    assert sympy.solve(sympy.Eq(5 / 10000, x / 10000 + x / 10000), x) == [2.5]
    assert np.allclose(scipy.linalg.solve([[2, 1], [1, 3]], [3, 4]), [1, 1])
    # Real DXF, vector drawing and PDF serialization, with semantic roundtrips.
    drawing = ezdxf.new("R2010")
    drawing.modelspace().add_lwpolyline([(0, 0), (4, 0), (4, 2), (0, 2)], close=True)
    drawing.saveas(out / "rectangle.dxf")
    assert (
        len(ezdxf.readfile(out / "rectangle.dxf").modelspace().query("LWPOLYLINE")) == 1
    )
    svg = svgwrite.Drawing(str(out / "rectangle.svg"), size=("120mm", "80mm"))
    svg.add(svg.rect((10, 10), (80, 40), fill="none", stroke="black"))
    svg.save()
    pdf = pymupdf.open()
    page = pdf.new_page(width=300, height=200)
    page.insert_text((30, 30), "Engineering vector export: 4 x 2 mm")
    page.draw_rect((30, 50, 230, 150))
    pdf.save(out / "rectangle.pdf")
    pdf.close()
    with pymupdf.open(out / "rectangle.pdf") as reopened:
        assert len(reopened) == 1 and "Engineering" in reopened[0].get_text()
    packages = [
        "cadquery",
        "build123d",
        "cadquery-ocp",
        "gmsh",
        "trimesh",
        "meshio",
        "shapely",
        "numpy",
        "scipy",
        "sympy",
        "pandas",
        "pint",
        "matplotlib",
        "pytest",
        "ruff",
        "PyMuPDF",
        "svgwrite",
        "ezdxf",
        "skidl",
        "PySpice",
    ]
    result = {
        "status": "passed",
        "tetrahedra": len(tetra),
        "mesh_volume": float(volumes.sum()),
        "mesh_roundtrip": True,
        "units_check": True,
        "polygon_check": True,
        "linear_algebra_check": True,
        "dxf_svg_pdf": True,
        "versions": {name: metadata.version(name) for name in packages},
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    import sys

    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/python/geometry"))
