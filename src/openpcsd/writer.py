"""Container-level writer for ``.pcsd`` documents.

Produces files byte-compatible with the original app's format: the
same header, the same chunk order (``thmb``, ``bndl``, then objects in
z-order), the same conditional extension TLVs.

Documents parsed from legacy (version-0) files are upgraded to
version 1 on write - the original reader accepts both.
"""

from __future__ import annotations

from .bundle import write_bundle
from .io import ByteWriter
from .model import HEADER_LEN, BalloonObject, PcsdDocument, PropObject, TextObject
from .objects import write_balloon, write_prop, write_text


def write_pcsd(doc: PcsdDocument) -> bytes:
    """Serialize *doc* to pcsd bytes."""
    doc.assign_ids()
    w = ByteWriter()

    # --- header -------------------------------------------------------
    w.buf += b"pcsd"
    w.i32(HEADER_LEN)
    w.i32(doc.format_version if doc.format_version >= 256 else 256)
    w.f32(doc.doc_width)
    w.f32(doc.doc_height)
    w.i32(0)  # reserved
    w.i32(doc.pixel_width)
    w.i32(doc.pixel_height)
    w.i32(max(1, doc.version_int))  # legacy docs upgrade to v1
    w.i64(doc.version_long)
    w.i64(doc.timestamp)

    # --- chunks -------------------------------------------------------
    if doc.thumbnail is not None:
        _chunk(w, "thmb", doc.thumbnail.data)
    if doc.bundle:
        bw = ByteWriter()
        write_bundle(bw, doc.bundle)
        _chunk(w, "bndl", bw.getvalue())
    for obj in doc.objects:
        body = ByteWriter()
        if isinstance(obj, TextObject):
            write_text(body, obj)
        elif isinstance(obj, BalloonObject):
            write_balloon(body, obj)
        elif isinstance(obj, PropObject):
            write_prop(body, obj)
        else:
            raise TypeError(f"cannot serialize object of type {type(obj).__name__}")
        payload = ByteWriter()
        payload.i32(obj.obj_id if obj.obj_id is not None else 0)
        payload.write(body.getvalue())
        _chunk(w, obj.tag, payload.getvalue())
    for chunk in doc.other_chunks:
        _chunk(w, chunk.tag, chunk.payload)
    return w.getvalue()


def _chunk(w: ByteWriter, tag: str, payload: bytes) -> None:
    w.tag4(tag)
    w.i32(len(payload))
    w.write(payload)
