"""In-memory model of a pcsd document and its objects.

The dataclasses mirror the wire layout one field at a time; see
``docs/FORMAT.md`` for the authoritative field tables and for which
semantics are *confirmed* vs *inferred* from the original app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .bundle import Bundle

#: 4CC tags understood by the reader.
TAG_THMB = "thmb"  # embedded preview image (PNG or JPEG)
TAG_BNDL = "bndl"  # Android-Bundle metadata
TAG_WRDB = "wrdb"  # word-balloon object
TAG_TEXT = "text"  # text object
TAG_PROP = "prop"  # prop / sticker object

#: Object ids used by convention (1-based, from the app's object registry).
ID_ZORDER_LIST = 1  # the ordered id list itself
ID_METADATA = 2  # the bndl chunk's bundle object
#: Content objects (wrdb/text/prop) use ids >= 3.
FIRST_FREE_ID = 3

#: The app's writer emits this as the header's format-version field and
#: its reader rejects anything below it.
MIN_FORMAT_VERSION = 256

#: Header length emitted by the app's writer (bytes after magic+length).
HEADER_LEN = 44


@dataclass
class StyleRef:
    """A font/style reference (the app's font-manager block).

    ``flags`` carries the typeface style bits (bit 0 bold, bit 1
    italic - the classic Android ``Typeface`` style), ``font_file`` is
    the bundled font's file name (empty string when the text uses a
    built-in family) and ``font_family`` the family name for
    platform fonts ("sans-serif", "serif", ...).
    """

    flags: int = 0
    font_file: str = ""
    font_family: str = ""


@dataclass
class ExtTLV:
    """An unparsed extension tag/length/value inside an object body."""

    tag: str
    payload: bytes


@dataclass
class DocObject:
    """Fields shared by every object stored in a pcsd document.

    ``width``/``height`` are the object's size in document units and
    ``matrix`` is the 3x3 transform in Android ``Matrix.getValues``
    order: ``[scaleX, skewX, transX, skewY, scaleY, transY, persp0,
    persp1, persp2]``.
    """

    obj_id: Optional[int] = None
    width: float = 0.0
    height: float = 0.0
    matrix: tuple[float, ...] = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    ext_tlvs: list[ExtTLV] = field(default_factory=list)
    raw_tail: bytes = b""  # bytes after the known fields that we could not name

    @property
    def tag(self) -> str:
        return "???"

    def kind(self) -> str:
        return self.__class__.__name__


@dataclass
class TextObject(DocObject):
    """A ``text`` object (the app's plain text tool).

    Field semantics beyond the wire order are partly inferred; the
    three colors are the shadow paint, the fill paint and the border
    paint of the original (all ARGB ints).
    """

    color_a: int = 0  # paint A color (shadow paint; ARGB)
    style_int: int = 0  # app-internal style/flags int
    flag_2048: bool = False  # mirrors state bit 0x800 of the original
    color_fill: int = 0xFF000000  # fill paint color (ARGB)
    stroke_width: float = 0.0
    color_stroke: int = 0xFF000000  # border paint color (ARGB)
    stroke_width2: float = 0.0  # border width (app adds stroke_width when painting)
    style: StyleRef = field(default_factory=StyleRef)
    font_size: float = 12.0  # document-unit font size
    text: str = ""

    # Extension TLVs (parsed)
    rotation: float = 0.0  # "tcrv": text curve/rotation angle, deg
    alignment: int = 0  # "lins": 0..2 (left/center/right - inferred)
    line_scale: float = 1.0  # "lins": line-spacing scale, clamped 0.01..2.0
    shadow: Optional[tuple[int, float, float, float]] = None  # "shdw"

    @property
    def tag(self) -> str:
        return TAG_TEXT


@dataclass
class BalloonObject(DocObject):
    """A ``wrdb`` (word balloon) object - the app's signature feature.

    The app exposes 16 balloon shapes; ``shape`` is the low nibble of
    the object's state int.  ``tail_x``/``tail_y``/``tail_scale``
    position and size the balloon's pointer (semantics inferred).
    """

    min_w: float = 0.0  # "m" - minimum body width (inferred)
    min_h: float = 0.0  # "n" - minimum body height (inferred)
    pad_w: float = 0.0  # "k" - body padding width (inferred)
    pad_h: float = 0.0  # "l" - body padding height (inferred)
    int_a: int = 0  # "x"
    int_b: int = 0  # "y"
    flag_2048: bool = False
    int_v: int = 0
    float_w: float = 0.0
    flag_1024: bool = False
    int_r: int = 0
    float_s: float = 0.0
    float_t: float = 0.0
    float_u: float = 0.0
    int_e: int = 0
    style: StyleRef = field(default_factory=StyleRef)
    shape: int = 0  # balloon shape, 0..15 (confirmed: state & 15)
    tail_x: float = 0.0  # "o" (inferred)
    tail_y: float = 0.0  # "p" (inferred)
    tail_scale: float = 1.0  # product of two scale floats on write (inferred)
    text: str = ""
    line_scale: float = 1.0  # "lins" extension

    @property
    def tag(self) -> str:
        return TAG_WRDB


@dataclass
class PropObject(DocObject):
    """A ``prop`` (sticker) object.

    The body is a small nested block structure: at most one color
    matrix (Android ``ColorMatrix``, 20 floats), an optional int of
    skin flags, or an opaque style blob written by the app's sticker
    machinery (preserved as raw bytes).
    """

    color_matrix: Optional[tuple[float, ...]] = None  # 20 floats, Android ColorMatrix
    skin_flags: Optional[int] = None
    styl_raw: Optional[bytes] = None
    name: str = ""  # resource/name reference

    @property
    def tag(self) -> str:
        return TAG_PROP


@dataclass
class Thumbnail:
    """The embedded ``thmb`` preview image."""

    data: bytes  # raw PNG or JPEG file bytes
    codec: str = "png"  # "png" or "jpeg"

    @classmethod
    def detect(cls, data: bytes) -> "Thumbnail":
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return cls(data=data, codec="png")
        if data[:3] == b"\xff\xd8\xff":
            return cls(data=data, codec="jpeg")
        return cls(data=data, codec="unknown")


@dataclass
class UnknownChunk:
    """A container chunk with an unknown 4CC tag (payload preserved)."""

    tag: str
    payload: bytes


@dataclass
class PcsdDocument:
    """A complete in-memory pcsd main document."""

    # Header
    format_version: int = MIN_FORMAT_VERSION
    doc_width: float = 0.0  # document-unit width
    doc_height: float = 0.0
    pixel_width: int = 0
    pixel_height: int = 0
    version_int: int = 1  # app version block; >= 1 enables long fields
    version_long: int = 0
    timestamp: int = 0

    # Payload
    thumbnail: Optional[Thumbnail] = None
    bundle: Optional[Bundle] = None  # metadata (bndl chunk)
    objects: list[DocObject] = field(default_factory=list)  # z-order, bottom first
    other_chunks: list[UnknownChunk] = field(default_factory=list)

    def next_free_id(self) -> int:
        used = {o.obj_id for o in self.objects if o.obj_id is not None}
        candidate = FIRST_FREE_ID
        while candidate in used:
            candidate += 1
        return candidate

    def assign_ids(self) -> None:
        """Give every id-less object a fresh id (stable, in z-order)."""
        for obj in self.objects:
            if obj.obj_id is None:
                obj.obj_id = self.next_free_id()

    # --- convenience -----------------------------------------------
    def texts(self) -> list[TextObject]:
        return [o for o in self.objects if isinstance(o, TextObject)]

    def balloons(self) -> list[BalloonObject]:
        return [o for o in self.objects if isinstance(o, BalloonObject)]

    def props(self) -> list[PropObject]:
        return [o for o in self.objects if isinstance(o, PropObject)]
