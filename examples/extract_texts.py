#!/usr/bin/env python3
"""Extract all text from a .pcsd document (text objects and balloons).

Usage::

    python examples/extract_texts.py file.pcsd [file2.pcsd ...]

Handy for rescuing captions from documents created by the (now
delisted) PicSay / PicSay Pro apps.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from openpcsd import BalloonObject, TextObject, read_pcsd  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for path in sys.argv[1:]:
        doc = read_pcsd(open(path, "rb").read())
        print(f"== {path} ({doc.pixel_width}x{doc.pixel_height}) ==")
        for obj in doc.objects:
            if isinstance(obj, (TextObject, BalloonObject)) and obj.text:
                kind = "balloon" if isinstance(obj, BalloonObject) else "text"
                print(f"  [{kind}] {obj.text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
