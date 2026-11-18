"""Unit tests for the Android-Bundle wire format."""

from openpcsd.bundle import Float, Long, Short, read_bundle, write_bundle
from openpcsd.io import ByteReader, ByteWriter


def roundtrip(bundle):
    w = ByteWriter()
    write_bundle(w, bundle)
    return read_bundle(ByteReader(w.getvalue()))


def test_all_value_types():
    bundle = {
        "str": "hello \u4f60\u597d",
        "int": -42,
        "nested": {"inner": 1, "deep": {"x": 2}},
        "short": Short(300),
        "long": Long(2**40),
        "float": Float(1.5),
        "double": 2.25,
        "bool": True,
        "iarr": [1, 2, 3, -4],
        "nothing": None,
    }
    out = roundtrip(bundle)
    assert out == bundle
    # exact wire types preserved
    assert type(out["short"]) is Short
    assert type(out["long"]) is Long
    assert type(out["float"]) is Float
    assert type(out["int"]) is int
    assert type(out["double"]) is float


def test_empty_bundle():
    assert roundtrip({}) == {}


def test_key_order_preserved():
    bundle = {k: i for i, k in enumerate(["z", "a", "m", "b"])}
    out = roundtrip(bundle)
    assert list(out.keys()) == ["z", "a", "m", "b"]


def test_wire_bytes_stable():
    bundle = {"a": 1, "b": "x", "c": [1, 2]}
    w1, w2 = ByteWriter(), ByteWriter()
    write_bundle(w1, bundle)
    write_bundle(w2, roundtrip(bundle))
    assert w1.getvalue() == w2.getvalue()


def test_short_distinguished_from_int():
    # Short and int serialize with different type tags but compare equal
    w = ByteWriter()
    write_bundle(w, {"a": Short(7), "b": 7})
    data = w.getvalue()
    # count(int32=2), key u16+"a", type tag 5 (short), int16 value,
    # key u16+"b", type tag 1 (int), int32 value
    assert data == (
        b"\x00\x00\x00\x02"          # entry count
        b"\x00\x01a"                 # key "a"
        b"\x00\x00\x00\x05"          # type: short
        b"\x00\x07"                  # int16 value
        b"\x00\x01b"                 # key "b"
        b"\x00\x00\x00\x01"          # type: int
        b"\x00\x00\x00\x07"          # int32 value
    )
