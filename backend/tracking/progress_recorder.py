"""Persist live training samples and completed epoch metrics."""

import json
import time

import torch

from core.trainer import TrainingStopped
from db.database import database
from tracking.metrics_export import append_metrics_csv


class TrainingProgressRecorder:
    def __init__(self, run_id, trainer, cancelled, set_run, external_tracking):
        self.run_id = run_id
        self.trainer = trainer
        self.cancelled = cancelled
        self.set_run = set_run
        self.external_tracking = external_tracking
        self.samples = []

    def progress(self, **reading):
        if self.cancelled():
            raise TrainingStopped("Stopped by user")
        reading["phase"] = "training"
        reading["lr"] = self.trainer.optimizer.param_groups[0]["lr"]
        device = self.trainer.device.type
        if device == "cuda":
            reading["device_memory_mb"] = torch.cuda.memory_allocated() / (1024 * 1024)
        elif device == "mps" and hasattr(torch.mps, "current_allocated_memory"):
            reading["device_memory_mb"] = torch.mps.current_allocated_memory() / (1024 * 1024)
        self.set_run(self.run_id, progress_json=json.dumps(reading))
        if reading.get("batch_idx", 0) > 0:
            self.samples.append((
                self.run_id, reading["epoch"], reading["batch_idx"],
                reading["total_batches"], reading["batch_loss"],
                reading["running_acc"], reading.get("samples_per_sec"),
                reading.get("device_memory_mb"), reading.get("worker_cpu_percent"),
                reading.get("peak_rss_mb"), int(time.time() * 1000),
            ))

    def _write_samples(self, conn):
        if not self.samples:
            return
        conn.executemany(
            "INSERT OR IGNORE INTO run_progress_samples("
            "run_id,epoch,batch_idx,total_batches,batch_loss,running_acc,"
            "samples_per_sec,device_memory_mb,worker_cpu_percent,peak_rss_mb,observed_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            self.samples,
        )
        self.samples.clear()

    def epoch(self, number, metrics):
        with database() as conn:
            conn.execute(
                """INSERT INTO epoch_metrics(
                    run_id,epoch,train_loss,train_acc,val_loss,val_acc,epoch_time_sec,learning_rate
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    self.run_id, number, metrics["train_loss"], metrics["train_acc"],
                    metrics["val_loss"], metrics["val_acc"], metrics["epoch_time_sec"],
                    metrics["learning_rate"],
                ),
            )
            self._write_samples(conn)
        append_metrics_csv(self.run_id, number)
        self.external_tracking.log({"epoch": number, **metrics})

    def flush_samples(self):
        """Keep partial-epoch readings when a run stops or fails."""
        with database() as conn:
            self._write_samples(conn)
