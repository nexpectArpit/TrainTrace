"""Predictions resolve only the explicitly activated, immutable model version."""

import io
import json
import threading
import time
from pathlib import Path
import torch
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, UploadFile, File, HTTPException
from core.models import get_model_by_name
from torchvision import transforms
from config import REGISTRY_DIR, get_default_device
from db.database import database
from storage import sha256

router = APIRouter(prefix="/api/v1/inference", tags=["Inference"])
CIFAR10_CLASSES = [
    "airplane",
    "automobile",
    "bird",
    "cat",
    "deer",
    "dog",
    "frog",
    "horse",
    "ship",
    "truck",
]
_cache = {}
_lock = threading.Lock()
MAX_UPLOAD = 5 * 1024 * 1024


@router.post("/predict")
def predict_image(file: UploadFile = File(...), model_id: str | None = None):
    with database() as c:
        active = c.execute("SELECT model_id FROM serving WHERE id=1").fetchone()
        if not active:
            raise HTTPException(409, "Activate a registered model version first")
        if model_id and model_id != active[0]:
            raise HTTPException(409, "Requested version is not the active serving model")
        row = c.execute("SELECT * FROM models WHERE id=?", (active[0],)).fetchone()
    if not row or not row["manifest_json"] or not row["sha256"]:
        raise HTTPException(409, "Serving version has no verified provenance")
    model = dict(row)
    path = Path(model["checkpoint_path"]).resolve()
    if (
        not path.is_relative_to(REGISTRY_DIR.resolve())
        or not path.is_file()
        or sha256(path) != model["sha256"]
    ):
        raise HTTPException(409, "Serving checkpoint missing or changed")
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
        image = image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as e:
        raise HTTPException(422, "Invalid or unsupported image") from e
    manifest = json.loads(model["manifest_json"])
    architecture = manifest["configuration"]["model_name"]
    device = get_default_device()
    with _lock:
        key = (model["id"], model["sha256"], str(device))
        if key not in _cache:
            net = get_model_by_name(architecture).to(device)
            checkpoint = torch.load(path, map_location=device, weights_only=True)
            if checkpoint["run_id"] != model["run_id"]:
                raise HTTPException(409, "Checkpoint identity mismatch")
            net.load_state_dict(checkpoint["model_state_dict"])
            net.eval()
            _cache.clear()
            _cache[key] = net
        net = _cache[key]
        preprocessing = manifest["dataset"]["preprocessing"]
        transform = transforms.Compose(
            [
                transforms.Resize(tuple(preprocessing["size"])),
                transforms.ToTensor(),
                transforms.Normalize(preprocessing["mean"], preprocessing["std"]),
            ]
        )
        tensor = transform(image).unsqueeze(0).to(device)
        if device.type == "cuda":
            torch.cuda.synchronize()
        if device.type == "mps":
            torch.mps.synchronize()
        start = time.perf_counter()
        with torch.inference_mode():
            probs = torch.softmax(net(tensor), dim=1)[0].cpu().tolist()
        latency = 1000 * (time.perf_counter() - start)
    order = sorted(range(10), key=lambda i: probs[i], reverse=True)
    return {
        "model_id": model["id"],
        "version": model["version"],
        "run_id": model["run_id"],
        "checkpoint_sha256": model["sha256"],
        "model_name": architecture,
        "predicted_class": CIFAR10_CLASSES[order[0]],
        "confidence_score": probs[order[0]],
        "latency_ms": latency,
        "all_probabilities": dict(zip(CIFAR10_CLASSES, probs)),
        "top_k": [{"class": CIFAR10_CLASSES[i], "confidence": probs[i]} for i in order[:3]],
    }
