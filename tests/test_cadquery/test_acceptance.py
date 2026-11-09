from .acceptance import main


def test_cadquery_roundtrip(tmp_path):
    main(tmp_path)
