"""
traintrace/backend/tracking/evaluator.py
========================================
Holdout Test Set Evaluator & Dual Reproducibility Protocol Engine (Protocol A & B).
"""

import time
from typing import Dict, Any, List
import torch
import numpy as np
from core.models import get_model_by_name
from core.dataset import get_cifar10_dataloaders
from core.trainer import evaluate, Trainer
from config import get_default_device


class Evaluator:
    """
    Evaluates trained model checkpoints and executes Reproducibility Audits.
    """
    def __init__(self, device: torch.device = None):
        self.device = device if device is not None else get_default_device()

    def evaluate_holdout(
        self,
        checkpoint_path: str,
        model_name: str,
        batch_size: int = 128
    ) -> Dict[str, Any]:
        """
        Executes evaluation on unseen holdout test dataset (10,000 samples).
        """
        _, _, test_loader = get_cifar10_dataloaders(batch_size=batch_size, num_workers=0)
        
        # Load model structure & weights from checkpoint
        model = get_model_by_name(model_name, num_classes=10).to(self.device)
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        model.load_state_dict(checkpoint["model_state_dict"])
        
        criterion = torch.nn.CrossEntropyLoss()
        
        start_time = time.time()
        test_loss, test_acc = evaluate(model, test_loader, criterion, self.device)
        eval_time_sec = time.time() - start_time
        
        # Calculate average latency per sample in milliseconds
        total_samples = len(test_loader.dataset)
        avg_latency_ms = (eval_time_sec / total_samples) * 1000.0
        
        return {
            "test_loss": test_loss,
            "test_accuracy": test_acc,
            "latency_ms_per_sample": avg_latency_ms,
            "total_samples_evaluated": total_samples
        }

    def audit_protocol_a(
        self,
        original_run_id: str,
        model_name: str,
        seed: int = 42,
        epochs: int = 2
    ) -> Dict[str, Any]:
        """
        PROTOCOL A: Same-Condition Repeatability Audit.
        Re-executes run under identical seed/config to verify deterministic metric match.
        """
        torch.manual_seed(seed)
        model1 = get_model_by_name(model_name)
        train_loader1, val_loader1, _ = get_cifar10_dataloaders(batch_size=128, seed=seed, num_workers=0)
        t1 = Trainer(model1, train_loader1, val_loader1, device=self.device)
        h1 = t1.train(num_epochs=epochs, run_id=f"{original_run_id}_repro_a1")

        torch.manual_seed(seed)
        model2 = get_model_by_name(model_name)
        train_loader2, val_loader2, _ = get_cifar10_dataloaders(batch_size=128, seed=seed, num_workers=0)
        t2 = Trainer(model2, train_loader2, val_loader2, device=self.device)
        h2 = t2.train(num_epochs=epochs, run_id=f"{original_run_id}_repro_a2")

        acc_diff = abs(h1["best_val_acc"] - h2["best_val_acc"])
        passed = acc_diff < 0.01  # Match within 0.01% tolerance

        return {
            "protocol": "Protocol A (Same-Condition Repeatability)",
            "run_1_val_acc": h1["best_val_acc"],
            "run_2_val_acc": h2["best_val_acc"],
            "accuracy_delta": acc_diff,
            "passed": passed
        }

    def audit_protocol_b(
        self,
        model_name: str,
        seeds: List[int] = [42, 101, 2024],
        epochs: int = 2
    ) -> Dict[str, Any]:
        """
        PROTOCOL B: Multi-Seed Sensitivity Analysis.
        Executes N runs across controlled random seeds to measure statistical variance.
        """
        val_accuracies = []
        for s in seeds:
            torch.manual_seed(s)
            model = get_model_by_name(model_name)
            t_loader, v_loader, _ = get_cifar10_dataloaders(batch_size=128, seed=s, num_workers=0)
            trainer = Trainer(model, t_loader, v_loader, device=self.device)
            res = trainer.train(num_epochs=epochs, run_id=f"prob_b_seed_{s}")
            val_accuracies.append(res["best_val_acc"])

        mean_acc = float(np.mean(val_accuracies))
        std_acc = float(np.std(val_accuracies))

        return {
            "protocol": "Protocol B (Multi-Seed Sensitivity Analysis)",
            "seeds_tested": seeds,
            "val_accuracies": val_accuracies,
            "mean_accuracy": mean_acc,
            "std_deviation": std_acc,
            "min_max_spread": float(max(val_accuracies) - min(val_accuracies))
        }
