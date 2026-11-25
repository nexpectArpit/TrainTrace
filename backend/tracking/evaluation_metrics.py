"""Final holdout metrics and synchronized model latency measurements."""

import time

import torch

from core.trainer import TrainingStopped

def evaluate_candidate(model, loader, device, cancel=None, num_classes=10):
    """Evaluate a selected model once against the final test partition."""
    model.eval()
    matrix = torch.zeros(num_classes, num_classes, dtype=torch.int64)
    loss_sum = count = 0
    if device.type == "cuda":
        torch.cuda.synchronize()
    if device.type == "mps":
        torch.mps.synchronize()
    start = time.perf_counter()
    with torch.inference_mode():
        for x, y in loader:
            if cancel and cancel():
                raise TrainingStopped("Stopped during holdout evaluation")
            x, y = x.to(device), y.to(device)
            out = model(x)
            loss = torch.nn.functional.cross_entropy(out, y)
            if not torch.isfinite(loss):
                raise ValueError("Non-finite holdout loss")
            count += len(y)
            loss_sum += loss.item() * len(y)
            values = (y * num_classes + out.argmax(1)).cpu()
            matrix += torch.bincount(values, minlength=num_classes**2).reshape(
                num_classes, num_classes
            )
    if not count:
        raise ValueError("Empty holdout dataset")
    if device.type == "cuda":
        torch.cuda.synchronize()
    if device.type == "mps":
        torch.mps.synchronize()
    elapsed = time.perf_counter() - start
    tp = matrix.diag().double()
    precision = tp / matrix.sum(0).clamp(min=1)
    recall = tp / matrix.sum(1).clamp(min=1)
    f1 = 2 * precision * recall / (precision + recall).clamp(min=1e-15)
    return {
        "test_loss": loss_sum / count,
        "test_accuracy": 100 * tp.sum().item() / count,
        "precision_macro": precision.mean().item(),
        "recall_macro": recall.mean().item(),
        "f1_macro": f1.mean().item(),
        "confusion_matrix": matrix.tolist(),
        "samples": count,
        "evaluation_seconds": elapsed,
        "test_set_accessed": True,
    }


def benchmark_model_latency(model, device, input_size, warmup=10, repetitions=50):
    """Measure batch-one model-only latency using a synthetic normalized tensor."""
    sample = torch.zeros((1, 3, input_size, input_size), device=device)
    model.eval()

    def synchronize():
        if device.type == "cuda":
            torch.cuda.synchronize()
        elif device.type == "mps":
            torch.mps.synchronize()

    timings = []
    with torch.inference_mode():
        for _ in range(warmup):
            model(sample)
        synchronize()
        for _ in range(repetitions):
            synchronize()
            start = time.perf_counter()
            model(sample)
            synchronize()
            timings.append((time.perf_counter() - start) * 1000)
    timings.sort()
    return {
        "model_only_latency_ms_p50": timings[len(timings) // 2],
        "model_only_latency_ms_p95": timings[min(len(timings) - 1, int(len(timings) * 0.95))],
        "latency_method": (
            f"batch-one model forward; {warmup} warmups and {repetitions} synchronized samples; "
            "preprocessing and model loading excluded"
        ),
    }
