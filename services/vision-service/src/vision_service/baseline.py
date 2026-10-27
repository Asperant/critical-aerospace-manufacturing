"""F2 baseline: generic local-deviation candidate detector (05 DEP-059).

A deliberately simple, label-free algorithm that lets the pipeline compute an
observation from real pixels before promoted ModelPackages exist. It has no
known-class taxonomy, so every candidate is UNKNOWN_REVIEW_REQUIRED with no class
label or class confidence. It is not a trained model and makes no accuracy claim.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

MODEL_PACKAGE_ID = "vision-baseline-local-deviation"
MODEL_VERSION = "1.0.0"
MAD_TO_SIGMA = 1.4826
MIN_SIGMA = 0.01


@dataclass(frozen=True)
class ThresholdPolicy:
    version: str = "vision-tp-baseline-z6/1"
    z_threshold: float = 6.0
    min_area_px: int = 4
    max_candidates: int = 64


@dataclass(frozen=True)
class Candidate:
    x: float
    y: float
    width: float
    height: float
    area_fraction: float
    score: float


@dataclass(frozen=True)
class Detection:
    candidates: tuple[Candidate, ...]
    image_score: float
    truncated: bool


def deviation(image: NDArray[np.float64]) -> NDArray[np.float64]:
    """Robust z-score of every pixel against the image median and MAD."""
    median = float(np.median(image))
    sigma = max(MAD_TO_SIGMA * float(np.median(np.abs(image - median))), MIN_SIGMA)
    return np.abs(image - median) / sigma


def _components(mask: NDArray[np.bool_]) -> list[list[tuple[int, int]]]:
    """4-connected components of the mask, in row-major order of first pixel."""
    height, width = mask.shape
    seen = np.zeros_like(mask)
    components: list[list[tuple[int, int]]] = []
    for start_y, start_x in zip(*np.nonzero(mask), strict=True):
        sy, sx = int(start_y), int(start_x)
        if seen[sy, sx]:
            continue
        seen[sy, sx] = True
        stack = [(sy, sx)]
        pixels: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            pixels.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and mask[ny, nx]
                    and not seen[ny, nx]
                ):
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        components.append(pixels)
    return components


def detect(image: NDArray[np.float64], policy: ThresholdPolicy) -> Detection:
    height, width = image.shape
    z = deviation(image)
    found: list[Candidate] = []
    for pixels in _components(z > policy.z_threshold):
        if len(pixels) < policy.min_area_px:
            continue
        ys = [y for y, _ in pixels]
        xs = [x for _, x in pixels]
        top, left = min(ys), min(xs)
        found.append(
            Candidate(
                x=left / width,
                y=top / height,
                width=(max(xs) - left + 1) / width,
                height=(max(ys) - top + 1) / height,
                area_fraction=len(pixels) / (height * width),
                score=float(max(z[y, x] for y, x in pixels)),
            )
        )
    found.sort(key=lambda c: (-c.score, c.y, c.x))
    return Detection(
        candidates=tuple(found[: policy.max_candidates]),
        image_score=float(z.max()),
        truncated=len(found) > policy.max_candidates,
    )
