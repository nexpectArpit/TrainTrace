"""Optional external experiment tracking with explicit availability state."""

import os


class WandbBridge:
    """Best-effort optional W&B synchronization; training remains local-first."""

    def __init__(self, config, run_id):
        self.run = None
        self.reason = None
        project = os.getenv("TRAINTRACE_WANDB_PROJECT", "").strip()
        if not project:
            return
        if not os.getenv("WANDB_API_KEY"):
            self.reason = "TRAINTRACE_WANDB_PROJECT is set but WANDB_API_KEY is missing"
            return
        try:
            import wandb

            self.run = wandb.init(
                project=project,
                entity=os.getenv("TRAINTRACE_WANDB_ENTITY") or None,
                name=config.get("approach_name", run_id),
                id=run_id,
                resume="never",
                config=config,
                tags=[f"{key}:{value}" for key, value in (config.get("tags") or {}).items()],
                reinit=True,
            )
        except Exception as exc:
            self.reason = f"W&B initialization failed: {type(exc).__name__}: {exc}"

    @property
    def metadata(self):
        if self.run:
            return {"status": "connected", "url": self.run.url}
        return {"status": "disabled" if not self.reason else "unavailable", "reason": self.reason}

    def log(self, values):
        if self.run:
            try:
                self.run.log(values)
            except Exception as exc:
                self.reason = f"W&B logging failed: {type(exc).__name__}: {exc}"
                try:
                    self.run.finish(exit_code=1)
                except Exception:
                    pass
                self.run = None

    def close(self):
        if self.run:
            try:
                self.run.finish()
            except Exception:
                pass
