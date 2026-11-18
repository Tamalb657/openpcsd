"""Per-object payload parsers and writers.

Field order is exactly the wire order of the original app's reader /
writer pair; see ``docs/FORMAT.md`` for the tables.
"""

from __future__ import annotations

from .io import ByteReader, ByteWriter
from .model import (
    BalloonObject,
    DocObject,
    ExtTLV,
    PropObject,
    StyleRef,
    TextObject,
)

# Extension TLV tags inside object bodies.
EXT_LINS = "lins"  # int + float: alignment + line-spacing scale
EXT_TCRV = "tcrv"  # float: text curve / rotation angle
EXT_SHDW = "shdw"  # int + 3 floats: shadow parameters
EXT_MTRX = "mtrx"  # 20 floats: Android ColorMatrix (prop)
EXT_SKIN = "skin"  # int: prop skin/flags
EXT_STYL = "styl"  # opaque sticker-style blob (prop)

_KNOWN_EXT = (EXT_LINS, EXT_TCRV, EXT_SHDW, EXT_MTRX, EXT_SKIN, EXT_STYL)


# --------------------------------------------------------------------------
# shared sub-blocks
# --------------------------------------------------------------------------

def read_style(r: ByteReader) -> StyleRef:
    """int flags + mutf8 font-file name + mutf8 font family name."""
    flags = r.i32()
    font_file = r.read_utf()
    font_family = r.read_utf()
    return StyleRef(flags=flags, font_file=font_file, font_family=font_family)


def write_style(w: ByteWriter, style: StyleRef) -> None:
    w.i32(style.flags)
    w.write_utf(style.font_file)
    w.write_utf(style.font_family)


def read_common(r: ByteReader, obj: DocObject) -> None:
    """The base-object block: width, height, 3x3 transform matrix."""
    obj.width = r.f32()
    obj.height = r.f32()
    obj.matrix = tuple(r.f32() for _ in range(9))


def write_common(w: ByteWriter, obj: DocObject) -> None:
    w.f32(obj.width)
    w.f32(obj.height)
    for v in obj.matrix:
        w.f32(v)


def _read_ext_tlvs(r: ByteReader, body_len: int, consumed: int) -> tuple[list[ExtTLV], bytes]:
    """Read trailing tag/len/value extensions until the body is spent.

    Mirrors the app's loop: while at least 8 bytes (tag + length) are
    left, read the pair; a zero tag or a non-positive length means the
    remainder is not TLV data.  Unlike the app (which drops those 8
    bytes) we rewind so the raw bytes survive in ``raw_tail``.
    """
    tlvs: list[ExtTLV] = []
    while body_len - consumed >= 8:
        tag_int = r.i32()
        length = r.i32()
        valid = tag_int != 0 and 0 < length <= r.remaining()
        if not valid:
            r.pos -= 8  # rewind: keep the 8 bytes as raw tail
            break
        payload = r.read(length)
        consumed += 8 + length
        tag = tag_int.to_bytes(4, "big", signed=True).decode("latin-1")
        tlvs.append(ExtTLV(tag=tag, payload=payload))
    tail = r.read(max(0, body_len - consumed))
    return tlvs, tail


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------

def parse_text(r: ByteReader, body_len: int) -> TextObject:
    obj = TextObject()
    read_common(r, obj)
    consumed = 44

    obj.color_a = r.i32()
    obj.style_int = r.i32()
    obj.flag_2048 = r.boolean()
    obj.color_fill = r.i32()
    obj.stroke_width = r.f32()
    obj.color_stroke = r.i32()
    obj.stroke_width2 = r.f32()
    obj.style = read_style(r)
    obj.font_size = r.f32()
    obj.text = r.read_utf()
    consumed += 25  # 6 ints/floats + 1 boolean above
    consumed += 4 + _mutf_len(obj.style.font_file) + _mutf_len(obj.style.font_family)
    consumed += 4 + _mutf_len(obj.text)

    tlvs, tail = _read_ext_tlvs(r, body_len, consumed)
    obj.ext_tlvs = tlvs
    obj.raw_tail = tail
    for tlv in tlvs:
        tr = ByteReader(tlv.payload)
        if tlv.tag == EXT_TCRV and len(tlv.payload) >= 4:
            obj.rotation = tr.f32()
        elif tlv.tag == EXT_LINS and len(tlv.payload) >= 8:
            obj.alignment = tr.i32() & 3
            obj.line_scale = tr.f32()
        elif tlv.tag == EXT_SHDW and len(tlv.payload) >= 16:
            obj.shadow = (tr.i32(), tr.f32(), tr.f32(), tr.f32())
    return obj


