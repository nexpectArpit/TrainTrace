"""Portable backups and non-destructive managed-storage integrity checks."""

import argparse
from contextlib import closing
import json
import shutil
import sqlite3
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath

from config import ARTIFACTS_DIR, DATA_DIR, REGISTRY_DIR
from db.database import get_db_connection
from storage import resolve_managed_path, sha256


def audit_storage():
    with closing(get_db_connection()) as conn:
        artifacts = [dict(r) for r in conn.execute("SELECT id,path,sha256 FROM artifacts")]
        models = [dict(r) for r in conn.execute("SELECT id,checkpoint_path,sha256 FROM models")]
    report = {
        "missing_artifacts": [],
        "corrupt_artifacts": [],
        "missing_models": [],
        "corrupt_models": [],
        "orphan_files": [],
    }
    known_artifacts = set()
    for row in artifacts:
        try:
            path = resolve_managed_path(ARTIFACTS_DIR, row["path"])
        except ValueError:
            report["missing_artifacts"].append({"id": row["id"], "reason": "unsafe key"})
            continue
        known_artifacts.add(path)
        if not path.is_file():
            report["missing_artifacts"].append({"id": row["id"], "key": row["path"]})
        elif sha256(path) != row["sha256"]:
            report["corrupt_artifacts"].append({"id": row["id"], "key": row["path"]})
    known_models = set()
    for row in models:
        try:
            path = resolve_managed_path(REGISTRY_DIR, row["checkpoint_path"])
        except ValueError:
            report["missing_models"].append({"id": row["id"], "reason": "unsafe key"})
            continue
        known_models.add(path)
        if not path.is_file():
            report["missing_models"].append({"id": row["id"], "key": row["checkpoint_path"]})
        elif row["sha256"] and sha256(path) != row["sha256"]:
            report["corrupt_models"].append({"id": row["id"], "key": row["checkpoint_path"]})
    for root, known in ((ARTIFACTS_DIR, known_artifacts), (REGISTRY_DIR, known_models)):
        for path in root.rglob("*"):
            if root == ARTIFACTS_DIR and "legacy-untracked" in path.relative_to(root).parts:
                continue
            if path.is_file() and path not in known and not path.name.endswith(".tmp"):
                report["orphan_files"].append(
                    {
                        "root": root.name,
                        "key": path.relative_to(root).as_posix(),
                        "age_days": max(0, int((time.time() - path.stat().st_mtime) / 86400)),
                    }
                )
    return report


def prune_orphans(report, older_than_days):
    removed = []
    for item in report["orphan_files"]:
        if item["age_days"] < older_than_days:
            continue
        root = ARTIFACTS_DIR if item["root"] == ARTIFACTS_DIR.name else REGISTRY_DIR
        path = resolve_managed_path(root, item["key"])
        if path.is_file():
            path.unlink()
            removed.append(item)
    return removed


def create_backup(destination):
    destination = Path(destination).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(get_db_connection()) as conn:
        active = conn.execute(
            "SELECT id,status FROM jobs WHERE status IN ('QUEUED','RUNNING') LIMIT 1"
        ).fetchone()
        if active:
            raise RuntimeError(
                f"Wait for or stop job {active['id']} ({active['status']}) before backup"
            )
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        with tempfile.TemporaryDirectory(prefix="traintrace-backup-") as tmp:
            snapshot = Path(tmp) / "traintrace.db"
            with sqlite3.connect(snapshot) as target:
                conn.backup(target)
            with tarfile.open(destination, "w:gz") as archive:
                archive.add(snapshot, arcname="db/traintrace.db")
                for path, key in (
                    (DATA_DIR, "data"),
                    (ARTIFACTS_DIR, "artifacts"),
                    (REGISTRY_DIR, "registry"),
                ):
                    if path.exists():
                        archive.add(path, arcname=key)
    return destination


def restore_backup(archive_path, destination):
    destination = Path(destination).expanduser().resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Restore destination must be empty; choose a new storage directory")
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts or member.issym() or member.islnk():
                raise ValueError("Backup contains an unsafe path")
        archive.extractall(destination, members=members, filter="data")
    if not (destination / "db" / "traintrace.db").is_file():
        shutil.rmtree(destination, ignore_errors=True)
        raise ValueError("Backup does not contain a TrainTrace database")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("audit", help="Report missing, corrupt, and untracked managed files")
    backup_parser = sub.add_parser("backup", help="Create a consistent compressed storage backup")
    backup_parser.add_argument("destination")
    restore_parser = sub.add_parser("restore", help="Restore to a new, empty storage directory")
    restore_parser.add_argument("archive")
    restore_parser.add_argument("destination")
    prune_parser = sub.add_parser(
        "prune-orphans", help="Delete only old files confirmed as untracked"
    )
    prune_parser.add_argument("--older-than-days", type=int, default=30)
    prune_parser.add_argument("--delete", action="store_true", help="Actually remove listed files")
    args = parser.parse_args()
    if args.command == "audit":
        print(json.dumps(audit_storage(), indent=2))
    elif args.command == "backup":
        print(create_backup(args.destination))
    elif args.command == "restore":
        print(restore_backup(args.archive, args.destination))
    else:
        report = audit_storage()
        eligible = [f for f in report["orphan_files"] if f["age_days"] >= args.older_than_days]
        print(json.dumps(eligible, indent=2))
        if args.delete:
            print(json.dumps({"removed": prune_orphans(report, args.older_than_days)}, indent=2))


if __name__ == "__main__":
    main()
