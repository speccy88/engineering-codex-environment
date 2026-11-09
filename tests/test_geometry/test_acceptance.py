from .acceptance import main
from .openscad_acceptance import main as openscad_main
from .skidl_acceptance import main as skidl_main


def test_engineering_geometry_roundtrip(tmp_path):
    main(tmp_path)


def test_openscad_csg_export(tmp_path):
    openscad_main(tmp_path)


def test_skidl_stock_library_netlist(tmp_path):
    skidl_main(tmp_path)
