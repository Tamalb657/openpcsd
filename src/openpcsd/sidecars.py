"""Sidecar files: the ``.dat`` EXIF container and path resolution.

A saved project is not a single file.  For a document at
``/path/to/name.pcsd`` the app also writes, next to it:

``/path/to/name.msk``   user mask (alpha selections), a native
                        *TimImageProxy* image written by libImageOp.so
``/path/to/name.dat``   EXIF metadata rescued from the source photo
                        (chunked container; see below)
``/path/to/name.pxy``   mipmap pyramid proxy of the working image
                        (native format)
``/path/to/name`` or    the *original, unedited* source image, kept
``/path/to/name.imd``   byte-for-byte (or as ``.imd`` when the base
                        path itself is not usable as a file name)

Only the ``.pcsd`` main document and the ``.dat`` container are pure
Java-side formats; the image sidecars are written by native code and
are out of scope for this library (see ``docs/FORMAT.md``).

``.dat`` layout::

    repeat until EOF:
        int32   tag (4CC; the app scans for "exif")
        int32   payload_len
        bytes   payload

The reader skips unknown tags, so the container is extensible.  The
"exif" payload is a TIFF-style EXIF structure ("II*\\0" / "MM\\0*"
endianness marker followed by IFD0 with Exif/GPS/Interop sub-IFDs).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .io import ByteReader, ByteWriter, PcsdError

EXIF_TAG = b"exif"

#: The app refuses "exif" payloads larger than 1 MiB.
MAX_EXIF_SIZE = 1024 * 1024


@dataclass(frozen=True)
class SidecarPaths:
    """File names associated with a pcsd document path."""

    document: str
    base: str  # document path without its extension
    source_image: str  # base + ".imd" (preferred by this library)
    source_image_alt: str  # the bare base path (app checks this first)
    mask: str  # base + ".msk"
    metadata: str  # base + ".dat"
    proxy: str  # base + ".pxy"

    def existing(self) -> dict[str, str]:
        """Map role -> path for the sidecars that exist on disk."""
        roles = {
            "document": self.document,
            "source_image": self.source_image,
            "source_image_alt": self.source_image_alt,
            "mask": self.mask,
            "metadata": self.metadata,
            "proxy": self.proxy,
        }
        return {role: path for role, path in roles.items() if os.path.exists(path)}


def sidecar_paths(document_path: str) -> SidecarPaths:
    """Compute the sidecar file names for *document_path*.

    Mirrors the app: the extension of the document path is stripped,
    then fixed suffixes are appended.
    """
    base = document_path
    dot = base.rfind(".")
    slash = max(base.rfind("/"), base.rfind(os.sep))
    if dot > slash + 1:
        base = base[:dot]  # "a.pcsd" -> "a" (dot and extension removed)
    return SidecarPaths(
        document=document_path,
        base=base,
        source_image=base + ".imd",
        source_image_alt=base,
        mask=base + ".msk",
        metadata=base + ".dat",
        proxy=base + ".pxy",
    )


def read_dat(data: bytes) -> dict[str, bytes]:
    """Parse a ``.dat`` container; returns 4CC tag -> payload.

    Unknown tags are preserved, mirroring the app's skip-and-continue
    reader.
    """
    r = ByteReader(data)
    chunks: dict[str, bytes] = {}
    while r.remaining() > 8:
        tag = r.read(4).decode("latin-1")
        length = r.i32()
        chunks[tag] = r.read(length)
    return chunks


def write_dat(chunks: dict[str, bytes]) -> bytes:
    """Serialize tag -> payload mappings back into a ``.dat`` container."""
    w = ByteWriter()
    for tag, payload in chunks.items():
        w.write(tag.encode("latin-1"))
        w.i32(len(payload))
        w.write(payload)
    return w.getvalue()


def extract_exif(dat_bytes: bytes) -> Optional[bytes]:
    """Return the raw EXIF payload of a ``.dat`` container, if any."""
    return read_dat(dat_bytes).get("exif")


def make_dat(exif: bytes) -> bytes:
    """Build a minimal ``.dat`` container holding one ``exif`` chunk."""
    if len(exif) > MAX_EXIF_SIZE:
        raise PcsdError(f"exif payload exceeds the app's {MAX_EXIF_SIZE} byte cap")
    return write_dat({"exif": exif})
