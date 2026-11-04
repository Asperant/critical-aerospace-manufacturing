"""F2 bounded local-contrast anomaly detector (05 DEP-059).

This remains a label-free baseline and does not make a quality decision.  The
original global median/MAD score was too sensitive to the illumination and
texture gradient of the magnetic-tile images.  The detector therefore scores
pixels against a local reflected median, while retaining the same normalized
bounding-box contract and UNKNOWN_REVIEW_REQUIRED semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import NDArray

MODEL_PACKAGE_ID = "vision-baseline-local-deviation"
MODEL_VERSION = "1.1.0"
MAD_TO_SIGMA = 1.4826
MIN_SIGMA = 0.01
BRIGHT_CONTRAST_WEIGHT = 0.35
MAX_ANALYSIS_PIXELS = 4_000_000


@dataclass(frozen=True)
class ThresholdPolicy:
    version: str = "vision-tp-local-contrast-z6/2"
    z_threshold: float = 6.0
    min_area_px: int = 4
    max_candidates: int = 64
    local_window_px: int = 15
    bridge_gap_px: int = 8


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


def _robust_z(
    values: NDArray[np.float64], center: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Return a one-sided robust z-score against a reference image."""
    residual = values - center
    median = float(np.median(residual))
    sigma = max(MAD_TO_SIGMA * float(np.median(np.abs(residual - median))), MIN_SIGMA)
    return np.maximum((residual - median) / sigma, 0.0)


def _local_background(image: NDArray[np.float64], window: int) -> NDArray[np.float64]:
    """Estimate the local surface baseline without zero-padding edge pixels."""
    size = max(3, int(window) | 1)
    half = size // 2
    padded = np.pad(image, ((0, 0), (half, half)), mode="reflect")
    windows = sliding_window_view(padded, size, axis=1)
    return np.median(windows, axis=-1)


def _analysis_view(image: NDArray[np.float64]) -> tuple[NDArray[np.float64], int]:
    """Bound memory use while preserving a source-normalized coordinate frame."""
    height, width = image.shape
    stride = max(1, ceil(sqrt((height * width) / MAX_ANALYSIS_PIXELS)))
    return image[::stride, ::stride], stride


def _contrast_scores(
    image: NDArray[np.float64], policy: ThresholdPolicy
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    horizontal = _local_background(image, policy.local_window_px)
    vertical = _local_background(image.T, policy.local_window_px).T
    # A dark vertical crack should be compared with the bright side context;
    # a bright pore/patch should be compared with the darker orthogonal context.
    dark_background = np.maximum(horizontal, vertical)
    bright_background = np.minimum(horizontal, vertical)
    dark = _robust_z(dark_background, image)
    bright = _robust_z(image, bright_background)
    return dark, bright


def deviation(image: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return the local dark/bright contrast score used for image-level output."""
    dark, bright = _contrast_scores(image, ThresholdPolicy())
    return np.maximum(dark, bright * BRIGHT_CONTRAST_WEIGHT)


def _bridge_dark_streaks(mask: NDArray[np.bool_], gap: int) -> NDArray[np.bool_]:
    """Join short vertical gaps in a thin dark defect without dilating it."""
    if gap <= 0:
        return mask
    bridged = mask.copy()
    for x in range(mask.shape[1]):
        rows = np.flatnonzero(mask[:, x])
        if rows.size < 2:
            continue
        for start, end in zip(rows[:-1], rows[1:], strict=True):
            if int(end - start - 1) <= gap:
                bridged[int(start) : int(end) + 1, int(x)] = True
    return bridged


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


def _is_border_streak(
    top: int, left: int, bottom: int, right: int, height: int, width: int
) -> bool:
    """Reject long narrow illumination strips glued to the image boundary."""
    edge_margin = 0.05
    touches_vertical = (
        left / width <= edge_margin or (width - 1 - right) / width <= edge_margin
    )
    touches_horizontal = (
        top / height <= edge_margin or (height - 1 - bottom) / height <= edge_margin
    )
    component_width = right - left + 1
    component_height = bottom - top + 1
    if (
        touches_vertical
        and component_width / width < 0.04
        and component_height / height > 0.04
    ):
        return True
    if (
        touches_horizontal
        and component_width / width < 0.04
        and component_height / height > 0.04
    ):
        return True
    if (
        (touches_vertical or touches_horizontal)
        and component_width / width < 0.04
        and component_height / height < 0.04
    ):
        return True
    return (
        touches_horizontal
        and component_height / height < 0.04
        and component_width / width > 0.04
    )


def detect(image: NDArray[np.float64], policy: ThresholdPolicy) -> Detection:
    source_height, source_width = image.shape
    working, stride = _analysis_view(image)
    dark, bright = _contrast_scores(working, policy)
    threshold = float(policy.z_threshold)
    mask = _bridge_dark_streaks(dark > threshold, policy.bridge_gap_px)
    mask |= (bright * BRIGHT_CONTRAST_WEIGHT) > threshold
    score_map = np.maximum(dark, bright * BRIGHT_CONTRAST_WEIGHT)
    found: list[Candidate] = []
    for pixels in _components(mask):
        if len(pixels) * stride * stride < policy.min_area_px:
            continue
        ys = [y for y, _ in pixels]
        xs = [x for _, x in pixels]
        top, left = min(ys), min(xs)
        bottom, right = max(ys), max(xs)
        if _is_border_streak(
            top, left, bottom, right, working.shape[0], working.shape[1]
        ):
            continue
        score = max(float(score_map[y, x]) for y, x in pixels)
        source_left = left * stride
        source_top = top * stride
        source_right = min(source_width - 1, (right + 1) * stride - 1)
        source_bottom = min(source_height - 1, (bottom + 1) * stride - 1)
        found.append(
            Candidate(
                x=source_left / source_width,
                y=source_top / source_height,
                width=(source_right - source_left + 1) / source_width,
                height=(source_bottom - source_top + 1) / source_height,
                area_fraction=len(pixels)
                * stride
                * stride
                / (source_height * source_width),
                score=score,
            )
        )
    found.sort(key=lambda c: (-c.score, c.y, c.x))
    image_score = float(score_map.max())
    return Detection(
        candidates=tuple(found[: policy.max_candidates]),
        image_score=image_score,
        truncated=len(found) > policy.max_candidates,
    )