def write_text(w: ByteWriter, obj: TextObject) -> None:
    write_common(w, obj)
    w.i32(obj.color_a)
    w.i32(obj.style_int)
    w.boolean(obj.flag_2048)
    w.i32(obj.color_fill)
    w.f32(obj.stroke_width)
    w.i32(obj.color_stroke)
    w.f32(obj.stroke_width2)
    write_style(w, obj.style)
    w.f32(obj.font_size)
    w.write_utf(obj.text)

    # Extension TLVs, in the original writer's order.
    if obj.rotation != 0.0:
        w.tag4(EXT_TCRV)
        w.i32(4)
        w.f32(obj.rotation)
    if obj.alignment != 0 or obj.line_scale != 1.0:
        w.tag4(EXT_LINS)
        w.i32(8)
        w.i32(obj.alignment)
        w.f32(obj.line_scale)
    if obj.shadow is not None:
        a, b, c, d = obj.shadow
        w.tag4(EXT_SHDW)
        w.i32(16)
        w.i32(a)
        w.f32(b)
        w.f32(c)
        w.f32(d)
    _write_leftover(w, obj)


# --------------------------------------------------------------------------
# word balloon
# --------------------------------------------------------------------------

def parse_balloon(r: ByteReader, body_len: int) -> BalloonObject:
    obj = BalloonObject()
    read_common(r, obj)
    consumed = 44

    obj.min_w = r.f32()
    obj.min_h = r.f32()
    obj.pad_w = r.f32()
    obj.pad_h = r.f32()
    obj.int_a = r.i32()
    obj.int_b = r.i32()
    obj.flag_2048 = r.boolean()
    obj.int_v = r.i32()
    obj.float_w = r.f32()
    obj.flag_1024 = r.boolean()
    obj.int_r = r.i32()
    obj.float_s = r.f32()
    obj.float_t = r.f32()
    obj.float_u = r.f32()
    obj.int_e = r.i32()
    obj.style = read_style(r)
    obj.shape = r.i32() & 15
    obj.tail_x = r.f32()
    obj.tail_y = r.f32()
    obj.tail_scale = r.f32()
    obj.text = r.read_utf()

    consumed += 54  # fixed fields above
    consumed += 4 + _mutf_len(obj.style.font_file) + _mutf_len(obj.style.font_family)
    consumed += 16 + _mutf_len(obj.text)

    tlvs, tail = _read_ext_tlvs(r, body_len, consumed)
    obj.ext_tlvs = tlvs
    obj.raw_tail = tail
    for tlv in tlvs:
        if tlv.tag == EXT_LINS and len(tlv.payload) >= 8:
            tr = ByteReader(tlv.payload)
            tr.i32()  # alignment slot; the original reader discards it
            obj.line_scale = tr.f32()
    return obj


