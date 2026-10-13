"""Validated graph retrieval filters shared by routing and Neo4j retrieval."""

from __future__ import annotations

from collections.abc import Mapping

GRAPH_PLAN_ENTITY_FIELDS = (
    "procedure_code",
    "procedure_name",
    "agency",
    "legal_basis",
    "field",
)
GRAPH_RELATIONSHIP_TYPES = (
    "HANDLED_BY",
    "AUTHORIZED_BY",
    "COORDINATED_BY",
    "DELEGATED_TO",
    "LEGAL_BASIS",
    "CONTAINS",
)
_MAX_GRAPH_ENTITY_CHARS = 256


def empty_graph_plan() -> dict[str, object]:
    """Return the inert plan used when extraction is unavailable."""
    return {**{field: "" for field in GRAPH_PLAN_ENTITY_FIELDS}, "relationship_types": []}


def normalize_graph_plan(value: object) -> dict[str, object]:
    """Validate a model-produced graph plan before it reaches the graph store."""
    expected = {*GRAPH_PLAN_ENTITY_FIELDS, "relationship_types"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("Invalid graph query plan")

    plan: dict[str, object] = {}
    for field in GRAPH_PLAN_ENTITY_FIELDS:
        entity = value[field]
        if not isinstance(entity, str):
            raise ValueError("Graph query entities must be strings")
        entity = entity.strip()
        if len(entity) > _MAX_GRAPH_ENTITY_CHARS:
            raise ValueError("Graph query entity is too long")
        plan[field] = entity

    relationship_types = value["relationship_types"]
    if not isinstance(relationship_types, list) or len(relationship_types) > len(GRAPH_RELATIONSHIP_TYPES):
        raise ValueError("Invalid graph relationship focus")
    if any(not isinstance(item, str) or item not in GRAPH_RELATIONSHIP_TYPES for item in relationship_types):
        raise ValueError("Invalid graph relationship type")
    if len(relationship_types) != len(set(relationship_types)):
        raise ValueError("Duplicate graph relationship type")
    plan["relationship_types"] = relationship_types
    return plan


def has_graph_entity_filters(plan: Mapping[str, object] | None) -> bool:
    """Whether a plan can narrow procedure candidates beyond token matching."""
    if plan is None:
        return False
    return any(bool(plan.get(field)) for field in GRAPH_PLAN_ENTITY_FIELDS)
