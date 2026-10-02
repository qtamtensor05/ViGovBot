"""Shared data contracts, independent of pipeline orchestration."""

DIMENSION = 1024
MODEL_NAME = "BAAI/bge-m3"
ARTIFACT_VERSION = 1
CACHE_VERSION = 1
FIELDS = (
    "chunk_id",
    "source_file",
    "source_code",
    "procedure_name",
    "section_type",
    "context_prefix",
    "text_content",
    "parent_section",
)


def validate_records(records: object, source: object, seen: set[str]) -> list[dict]:
    if not isinstance(records, list) or not records:
        raise ValueError(f"{source}: expected a nonempty JSON array of chunks")
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"{source}[{i}]: expected an object")
        for field in FIELDS:
            if not isinstance(record.get(field), str):
                raise ValueError(f"{source}[{i}]: {field} must be a string")
        chunk_id = record["chunk_id"]
        if not chunk_id.strip() or not record["text_content"].strip():
            raise ValueError(f"{source}[{i}]: empty chunk_id or text_content")
        if chunk_id in seen:
            raise ValueError(f"{source}: duplicate chunk_id {chunk_id!r}")
        seen.add(chunk_id)
    return records
