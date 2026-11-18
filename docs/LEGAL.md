# Legal posture and clean-room methodology

*This is engineering documentation, not legal advice. Copyright and
reverse-engineering law varies by jurisdiction; consult a lawyer
before relying on any of this for a commercial project.*

## What this repository is

`openpcsd` is a **clean-room interoperability project**:

* **Specifications** (`docs/FORMAT.md`, `docs/ARCHITECTURE.md`,
  `docs/HISTORY.md`) are original written descriptions of file-layout
  facts and observed behavior, produced by static analysis of a
  legitimately obtained copy of the app.
* **Code** (`src/openpcsd/`) is an original Python implementation
  written from those specifications. No source code, resources, or
  binary data from the app is included, copied, or translated
  line-by-line.
* **The app itself is NOT open source.** PicSay and PicSay Pro are
  copyrighted works of their author. Removal from Google Play in
  August 2024 changed their *availability*, not their *legal status*:
  "abandonware" is still protected by copyright, which in the EU
  lasts 70 years after the author's death and in the US similarly
  long for corporate works.

## Why this is the standard, defensible approach

1. **File formats and protocols are functional facts, not expression.**
   Copyright protects the *code that implements* a format, not the
   format's field layout. Interoperability specs derived from
   observation are the basis of the entire reverse-engineering
   industry and of landmark cases on interoperability (the EU
   Software Directive's RE exception, Art. 6, and the US
   *Sega v. Accolade* line of reasoning).
2. **The app contains no effective technological protection
   measures** on its document format: files are unencrypted,
   unobfuscated, and read/write-able with stock tools. Nothing was
   circumvented to produce this spec.
3. **No decompiled source ships in this repository.** The private
   analysis workspace used to derive the spec is not distributed.
   Redistribution of decompiled code would be derivative-work
   infringement regardless of the app's delisting.

## Trademark

"PicSay" is the app's name and is treated as its developer's mark.
This project is named after the **format** (`pcsd`, the file magic),
uses the app's name only descriptively ("a PicSay-compatible
library"), and implies no endorsement. If the mark's owner objects to
any descriptive use, we will adjust.

## Trademark/copyright status of specific artifacts

| Artifact | Status |
|---|---|
| `pcsd` file format, chunk tags, field layout | functional facts — free to implement |
| `docs/*.md`, `src/openpcsd/**` in this repo | original work of this project (Apache-2.0 / CC-BY-4.0) |
| PicSay / PicSay Pro APK, code, name, icon, screenshots | © the original author — **not included, do not commit** |
| Font name `Laffayette_Comic_Pro_PS.ttf` | referenced descriptively; font not included |
| EXIF/TIFF structures | industry standards (ISO/IEC 12257 / JEITA CP-3451 lineage) |

## Ground rules for contributors

1. **Never commit** the app's APK, decompiled sources, resources, or
   any byte-for-byte extract beyond what fair-use quotation of a few
   bytes requires for test vectors (and label those clearly).
2. Write code **from the spec** (`docs/FORMAT.md`), not from
   decompiler output. If you consult the binary privately, document
   what you learned as spec text first.
3. If the original author ever open-sources the app or objects to
   this project, **stop and reassess immediately** — an
   author-endorsed revival is strictly better than a clean-room one.
4. A truly licensed revival requires the author's permission; see
   `docs/HISTORY.md` for his public footprint. If you can reach him,
   be polite, show him this repo, and offer to hand everything over.

## The best outcome

This project exists to keep users' data alive, not to pirate an app.
The ideal end state is the author saying "here's the source" — making
every clean-room workaround unnecessary. Until then, this repo keeps
the documents readable, which is the part that would otherwise be
lost forever.
