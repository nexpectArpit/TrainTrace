"""Validated product contracts and storage identities."""

from typing import Annotated, Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
TagMap = dict[
    Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,63}")],
    Annotated[str, StringConstraints(max_length=256)],
]
Architecture = Literal["custom_cnn", "resnet18", "mobilenet_v2", "efficientnet_b0"]
DatasetName = Literal["cifar10", "cifar100", "mnist", "fashion_mnist", "svhn"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class CustomCNNConfig(Contract):
    depth: int = Field(default=3, ge=2, le=6, description="Number of convolutional feature blocks")
    width: int = Field(
        default=32, ge=8, le=128, description="Channels in the first block; later blocks double"
    )
    classifier_width: int = Field(default=256, ge=16, le=2048)
    dropout: float = Field(default=0.3, ge=0, lt=1)

    @field_validator("classifier_width")
    @classmethod
    def validate_classifier_width_step(cls, value: int) -> int:
        if value % 16 != 0:
            raise ValueError("classifier_width must be a multiple of 16")
        return value


class ExperimentCreate(Contract):
    id: Identifier
    name: Text
    objective: Text
    hypothesis: Text
    target_accuracy: float | None = Field(default=None, ge=0, le=100)
    target_latency_ms: float | None = Field(default=None, gt=0)
    parent_run_id: Identifier | None = None
    tags: TagMap = Field(default_factory=dict, max_length=50)


class ExperimentUpdate(Contract):
    name: Text
    objective: Text
    hypothesis: Text
    conclusion: str = Field(default="", max_length=10000)
    archived: bool = False
    target_accuracy: float | None = Field(default=None, ge=0, le=100)
    target_latency_ms: float | None = Field(default=None, gt=0)
    tags: TagMap | None = Field(default=None, max_length=50)


class LaunchRun(Contract):
    run_id: Identifier
    experiment_id: Identifier
    approach_name: Text
    model_name: Architecture = "custom_cnn"
    dataset_name: DatasetName = "cifar10"
    architecture_config: CustomCNNConfig = Field(default_factory=CustomCNNConfig)
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
    initialize_from_run_id: Identifier | None = None
    tags: TagMap = Field(default_factory=dict, max_length=50)
    motivating_reason: str = Field(default="", max_length=10000)
    queue_policy: Literal["queue", "reject"] = "queue"
    execution_target: Literal["local", "kaggle"] = "local"

    @model_validator(mode="after")
    def motivation(self):
        if self.predecessor_run_id and not self.motivating_reason.strip():
            raise ValueError("A successor run requires a motivating limitation.")
        if self.model_name == "custom_cnn" and self.pretrained:
            raise ValueError("CustomCNN has no pretrained weights.")
        if self.model_name != "custom_cnn" and self.architecture_config != CustomCNNConfig():
            raise ValueError("Architecture controls are currently available for CustomCNN only.")
        return self


class FinalEvaluationRequest(Contract):
    run_id: Identifier


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
    tags: TagMap = Field(default_factory=dict, max_length=50)


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
