from .acceptance import main


def test_build123d_roundtrip(tmp_path):
    main(tmp_path)
