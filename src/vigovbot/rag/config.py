"""Cấu hình riêng cho RAG, không thay đổi cấu hình parse/chunk PDF."""

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    routing_enabled: bool = True
    citations_enabled: bool = False
    routing_num_predict: int = Field(default=160, gt=0, le=512)


class GraphRAGConfig(StrictModel):
    enabled: bool = False
    uri: str = "bolt://127.0.0.1:7687"
    database: str = "neo4j"
    username: str = "neo4j"
    password_env: str = "NEO4J_PASSWORD"
    max_procedures: int = Field(default=3, ge=1, le=10)
    max_relationships: int = Field(default=6, ge=1, le=20)
    max_context_chars: int = Field(default=2400, ge=200, le=12000)
    query_timeout_s: float = Field(default=5.0, gt=0, le=60)
    wait_timeout_s: float = Field(default=6.0, gt=0, le=65)
    cache_ttl_s: int = Field(default=120, ge=0, le=3600)
    cache_max_entries: int = Field(default=128, ge=0, le=1000)

    @model_validator(mode="after")
    def check_timeouts(self):
        if self.wait_timeout_s < self.query_timeout_s:
            raise ValueError("graph.wait_timeout_s phải lớn hơn hoặc bằng graph.query_timeout_s")
        return self

    @field_validator("uri")
    @classmethod
    def check_uri(cls, value):
        if not re.fullmatch(r"(?:bolt|neo4j)(?:\+(?:s|ssc))?://[^\s/]+", value):
            raise ValueError("graph.uri phải là URI Bolt/Neo4j hợp lệ")
        return value

    @field_validator("password_env")
    @classmethod
    def check_password_env(cls, value):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError("graph.password_env phải là tên biến môi trường hợp lệ")
        return value


class WebModelConfig(StrictModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    label: str = Field(min_length=1, max_length=100)
    provider: str = Field(pattern=r"^(ollama|openai_compatible)$")
    model: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    api_key_env: str | None = None
    mode: str = Field(default="rag", pattern=r"^(base|rag|graphrag)$")

    @model_validator(mode="after")
    def check_credentials(self):
        if self.api_key_env is not None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env):
            raise ValueError("api_key_env phải là tên biến môi trường hợp lệ")
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
    graph: GraphRAGConfig = Field(default_factory=GraphRAGConfig)
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
    return config
