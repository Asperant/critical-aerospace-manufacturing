"""Versioned preprocessing and input-quality assessment.

Any change to the arithmetic below is a new PREPROCESSING_VERSION, because the
version is part of the evaluated pipeline identity carried on every observation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

PREPROCESSING_VERSION = "vision-prep-gray-unit/1"
MIN_SIDE_PX = 16
LOW_CONTRAST_STD = 0.01
LUMA = np.array([0.299, 0.587, 0.114])

Quality = Literal["VALID", "DEGRADED_INPUT", "INVALID_INPUT"]


@dataclass(frozen=True)
class Preprocessed:
    image: NDArray[np.float64]
    quality: Quality
    flags: tuple[str, ...]


def to_unit_gray(pixels: NDArray[np.uint8]) -> NDArray[np.float64]:
    """Grayscale in [0, 1]; alpha is ignored, color uses ITU-R BT.601 luma."""
    channels = pixels.shape[2]
    values = pixels.astype(np.float64) / 255.0
    if channels in (1, 2):
        return values[:, :, 0]
    return values[:, :, :3] @ LUMA


def preprocess(pixels: NDArray[np.uint8]) -> Preprocessed:
    height, width = pixels.shape[:2]
    if min(height, width) < MIN_SIDE_PX:
        return Preprocessed(np.zeros((0, 0)), "INVALID_INPUT", ("IMAGE_TOO_SMALL",))
    image = to_unit_gray(pixels)
    if float(image.std()) < LOW_CONTRAST_STD:
        return Preprocessed(image, "DEGRADED_INPUT", ("LOW_CONTRAST",))
    return Preprocessed(image, "VALID", ())
