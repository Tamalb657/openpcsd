"""The Android-Bundle wire format used inside ``bndl`` chunks.

The original app stores document metadata (title, markers, geotags,
quality settings, ...) as an ``android.os.Bundle`` serialized with a
tiny custom writer.  A bundle is::

    int32   entry_count
    repeat entry_count times:
        mutf8   key
        int32   value_type
        ...     typed value

Value types (from the app's Bundle writer / reader pair):

===== ===== ===============================
Tag   Type  Payload
===== ===== ===============================
-1    null  (nothing)
0     str   mutf8 string
1     int   int32
3     bnd   nested bundle
5     short int16
6     long  int64
7     float float32 (IEEE-754 bits)
8     dbl   float64
9     bool  1 byte (0/1)
18    i[]   int32 count + that many int32
===== ===== ===============================

Python mapping: ``str``, ``int``, ``dict`` (nested bundle),
:class:`Short`, :class:`Long`, :class:`Float`, ``float``, ``bool``,
``None`` and ``list[int]``.  :class:`Short`/:class:`Long`/:class:`Float`
subclass ``int``/``float`` so they behave like plain numbers but keep
the exact wire type for byte-faithful re-serialization.
"""

from __future__ import annotations

from typing import Any, Mapping, Union

from .io import ByteReader, ByteWriter

TYPE_NULL = -1
TYPE_STRING = 0
TYPE_INT = 1
TYPE_BUNDLE = 3
TYPE_SHORT = 5
TYPE_LONG = 6
TYPE_FLOAT = 7
TYPE_DOUBLE = 8
TYPE_BOOLEAN = 9
TYPE_INT_ARRAY = 18


class Short(int):
    """An ``int`` that serializes as the app's *short* (tag 5)."""


class Long(int):
    """An ``int`` that serializes as the app's *long* (tag 6)."""


class Float(float):
    """A ``float`` that serializes as the app's 32-bit *float* (tag 7)."""


#: A parsed bundle: ordered mapping of key -> tagged value.
Bundle = dict


def read_bundle(r: ByteReader) -> Bundle:
    """Parse one bundle (including its leading count) from *r*."""
    count = r.i32()
    if count < 0:
        raise ValueError(f"negative bundle entry count {count}")
    bundle: Bundle = {}
    for _ in range(count):
        key = r.read_utf()
        bundle[key] = _read_value(r)
    return bundle


def _read_value(r: ByteReader) -> Any:
    tag = r.i32()
    if tag == TYPE_NULL:
        return None
    if tag == TYPE_STRING:
        return r.read_utf()
    if tag == TYPE_INT:
        return r.i32()
    if tag == TYPE_BUNDLE:
        return read_bundle(r)
    if tag == TYPE_SHORT:
        return Short(r.i16())
    if tag == TYPE_LONG:
        return Long(r.i64())
    if tag == TYPE_FLOAT:
        return Float(r.f32())
    if tag == TYPE_DOUBLE:
        return r.f64()
    if tag == TYPE_BOOLEAN:
        return r.boolean()
    if tag == TYPE_INT_ARRAY:
        n = r.i32()
        if n < 0:
            raise ValueError(f"negative int[] length {n}")
        return [r.i32() for _ in range(n)]
    raise ValueError(f"unknown bundle value type {tag}")


def write_bundle(w: ByteWriter, bundle: Mapping[str, Any]) -> None:
    """Serialize *bundle* (including the leading count) into *w*."""
    w.i32(len(bundle))
    for key, value in bundle.items():
        w.write_utf(key)
        _write_value(w, value)


def _write_value(w: ByteWriter, value: Any) -> None:
    if value is None:
        w.i32(TYPE_NULL)
    elif isinstance(value, str):
        w.i32(TYPE_STRING)
        w.write_utf(value)
    elif isinstance(value, bool):  # must come before int (bool is an int subclass)
        w.i32(TYPE_BOOLEAN)
        w.boolean(value)
    elif isinstance(value, Short):
        w.i32(TYPE_SHORT)
        w.i16(value)
    elif isinstance(value, Long):
        w.i32(TYPE_LONG)
        w.i64(value)
    elif isinstance(value, Float):
        w.i32(TYPE_FLOAT)
        w.f32(value)
    elif isinstance(value, int):
        w.i32(TYPE_INT)
        w.i32(value)
    elif isinstance(value, float):
        w.i32(TYPE_DOUBLE)
        w.f64(value)
    elif isinstance(value, Mapping):
        w.i32(TYPE_BUNDLE)
        write_bundle(w, value)
    elif isinstance(value, (list, tuple)):
        for item in value:
            if not isinstance(item, int) or isinstance(item, bool):
                raise TypeError("only int arrays are representable; got %r" % (item,))
        w.i32(TYPE_INT_ARRAY)
        w.i32(len(value))
        for item in value:
            w.i32(item)
    else:
        raise TypeError(f"cannot serialize {type(value).__name__} as a bundle value")


def to_plain(bundle: Bundle) -> dict:
    """Return a copy with Short/Long/Float widened to plain int/float."""
    out: dict = {}
    for key, value in bundle.items():
        if isinstance(value, Mapping):
            out[key] = to_plain(value)
        elif isinstance(value, (list, tuple)):
            out[key] = list(value)
        else:
            out[key] = value  # Short/Long are ints, Float is a float already
    return out
