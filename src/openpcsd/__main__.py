"""Command line interface: ``python -m openpcsd <command> ...``.

Commands:

* ``inspect FILE``    - print a structural summary of a .pcsd document
* ``thumbnail FILE``  - extract the embedded preview image
* ``sidecars FILE``   - list the sidecar files that exist for FILE
* ``exif FILE.dat``   - dump the chunk tags of a .dat sidecar
"""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__, extract_exif, read_dat, read_pcsd, sidecar_paths


def _cmd_inspect(args: argparse.Namespace) -> int:
    data = open(args.file, "rb").read()
    doc = read_pcsd(data)
    print(f"file          : {args.file} ({len(data)} bytes)")
    print(f"format version: {doc.format_version}")
    print(f"document size : {doc.doc_width:g} x {doc.doc_height:g} units")
    print(f"pixel size    : {doc.pixel_width} x {doc.pixel_height}")
    print(f"version block : int={doc.version_int} long={doc.version_long} ts={doc.timestamp}")
    if doc.thumbnail is not None:
        print(f"thumbnail     : {doc.thumbnail.codec}, {len(doc.thumbnail.data)} bytes")
    else:
        print("thumbnail     : (none)")
    if doc.bundle is not None:
        print(f"metadata      : {len(doc.bundle)} bundle entries")
        for key, value in doc.bundle.items():
            print(f"                {key} = {value!r}")
    print(f"objects       : {len(doc.objects)}")
    for obj in doc.objects:
        extra = ""
        if getattr(obj, "text", ""):
            extra = f" text={obj.text!r}"
        elif getattr(obj, "name", ""):
            extra = f" name={obj.name!r}"
        print(
            f"  [{obj.obj_id}] {obj.tag:4s} {obj.width:.1f}x{obj.height:.1f}"
            f" matrix_scale=({obj.matrix[0]:.2f},{obj.matrix[4]:.2f}){extra}"
        )
        for tlv in getattr(obj, "ext_tlvs", []):
            print(f"        ext {tlv.tag} ({len(tlv.payload)} bytes)")
    for chunk in doc.other_chunks:
        print(f"  (unknown chunk {chunk.tag!r}, {len(chunk.payload)} bytes)")
    return 0


def _cmd_thumbnail(args: argparse.Namespace) -> int:
    data = open(args.file, "rb").read()
    doc = read_pcsd(data)
    if doc.thumbnail is None:
        print("no thumbnail chunk in this document", file=sys.stderr)
        return 1
    out = args.out or os.path.splitext(args.file)[0] + "-thumb." + (
        "png" if doc.thumbnail.codec == "png" else "jpg"
    )
    with open(out, "wb") as fh:
        fh.write(doc.thumbnail.data)
    print(f"wrote {out} ({doc.thumbnail.codec}, {len(doc.thumbnail.data)} bytes)")
    return 0


def _cmd_sidecars(args: argparse.Namespace) -> int:
    paths = sidecar_paths(args.file)
    print(f"base           : {paths.base}")
    for role, path in paths.existing().items():
        size = os.path.getsize(path)
        print(f"{role:14s} : {path} ({size} bytes)")
    return 0


def _cmd_exif(args: argparse.Namespace) -> int:
    data = open(args.file, "rb").read()
    chunks = read_dat(data)
    for tag, payload in chunks.items():
        print(f"{tag}: {len(payload)} bytes")
    exif = extract_exif(data)
    if exif is not None:
        print(f"exif header bytes: {exif[:8].hex()} (II*/MM* TIFF marker expected)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="openpcsd", description="Work with PicSay .pcsd documents"
    )
    parser.add_argument("--version", action="version", version=f"openpcsd {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inspect", help="print a structural summary")
    p.add_argument("file")
    p.set_defaults(func=_cmd_inspect)

    p = sub.add_parser("thumbnail", help="extract the embedded preview image")
    p.add_argument("file")
    p.add_argument("-o", "--out", default=None)
    p.set_defaults(func=_cmd_thumbnail)

    p = sub.add_parser("sidecars", help="list existing sidecar files")
    p.add_argument("file")
    p.set_defaults(func=_cmd_sidecars)

    p = sub.add_parser("exif", help="dump .dat sidecar chunk tags")
    p.add_argument("file")
    p.set_defaults(func=_cmd_exif)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
