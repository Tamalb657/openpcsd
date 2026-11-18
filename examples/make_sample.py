#!/usr/bin/env python3
"""Build a small sample .pcsd document with one of each object kind.

Usage::

    python examples/make_sample.py [out.pcsd]

The result is a valid pcsd file that the original PicSay / PicSay Pro
apps would accept (same container, header and chunk framing).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from openpcsd import (  # noqa: E402
    BalloonObject,
    PcsdDocument,
    PropObject,
    StyleRef,
    TextObject,
    Thumbnail,
    write_pcsd,
)

# A 1x1 transparent PNG - the smallest valid thumbnail we can embed.
PNG_1PX = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def build() -> PcsdDocument:
    doc = PcsdDocument(
        doc_width=1024.0,
        doc_height=768.0,
        pixel_width=1024,
        pixel_height=768,
        version_int=1,
        version_long=1,
        timestamp=1700000000000,
    )
    doc.bundle = {
        "title": "openpcsd sample",
        "sample": True,
        "nested": {"source": "examples/make_sample.py"},
    }
    doc.thumbnail = Thumbnail(data=PNG_1PX, codec="png")

    doc.objects = [
        TextObject(
            width=420.0,
            height=48.0,
            matrix=(1.0, 0.0, 64.0, 0.0, 1.0, 64.0, 0.0, 0.0, 1.0),
            color_fill=0xFF2255AA - 2**32,  # signed Java int on the wire
            style=StyleRef(flags=1, font_family="sans-serif"),
            font_size=36.0,
            text="Made with openpcsd",
        ),
        BalloonObject(
            width=300.0,
            height=120.0,
            matrix=(1.0, 0.0, 250.0, 0.0, 1.0, 400.0, 0.0, 0.0, 1.0),
            min_w=60.0,
            min_h=30.0,
            shape=3,
            tail_x=150.0,
            tail_y=130.0,
            text="Hello from the clean-room implementation!",
        ),
        PropObject(
            width=96.0,
            height=96.0,
            matrix=(1.5, 0.0, 480.0, 0.0, 1.5, 200.0, 0.0, 0.0, 1.0),
            skin_flags=1,
            name="res/stickers/star",
        ),
    ]
    return doc


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "sample.pcsd"
    data = write_pcsd(build())
    with open(out, "wb") as fh:
        fh.write(data)
    print(f"wrote {out} ({len(data)} bytes)")
    print("inspect it with: python -m openpcsd inspect", out)


if __name__ == "__main__":
    main()
