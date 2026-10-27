"""Minimal, bounded PNG decoder for inspection images.

Supports non-interlaced 8-bit grayscale, grayscale+alpha, RGB and RGBA, which is
what the inspection-image lane produces. Anything else raises ImageDecodeError
rather than being guessed. Chunk CRCs are verified and the decompressed size is
bounded before inflation completes, so a hostile artifact cannot exhaust memory.
"""

from __future__ import annotations

import struct
import zlib

import numpy as np
from numpy.typing import NDArray

SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}
MAX_PIXELS = 40_000_000
MAX_SIDE = 65_535


class ImageDecodeError(ValueError):
    """The bytes are not a supported, well-formed PNG image."""


def _chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    if not data.startswith(SIGNATURE):
        raise ImageDecodeError("not a PNG signature")
    chunks: list[tuple[bytes, bytes]] = []
    offset = len(SIGNATURE)
    while offset < len(data):
        if offset + 8 > len(data):
            raise ImageDecodeError("truncated chunk header")
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        kind = data[offset + 4 : offset + 8]
        end = offset + 8 + length
        if end + 4 > len(data):
            raise ImageDecodeError("truncated chunk")
        body = data[offset + 8 : end]
        (crc,) = struct.unpack(">I", data[end : end + 4])
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            raise ImageDecodeError("chunk CRC mismatch")
        chunks.append((kind, body))
        offset = end + 4
        if kind == b"IEND":
            return chunks
    raise ImageDecodeError("missing IEND")


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _unfilter(raw: bytes, width: int, height: int, bpp: int) -> NDArray[np.uint8]:
    stride = width * bpp
    if len(raw) != height * (stride + 1):
        raise ImageDecodeError("image data length does not match the header")
    rows = np.frombuffer(raw, dtype=np.uint8).reshape(height, stride + 1)
    out = np.zeros((height, stride), dtype=np.uint8)
    prior = np.zeros(stride, dtype=np.uint8)
    for y in range(height):
        kind = int(rows[y, 0])
        line = rows[y, 1:]
        if kind == 0:
            current = line.copy()
        elif kind == 2:
            current = (line.astype(np.uint16) + prior).astype(np.uint8)
        elif kind == 1:
            # Recon(x) = Filt(x) + Recon(x - bpp): a per-channel running sum mod 256.
            pixels = line.reshape(width, bpp).astype(np.uint64)
            current = (np.cumsum(pixels, axis=0) % 256).astype(np.uint8).reshape(stride)
        elif kind in (3, 4):
            current = np.zeros(stride, dtype=np.uint8)
            left = [0] * bpp
            for x in range(stride):
                up = int(prior[x])
                left_value = left[x % bpp] if x >= bpp else 0
                if kind == 3:
                    predictor = (left_value + up) // 2
                else:
                    up_left = int(prior[x - bpp]) if x >= bpp else 0
                    predictor = _paeth(left_value, up, up_left)
                value = (int(line[x]) + predictor) & 0xFF
                current[x] = value
                left[x % bpp] = value
        else:
            raise ImageDecodeError(f"unsupported filter type {kind}")
        out[y] = current
        prior = current
    return out


def decode_png(data: bytes) -> NDArray[np.uint8]:
    """Decode to an (height, width, channels) uint8 array."""
    chunks = _chunks(data)
    if not chunks or chunks[0][0] != b"IHDR" or len(chunks[0][1]) != 13:
        raise ImageDecodeError("missing IHDR")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", chunks[0][1]
    )
    if not (0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE):
        raise ImageDecodeError("invalid image dimensions")
    if width * height > MAX_PIXELS:
        raise ImageDecodeError("image exceeds the pixel limit")
    if depth != 8 or color not in CHANNELS:
        raise ImageDecodeError("unsupported bit depth or color type")
    if compression != 0 or filtering != 0 or interlace != 0:
        raise ImageDecodeError("unsupported compression, filter method or interlace")
    channels = CHANNELS[color]
    expected = height * (width * channels + 1)
    compressed = b"".join(body for kind, body in chunks if kind == b"IDAT")
    inflater = zlib.decompressobj()
    try:
        raw = inflater.decompress(compressed, expected + 1)
    except zlib.error as exc:
        raise ImageDecodeError("corrupt image data") from exc
    if len(raw) != expected or inflater.unconsumed_tail or not inflater.eof:
        raise ImageDecodeError("image data length does not match the header")
    return _unfilter(raw, width, height, channels).reshape(height, width, channels)
