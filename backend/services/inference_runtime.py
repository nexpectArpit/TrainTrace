"""Upload decoding and checkpoint execution for image inference."""

import base64
import io
import threading
import time

import torch
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from torchvision import transforms

from core.models import get_model_by_name
from core.preprocessing import prepare_external_image

_cache = {}
_lock = threading.Lock()
_MAX_CACHE_ENTRIES = 6
MAX_UPLOAD = 5 * 1024 * 1024


def _decode_uploaded_image(file: UploadFile) -> Image.Image:
    contents = file.file.read(MAX_UPLOAD + 1)
    if len(contents) > MAX_UPLOAD:
        raise HTTPException(413, "Image must be at most 5 MB")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(422, "Upload a PNG or JPEG image")
    try:
        image = Image.open(io.BytesIO(contents))
        if image.format not in ["PNG", "JPEG"] or image.width * image.height > 16_000_000:
            raise ValueError("Use PNG/JPEG up to 16 megapixels")
        image.load()
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            # Composite transparent pixels onto a clean white background so black ink
            # on transparent canvases (e.g. tablet drawings, Mac Preview, HTML canvas)
            # does not collapse into a solid all-black square.
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            background.alpha_composite(rgba)
            return background.convert("RGB")
        return image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as e:
        raise HTTPException(422, "Invalid or unsupported image") from e


def _build_eval_transform(preprocessing: dict) -> transforms.Compose:
    steps = []
    if preprocessing.get("input_conversion") == "grayscale_to_rgb":
        steps.append(transforms.Grayscale(num_output_channels=3))
    steps.extend(
        [
            transforms.Resize(tuple(preprocessing["size"])),
            transforms.ToTensor(),
            transforms.Normalize(preprocessing["mean"], preprocessing["std"]),
        ]
    )
    return transforms.Compose(steps)


def _predict_with_checkpoint(
    *,
    cache_key,
    architecture: str,
    num_classes: int,
    configuration: dict,
    preprocessing: dict,
    path,
    expected_run_id: str,
    image: Image.Image,
    device: torch.device,
):
    with _lock:
        if cache_key in _cache:
            net = _cache.pop(cache_key)
            _cache[cache_key] = net
        else:
            net = get_model_by_name(
                architecture,
                num_classes=num_classes,
                native_stem=bool(configuration.get("pretrained")),
                architecture_config=configuration.get("architecture_config"),
            ).to(device)
            checkpoint = torch.load(path, map_location=device, weights_only=True)
            if checkpoint.get("run_id") != expected_run_id:
                raise HTTPException(409, "Checkpoint identity mismatch")
            net.load_state_dict(checkpoint["model_state_dict"])
            net.eval()
            while len(_cache) >= _MAX_CACHE_ENTRIES:
                _cache.pop(next(iter(_cache)))
            _cache[cache_key] = net
        try:
            model_image = prepare_external_image(image, preprocessing)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(409, f"Invalid model preprocessing contract: {exc}") from exc
        transform = _build_eval_transform(preprocessing)
        tensor = transform(model_image).unsqueeze(0).to(device)
        if device.type == "cuda":
            torch.cuda.synchronize()
        if device.type == "mps":
            torch.mps.synchronize()
        start = time.perf_counter()
        with torch.inference_mode():
            probs = torch.softmax(net(tensor), dim=1)[0].cpu().tolist()
        latency = 1000 * (time.perf_counter() - start)
    order = sorted(range(num_classes), key=lambda i: probs[i], reverse=True)
    preview = io.BytesIO()
    model_image.save(preview, format="PNG")
    preview_data_url = "data:image/png;base64," + base64.b64encode(preview.getvalue()).decode(
        "ascii"
    )
    return probs, latency, order, preview_data_url
