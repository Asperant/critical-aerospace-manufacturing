"""TEST-VIS-PIPELINE: bounded PNG decoding of inspection images."""

import struct
import zlib

import numpy as np
import pytest
from conftest import chunk, encode_png
from vision_service import ImageDecodeError, decode_png


@pytest.mark.parametrize("channels", [1, 2, 3, 4])
@pytest.mark.parametrize("filter_kind", [0, 1, 2, 3, 4])
def test_round_trip_for_every_color_type_and_filter(
    channels: int, filter_kind: int
) -> None:
    rng = np.random.default_rng(channels * 10 + filter_kind)
    pixels = rng.integers(0, 256, (9, 13, channels), dtype=np.uint8)
    decoded = decode_png(encode_png(pixels, filter_kind))
    assert decoded.dtype == np.uint8
    assert np.array_equal(decoded, pixels)


def _header(
    width: int, height: int, depth: int = 8, color: int = 0, interlace: int = 0
) -> bytes:
    return chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, depth, color, 0, 0, interlace)
    )


def _png(header: bytes, raw: bytes) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + header
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def test_rejects_non_png_and_truncated_data() -> None:
    good = encode_png(np.zeros((4, 4, 1), dtype=np.uint8))
    for data in (b"GIF89a", good[:-6], good[:20], b""):
        with pytest.raises(ImageDecodeError):
            decode_png(data)


def test_rejects_crc_mismatch() -> None:
    data = bytearray(encode_png(np.zeros((4, 4, 1), dtype=np.uint8)))
    data[20] ^= 0xFF
    with pytest.raises(ImageDecodeError, match="CRC"):
        decode_png(bytes(data))


@pytest.mark.parametrize(
    ("header", "message"),
    [
        (_header(4, 4, depth=16), "bit depth"),
        (_header(4, 4, color=3), "color type"),
        (_header(4, 4, interlace=1), "interlace"),
        (_header(0, 4), "dimensions"),
        (_header(10_000, 10_000), "pixel limit"),
    ],
)
def test_rejects_unsupported_or_hostile_headers(header: bytes, message: str) -> None:
    with pytest.raises(ImageDecodeError, match=message):
        decode_png(_png(header, b"\x00" * 5 * 4))


def test_rejects_data_length_mismatch_and_unknown_filter() -> None:
    with pytest.raises(ImageDecodeError, match="length"):
        decode_png(_png(_header(4, 4), b"\x00" * 7))
    with pytest.raises(ImageDecodeError, match="filter"):
        decode_png(_png(_header(4, 4), (b"\x07" + b"\x00" * 4) * 4))


def test_decompression_is_bounded_by_the_header() -> None:
    oversized = (b"\x00" + b"\x00" * 4) * 4 + b"\x00" * 1_000_000
    with pytest.raises(ImageDecodeError, match="length"):
        decode_png(_png(_header(4, 4), oversized))
