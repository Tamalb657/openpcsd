"""Container-level reader for ``.pcsd`` documents.

Layout (all big-endian)::

    "pcsd"          4CC magic
    int32           header_len (44 for current files; the reader skips
                    header bytes it does not understand via this value)
    int32           format_version (must be >= 256)
    float32         doc_width
    float32         doc_height
    int32           reserved
    int32           pixel_width
    int32           pixel_height
    int32           version_int    (>= 1 enables the two int64 fields)
    int64           version_long
    int64           timestamp
    chunks until EOF (stop when <= 8 bytes remain):
        int32       tag (4CC)
        int32       payload_len
        bytes       payload
"""

from __future__ import annotations

from .bundle import read_bundle
from .io import ByteReader, PcsdError
from .model import (
    MIN_FORMAT_VERSION,
    PcsdDocument,
    Thumbnail,
    UnknownChunk,
)
from .objects import PARSERS

MAGIC = b"pcsd"

#: The original reader stops looking for chunks when this many bytes
#: (or fewer) remain.
STOP_MARGIN = 8


class BadMagic(PcsdError):
    """The file does not start with the ``pcsd`` magic."""


class UnsupportedVersion(PcsdError):
    """The header's format version is below the app's minimum (256)."""


def read_pcsd(data: bytes) -> PcsdDocument:
    """Parse a complete ``.pcsd`` main document from *data*."""
    r = ByteReader(data)

    if r.read(4) != MAGIC:
        raise BadMagic("not a pcsd file (missing 'pcsd' magic)")
    header_len = r.i32()
    if header_len < 24:
        raise PcsdError(f"implausible header length {header_len}")

    doc = PcsdDocument()
    doc.version_int = 0  # stays 0 for legacy files without the block
    _read_header_fields(r, doc, header_len)
    _read_chunks(r, doc)
    return doc


def read_header(data: bytes) -> PcsdDocument:
    """Parse only the header (the app's "quick look" mode)."""
    r = ByteReader(data)
    if r.read(4) != MAGIC:
        raise BadMagic("not a pcsd file (missing 'pcsd' magic)")
    header_len = r.i32()
    doc = PcsdDocument()
    doc.version_int = 0
    _read_header_fields(r, doc, header_len)
    return doc


def _read_header_fields(r: ByteReader, doc: PcsdDocument, header_len: int) -> None:
    doc.format_version = r.i32()
    if doc.format_version < MIN_FORMAT_VERSION:
        raise UnsupportedVersion(
            f"format version {doc.format_version} < minimum {MIN_FORMAT_VERSION}"
        )
    doc.doc_width = r.f32()
    doc.doc_height = r.f32()
    r.i32()  # reserved
    doc.pixel_width = r.i32()
    doc.pixel_height = r.i32()

    optional = header_len - 24
    if optional >= 20:
        doc.version_int = r.i32()
        optional -= 4
        if doc.version_int >= 1:
            doc.version_long = r.i64()
            doc.timestamp = r.i64()
            optional -= 16
    if optional > 0:
        r.skip(optional)  # header extension we do not know (forward compat)


def _read_chunks(r: ByteReader, doc: PcsdDocument) -> None:
    while r.remaining() > STOP_MARGIN:
        tag = r.tag4()
        length = r.i32()
        payload = r.read(length)

        if tag == "thmb":
            doc.thumbnail = Thumbnail.detect(payload)
        elif tag == "bndl":
            doc.bundle = read_bundle(ByteReader(payload))
        elif tag in PARSERS:
            br = ByteReader(payload)
            # The id field is always present; it is only *used* as the
            # object id when the version block says >= 1.
            id_value = br.i32()
            obj = PARSERS[tag](br, len(payload) - 4)
            obj.obj_id = id_value if doc.version_int >= 1 else None
            doc.objects.append(obj)
        else:
            # The original reader skips unknown chunks entirely; we keep
            # their payloads verbatim so files round-trip losslessly.
            doc.other_chunks.append(UnknownChunk(tag=tag, payload=payload))
