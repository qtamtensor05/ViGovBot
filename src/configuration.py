"""Validated YAML configuration. No global cache: edits apply on the next run."""
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SettingsModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class OCRSettings(SettingsModel):
    enabled: bool = True
    language: str = Field(default='vie+eng', min_length=1)
    dpi: int = Field(default=300, ge=72, le=600)
    full: bool = True
    tessdata: str | None = None


class IngestionSettings(SettingsModel):
    max_pdf_size_mb: float = Field(default=20, gt=0, le=100)
    reports_dir: str = 'reports'
    review_dir: str = 'review'
    recover_metadata: bool = True
    ocr: OCRSettings = Field(default_factory=OCRSettings)

    @model_validator(mode='after')
    def validate_directories(self):
        for value in (self.reports_dir, self.review_dir):
            if not value or value in ('.', '..') or any(c in value for c in '/\\:'):
                raise ValueError('reports_dir/review_dir must be single directory names')
        if self.reports_dir == self.review_dir:
            raise ValueError('reports_dir and review_dir must differ')
        return self


class ChunkingSettings(SettingsModel):
    target_chars: int = Field(default=1200, ge=100)
    max_chars: int = Field(default=1500, ge=100)
    overlap_chars: int = Field(default=100, ge=0)
    min_content_chars: int = Field(default=10, ge=0)
    section_keywords: dict[Literal['metadata_identity', 'procedure_step', 'required_documents', 'submission_deadline_fee', 'legal_basis', 'other'], list[str]]

    @model_validator(mode='after')
    def validate_sizes(self):
        if not self.overlap_chars < self.target_chars <= self.max_chars:
            raise ValueError('Require overlap_chars < target_chars <= max_chars')
        return self


class ModulePaths(SettingsModel):
    ingestion: str
    chunking: str


class ColabSettings(SettingsModel):
    use_google_drive: bool = False
    drive_input: str = '/content/drive/MyDrive/ViGovBot/Data'
    output: str = '/content/ViGovBot_outputs'


class PipelineSettings(SettingsModel):
    input: Path
    output: Path
    overwrite: bool = False
    modules: ModulePaths
    colab: ColabSettings = Field(default_factory=ColabSettings)


def read_yaml(path: Path) -> dict:
    """Read a mapping, reporting its path if loading fails."""
    try:
        value = yaml.safe_load(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('Expected a YAML mapping')
        return value
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise ValueError(f'Invalid configuration {path}: {error}') from error


def load_configuration(path: str | Path | None = None):
    """Return pipeline, ingestion and chunking settings; resolve relative paths."""
    path = Path(path).resolve() if path else PROJECT_ROOT / 'config.yaml'
    root = PipelineSettings(**read_yaml(path))
    for field in ('input', 'output'):
        value = getattr(root, field)
        setattr(root, field, value if value.is_absolute() else (path.parent / value).resolve())
    ingestion_path = (path.parent / root.modules.ingestion).resolve()
    chunking_path = (path.parent / root.modules.chunking).resolve()
    ingestion = IngestionSettings(**read_yaml(ingestion_path))
    if ingestion.ocr.tessdata:
        ingestion.ocr.tessdata = str((ingestion_path.parent / ingestion.ocr.tessdata).resolve())
    return root, ingestion, ChunkingSettings(**read_yaml(chunking_path))
