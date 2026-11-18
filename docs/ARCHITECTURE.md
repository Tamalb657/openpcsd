# How the original app worked

*Architecture notes from a static forensic teardown of PicSay Pro
1.8.0.5 — the companion document to `FORMAT.md`. These notes describe
behavior; they contain no source code from the app.*

## The app in one paragraph

PicSay (Shinycore, one developer: Eric Wijngaard) was an
Android photo editor built around a **native image engine** with a thin
Java UI on top. Projects save as the multi-file `pcsd` family
(`FORMAT.md` §2): a slim Java-written main document plus native image
sidecars. The design goal visible everywhere is *never hold a full
size image in Java heap*: pixel data lives in native "Tim" objects,
Java only ever sees handles, downsampled proxies, and one bitmap at
export time.

## Layered architecture

```
┌─────────────────────────────────────────────────────┐
│ picsaypro (8 classes)      entry points, billing glue│
├─────────────────────────────────────────────────────┤
│ PicSayUI (305 classes)     activities, tool UI,      │
│                            dialogs, Filters package  │
├─────────────────────────────────────────────────────┤
│ PicSay (197 classes)       the editor core: document │
│                            model, pcsd serializer,   │
│                            ~50 Action classes        │
├─────────────────────────────────────────────────────┤
│ Shared (59 classes)        TimImageProxy JNI bridge, │
│ + QuartzCore (11)          task pipeline, proxies    │
├─────────────────────────────────────────────────────┤
│ libImageOp.so (371 exports) Tim engine, filters,     │
│                            static libjpeg, GPU warp  │
└─────────────────────────────────────────────────────┘
```

## The native bridge

`libImageOp.so` registers 7 groups of JNI methods dynamically from
`JNI_OnLoad` (no `Java_*` exports): `TimImageProxy`, `filter`,
`PEStroke`, `ImageConverter`, `ImageTask`, `fileRenderer`,
`scUtils` — 135 native method declarations on the Java side. The
native symbol census (371 exports) breaks down as:

| Group | Symbols | What it is |
|---|---|---|
| Filter classes | 142 | the `Filter*` C++ class hierarchy |
| setupEffect factories | 51 | `setupEffectXray`, `setupEffectFauxHDR`, `setupEffectDistortTwirl`, ... |
| JNI registration glue | ~55 | the dynamic bridges above |
| static libjpeg | 55 | a whole libjpeg linked in (`jpeg_*` symbols) |
| Tim engine + misc | remainder | image objects, strokes, conversion |

The **GPU path exists but only serves the Warp Brush** (OpenGL ES via
QuartzCore); every other effect runs on CPU through the filter
factories.

## The document object model

* A document holds a **registry** of objects with 1-based ids. By
  convention id 1 is the z-order list, id 2 the metadata bundle;
  content objects take ids ≥ 3.
* All content objects share a prologue (width, height, 3×3 matrix) —
  the same prologue `FORMAT.md` §5.1 specifies.
* Editing operations are **Command-pattern `Action` classes** (~50 of
  them). The undo stack is **persisted to disk** as `.history`
  snapshots, which is why a killed app can offer undo on reopen.
* The **"Tim" image objects** are handle-based native images. Java
  wraps them in `TimImageProxy`; resolution is tiered by device memory
  class (≥64 MB → up to 4208×3120; the code contains a dead
  4096→4208 migration).

## Saving a project

1. The Java side serializes the slim `.pcsd` main document (header,
   thumbnail, bundle, objects) with a buffered `DataOutputStream`
   subclass that backpatches chunk lengths — the framing in
   `FORMAT.md` §3.
2. Native tasks asynchronously write the sidecars: mask (`.msk`),
   EXIF container (`.dat`, `FORMAT.md` §8), mipmap proxy (`.pxy`).
3. The **source photo is preserved byte-for-byte** at the base path
   (or `.imd`) — non-destructive editing by construction.

## Export pipeline

Export renders through the native `ImageConverter`, writes to a
temp file, then **atomically renames** into place, and re-attaches
rescued EXIF tags (including GPS) to the output — a detail few
editors of the era got right.

## Forensic asides

* An empty `ProcessingService` class and an Amazon-appstore vendor
  branch betray a multi-store build.
* The bundled-font reference `Laffayette_Comic_Pro_PS.ttf` matches no
  shipped asset — the font was optional downloadable content.
* The Pro build contains **no runtime license check**; Pro vs Free
  was enforced by distribution channel and package name
  (`com.shinycore.picsaypro` vs `com.shinycore.picsay`).
* A `PictureProvider` content provider impersonates MediaStore
  cursors so the app can act as a **camera target without camera
  permission** (character-level mode parsing in `openFile`).

## Why this matters for the revival

The **pure-Java formats** (`.pcsd` main document, `.dat` container)
are fully recoverable and now implemented by openpcsd. The **native
sidecar formats** (`.msk`, `.pxy`) and the filter engine are the
remaining mountain: reviving them means either disassembling
`libImageOp.so` or re-implementing from observed behavior. That is
the fork in the road for anyone continuing this project.
