# Storage backup, restore, and optional W&B sync

## Backup and integrity checks

Run these from the `backend/` directory with the TrainTrace virtual environment active. Backups stop if a job is currently running so the database and checkpoints are captured at a stable boundary.

```sh
python storage_maintenance.py audit
python storage_maintenance.py backup /path/to/backups/traintrace-YYYYMMDD.tar.gz
```

The archive contains a SQLite online-backup snapshot and the managed data, artifacts, and registry folders. Keep it outside the TrainTrace storage directory. Copy the archive to a second device or protected cloud location for disaster recovery.

Restore into a new, empty directory, then point `TRAINTRACE_STORAGE_DIR` at it before launching the backend:

```sh
python storage_maintenance.py restore /path/to/backups/traintrace-YYYYMMDD.tar.gz /path/to/restored-traintrace
export TRAINTRACE_STORAGE_DIR=/path/to/restored-traintrace
```

The audit command reports missing or checksum-mismatched files and untracked files. Orphan cleanup is a separate explicit action and prints its candidates without deleting by default:

```sh
python storage_maintenance.py prune-orphans --older-than-days 30
python storage_maintenance.py prune-orphans --older-than-days 30 --delete
```

Inspect the candidates and retain a backup before using `--delete`.

## Optional Weights & Biases synchronization

Install the optional integration and set the project plus W&B credential before launching the API:

```sh
pip install -r requirements-optional.txt
export TRAINTRACE_WANDB_PROJECT=traintrace
export WANDB_API_KEY=your-key
```

`TRAINTRACE_WANDB_ENTITY` is optional. TrainTrace logs epoch metrics from the worker and records the sync URL/status on the run. Missing credentials, the optional package, or a W&B outage do not stop local training; the run records why synchronization was unavailable.
