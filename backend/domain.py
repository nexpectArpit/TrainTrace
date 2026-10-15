"""Validated product contracts and storage identities."""

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
Architecture = Literal["custom_cnn", "resnet18", "mobilenet_v2", "efficientnet_b0"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ExperimentCreate(Contract):
    id: Identifier
    name: Text
    objective: Text
    hypothesis: Text
    target_accuracy: float | None = Field(default=None, ge=0, le=100)
    target_latency_ms: float | None = Field(default=None, gt=0)
    parent_run_id: Identifier | None = None


class ExperimentUpdate(Contract):
    name: Text
    objective: Text
    hypothesis: Text
    conclusion: str = Field(default="", max_length=10000)
    archived: bool = False
    target_accuracy: float | None = Field(default=None, ge=0, le=100)
    target_latency_ms: float | None = Field(default=None, gt=0)


class LaunchRun(Contract):
    run_id: Identifier
    experiment_id: Identifier
    approach_name: Text
    model_name: Architecture = "custom_cnn"
    epochs: int = Field(default=5, ge=1, le=1000)
    batch_size: int = Field(default=128, ge=2, le=2048)
    learning_rate: float = Field(default=0.001, gt=0, le=1)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    split_seed: int = Field(default=42, ge=0, le=2**32 - 1)
    pretrained: bool = False
    scheduler_type: Literal["constant", "cosine", "step"] = "constant"
    optimizer: Literal["adamw", "sgd"] = "adamw"
    weight_decay: float = Field(default=0.0001, ge=0, le=1)
    predecessor_run_id: Identifier | None = None
    motivating_reason: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def motivation(self):
        if self.predecessor_run_id and not self.motivating_reason.strip():
            raise ValueError("A successor run requires a motivating limitation.")
        if self.model_name == "custom_cnn" and self.pretrained:
            raise ValueError("CustomCNN has no pretrained weights.")
        return self


class DecisionRecord(Contract):
    run_id: Identifier
    status: Literal["CANDIDATE", "ACCEPTED", "REJECTED", "SUPERSEDED", "SELECTED"]
    rationale: Text
    limitations: Text
    alternatives_considered: Text
    why_not_alternative: Text
    tradeoff_acknowledged: Text
    next_investigation: str = Field(default="", max_length=10000)


class RegisterModel(Contract):
    name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")]
    run_id: Identifier
    version: Annotated[
        str, StringConstraints(pattern=r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    ]


class AuditRequest(Contract):
    run_id: Identifier
    seeds: list[Annotated[int, Field(ge=0, le=2**32 - 1)]] = Field(
        default_factory=lambda: [42, 101, 2024, 7, 99], min_length=2, max_length=10
    )

    @model_validator(mode="after")
    def unique_seeds(self):
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Seeds must be distinct.")
        return self
