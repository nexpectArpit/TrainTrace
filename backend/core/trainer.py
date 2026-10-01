"""
traintrace/core/trainer.py
==========================
PyTorch Autograd Training Loop Engine & Checkpointing Module.

Senior Engineering Rationale:
-----------------------------
1. Manages the execution heart of PyTorch training:
   - Batch Training Loop: Forward Pass -> Loss Calculation -> Autograd Backward Pass -> Optimizer Step
   - Weights are updated per batch via `optimizer.step()`, NOT just at the end of an epoch.
   - Disables gradient computation graph during validation using `torch.no_grad()` for memory efficiency.
2. Handles PyTorch compute device placement dynamically (`cpu`, `mps`, `cuda`).
3. Serializes checkpoints (`.pt` files) containing model weight state dicts, optimizer state, epoch count, and metrics.
"""

import time
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

# Import centralized configuration settings
from config import ARTIFACTS_DIR, get_default_device


# =============================================================================
# HELPER: SINGLE EPOCH TRAINING LOOP
# =============================================================================
def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device
) -> Tuple[float, float]:
    """
    Executes one complete training epoch over all DataLoader mini-batches.
    
    Args:
        model (nn.Module): PyTorch neural network model.
        dataloader (DataLoader): Training dataset batch generator.
        criterion (nn.Module): Loss function (e.g. CrossEntropyLoss).
        optimizer (optim.Optimizer): Parameter update algorithm (e.g. AdamW, SGD).
        device (torch.device): Compute execution target (cpu, mps, cuda).
        
    Returns:
        Tuple[float, float]: (average_epoch_loss, epoch_accuracy_percentage)
    """
    # Set model to training mode (enables Dropout layers and BatchNorm running stats tracking)
    model.train()
    
    running_loss = 0.0
    correct_predictions = 0
    total_samples = 0
    
    for batch_idx, (inputs, targets) in enumerate(dataloader):
        # Step 1: Move batch image tensors and label tensors to target compute device (GPU/CPU)
        inputs = inputs.to(device)
        targets = targets.to(device)
        
        # Step 2: Clear accumulated gradient buffers from the preceding batch step
        # Crucial: PyTorch accumulates gradients by default; zero_grad() prevents gradient contamination
        optimizer.zero_grad()
        
        # Step 3: Forward Pass — Execute model computation graph to produce unnormalized logits [B, 10]
        logits = model(inputs)
        
        # Step 4: Compute loss scalar measuring discrepancy between predictions and target labels
        loss = criterion(logits, targets)
        
        # Step 5: Autograd Backward Pass — Traverse computation graph backward to calculate dL/dW gradients
        loss.backward()
        
        # Step 6: Optimizer Step — Update layer weight parameters: W_new = W_old - lr * Gradient
        # Note: Weights update AFTER EVERY SINGLE BATCH!
        optimizer.step()
        
        # Accumulate scalar loss (loss.item() detaches tensor from computation graph to avoid memory leaks)
        running_loss += loss.item() * inputs.size(0)
        
        # Compute accuracy: argmax along class dimension (dim=1) gives predicted class index
        _, predicted_classes = torch.max(logits, dim=1)
        correct_predictions += (predicted_classes == targets).sum().item()
        total_samples += targets.size(0)
        
    avg_loss = running_loss / total_samples
    accuracy = (correct_predictions / total_samples) * 100.0
    return avg_loss, accuracy


