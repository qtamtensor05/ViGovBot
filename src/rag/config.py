"""Cấu hình riêng cho RAG, không thay đổi cấu hình parse/chunk PDF."""
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

    @model_validator(mode="after")
    def check_dataset(self):
        if self.dataset_path is None and self.dataset_zip is None:
            raise ValueError("Cần dataset_path hoặc dataset_zip")
        return self


class EmbeddingConfig(StrictModel):
    model: str = "BAAI/bge-m3"
    revision: str | None = None
    device: str = "cpu"


class LLMConfig(StrictModel):
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
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)

    def inference_settings(self):
        settings = self.llm.model_dump(exclude={"tokenizer", "tokenizer_revision"})
        settings.update(self.retrieval.model_dump())
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
    return config
