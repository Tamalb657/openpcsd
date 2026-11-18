# The `pcsd` document format

* **Status:** v1 (clean-room specification, implemented by openpcsd 0.1)
* **Origin:** PicSay / PicSay Pro for Android (Shinycore, 2008–2024)
* **Scope:** the `.pcsd` main document (fully specified) and the `.dat`
  EXIF sidecar (fully specified); the image sidecars (`.msk`, `.pxy`,
  `.imd`) are native formats documented structurally only.

This specification was produced by static analysis of the last
published app (v1.8.0.5). Fields whose *semantics* could not be
confirmed are marked **inferred**; their *position and wire type* are
certain (they come straight from the app's reader/writer pair).

---

## 1. Conventions

* All multi-byte values are **big-endian** (Java `DataOutput` order).
* `int32` / `int64` are **signed** two's complement. Colors are ARGB
  `int32`s — opaque colors are *negative* on the wire.
* `float32` / `float64` are IEEE-754, written as raw bit patterns.
* Strings use **Java modified UTF-8** with a `uint16` byte-count
  prefix (details in §7).
* Four-character codes (**4CC**) are tags made of four Latin-1 bytes,
  read as one big-endian `int32` (e.g. `"pcsd"` = `0x70637364` =
  `1885565796`).

## 2. File overview

A saved *project* is a file family sharing a base name. For a document
at `/photos/vacation.pcsd`:

| File | Contents | Written by | In this spec |
|---|---|---|---|
| `vacation.pcsd` | main document: header, preview, metadata, object stack | Java (fully understood) | §3–§6 |
| `vacation.dat` | EXIF metadata rescued from the source photo | Java (fully understood) | §8 |
| `vacation.msk` | user mask (alpha selections) | native `libImageOp.so` | structure only (§9) |
| `vacation.pxy` | mipmap pyramid of the working image | native `libImageOp.so` | structure only (§9) |
| `vacation` or `vacation.imd` | the **original, unedited** source image, kept byte-for-byte | native pipeline | structure only (§9) |

The main document is deliberately "slim": the heavy pixel data lives
in the sidecars, so a `.pcsd` can be rewritten constantly without
touching megabytes of image data.

## 3. Main document layout

```
pcsd_file      := magic header chunk*          ; chunks until EOF
magic          := "pcsd"                       ; 0x70637364
header         := int32 header_len             ; 44 in current files
                  int32 format_version         ; must be >= 256
                  float32 doc_width            ; document units
                  float32 doc_height
                  int32 reserved               ; always 0
                  int32 pixel_width
                  int32 pixel_height
                  [ version block, if header_len >= 44:
                    int32 version_int           ; >= 1 enables the block
                    int64 version_long
                    int64 timestamp ]
                  [ header_len may be larger in future files;
                    readers must skip what they do not know ]
chunk          := int32 tag (4CC) int32 payload_len payload
```

Notes:

* `header_len` counts the bytes **after** the magic and the length
  field itself. Current files: `44` = 24 fixed bytes + 20-byte version
  block. Older files with `header_len = 24` have no version block;
  object ids in chunks are then ignored by the reader (the 4-byte id
  field is still present — see §5).
* `format_version` is a constant `256` emitted by the last writer; the
  reader rejects anything below `256`. It is a format-generation
  marker, not a feature-flags word.
* The reader stops looking for chunks when **8 or fewer bytes** remain.
* Chunk order in writer output: `thmb`, `bndl`, then objects in
  z-order (bottom-most first).

## 4. Chunk registry

| 4CC | int32 | Payload | Notes |
|---|---|---|---|
| `thmb` | `1953000802` | a complete PNG or JPEG file | PNG when a mask sidecar exists, JPEG (quality 75) otherwise; the reader skips this chunk entirely (it is for file managers) |
| `bndl` | `1651401836` | Android-Bundle structure, §6 | document metadata; associated with object id 2 by convention |
| `wrdb` | `2003985506` | object id + word-balloon body, §5.3 | the app's signature feature |
| `text` | `1952807028` | object id + text body, §5.2 | |
| `prop` | `1886547824` | object id + prop/sticker body, §5.4 | |
| *other* | — | — | the original reader skips unknown chunks; openpcsd preserves them verbatim |

## 5. Objects

### 5.1 Common prologue (all object bodies)

```
prologue  := float32 width float32 height float32 matrix[9]
```

`matrix` is an Android `Matrix.getValues()` array in row-major order:
`[scaleX, skewX, transX, skewY, scaleY, transY, persp0, persp1,
persp2]`. Width/height are the object's intrinsic size in document
units; the matrix places it on the canvas.

### 5.2 `text`

```
text_body := prologue
             int32 color_a            ; paint A color, ARGB (inferred: shadow paint)
             int32 style_int          ; app-internal flags
             boolean flag_2048        ; mirrors state bit 0x800
             int32 color_fill         ; fill paint color, ARGB
             float32 stroke_width     ; fill stroke width (app uses 0 for plain fill)
             int32 color_stroke       ; border paint color, ARGB
             float32 stroke_width2    ; border width (app adds stroke_width when painting)
             style_block              ; §5.5
             float32 font_size        ; document units
             string text
             ext_tlv*                 ; §5.6
```

### 5.3 `wrdb` (word balloon)

```
wrdb_body := prologue
             float32 min_w            ; inferred: minimum body width
             float32 min_h            ; inferred: minimum body height
             float32 pad_w            ; inferred: body padding x
             float32 pad_h            ; inferred: body padding y
             int32 int_a
             int32 int_b
             boolean flag_2048
             int32 int_v
             float32 float_w
             boolean flag_1024        ; size-relative-to-screen state
             int32 int_r
             float32 float_s
             float32 float_t
             float32 float_u
             int32 int_e
             style_block              ; §5.5
             int32 shape              ; low nibble of the state int: balloon shape 0..15
             float32 tail_x           ; inferred: pointer x
             float32 tail_y           ; inferred: pointer y
             float32 tail_scale       ; inferred: pointer size (product of 2 scale floats)
             string text
             ext_tlv*                 ; only "lins" is known to occur
```

### 5.4 `prop` (sticker)

```
prop_body := prologue
             int32 block_len
             nested_block            ; sized by block_len
             string name             ; sticker resource reference

nested_block := "mtrx" float32[20]             ; Android ColorMatrix, row-major
               | "skin" int32                   ; skin/flags
               | "styl" <opaque sticker-style bytes, rest of block>
               | "mtrx" float32[20] "skin" int32   ; chain
               | <80 bytes of ColorMatrix floats>   ; legacy: block_len == 80, no tag
```

The nested block is a chain of `[tag][fixed-size content]` entries —
there are **no per-entry length fields**; each tag has an implicit
size (`mtrx` = 80 bytes, `skin` = 4 bytes, `styl` = the remainder of
the block). A `block_len` of exactly `80` denotes a legacy implicit
ColorMatrix written without a tag.

### 5.5 `style_block` (font reference)

```
style_block := int32 flags        ; Typeface style bits: bit 0 bold, bit 1 italic
               string font_file   ; bundled font file name, "" if platform font
               string font_family ; e.g. "sans-serif", "serif"; "" if file font
```

Exactly one of the two strings is non-empty in practice. The original
reader maps the bundled file name `"Laffayette_Comic_Pro_PS.ttf"`
(a font referenced by the app but never shipped inside the APK) to
built-in font index 8.

### 5.6 Extension TLVs

Object bodies end with a sequence of tag/length/value extensions,
iterated while at least 8 bytes (tag + length) remain:

```
ext_tlv := int32 tag (4CC) int32 length payload[length]
```

A zero tag or non-positive length means "no more extensions". Known
tags:

| 4CC | int32 | Payload | Used by |
|---|---|---|---|
| `tcrv` | `1952674422` | `float32` rotation angle (clamped ±360°) | text |
| `lins` | `1818848883` | `int32` alignment (0..2; the balloon reader discards it) + `float32` line-spacing scale (clamped 0.01..2.0) | text, balloon |
| `shdw` | `1936221303` | `int32` + 3 × `float32` — shadow parameters (inferred: color, dx, dy, blur) | text |

Writers emit these **conditionally** (`tcrv` only when rotation ≠ 0,
`lins` only when alignment ≠ 0 or scale ≠ 1.0, `shdw` only when a
shadow exists); readers must tolerate any order and unknown tags.

## 6. `bndl` — the metadata bundle

An `android.os.Bundle` serialized with the app's own writer:

```
bundle := int32 entry_count
          ( string key int32 type_tag typed_value )*
```

| Type tag | Type | Payload |
|---|---|---|
| `-1` | null | — |
| `0` | string | modified-UTF-8 string |
| `1` | int | `int32` |
| `3` | bundle | nested `bundle` |
| `5` | short | `int16` |
| `6` | long | `int64` |
| `7` | float | `float32` |
| `8` | double | `float64` |
| `9` | boolean | 1 byte (`0`/`1`) |
| `18` | int[] | `int32 count` + `count` × `int32` |

Key order is the iteration order of the original `Bundle` (hash
order); openpcsd preserves file order on re-serialization.

## 7. Modified UTF-8

Java's `DataOutput.writeUTF` format:

* `uint16` byte count, then the bytes;
* `U+0000` encodes as `0xC0 0x80` (never a raw `0x00`);
* code points `> U+FFFF` encode as **two** 3-byte sequences (one per
  UTF-16 surrogate), never a 4-byte sequence;
* **the original writer refuses strings longer than 2730 UTF-16 code
  units** (a hard limit in its buffered stream class, beyond the
  65535-byte prefix maximum).

## 8. `.dat` — the EXIF sidecar

```
dat_file := ( int32 tag int32 payload_len payload )*
```

The reader scans for the `exif` tag (`0x65786966`) and skips unknown
tags, so the container is extensible. The `exif` payload is a
TIFF-style EXIF structure: `"II*\0"` or `"MM\0*"` endianness marker
followed by IFD0, with Exif (`34665`), GPS (`34853`) and Interop
(`40965`) sub-IFDs. The payload is capped at 1 MiB by the reader.

The tags the app rescues from the source photo: Orientation (274),
Make (271), Model (272), GPSInfo (34853), DateTimeOriginal (36867),
ExifVersion (36864), Artist (315), Copyright (33432),
ImageDescription (270), DateTimeDigitized (36868).

## 9. Image sidecars (out of scope, structurally documented)

* **`.msk`** — the user's mask/alpha selections, serialized by the
  native `libImageOp.so` through its file-renderer JNI surface. Not a
  standard image format; decoding requires the native code path.
* **`.pxy`** — a mipmap pyramid of the working image (the app's
  "Tim" image object proxy chain), also native.
* **source image** — kept at the base path if a file already exists
  there, otherwise `base + ".imd"`. The app's loader resolves
  `"#"+extension` through its image-proxy URI scheme; a bare `.imd`
  extension denotes "raw image data" in that scheme.

Decoding these is the library's roadmap item #1; the relevant native
entry points are the `fileRenderer` and `TimImageProxy` JNI
registrations documented in the architecture notes.

## 10. Worked example

First 52 bytes of a openpcsd-generated file, annotated:

```
00000000  70 63 73 64                                  "pcsd" magic
00000004  00 00 00 2c                                  header_len = 44
00000008  00 00 01 00                                  format_version = 256
0000000c  44 80 00 00                                  doc_width  = 1024.0f
00000010  43 c0 00 00                                  doc_height = 768.0f
00000014  00 00 00 00                                  reserved
00000018  00 00 04 00                                  pixel_width  = 1024
0000001c  00 00 03 00                                  pixel_height = 768
00000020  00 00 00 01                                  version_int  = 1
00000024  00 00 00 00 00 00 00 01                      version_long = 1
0000002c  00 00 01 8b 1c 9d 98 00                      timestamp    = 1700000000000
00000034  74 68 6d 62 00 00 00 43                      chunk "thmb", 67 bytes...
```

## 11. Implementation checklist

A conforming reader must:

1. verify the magic and reject `format_version < 256`;
2. skip unknown header bytes via `header_len` (forward compatibility);
3. tolerate missing version block (legacy `header_len = 24`);
4. skip unknown chunk tags without failing;
5. always consume the 4-byte id field of object chunks, using it as
   the object id only when `version_int >= 1`;
6. iterate extension TLVs defensively (stop at zero tag / bad length);
7. handle both thumbnail codecs (PNG, JPEG).

A conforming writer should mirror the original's conditional output
(omit default extensions, write the legacy implicit ColorMatrix only
for compatibility) if byte-level fidelity with the app matters.
