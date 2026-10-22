"""Cấu hình riêng cho RAG, không thay đổi cấu hình parse/chunk PDF."""

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataConfig(StrictModel):
    unified_source: Path
    dataset_path: Path | None = None
    dataset_zip: Path | None = None
    cache_dir: Path = Path("outputs/rag_cache")
    output_dir: Path = Path("outputs/rag_results")
    allow_legacy_corpus: bool = False


class EmbeddingConfig(StrictModel):
    model: str = "BAAI/bge-m3"
    revision: str | None = None
    device: str = "cpu"


class LLMConfig(StrictModel):
    measure_ttft: bool = False
    model: str = "qwen2.5:7b"
    ollama_url: str = "http://localhost:11434"
    tokenizer: str = "Qwen/Qwen2.5-7B-Instruct"
    tokenizer_revision: str | None = None
    temperature: float = Field(default=0.0, ge=0)
    num_ctx: int = Field(default=8192, gt=0)
    num_predict: int = Field(default=512, gt=0)
    seed: int = 42
    timeout: int = Field(default=300, gt=0)
    keep_alive: str = "10m"

    @model_validator(mode="after")
    def check_budget(self):
        if self.num_ctx <= self.num_predict + 256:
            raise ValueError("num_ctx phải lớn hơn num_predict + 256")
        return self


class RetrievalConfig(StrictModel):
    top_k: int = Field(default=5, gt=0)
    max_chunk_tokens: int = Field(default=1200, gt=0)


class ConversationConfig(StrictModel):
    decompose_queries: bool = False
    routing_enabled: bool = True
    citations_enabled: bool = False


class WebModelConfig(StrictModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    label: str = Field(min_length=1, max_length=100)
    provider: str = Field(pattern=r"^(ollama|openai_compatible|local_transformers)$")
    model: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    api_key_env: str | None = None
    mode: str = Field(default="rag", pattern=r"^(base|rag|qlora)$")
    adapter_path: Path | None = None
    load_in_4bit: bool = True
    allow_multiple_models: bool = False
    cpu_offload: bool = False
    gpu_memory_gib: float | None = Field(default=None, gt=0)
    cpu_memory_gib: float | None = Field(default=None, gt=0)
    force_single_gpu: bool = False

    @model_validator(mode="after")
    def check_credentials(self):
        if self.api_key_env is not None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env):
            raise ValueError("api_key_env phải là tên biến môi trường hợp lệ")
        if self.mode == "qlora" and self.provider != "local_transformers":
            raise ValueError("mode qlora yêu cầu provider local_transformers")
        if self.mode == "qlora" and self.adapter_path is None:
            raise ValueError("mode qlora yêu cầu adapter_path")
        return self


class WebConfig(StrictModel):
    models: list[WebModelConfig] = Field(default_factory=list)
    debug_routing: bool = False

    @model_validator(mode="after")
    def unique_model_ids(self):
        ids = [item.id for item in self.models]
        if len(ids) != len(set(ids)):
            raise ValueError("web.models không được trùng id")
        return self


class EvaluationConfig(StrictModel):
    smoke_test_n: int = Field(default=5, ge=0)
    max_cases: int | None = Field(default=None, gt=0)
    bertscore_model: str = "xlm-roberta-large"
    bertscore_device: str = "cpu"
    bertscore_batch_size: int = Field(default=1, gt=0)
    baseline_summary_path: Path | None = None


class RAGConfig(StrictModel):
    data: DataConfig
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)

    def inference_settings(self):
        settings = self.llm.model_dump(exclude={"tokenizer", "tokenizer_revision"})
        settings.update(self.retrieval.model_dump())
        settings.update(self.conversation.model_dump())
        return settings


def load_config(path):
    path = Path(path).resolve()
    config = RAGConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8-sig")))
    for key in ("unified_source", "dataset_path", "dataset_zip", "cache_dir", "output_dir"):
        value = getattr(config.data, key)
        if value is not None:
            setattr(config.data, key, (path.parent / value).resolve())
    if config.evaluation.baseline_summary_path is not None:
        config.evaluation.baseline_summary_path = (path.parent / config.evaluation.baseline_summary_path).resolve()
    for model in config.web.models:
        if model.adapter_path is not None:
            override = os.environ.get("QLORA_ADAPTER_PATH") if model.provider == "local_transformers" else None
            if override:
                model.adapter_path = Path(override).expanduser().resolve()
            else:
                model.adapter_path = (path.parent / model.adapter_path).resolve()
    return config
