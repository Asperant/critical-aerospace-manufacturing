"""Format-boundary tests for the real Vision image decoder."""

from io import BytesIO

import numpy as np
import pytest
from PIL import Image
from vision_service import ImageDecodeError, decode_image, decode_jpeg


def _jpeg() -> bytes:
    image = Image.fromarray(
        np.arange(32 * 24, dtype=np.uint8).reshape(24, 32), mode="L"
    )
    stream = BytesIO()
    image.save(stream, format="JPEG", quality=95)
    return stream.getvalue()


def test_jpeg_is_decoded_to_bounded_rgb_pixels() -> None:
    decoded = decode_jpeg(_jpeg())
    assert decoded.shape == (24, 32, 3)
    assert decoded.dtype == np.uint8


@pytest.mark.parametrize("content_type", ["image/jpeg", "image/jpg"])
def test_jpeg_content_type_aliases_are_supported(content_type: str) -> None:
    assert decode_image(_jpeg(), content_type).shape == (24, 32, 3)


def test_invalid_jpeg_is_an_image_input_error() -> None:
    with pytest.raises(ImageDecodeError):
        decode_jpeg(b"not a jpeg")
