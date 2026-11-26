"""Coordinate Kaggle submission, status polling, telemetry and ingestion."""

from __future__ import annotations

import json
import os
from typing import Any

from cloud.artifacts import ingest_completed_run
from cloud.credentials import get_authenticated_api
from cloud.kernel import dispatch_kaggle_run
from cloud.telemetry import ingest_kernel_logs


def get_kaggle_run_status(kernel_id: str) -> dict[str, Any]:
    """Check live execution status of the Kaggle kernel."""
    try:
        api, _ = get_authenticated_api()
        status_info = api.kernels_status(kernel_id)
        status_obj = getattr(status_info, "status", None)
        status_name = getattr(status_obj, "name", None) or str(status_obj or "")
        if not status_name:
            raise ValueError("Kaggle returned an empty kernel status")
        error = getattr(status_info, "failure_message", None) or getattr(
            status_info, "failureMessage", None
        )
        return {
            "status": str(status_name).upper(),
            "error": str(error) if error else None,
            "kernel_id": kernel_id,
        }
    except Exception as exc:
        error = str(exc)
        normalized = (
            "DELETED"
            if any(marker in error.lower() for marker in ("404", "not found", "does not exist"))
            else "UNKNOWN"
        )
        return {"status": normalized, "error": error, "kernel_id": kernel_id}


def execute_remote_kaggle_run(payload: dict[str, Any], job_id: str, check_cancelled=None):
    """Execute a complete cloud GPU training lifecycle via Kaggle."""
    import time
    from db.database import database

    run_id = payload["run_id"]

    def set_run_state(**fields):
        with database() as c:
            c.execute(
                "UPDATE runs SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?",
                (*fields.values(), run_id),
            )

    def log_event(message: str):
        with database() as c:
            c.execute("INSERT INTO events(run_id, message) VALUES(?,?)", (run_id, message))

    if check_cancelled and check_cancelled():
        from core.trainer import TrainingStopped

        raise TrainingStopped("Stopped before cloud execution")

    set_run_state(
        status="RUNNING",
        progress_json=json.dumps(
            {
                "phase": "cloud_dispatch",
                "provider": "Kaggle Cloud GPU",
                "message": "Packaging code and submitting kernel to Kaggle GPU cluster...",
            }
        ),
    )
    log_event("Packaging and dispatching training run to Kaggle Cloud GPU...")

    dispatch_info = dispatch_kaggle_run(payload)
    kernel_id = dispatch_info["kernel_id"]
    set_run_state(
        progress_json=json.dumps(
            {
                "phase": "cloud_startup",
                "provider": "Kaggle Cloud GPU",
                "kernel_id": kernel_id,
                "remote_status": "SUBMITTED",
                "message": "Kernel submitted; waiting for Kaggle to start the worker.",
                "started_at": time.time(),
            }
        )
    )
    log_event(f"Kaggle kernel pushed successfully. Kernel ID: {kernel_id}")

    # Poll until remote execution completes and stream live progress into TrainTrace
    poll_start = time.time()
    timeout_seconds = int(os.getenv("TRAINTRACE_KAGGLE_TIMEOUT_SECONDS", str(12 * 60 * 60)))
    last_reported_status = ""
    unknown_since = None
    status_grace_seconds = int(os.getenv("TRAINTRACE_KAGGLE_STATUS_GRACE_SECONDS", "120"))
    seen_log_lines = set()
    last_log_error = None

    while True:
        if check_cancelled and check_cancelled():
            from core.trainer import TrainingStopped

            log_event(
                f"TrainTrace stopped monitoring this run. Kaggle kernel {kernel_id} may still be running; stop it on Kaggle."
            )
            raise TrainingStopped("Stopped by user during cloud execution")

        if time.time() - poll_start > timeout_seconds:
            log_event(
                f"TrainTrace stopped monitoring after {timeout_seconds} seconds; stop Kaggle kernel {kernel_id} on Kaggle if it is still running."
            )
            raise TimeoutError(
                f"Kaggle run exceeded its {timeout_seconds}-second monitoring limit; remote kernel {kernel_id} may still be running"
            )

        time.sleep(2)
        status_info = get_kaggle_run_status(kernel_id)
        current_status = status_info.get("status", "UNKNOWN")

        if current_status == "UNKNOWN":
            unknown_since = unknown_since or time.time()
            set_run_state(
                progress_json=json.dumps(
                    {
                        "phase": "cloud_connection",
                        "provider": "Kaggle Cloud GPU",
                        "kernel_id": kernel_id,
                        "remote_status": "UNKNOWN",
                        "message": "Kaggle status is unavailable; retrying connection.",
                        "elapsed_seconds": round(time.time() - poll_start, 1),
                    }
                )
            )
            if time.time() - unknown_since >= status_grace_seconds:
                detail = status_info.get("error") or "No status was returned"
                raise ConnectionError(
                    f"Could not confirm Kaggle kernel {kernel_id} for {status_grace_seconds} seconds: "
                    f"{detail}. Remote training may still be running; check Kaggle."
                )
        else:
            unknown_since = None

        if current_status != last_reported_status:
            last_reported_status = current_status
            log_event(f"Kaggle Cloud GPU state: {current_status}")

        # Read remote telemetry independently of the kernel status check.
        try:
            api, _ = get_authenticated_api()
            raw_logs = api.kernels_logs(kernel_id)
            ingest_kernel_logs(
                raw_logs or "",
                seen_log_lines,
                run_id=run_id,
                payload=payload,
                kernel_id=kernel_id,
                remote_status=current_status,
                poll_start=poll_start,
                set_run_state=set_run_state,
                log_event=log_event,
            )
            last_log_error = None
        except Exception as exc:
            log_error = f"{type(exc).__name__}: {exc}"
            if log_error != last_log_error:
                log_event(f"Kaggle telemetry temporarily unavailable: {log_error}")
                last_log_error = log_error

        if not seen_log_lines and current_status in ("QUEUED", "RUNNING"):
            elapsed = round(time.time() - poll_start, 1)
            set_run_state(
                progress_json=json.dumps(
                    {
                        "phase": "cloud_startup" if current_status == "QUEUED" else "cloud_running",
                        "provider": "Kaggle Cloud GPU",
                        "kernel_id": kernel_id,
                        "remote_status": current_status,
                        "elapsed_seconds": elapsed,
                        "message": (
                            f"Kaggle worker is {current_status.lower()} ({int(elapsed)}s elapsed); "
                            "preparing environment and dataset. Live logs flush when Kaggle buffers update."
                        ),
                    }
                )
            )

        if current_status == "COMPLETE":
            break
        elif current_status in ("ERROR", "CANCELLED", "FAILED", "DELETED"):
            err_msg = (
                status_info.get("error") or f"Kaggle kernel exited with status: {current_status}"
            )
            raise RuntimeError(err_msg)

    return ingest_completed_run(kernel_id, run_id, set_run_state, log_event)