def write_balloon(w: ByteWriter, obj: BalloonObject) -> None:
    write_common(w, obj)
    w.f32(obj.min_w)
    w.f32(obj.min_h)
    w.f32(obj.pad_w)
    w.f32(obj.pad_h)
    w.i32(obj.int_a)
    w.i32(obj.int_b)
    w.boolean(obj.flag_2048)
    w.i32(obj.int_v)
    w.f32(obj.float_w)
    w.boolean(obj.flag_1024)
    w.i32(obj.int_r)
    w.f32(obj.float_s)
    w.f32(obj.float_t)
    w.f32(obj.float_u)
    w.i32(obj.int_e)
    write_style(w, obj.style)
    w.i32(obj.shape & 15)
    w.f32(obj.tail_x)
    w.f32(obj.tail_y)
    w.f32(obj.tail_scale)
    w.write_utf(obj.text)
    if obj.line_scale != 1.0:
        w.tag4(EXT_LINS)
        w.i32(8)
        w.i32(0)
        w.f32(obj.line_scale)
    _write_leftover(w, obj)


# --------------------------------------------------------------------------
# prop / sticker
# --------------------------------------------------------------------------

def parse_prop(r: ByteReader, body_len: int) -> PropObject:
    obj = PropObject()
    read_common(r, obj)
    consumed = 44

    block_len = r.i32()
    consumed += 4

    # Nested block: a chain of [tag][fixed-size content] sub-blocks,
    # with NO per-entry length fields - each tag has an implicit size
    # ("mtrx" = 80 bytes, "skin" = 4 bytes, "styl" = the rest).  The
    # whole chain is sized by block_len.  A block_len of exactly 80 is
    # an implicit "mtrx" written by an even older writer (no tag).
    if block_len == 80:
        obj.color_matrix = tuple(r.f32() for _ in range(20))
        consumed += 80
    elif block_len >= 4:
        tag = r.tag4()
        consumed += 4
        remaining = block_len - 4
        while True:
            if tag == EXT_MTRX and remaining >= 80:
                obj.color_matrix = tuple(r.f32() for _ in range(20))
                consumed += 80
                remaining -= 80
            elif tag == EXT_SKIN and remaining >= 4:
                obj.skin_flags = r.i32()
                consumed += 4
                remaining -= 4
            elif tag == EXT_STYL and remaining <= r.remaining():
                obj.styl_raw = r.read(remaining)
                consumed += remaining
                remaining = 0
                break
            else:
                # Unknown tag: the original skips the rest of the block.
                r.skip(remaining)
                consumed += remaining
                remaining = 0
                break
            if remaining < 4:
                break
            tag = r.tag4()
            consumed += 4
            remaining -= 4
        if remaining > 0:
            r.skip(remaining)
            consumed += remaining

    obj.name = r.read_utf()
    consumed += _mutf_len(obj.name)
    obj.raw_tail = r.read(max(0, body_len - consumed))
    return obj


def write_prop(w: ByteWriter, obj: PropObject) -> None:
    write_common(w, obj)
    if obj.styl_raw is not None:
        w.i32(len(obj.styl_raw) + 4)
        w.tag4(EXT_STYL)
        w.write(obj.styl_raw)
    else:
        extra = 8 if obj.skin_flags is not None else 0
        if obj.color_matrix is not None:
            w.i32(extra + 84)
            w.tag4(EXT_MTRX)
            for v in obj.color_matrix:
                w.f32(v)
        else:
            w.i32(extra)
        if obj.skin_flags is not None:
            w.tag4(EXT_SKIN)
            w.i32(obj.skin_flags)
    w.write_utf(obj.name)
    _write_leftover(w, obj)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _mutf_len(s: str) -> int:
    """Byte size of a string as written on the wire (length prefix incl.)."""
    from .io import encode_mutf8

    return len(encode_mutf8(s, enforce_app_limit=False)) + 2


def _write_leftover(w: ByteWriter, obj: DocObject) -> None:
    """Re-emit unknown extension TLVs and raw tail bytes, if any."""
    for tlv in obj.ext_tlvs:
        if tlv.tag in _KNOWN_EXT:
            continue  # already written through parsed fields
        w.tag4(tlv.tag)
        w.i32(len(tlv.payload))
        w.write(tlv.payload)
    if obj.raw_tail:
        w.write(obj.raw_tail)


PARSERS = {
    "text": parse_text,
    "wrdb": parse_balloon,
    "prop": parse_prop,
}
