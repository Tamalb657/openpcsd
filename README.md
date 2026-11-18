# OpenPCSD

**A clean-room, open-source revival of the PicSay document format.**

[![CI](https://img.shields.io/badge/CI-github--actions-2088ff?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-blue)](LICENSE)
[![License: CC-BY-4.0](https://img.shields.io/badge/docs-CC--BY--4.0-lightgrey)](LICENSE-DOCS.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](pyproject.toml)

[PicSay](docs/HISTORY.md) was a beloved Android photo editor
(2008–2024, ~830k installs) whose projects are saved as `.pcsd`
documents. The app was **delisted from Google Play in August 2024**
and no longer installs on modern devices — but the documents still
sit on people's phones and backups with nothing left that can open
them.

`openpcsd` keeps that data alive:

* **`openpcsd`** — a zero-dependency Python library that reads,
  inspects and writes `.pcsd` main documents and `.dat` EXIF sidecars,
* **the format spec** — the first complete public documentation of
  the format, produced by clean-room static analysis
  ([docs/FORMAT.md](docs/FORMAT.md)),
* **architecture notes** on how the original app worked
  ([docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).

```python
from openpcsd import read_pcsd, write_pcsd

doc = read_pcsd(open("vacation.pcsd", "rb").read())
print(doc.pixel_width, "x", doc.pixel_height)      # 1024 x 768
for obj in doc.objects:                            # texts, balloons, stickers
    print(obj.tag, getattr(obj, "text", obj))
open("copy.pcsd", "wb").write(write_pcsd(doc))     # byte-stable round trip
```

## Install

```bash
pip install -e .          # from a checkout (stdlib only, no runtime deps)
```

## Command line

```console
$ python -m openpcsd inspect vacation.pcsd
file          : vacation.pcsd (4582 bytes)
format version: 256
document size : 1024 x 768 units
pixel size    : 1024 x 768
thumbnail     : png, 6731 bytes
metadata      : 3 bundle entries
objects       : 2
  [3] text 420.0x48.0 ... text='Made with openpcsd'
  [4] wrdb 300.0x120.0 ... text='Hello from the clean-room implementation!'

$ python -m openpcsd thumbnail vacation.pcsd -o preview.png
$ python -m openpcsd sidecars vacation.pcsd      # which sidecar files exist
$ python -m openpcsd exif vacation.dat           # .dat sidecar contents
```

## What a project folder looks like

PicSay did not save single files. Next to `name.pcsd` you may find
`name.dat` (EXIF rescued from the source photo), `name.msk` (mask),
`name.pxy` (image pyramid) and the untouched original photo. See
[FORMAT.md §2](docs/FORMAT.md#2-file-overview) for the full family and
what openpcsd supports today.

## Status & roadmap

| Capability | Status |
|---|---|
| `.pcsd` header + chunk container | read/write, tested |
| `text` / `wrdb` (balloon) / `prop` objects | read/write, tested |
| metadata bundle (10 value types) | read/write, tested |
| embedded thumbnail extraction | read/write (PNG & JPEG) |
| `.dat` EXIF sidecar container | read/write, tested |
| unknown chunk/TLV round-tripping | preserved byte-for-byte |
| `.msk` / `.pxy` image sidecars | not yet (native format) — [roadmap](#roadmap) |
| rendering documents to PNG | not yet — needs sidecar decode + effects |

### Roadmap

1. **`.pxy` / `.msk` decode** — reverse the native `fileRenderer`
   output format of `libImageOp.so` (see
   [ARCHITECTURE.md](docs/ARCHITECTURE.md)).
2. **Renderer** — composite objects (matrix transforms, text,
   balloons) into a PNG so documents become viewable without the app.
3. **Migration tool** — batch-convert `.pcsd` projects to layered
   open formats (OpenRaster).
4. If you own real `.pcsd` documents: **please open an issue** — test
   files from the wild are the best way to validate the spec.

## Why clean-room? (the short version)

The app being dead does not make its code free: copyright persists,
so this repo contains **no decompiled code** — only our original
specification and an original implementation of documented behavior.
The full methodology and ground rules: [docs/LEGAL.md](docs/LEGAL.md).
If you are (or can reach) the original author: we would happily hand
everything over to an official open-sourcing.

## Repository layout

```
src/openpcsd/        the library (io, bundle, model, objects, reader, writer, sidecars, cli)
tests/              round-trip + format unit tests (pytest)
examples/           make_sample.py, extract_texts.py
docs/               FORMAT.md (the spec), ARCHITECTURE.md, HISTORY.md, LEGAL.md
```

## Contributing

Bug reports, real-world `.pcsd` samples, and spec corrections are
extremely welcome. Read [docs/LEGAL.md](docs/LEGAL.md) ground rules
first (short version: never commit app code or the APK). Run tests
with `pip install -e .[test] && pytest`.

## License

* **Code** (`src/`, `tests/`, `examples/`): [Apache-2.0](LICENSE)
* **Documentation** (`docs/`, README): [CC-BY-4.0](LICENSE-DOCS.md)

PicSay is a trademark of its author; this project is not affiliated
with or endorsed by them. "pcsd" is the file format's own magic bytes.
