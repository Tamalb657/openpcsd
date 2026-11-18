"""Unit tests for the low-level io primitives (modified UTF-8, BE)."""

import pytest

from openpcsd.io import (
    APP_UTF_LIMIT,
    ByteReader,
    ByteWriter,
    UtfLimitError,
    decode_mutf8,
    encode_mutf8,
)


class TestModifiedUtf8:
    def test_ascii_roundtrip(self):
        s = "Hello, PicSay!"
        assert decode_mutf8(encode_mutf8(s)) == s

    def test_nul_encoded_as_two_bytes(self):
        encoded = encode_mutf8("a\x00b", enforce_app_limit=False)
        # U+0000 becomes 0xC0 0x80, never a raw 0x00 byte
        assert encoded == b"a\xc0\x80b"
        assert decode_mutf8(encoded) == "a\x00b"

    def test_latin1_two_byte_region(self):
        s = "caf\u00e9"
        encoded = encode_mutf8(s)
        assert len(encoded) == 5  # 1 + 2 + 2
        assert decode_mutf8(encoded) == s

    def test_cjk_three_byte(self):
        s = "\u4f60\u597d"  # ni hao
        encoded = encode_mutf8(s)
        assert len(encoded) == 6
        assert decode_mutf8(encoded) == s

    def test_supplementary_uses_surrogate_pair(self):
        s = "\U0001f600"  # emoji, > U+FFFF
        encoded = encode_mutf8(s)
        # Java writes two 3-byte surrogate sequences, never a 4-byte form
        assert len(encoded) == 6
        assert b"\xf0" not in encoded
        assert decode_mutf8(encoded) == s

    def test_mixed(self):
        s = "PicSay caf\u00e9 \u4f60\u597d \U0001f44d \x00 end"
        assert decode_mutf8(encode_mutf8(s, enforce_app_limit=False)) == s

    def test_app_limit_enforced(self):
        with pytest.raises(UtfLimitError):
            encode_mutf8("x" * (APP_UTF_LIMIT + 1))
        # exactly at the limit is fine
        encode_mutf8("x" * APP_UTF_LIMIT)

    def test_write_utf_prefix(self):
        w = ByteWriter()
        w.write_utf("abc")
        assert w.getvalue() == b"\x00\x03abc"


class TestPrimitives:
    def test_roundtrip_all(self):
        w = ByteWriter()
        w.i32(-202116108)  # "pcsd" as signed int, why not
        w.i64(-(2**40) + 123)
        w.f32(3.5)
        w.f64(-0.125)
        w.boolean(True)
        w.i16(-2)
        w.tag4("thmb")
        r = ByteReader(w.getvalue())
        assert r.i32() == -202116108
        assert r.i64() == -(2**40) + 123
        assert r.f32() == 3.5
        assert r.f64() == -0.125
        assert r.boolean() is True
        assert r.i16() == -2
        assert r.tag4() == "thmb"
        assert r.remaining() == 0

    def test_truncated_raises(self):
        r = ByteReader(b"\x00\x00")
        with pytest.raises(Exception):
            r.i32()
