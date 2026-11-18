"""Round-trip tests: write -> read -> compare, and byte-stability."""

import pytest

from openpcsd import (
    BalloonObject,
    ExtTLV,
    PcsdDocument,
    PropObject,
    StyleRef,
    TextObject,
    Thumbnail,
    UnknownChunk,
    read_pcsd,
    write_pcsd,
)

PNG_1PX = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_document():
    doc = PcsdDocument(
        doc_width=320.0,
        doc_height=240.0,
        pixel_width=320,
        pixel_height=240,
        version_int=1,
        version_long=0x123456789,
        timestamp=1700000000000,
    )
    doc.bundle = {
        "title": "day at the beach",
        "quality": 90,
        "geo": {"lat": 52.9, "lon": 6.4},
    }
    doc.thumbnail = Thumbnail(data=PNG_1PX, codec="png")

    text = TextObject(
        width=120.0,
        height=20.0,
        matrix=(1.0, 0.0, 10.0, 0.0, 1.0, 30.0, 0.0, 0.0, 1.0),
        color_a=0x00000000,
        style_int=1,
        flag_2048=False,
        color_fill=0xFF3366CC,
        stroke_width=0.0,
        color_stroke=0xFF000000,
        stroke_width2=0.0,
        style=StyleRef(flags=1, font_file="", font_family="sans-serif"),
        font_size=18.0,
        text="Hello pcsd!",
        rotation=15.0,
        alignment=1,
        line_scale=1.2,
        shadow=(0xFF000000, 2.0, 3.0, 4.0),
    )
    balloon = BalloonObject(
        width=200.0,
        height=80.0,
        matrix=(1.0, 0.0, 50.0, 0.0, 1.0, 50.0, 0.0, 0.0, 1.0),
        min_w=40.0,
        min_h=20.0,
        pad_w=8.0,
        pad_h=6.0,
        int_a=16,
        int_b=32,
        int_v=255,
        float_w=1.5,
        int_r=7,
        float_s=1.0,
        float_t=2.0,
        float_u=3.0,
        int_e=5,
        style=StyleRef(flags=0, font_file="Laffayette_Comic_Pro_PS.ttf", font_family=""),
        shape=9,
        tail_x=100.0,
        tail_y=90.0,
        tail_scale=1.75,
        text="A word balloon!",
        line_scale=1.1,
    )
    prop = PropObject(
        width=64.0,
        height=64.0,
        matrix=(2.0, 0.0, 5.0, 0.0, 2.0, 5.0, 0.0, 0.0, 1.0),
        color_matrix=tuple([1.0, 0, 0, 0, 0] * 4),
        skin_flags=3,
        name="res/stickers/crown",
    )
    doc.objects = [text, balloon, prop]
    return doc


def jcolor(x: int) -> int:
    """Colors are signed Java ints on the wire (ARGB with alpha set is negative)."""
    return x - 2**32 if x >= 2**31 else x


