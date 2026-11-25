"""Move legacy flat artifacts into run folders while preserving database references."""

import argparse
import hashlib
import os
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = Path(os.environ.get("TRAINTRACE_STORAGE_DIR", ROOT / "backend/storage")).resolve()
DB = STORAGE / "db/traintrace.db"
ARTIFACTS = STORAGE / "artifacts"


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def category(kind, filename):
    if "checkpoint" in kind or filename.endswith("_checkpoint.pt"):
        return "checkpoints"
    if kind == "metrics_csv":
        return "metrics"
    if kind == "split":
        return "data"
    if kind.endswith("_png") or kind == "user_image_png":
        return "images"
    return "reports"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Perform the checked migration")
    args = parser.parse_args()
    if not DB.is_file():
        parser.exit(1, f"Database not found: {DB}\n")

    conn = sqlite3.connect(DB, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        active = conn.execute(
            "SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING')"
        ).fetchone()[0]
        if active:
            parser.exit(1, f"Stop or finish {active} active jobs before organizing artifacts.\n")
        records = [
            dict(row) for row in conn.execute("SELECT id,run_id,kind,path,sha256 FROM artifacts")
        ]
        moves = []
        for row in records:
            key = Path(row["path"])
            if len(key.parts) != 1:
                continue
            source = ARTIFACTS / key
            if not source.is_file() or checksum(source) != row["sha256"]:
                parser.exit(1, f"Missing or changed artifact: {source}\n")
            run_id = row["run_id"]
            if not run_id or not all(c.isalnum() or c in "_-" for c in run_id):
                parser.exit(1, f"Unsafe run ID: {run_id!r}\n")
            destination = ARTIFACTS / "runs" / run_id / category(row["kind"], key.name) / key
            if destination.exists():
                parser.exit(1, f"Destination already exists: {destination}\n")
            moves.append((row, source, destination))
        tracked_names = {
            Path(row["path"]).name for row in records if len(Path(row["path"]).parts) == 1
        }
        untracked = [
            path
            for path in ARTIFACTS.iterdir()
            if path.is_file() and path.name not in tracked_names
        ]
        print(f"Tracked flat artifacts: {len(moves)}")
        print(f"Untracked flat files to archive: {len(untracked)}")
        print(f"Storage: {ARTIFACTS}")
        if not args.apply:
            print("Dry run only. Use --apply to organize these files.")
            return

        backup = DB.with_name("traintrace.before-artifact-layout.db")
        if not backup.exists():
            with sqlite3.connect(backup) as target:
                conn.backup(target)
        copied = []
        try:
            for row, source, destination in moves:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                if checksum(destination) != row["sha256"]:
                    raise OSError(f"Checksum changed during copy: {destination}")
                copied.append(destination)
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING')"
            ).fetchone()[0]:
                raise RuntimeError("A job started during migration; retry after it finishes")
            for row, _, destination in moves:
                key = destination.relative_to(ARTIFACTS).as_posix()
                conn.execute(
                    "UPDATE artifacts SET path=? WHERE id=? AND path=?",
                    (key, row["id"], row["path"]),
                )
            conn.commit()
        except BaseException:
            conn.rollback()
            for path in copied:
                path.unlink(missing_ok=True)
            raise

        for _, source, _ in moves:
            source.unlink()
        archive = ARTIFACTS / "legacy-untracked"
        archive.mkdir(exist_ok=True)
        for source in untracked:
            target = archive / source.name
            if target.exists():
                raise FileExistsError(f"Archive collision: {target}")
            source.rename(target)
        print(
            f"Organized {len(moves)} tracked artifacts and archived {len(untracked)} untracked files."
        )
        print(f"Database backup: {backup}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
