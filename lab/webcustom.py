"""Chromium web-custom-data pickle (macOS UTI org.chromium.web-custom-data): decode and encode.

Layout: uint32 payload_size | uint32 count | count x (string16 type, string16 value)
string16 = uint32 length in UTF-16 code units, then UTF-16LE data padded to 4 bytes.
"""
import struct


def _read16(b, o):
    (n,) = struct.unpack_from("<I", b, o); o += 4
    raw = b[o:o + 2 * n]; o += (2 * n + 3) & ~3
    return raw.decode("utf-16-le"), o


def decode(b: bytes) -> dict:
    (size,) = struct.unpack_from("<I", b, 0)
    (count,) = struct.unpack_from("<I", b, 4)
    o, out = 8, {}
    for _ in range(count):
        k, o = _read16(b, o); v, o = _read16(b, o); out[k] = v
    return out


def _w16(s: str) -> bytes:
    raw = s.encode("utf-16-le"); n = len(raw) // 2
    return struct.pack("<I", n) + raw + b"\0" * ((-len(raw)) % 4)


def encode(items: dict) -> bytes:
    body = struct.pack("<I", len(items)) + b"".join(_w16(k) + _w16(v) for k, v in items.items())
    return struct.pack("<I", len(body)) + body
