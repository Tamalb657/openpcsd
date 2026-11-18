"""Low-level primitives shared by the pcsd reader and writer.

Everything in a pcsd stream is big-endian.  Strings use Java's
*modified UTF-8* (see ``docs/FORMAT.md``) with a two-byte length
prefix, and the original writer refuses any string longer than 2730
UTF-16 code units.
"""

from __future__ import annotations

import struct

#: The original app's writer refuses strings longer than this many
#: UTF-16 code units (the limit in the app's buffered DataOutputStream).
APP_UTF_LIMIT = 2730


class PcsdError(Exception):
    """Base class for all openpcsd errors."""


class Truncated(PcsdError):
    """The byte stream ended in the middle of a structure."""


class UtfLimitError(PcsdError):
    """A string exceeds the app's 2730-code-unit limit."""


class UtfOverflowError(PcsdError):
    """A string's modified-UTF-8 encoding exceeds 65535 bytes."""


def _utf16_units(s: str) -> list[int]:
    """Return the UTF-16 code units of *s* (how Java sees a String)."""
    units: list[int] = []
    for ch in s:
        cp = ord(ch)
        if cp > 0xFFFF:
            cp -= 0x10000
            units.append(0xD800 | (cp >> 10))
            units.append(0xDC00 | (cp & 0x3FF))
        else:
            units.append(cp)
    return units


def _units_to_str(units: list[int]) -> str:
    """Combine UTF-16 code units into a Python string.

    Surrogate pairs are joined; lone surrogates are preserved (Java
    tolerates them and so do we).
    """
    out: list[str] = []
    i = 0
    n = len(units)
    while i < n:
        u = units[i]
        if 0xD800 <= u <= 0xDBFF and i + 1 < n and 0xDC00 <= units[i + 1] <= 0xDFFF:
            out.append(chr(0x10000 + ((u - 0xD800) << 10) + (units[i + 1] - 0xDC00)))
            i += 2
        else:
            out.append(chr(u))
            i += 1
    return "".join(out)


def encode_mutf8(s: str, enforce_app_limit: bool = True) -> bytes:
    """Encode *s* as Java modified UTF-8 (without the length prefix).

    Differences from standard UTF-8:

    * ``U+0000`` is encoded as the two bytes ``0xC0 0x80``;
    * supplementary characters (``> U+FFFF``) are encoded as *two*
      three-byte sequences (one per UTF-16 surrogate), never as the
      four-byte form.

    Raises :class:`UtfLimitError` when the string is longer than the
    app's 2730-code-unit limit (unless *enforce_app_limit* is false)
    and :class:`UtfOverflowError` when the encoding cannot fit in a
    two-byte length prefix.
    """
    units = _utf16_units(s)
    if enforce_app_limit and len(units) > APP_UTF_LIMIT:
        raise UtfLimitError(
            f"string has {len(units)} UTF-16 code units; the app limit is {APP_UTF_LIMIT}"
        )
    out = bytearray()
    for u in units:
        if u != 0 and u < 0x80:
            out.append(u)
        elif u < 0x800:  # includes U+0000
            out.append(0xC0 | (u >> 6))
            out.append(0x80 | (u & 0x3F))
        else:
            out.append(0xE0 | (u >> 12))
            out.append(0x80 | ((u >> 6) & 0x3F))
            out.append(0x80 | (u & 0x3F))
    if len(out) > 0xFFFF:
        raise UtfOverflowError("modified-UTF-8 encoding exceeds 65535 bytes")
    return bytes(out)


def decode_mutf8(data: bytes) -> str:
    """Decode Java modified UTF-8 bytes (without a length prefix)."""
    units: list[int] = []
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b < 0x80 and b != 0:
            units.append(b)
            i += 1
        elif 0xC0 <= b <= 0xDF and i + 1 < n:
            units.append(((b & 0x1F) << 6) | (data[i + 1] & 0x3F))
            i += 2
        elif 0xE0 <= b <= 0xEF and i + 2 < n:
            units.append(((b & 0x0F) << 12) | ((data[i + 1] & 0x3F) << 6) | (data[i + 2] & 0x3F))
            i += 3
        else:
            raise PcsdError(f"invalid modified-UTF-8 byte 0x{b:02x} at offset {i}")
    return _units_to_str(units)


class ByteReader:
    """Cursor over a ``bytes`` object with big-endian primitives."""

    __slots__ = ("data", "pos")

    def __init__(self, data: bytes, pos: int = 0) -> None:
        self.data = data
        self.pos = pos

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def read(self, n: int) -> bytes:
        if n < 0 or self.remaining() < n:
            raise Truncated(f"need {n} bytes at offset {self.pos}, have {self.remaining()}")
        chunk = self.data[self.pos : self.pos + n]
        self.pos += n
        return chunk

    def skip(self, n: int) -> None:
        if n < 0 or self.remaining() < n:
            raise Truncated(f"cannot skip {n} bytes at offset {self.pos}")
        self.pos += n

    # --- typed reads --------------------------------------------------
    def u8(self) -> int:
        return self.read(1)[0]

    def boolean(self) -> bool:
        return self.read(1)[0] != 0

    def i16(self) -> int:
        return int.from_bytes(self.read(2), "big", signed=True)

    def u16(self) -> int:
        return int.from_bytes(self.read(2), "big", signed=False)

    def i32(self) -> int:
        return int.from_bytes(self.read(4), "big", signed=True)

    def u32(self) -> int:
        return int.from_bytes(self.read(4), "big", signed=False)

    def i64(self) -> int:
        return int.from_bytes(self.read(8), "big", signed=True)

    def f32(self) -> float:
        return struct.unpack(">f", self.read(4))[0]

    def f64(self) -> float:
        return struct.unpack(">d", self.read(8))[0]

    def read_utf(self) -> str:
        length = self.u16()
        return decode_mutf8(self.read(length))

    def tag4(self) -> str:
        """Read a four-character code such as ``'pcsd'`` or ``'thmb'``."""
        return self.read(4).decode("latin-1")


class ByteWriter:
    """Growable byte buffer with big-endian primitives."""

    __slots__ = ("buf",)

    def __init__(self) -> None:
        self.buf = bytearray()

    def getvalue(self) -> bytes:
        return bytes(self.buf)

    def __len__(self) -> int:
        return len(self.buf)

    # --- typed writes -------------------------------------------------
    def write(self, data: bytes) -> None:
        self.buf += data

    def u8(self, v: int) -> None:
        self.buf.append(v & 0xFF)

    def boolean(self, v: bool) -> None:
        self.buf.append(1 if v else 0)

    def i16(self, v: int) -> None:
        self.buf += int(v & 0xFFFF).to_bytes(2, "big")

    def i32(self, v: int) -> None:
        self.buf += int(v & 0xFFFFFFFF).to_bytes(4, "big")

    def i64(self, v: int) -> None:
        self.buf += int(v & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "big")

    def f32(self, v: float) -> None:
        self.buf += struct.pack(">f", v)

    def f64(self, v: float) -> None:
        self.buf += struct.pack(">d", v)

    def write_utf(self, s: str, enforce_app_limit: bool = True) -> None:
        encoded = encode_mutf8(s, enforce_app_limit=enforce_app_limit)
        self.buf += len(encoded).to_bytes(2, "big")
        self.buf += encoded

    def tag4(self, s: str) -> None:
        if len(s) != 4:
            raise ValueError("4CC tags are exactly four characters")
        self.buf += s.encode("latin-1")