# =============================================================================
# HELPER: EVALUATION LOOP
# =============================================================================
def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> Tuple[float, float]:
    """
    Evaluates model performance on validation or test dataset splits.
    
    Args:
        model (nn.Module): PyTorch neural network model.
        dataloader (DataLoader): Validation or Test dataset batch generator.
        criterion (nn.Module): Loss function.
        device (torch.device): Compute execution target.
        
    Returns:
        Tuple[float, float]: (average_eval_loss, eval_accuracy_percentage)
    """
    # Set model to evaluation mode (disables Dropout and freezes BatchNorm running stats)
    model.eval()
    
    running_loss = 0.0
    correct_predictions = 0
    total_samples = 0
    
    # torch.no_grad() disables PyTorch autograd graph construction, reducing memory usage and speeding up evaluation
    with torch.no_grad():
        for inputs, targets in dataloader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            
            # Forward pass only (no backward pass or optimizer step during evaluation!)
            logits = model(inputs)
            loss = criterion(logits, targets)
            
            running_loss += loss.item() * inputs.size(0)
            _, predicted_classes = torch.max(logits, dim=1)
            correct_predictions += (predicted_classes == targets).sum().item()
            total_samples += targets.size(0)
            
    avg_loss = running_loss / total_samples
    accuracy = (correct_predictions / total_samples) * 100.0
    return avg_loss, accuracy


# =============================================================================
# TRAINER ENGINE CLASS
# =============================================================================
class Trainer:
    """
    Orchestrates multi-epoch PyTorch model training, evaluation, and checkpoint serialization.
    """
    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        learning_rate: float = 0.001,
        device: Optional[torch.device] = None,
        save_dir: Path = ARTIFACTS_DIR
    ):
        self.device = device if device is not None else get_default_device()
        self.model = model.to(self.device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.save_dir = save_dir
        
        # Loss Function: CrossEntropyLoss (combines LogSoftmax and NLLLoss internally)
        self.criterion = nn.CrossEntropyLoss()
        
        # Optimizer: AdamW (Adam with decoupled Weight Decay regularization)
        self.optimizer = optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=1e-4)

    def train(self, num_epochs: int, run_id: str = "run_default") -> Dict[str, Any]:
        """
        Executes multi-epoch training loop, logging metrics per epoch and saving best checkpoint.
        
        Args:
            num_epochs (int): Total number of epochs to train.
            run_id (str): Unique identifier string for the execution run.
            
        Returns:
            Dict[str, Any]: Dictionary containing complete training metric history.
        """
        history = {
            "train_loss": [],
            "train_acc": [],
            "val_loss": [],
            "val_acc": [],
            "epoch_times": []
        }
        
        best_val_acc = 0.0
        best_checkpoint_path = None
        
        print(f"Starting Training Run [{run_id}] for {num_epochs} Epochs on Device: {self.device}")
        
        for epoch in range(1, num_epochs + 1):
            start_time = time.time()
            
            # Execute 1 epoch of batch training
            train_loss, train_acc = train_one_epoch(
                self.model, self.train_loader, self.criterion, self.optimizer, self.device
            )
            
            # Evaluate on validation dataset split
            val_loss, val_acc = evaluate(
                self.model, self.val_loader, self.criterion, self.device
            )
            
            elapsed_time = time.time() - start_time
            
            # Record epoch metrics into history lists
            history["train_loss"].append(train_loss)
            history["train_acc"].append(train_acc)
            history["val_loss"].append(val_loss)
            history["val_acc"].append(val_acc)
            history["epoch_times"].append(elapsed_time)
            
            print(
                f"  Epoch [{epoch:02d}/{num_epochs:02d}] ({elapsed_time:.1f}s) | "
                f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}% | "
                f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%"
            )
            
            # Checkpoint Serialization: Save best model weights when validation accuracy improves
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                checkpoint_filename = f"{run_id}_best_checkpoint.pt"
                best_checkpoint_path = self.save_dir / checkpoint_filename
                
                # Serialized PyTorch Checkpoint State Payload
                checkpoint_payload = {
                    "epoch": epoch,
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "val_acc": val_acc,
                    "val_loss": val_loss,
                    "run_id": run_id
                }
                
                # Save serialized state payload to disk
                torch.save(checkpoint_payload, best_checkpoint_path)
                
        print(f"Run [{run_id}] Complete! Best Validation Accuracy: {best_val_acc:.2f}%")
        history["best_val_acc"] = best_val_acc
        history["best_checkpoint_path"] = str(best_checkpoint_path) if best_checkpoint_path else None
        return history
