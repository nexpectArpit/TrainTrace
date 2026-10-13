"""
traintrace/backend/tracking/tracker.py
======================================
Experiment Tracker bridging PyTorch execution to SQLite storage and artifact sinks.
"""

from typing import Dict, Any, Optional
import torch
from core.models import get_model_by_name
from core.dataset import get_cifar10_dataloaders
from core.trainer import Trainer
from db.database import get_db_connection
from db import repository


class ExperimentTracker:
    """
    Orchestrates experiment execution, metric tracking, database persistence, and artifact saving.
    """
    def __init__(self, exp_id: str, exp_name: str, objective: str):
        self.exp_id = exp_id
        self.exp_name = exp_name
        self.objective = objective
        
        # Ensure experiment parent record exists in database
        conn = get_db_connection()
        existing = repository.get_experiment(conn, exp_id)
        if not existing:
            repository.create_experiment(conn, exp_id, exp_name, objective)
        conn.close()

    def run_experiment(
        self,
        run_id: str,
        approach_name: str,
        model_name: str,
        epochs: int = 10,
        batch_size: int = 128,
        lr: float = 0.001,
        seed: int = 42
    ) -> Dict[str, Any]:
        """
        Executes a training run, logs metrics per epoch to SQLite, and saves model checkpoints.
        Uses short transient database connections to prevent SQLite locking during training.
        """
        # 1. Create or update Run record in SQLite
        conn = get_db_connection()
        existing_run = repository.get_run(conn, run_id)
        if existing_run:
            repository.update_run_status(conn, run_id, "RUNNING")
        else:
            repository.create_run(
                conn, run_id, self.exp_id, approach_name, model_name, batch_size, epochs, lr, seed, status="RUNNING"
            )
        conn.close()  # Close connection immediately so DB is NOT locked during PyTorch training!
        
        try:
            # 2. Set random seed for PyTorch CPU & GPU reproducibility
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
                
            # 3. Instantiate Model and DataLoaders
            model = get_model_by_name(model_name, num_classes=10)
            train_loader, val_loader, _ = get_cifar10_dataloaders(
                batch_size=batch_size, seed=seed, num_workers=0
            )
            
            # 4. Execute PyTorch Training Loop
            trainer = Trainer(
                model=model,
                train_loader=train_loader,
                val_loader=val_loader,
                learning_rate=lr
            )
            
            history = trainer.train(num_epochs=epochs, run_id=run_id)
            
            # 5. Persist per-epoch metrics and update status to COMPLETED using transient connection
            conn = get_db_connection()
            for epoch_idx in range(len(history["train_loss"])):
                repository.save_epoch_metric(
                    conn,
                    run_id=run_id,
                    epoch=epoch_idx + 1,
                    train_loss=history["train_loss"][epoch_idx],
                    train_acc=history["train_acc"][epoch_idx],
                    val_loss=history["val_loss"][epoch_idx],
                    val_acc=history["val_acc"][epoch_idx],
                    epoch_time_sec=history["epoch_times"][epoch_idx]
                )
                
            repository.update_run_status(conn, run_id, "COMPLETED")
            conn.close()
            return history

        except Exception as e:
            conn = get_db_connection()
            repository.update_run_status(conn, run_id, "FAILED")
            conn.close()
            raise e
