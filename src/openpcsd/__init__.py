"""openpcsd - a clean-room reader/writer for PicSay ``.pcsd`` documents.

The PicSay / PicSay Pro Android photo editors (Shinycore, 2008-2024)
saved projects in a custom ``.pcsd`` format.  The apps are no longer
distributed, but documents live on; this library keeps them readable,
writable and convertible - implemented from the public format
specification in ``docs/FORMAT.md``, with no code from the original
app.

Quick start::

    from openpcsd import read_pcsd, write_pcsd

    doc = read_pcsd(open("vacation.pcsd", "rb").read())
    for obj in doc.objects:
        print(obj.tag, getattr(obj, "text", ""))
    open("copy.pcsd", "wb").write(write_pcsd(doc))
"""

from .bundle import Bundle, Float, Long, Short, read_bundle, write_bundle
from .io import (
    APP_UTF_LIMIT,
    PcsdError,
    Truncated,
    UtfLimitError,
    UtfOverflowError,
    decode_mutf8,
    encode_mutf8,
)
from .model import (
    BalloonObject,
    DocObject,
    ExtTLV,
    ID_METADATA,
    ID_ZORDER_LIST,
    MIN_FORMAT_VERSION,
    PcsdDocument,
    PropObject,
    StyleRef,
    TextObject,
    Thumbnail,
    UnknownChunk,
)
from .reader import BadMagic, UnsupportedVersion, read_header, read_pcsd
from .sidecars import (
    MAX_EXIF_SIZE,
    SidecarPaths,
    extract_exif,
    make_dat,
    read_dat,
    sidecar_paths,
    write_dat,
)
from .writer import write_pcsd

__version__ = "0.1.0"

__all__ = [
    # container
    "read_pcsd",
    "write_pcsd",
    "read_header",
    # model
    "PcsdDocument",
    "DocObject",
    "TextObject",
    "BalloonObject",
    "PropObject",
    "UnknownObject",
    "UnknownChunk",
    "Thumbnail",
    "StyleRef",
    "ExtTLV",
    "ID_METADATA",
    "ID_ZORDER_LIST",
    "MIN_FORMAT_VERSION",
    # bundle
    "Bundle",
    "read_bundle",
    "write_bundle",
    "Short",
    "Long",
    "Float",
    # strings
    "encode_mutf8",
    "decode_mutf8",
    "APP_UTF_LIMIT",
    "UtfLimitError",
    "UtfOverflowError",
    # sidecars
    "SidecarPaths",
    "sidecar_paths",
    "read_dat",
    "write_dat",
    "extract_exif",
    "make_dat",
    "MAX_EXIF_SIZE",
    # errors
    "PcsdError",
    "BadMagic",
    "UnsupportedVersion",
    "Truncated",
    "__version__",
]
