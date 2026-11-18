"""Unit tests for the .dat EXIF container and sidecar path logic."""

import pytest

from openpcsd.sidecars import (
    MAX_EXIF_SIZE,
    extract_exif,
    make_dat,
    read_dat,
    sidecar_paths,
    write_dat,
)

EXIF_TIFF = b"II*\x00\x08\x00\x00\x00\x01\x00" + b"\x00" * 26  # minimal-ish IFD0 blob


class TestDatContainer:
    def test_roundtrip(self):
        dat = make_dat(EXIF_TIFF)
        chunks = read_dat(dat)
        assert list(chunks.keys()) == ["exif"]
        assert chunks["exif"] == EXIF_TIFF
        assert extract_exif(dat) == EXIF_TIFF

    def test_unknown_chunks_preserved(self):
        dat = write_dat({"exif": EXIF_TIFF, "ownr": b"someone", "junk": b"\xff" * 5})
        chunks = read_dat(dat)
        assert set(chunks.keys()) == {"exif", "ownr", "junk"}
        assert chunks["ownr"] == b"someone"
        # byte-stable
        assert write_dat(chunks) == dat

    def test_empty_payload(self):
        assert read_dat(write_dat({})) == {}

    def test_size_cap_enforced(self):
        with pytest.raises(Exception):
            make_dat(b"\x00" * (MAX_EXIF_SIZE + 1))

    def test_wire_layout(self):
        # tag(4) + len(4) + payload, big-endian, app scans for "exif"
        dat = make_dat(b"ABCD")
        assert dat == b"exif" + (4).to_bytes(4, "big") + b"ABCD"


class TestSidecarPaths:
    def test_names(self):
        p = sidecar_paths("/photos/vacation.pcsd")
        assert p.base == "/photos/vacation"
        assert p.mask == "/photos/vacation.msk"
        assert p.metadata == "/photos/vacation.dat"
        assert p.proxy == "/photos/vacation.pxy"
        assert p.source_image == "/photos/vacation.imd"
        assert p.source_image_alt == "/photos/vacation"

    def test_no_extension(self):
        p = sidecar_paths("/photos/doc")
        assert p.base == "/photos/doc"
        assert p.mask == "/photos/doc.msk"

    def test_dot_in_directory_only(self):
        p = sidecar_paths("/my.photos/doc")
        assert p.base == "/my.photos/doc"

    def test_existing(self, tmp_path):
        doc = tmp_path / "project.pcsd"
        doc.write_bytes(b"pcsd...")
        (tmp_path / "project.dat").write_bytes(b"exif...")
        p = sidecar_paths(str(doc))
        found = p.existing()
        assert "document" in found
        assert "metadata" in found
        assert "mask" not in found
        assert found["metadata"].endswith("project.dat")
