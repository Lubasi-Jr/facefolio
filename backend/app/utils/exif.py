"""Reads just the capture timestamp out of a JPEG's EXIF block.

Walks the file's marker segments directly (SOI -> APPn headers -> the TIFF
structure inside APP1) and stops at the first scan marker, so it never asks
anything to decode pixel data just to read one timestamp field.
"""

import struct
from datetime import datetime, timezone
from pathlib import Path

import structlog

log = structlog.get_logger()

_JPEG_SOI = b"\xff\xd8"
_APP1_MARKER = b"\xff\xe1"
_SOS_MARKER = b"\xff\xda"
_EXIF_HEADER = b"Exif\x00\x00"

_TAG_EXIF_IFD_POINTER = 0x8769
_TAG_DATETIME_ORIGINAL = 0x9003
_TAG_DATETIME = 0x0132
_TYPE_ASCII = 2

_DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S"


def _read_app1_tiff(f) -> bytes | None:
    """Scans marker segments from the start of the file and returns the TIFF
    payload of the first Exif APP1 segment found, or None if there isn't one
    before the compressed scan data starts."""
    if f.read(2) != _JPEG_SOI:
        return None

    while True:
        marker = f.read(2)
        if len(marker) < 2 or marker[0:1] != b"\xff":
            return None
        if marker == _SOS_MARKER:
            return None  # compressed scan data starts here; no APP1 seen

        length_bytes = f.read(2)
        if len(length_bytes) < 2:
            return None
        length = struct.unpack(">H", length_bytes)[0]
        payload = f.read(length - 2)

        if marker == _APP1_MARKER and payload.startswith(_EXIF_HEADER):
            return payload[len(_EXIF_HEADER) :]


def _iter_ifd_entries(tiff: bytes, byte_order: str, ifd_offset: int):
    """Yields (tag, type, count, value_bytes) for each entry in one IFD."""
    entry_count = struct.unpack(byte_order + "H", tiff[ifd_offset : ifd_offset + 2])[0]
    entries_start = ifd_offset + 2
    for i in range(entry_count):
        entry = tiff[entries_start + i * 12 : entries_start + (i + 1) * 12]
        tag, value_type, count = struct.unpack(byte_order + "HHI", entry[:8])
        yield tag, value_type, count, entry[8:12]


def _ascii_tag_value(tiff: bytes, byte_order: str, ifd_offset: int, tag: int) -> str | None:
    for entry_tag, value_type, count, value_bytes in _iter_ifd_entries(tiff, byte_order, ifd_offset):
        if entry_tag != tag or value_type != _TYPE_ASCII:
            continue
        # Short ASCII values are stored inline in the 4-byte field; longer
        # ones store an offset to where the string actually lives.
        if count <= 4:
            raw = value_bytes[:count]
        else:
            offset = struct.unpack(byte_order + "I", value_bytes)[0]
            raw = tiff[offset : offset + count]
        return raw.rstrip(b"\x00").decode("ascii", errors="replace")
    return None


def _long_tag_value(tiff: bytes, byte_order: str, ifd_offset: int, tag: int) -> int | None:
    for entry_tag, _value_type, _count, value_bytes in _iter_ifd_entries(tiff, byte_order, ifd_offset):
        if entry_tag == tag:
            return struct.unpack(byte_order + "I", value_bytes)[0]
    return None


def read_taken_at(source_path: str | Path) -> datetime | None:
    try:
        with open(source_path, "rb") as f:
            tiff = _read_app1_tiff(f)
        if tiff is None:
            return None

        byte_order = "<" if tiff[:2] == b"II" else ">"
        ifd0_offset = struct.unpack(byte_order + "I", tiff[4:8])[0]

        raw = None
        exif_ifd_offset = _long_tag_value(tiff, byte_order, ifd0_offset, _TAG_EXIF_IFD_POINTER)
        if exif_ifd_offset is not None:
            raw = _ascii_tag_value(tiff, byte_order, exif_ifd_offset, _TAG_DATETIME_ORIGINAL)
        if raw is None:
            raw = _ascii_tag_value(tiff, byte_order, ifd0_offset, _TAG_DATETIME)
        if raw is None:
            return None

        # EXIF datetimes carry no timezone info. Treated as UTC — the only
        # deterministic choice available without an OffsetTimeOriginal tag.
        return datetime.strptime(raw, _DATETIME_FORMAT).replace(tzinfo=timezone.utc)
    except (OSError, struct.error, ValueError, IndexError):
        log.debug("exif.taken_at_missing", source_path=str(source_path))
        return None
