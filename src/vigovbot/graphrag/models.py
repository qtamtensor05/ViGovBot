"""Data contracts shared by GraphRAG orchestration and graph stores."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GraphRelationship:
    """A labeled relation connected to a procedure in the knowledge graph."""

    relationship_type: str
    entity_labels: tuple[str, ...]
    entity_name: str

    def as_public_dict(self) -> dict[str, object]:
        return {
            "relationship_type": self.relationship_type,
            "entity_labels": list(self.entity_labels),
            "entity_name": self.entity_name,
        }


@dataclass(frozen=True)
class GraphProcedure:
    """A procedure and its bounded graph neighbourhood."""

    procedure_code: str
    procedure_name: str
    relationships: tuple[GraphRelationship, ...]

    def as_public_dict(self) -> dict[str, object]:
        return {
            "procedure_code": self.procedure_code,
            "procedure_name": self.procedure_name,
            "relationships": [relationship.as_public_dict() for relationship in self.relationships],
        }


class GraphRetriever(Protocol):
    """Strategy contract for retrieving graph evidence from a rewritten query."""

    def search(
        self,
        query: str,
        plan: dict[str, object] | None = None,
        procedure_codes: list[str] | None = None,
    ) -> list[GraphProcedure]:
        """Return graph facts, prioritising procedure codes recovered by vector retrieval."""

    def close(self) -> None:
        """Release any graph-store resources."""