class TestRoundTrip:
    def test_full_document(self):
        doc = make_document()
        data = write_pcsd(doc)
        parsed = read_pcsd(data)

        assert parsed.doc_width == 320.0
        assert parsed.doc_height == 240.0
        assert parsed.pixel_width == 320
        assert parsed.pixel_height == 240
        assert parsed.version_long == 0x123456789
        assert parsed.timestamp == 1700000000000
        assert parsed.thumbnail.data == PNG_1PX
        assert parsed.bundle == doc.bundle

        assert len(parsed.objects) == 3
        text, balloon, prop = parsed.objects

        assert isinstance(text, TextObject)
        assert text.text == "Hello pcsd!"
        assert text.color_fill == jcolor(0xFF3366CC)
        assert text.matrix == (1.0, 0.0, 10.0, 0.0, 1.0, 30.0, 0.0, 0.0, 1.0)
        assert text.style.font_family == "sans-serif"
        assert text.rotation == 15.0
        assert text.alignment == 1
        assert text.line_scale == pytest.approx(1.2)
        assert text.shadow == (jcolor(0xFF000000), 2.0, 3.0, 4.0)

        assert isinstance(balloon, BalloonObject)
        assert balloon.text == "A word balloon!"
        assert balloon.shape == 9
        assert balloon.style.font_file == "Laffayette_Comic_Pro_PS.ttf"
        assert balloon.tail_scale == 1.75
        assert balloon.line_scale == pytest.approx(1.1)

        assert isinstance(prop, PropObject)
        assert prop.color_matrix == tuple([1.0, 0, 0, 0, 0] * 4)
        assert prop.skin_flags == 3
        assert prop.name == "res/stickers/crown"

    def test_byte_stability(self):
        """write(read(write(doc))) == write(doc) - deterministic writer."""
        doc = make_document()
        data1 = write_pcsd(doc)
        parsed = read_pcsd(data1)
        data2 = write_pcsd(parsed)
        assert data1 == data2

    def test_ids_assigned_and_stable(self):
        doc = make_document()
        data = write_pcsd(doc)
        ids = [o.obj_id for o in doc.objects]
        assert ids == [3, 4, 5]
        parsed = read_pcsd(data)
        assert [o.obj_id for o in parsed.objects] == ids

    def test_default_omitted_extensions(self):
        """Rotation 0 / alignment 0 / scale 1 / no shadow => no TLV bytes."""
        doc = make_document()
        doc.objects = [
            TextObject(text="plain", font_size=10.0, width=10, height=10)
        ]
        data = write_pcsd(doc)
        parsed = read_pcsd(data)
        text = parsed.objects[0]
        assert text.rotation == 0.0
        assert text.alignment == 0
        assert text.line_scale == 1.0
        assert text.shadow is None
        assert text.ext_tlvs == []
        # and the body must exactly match the fixed fields:
        # 44 common + 25 fixed + style(4+2+2... sans-serif) + 4 + utf
        assert text.raw_tail == b""

    def test_unicode_text(self):
        doc = make_document()
        doc.objects = [
            TextObject(
                text="emoji \U0001f600 nihao \u4f60\u597d caf\u00e9",
                font_size=12.0,
                width=50.0,
                height=12.0,
            )
        ]
        parsed = read_pcsd(write_pcsd(doc))
        assert parsed.objects[0].text == "emoji \U0001f600 nihao \u4f60\u597d caf\u00e9"

    def test_unknown_chunk_preserved(self):
        doc = make_document()
        doc.other_chunks = [UnknownChunk(tag="futr", payload=b"\x01\x02\x03")]
        data = write_pcsd(doc)
        parsed = read_pcsd(data)
        assert parsed.other_chunks[0].tag == "futr"
        assert parsed.other_chunks[0].payload == b"\x01\x02\x03"
        # unknown chunks survive a full round trip byte-for-byte
        assert write_pcsd(parsed) == data

    def test_unknown_ext_tlv_preserved(self):
        doc = make_document()
        text = doc.objects[0]
        text.ext_tlvs.append(ExtTLV(tag="futx", payload=b"\x00\x01\x02"))
        data = write_pcsd(doc)
        parsed = read_pcsd(data)
        tags = [t.tag for t in parsed.objects[0].ext_tlvs]
        assert "futx" in tags
        futx = [t for t in parsed.objects[0].ext_tlvs if t.tag == "futx"][0]
        assert futx.payload == b"\x00\x01\x02"
        # byte stability with the extra TLV, too
        assert write_pcsd(parsed) == data

    def test_prop_styl_raw(self):
        doc = make_document()
        doc.objects = [
            PropObject(width=10, height=10, styl_raw=b"\x01\x02\x03\x04", name="s")
        ]
        parsed = read_pcsd(write_pcsd(doc))
        prop = parsed.objects[0]
        assert prop.styl_raw == b"\x01\x02\x03\x04"
        assert prop.color_matrix is None
        assert prop.skin_flags is None
        assert prop.name == "s"

    def test_prop_legacy_implicit_matrix(self):
        """block_len == 80 with no tag byte: implicit color matrix."""
        from openpcsd.io import ByteWriter
        from openpcsd.model import HEADER_LEN

        w = ByteWriter()
        w.buf += b"pcsd"
        w.i32(HEADER_LEN)
        w.i32(256)
        w.f32(10.0)
        w.f32(10.0)
        w.i32(0)
        w.i32(10)
        w.i32(10)
        w.i32(1)
        w.i64(0)
        w.i64(0)

        body = ByteWriter()
        body.i32(3)  # object id
        body.f32(4.0)  # width
        body.f32(4.0)  # height
        for v in (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0):
            body.f32(v)  # matrix
        body.i32(80)  # legacy implicit mtrx block length
        for _ in range(20):
            body.f32(0.5)
        body.write_utf("x")

        w.tag4("prop")
        w.i32(len(body.getvalue()))
        w.write(body.getvalue())

        parsed = read_pcsd(w.getvalue())
        prop = parsed.objects[0]
        assert isinstance(prop, PropObject)
        assert prop.color_matrix == tuple([0.5] * 20)
        assert prop.name == "x"


class TestLegacyHeader:
    def test_version_zero_header(self):
        """Old files without the version block (header_len 24)."""
        from openpcsd.io import ByteWriter

        w = ByteWriter()
        w.buf += b"pcsd"
        w.i32(24)
        w.i32(256)
        w.f32(100.0)
        w.f32(80.0)
        w.i32(0)
        w.i32(100)
        w.i32(80)
        doc = read_pcsd(w.getvalue())
        assert doc.doc_width == 100.0
        assert doc.version_int == 0  # absent block defaults in model


class TestErrors:
    def test_bad_magic(self):
        from openpcsd import BadMagic

        with pytest.raises(BadMagic):
            read_pcsd(b"NOTAPCSDFILE_0123456789")

    def test_unsupported_version(self):
        from openpcsd import UnsupportedVersion
        from openpcsd.io import ByteWriter

        w = ByteWriter()
        w.buf += b"pcsd"
        w.i32(24)
        w.i32(200)  # below the 256 gate
        with pytest.raises(UnsupportedVersion):
            read_pcsd(w.getvalue())
