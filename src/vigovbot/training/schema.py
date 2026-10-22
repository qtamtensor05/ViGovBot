"""Typed training configuration used from file loading through runtime."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ModelSettings(StrictModel):
    name: str = Field(min_length=1)
    trust_remote_code: Literal[False]
    max_seq_length: int = Field(gt=0)
    experimental: bool = False

    @model_validator(mode="after")
    def model_policy(self):
        if self.name != "Qwen/Qwen2.5-7B-Instruct" and not self.experimental:
            raise ValueError("Other models require model.experimental=true; compatibility is not verified")
        return self


class Splits(StrictModel):
    train: str = Field(min_length=1)
    validation: str = Field(min_length=1)
    test: str | None = Field(default=None, min_length=1)


class DataSettings(StrictModel):
    splits: Splits
    output_dir: str = Field(min_length=1)
    near_duplicate_threshold: float = Field(ge=0, le=1)


class QuantizationSettings(StrictModel):
    load_in_4bit: Literal[True]
    bnb_4bit_quant_type: Literal["nf4"]
    bnb_4bit_use_double_quant: Literal[True]
    bnb_4bit_compute_dtype: Literal["bfloat16", "float16"]


class LoraSettings(StrictModel):
    r: int = Field(gt=0)
    alpha: int = Field(gt=0)
    dropout: float = Field(ge=0, lt=1)
    bias: Literal["none"]
    target_modules: list[str] = Field(min_length=1)


class TrainerSettings(StrictModel):
    num_train_epochs: float = Field(gt=0)
    per_device_train_batch_size: int = Field(gt=0)
    per_device_eval_batch_size: int = Field(gt=0)
    gradient_accumulation_steps: int = Field(gt=0)
    learning_rate: float = Field(gt=0)
    weight_decay: float = Field(ge=0)
    lr_scheduler_type: str = Field(min_length=1)
    warmup_ratio: float = Field(ge=0, le=1)
    max_grad_norm: float = Field(gt=0)
    gradient_checkpointing: bool
    dataloader_num_workers: int = Field(default=0, ge=0)
    dataloader_pin_memory: bool = True
    dataloader_persistent_workers: bool = False
    optim: Literal["paged_adamw_8bit"]
    seed: int
    logging_steps: int = Field(gt=0)
    eval_strategy: Literal["steps"]
    eval_steps: int = Field(gt=0)
    save_strategy: Literal["steps"]
    save_steps: int = Field(gt=0)
    save_total_limit: int = Field(gt=0)
    load_best_model_at_end: bool
    metric_for_best_model: str = Field(min_length=1)
    greater_is_better: bool


class EarlyStoppingSettings(StrictModel):
    enabled: bool
    patience: int = Field(gt=0)
    threshold: float = Field(ge=0)


class ReportingSettings(StrictModel):
    tensorboard: bool
    save_csv: bool
    save_json: bool
    generate_plots: bool


class ExecutionSettings(StrictModel):
    approved: bool = False
    max_samples: int | None = Field(default=None, gt=0)
    max_steps: int = Field(default=-1, ge=-1)
    artifact_label: str | None = None

    @model_validator(mode="after")
    def steps_nonzero(self):
        if self.max_steps == 0:
            raise ValueError("max_steps must be -1 or positive")
        return self


class GenerationSettings(StrictModel):
    max_new_tokens: int = Field(gt=0)
    temperature: float = Field(ge=0)


class EvaluationSettings(StrictModel):
    generation: GenerationSettings


class TrainingConfig(StrictModel):
    _config_path: str = PrivateAttr(default="")
    _project_root: str = PrivateAttr(default="")

    @property
    def config_path(self) -> str:
        return self._config_path

    @property
    def project_root(self) -> str:
        return self._project_root

    def snapshot(self) -> dict:
        """Preserve supplied keys; defaults must not change historical resume snapshots."""
        return self.model_dump(exclude_unset=True)

    model: ModelSettings
    data: DataSettings
    quantization: QuantizationSettings
    lora: LoraSettings
    training: TrainerSettings
    early_stopping: EarlyStoppingSettings
    reporting: ReportingSettings
    execution: ExecutionSettings | None = None
    evaluation: EvaluationSettings | None = None

    @model_validator(mode="after")
    def compatible_settings(self):
        targets = self.lora.target_modules
        if any(not target.strip() for target in targets) or len(targets) != len(set(targets)):
            raise ValueError("lora.target_modules must be non-empty and unique")
        expected = {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"}
        if self.model.name == "Qwen/Qwen2.5-7B-Instruct" and set(targets) != expected:
            raise ValueError("Qwen2.5 LoRA target_modules must equal the audited projection set")
        if self.training.eval_steps != self.training.save_steps:
            raise ValueError("Evaluation and checkpoint cadence must align")
        if self.early_stopping.enabled and not self.training.load_best_model_at_end:
            raise ValueError("Early stopping requires load_best_model_at_end=true")
        if self.training.dataloader_persistent_workers and self.training.dataloader_num_workers == 0:
            raise ValueError("Persistent dataloader workers require dataloader_num_workers > 0")
        return self
