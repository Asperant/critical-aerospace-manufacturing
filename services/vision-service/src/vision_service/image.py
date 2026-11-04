"""Bounded decoding for the image formats accepted by the Vision pipeline."""

from __future__ import annotations

import warnings
from io import BytesIO

import numpy as np
from numpy.typing import NDArray
from PIL import Image, UnidentifiedImageError

from vision_service.png import ImageDecodeError, decode_png

SUPPORTED_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "image/jpg"})
MAX_PIXELS = 40_000_000


def decode_jpeg(data: bytes) -> NDArray[np.uint8]:
    """Decode a bounded JPEG/JPG into an RGB uint8 array.

    The image is opened once for structural verification and then reopened for
    loading so truncated or decompression-bomb inputs become an input error,
    not an unhandled worker failure.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as probe:
                if probe.format not in {"JPEG", "JPG"}:
                    raise ImageDecodeError("not a JPEG image")
                width, height = probe.size
                if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                    raise ImageDecodeError("image exceeds the pixel limit")
                probe.verify()
            with Image.open(BytesIO(data)) as decoded:
                decoded.load()
                return np.asarray(decoded.convert("RGB"), dtype=np.uint8).copy()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageDecodeError("image exceeds the pixel limit") from exc
    except (OSError, UnidentifiedImageError) as exc:
        raise ImageDecodeError("corrupt or unsupported JPEG image") from exc


def decode_image(data: bytes, content_type: str) -> NDArray[np.uint8]:
    """Decode an accepted image according to its declared content type."""
    if content_type == "image/png":
        return decode_png(data)
    if content_type in {"image/jpeg", "image/jpg"}:
        return decode_jpeg(data)
    raise ImageDecodeError(f"unsupported image content type: {content_type}")
