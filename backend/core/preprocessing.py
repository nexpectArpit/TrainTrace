"""Deterministic adapters for user-uploaded images before dataset normalization."""

from collections import deque

import numpy as np
from PIL import Image, ImageChops, ImageOps


def _digit_photo(image: Image.Image, size: int) -> Image.Image:
    """Extract the main colored/gray digit and render it like an MNIST glyph."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    edge = (
        [pixels[x, 0] for x in range(width)]
        + [pixels[x, height - 1] for x in range(width)]
        + [pixels[0, y] for y in range(height)]
        + [pixels[width - 1, y] for y in range(height)]
    )
    background = tuple(
        sorted(pixel[channel] for pixel in edge)[len(edge) // 2] for channel in range(3)
    )
    bg = Image.new("RGB", rgb.size, background)
    channels = ImageChops.difference(rgb, bg).split()
    foreground = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])

    # Detect components on a bounded mask so detached captions/watermarks do
    # not stretch the digit to the edge of the model input.
    scale = min(1.0, 512 / max(width, height))
    mask_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    mask = np.asarray(foreground.resize(mask_size, Image.Resampling.BILINEAR), dtype=np.uint8) >= 24
    visited = np.zeros(mask.shape, dtype=bool)
    best_count = 0
    best_bounds = None
    rows, cols = mask.shape
    for y, x in zip(*np.nonzero(mask)):
        if visited[y, x]:
            continue
        visited[y, x] = True
        queue = deque([(int(y), int(x))])
        count = 1
        min_x = max_x = int(x)
        min_y = max_y = int(y)
        while queue:
            cy, cx = queue.pop()
            for ny in range(max(0, cy - 1), min(rows, cy + 2)):
                for nx in range(max(0, cx - 1), min(cols, cx + 2)):
                    if mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((ny, nx))
                        count += 1
                        min_x, max_x = min(min_x, nx), max(max_x, nx)
                        min_y, max_y = min(min_y, ny), max(max_y, ny)
        if count > best_count:
            best_count = count
            best_bounds = (min_x, min_y, max_x + 1, max_y + 1)
    if best_bounds:
        left, top, right, bottom = best_bounds
        left = max(0, int(left * width / cols))
        top = max(0, int(top * height / rows))
        right = min(width, int(np.ceil(right * width / cols)))
        bottom = min(height, int(np.ceil(bottom * height / rows)))
        foreground = foreground.crop((left, top, right, bottom))
    else:
        foreground = foreground.crop(foreground.getbbox() or (0, 0, width, height))
    foreground = ImageOps.autocontrast(foreground, cutoff=1)

    target = max(1, round(size * 0.72))
    fitted = ImageOps.contain(foreground, (target, target), method=Image.Resampling.LANCZOS)
    canvas = Image.new("L", (size, size), 0)
    canvas.paste(fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2))
    return canvas.convert("RGB")


def _aspect_fit(image: Image.Image, preprocessing: dict) -> Image.Image:
    size = tuple(preprocessing["size"])
    image = image.convert("RGB")
    fitted = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
    means = preprocessing["mean"]
    fill = tuple(round(max(0, min(1, channel)) * 255) for channel in means[:3])
    if len(fill) == 1:
        fill *= 3
    canvas = Image.new("RGB", size, fill)
    canvas.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return canvas


def prepare_external_image(image: Image.Image, preprocessing: dict) -> Image.Image:
    """Apply the recorded upload adapter; missing provenance is an error."""
    size = preprocessing["size"]
    adapter = preprocessing.get("external_input_adapter")
    if not adapter:
        raise ValueError("Recorded external input adapter is missing")
    if adapter == "digit_photo_ink_v2":
        return _digit_photo(image, int(size[0]))
    if adapter == "aspect_fit_mean_pad":
        return _aspect_fit(image, preprocessing)
    raise ValueError(f"Unsupported external input adapter: {adapter}")
