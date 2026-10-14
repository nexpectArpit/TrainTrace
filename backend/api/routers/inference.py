"""
traintrace/backend/api/routers/inference.py
===========================================
FastAPI Router for Real-time PyTorch Model Prediction Serving.
"""

import io
import time
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image
import torch

from core.models import get_model_by_name
from core.dataset import get_transforms
from config import get_default_device, ARTIFACTS_DIR

router = APIRouter(prefix="/api/v1/inference", tags=["Inference Serving"])

# CIFAR-10 10 Class Labels
CIFAR10_CLASSES = [
    "airplane", "automobile", "bird", "cat", "deer",
    "dog", "frog", "horse", "ship", "truck"
]


@router.post("/predict")
async def predict_image(file: UploadFile = File(...), model_name: str = "custom_cnn") -> Dict[str, Any]:
    """
    Executes PyTorch forward pass on uploaded image byte payload.
    Uses model in evaluation mode (model.eval() + torch.no_grad()).
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a valid image format.")
        
    try:
        # 1. Read & Decode Image Bytes to PIL Image
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # 2. Apply Evaluation Transforms (Resize 32x32 -> ToTensor -> Normalize)
        eval_transform = get_transforms(augment=False)
        input_tensor = eval_transform(pil_image).unsqueeze(0)  # Shape: [1, 3, 32, 32]
        
        device = get_default_device()
        model = get_model_by_name(model_name, num_classes=10).to(device)
        
        # Load best checkpoint if available
        checkpoint_path = ARTIFACTS_DIR / f"run_demo_01_best_checkpoint.pt"
        if checkpoint_path.exists():
            checkpoint = torch.load(checkpoint_path, map_location=device)
            model.load_state_dict(checkpoint["model_state_dict"])
            
        model.eval()  # Freeze Dropout and BatchNorm running stats
        
        # 3. Execute PyTorch Forward Pass without Autograd Gradient Construction
        start_time = time.time()
        with torch.no_grad():
            input_tensor = input_tensor.to(device)
            logits = model(input_tensor)
            probabilities = torch.softmax(logits, dim=1)[0]
            
            top_prob, top_class_idx = torch.max(probabilities, dim=0)
            
        latency_ms = (time.time() - start_time) * 1000.0
        predicted_label = CIFAR10_CLASSES[top_class_idx.item()]
        confidence = float(top_prob.item())
        
        return {
            "model_name": model_name,
            "predicted_class": predicted_label,
            "confidence_score": round(confidence, 4),
            "latency_ms": round(latency_ms, 2),
            "all_probabilities": {
                CIFAR10_CLASSES[i]: round(float(probabilities[i].item()), 4)
                for i in range(10)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference execution failed: {str(e)}")
