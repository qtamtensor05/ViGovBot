"""Neo4j implementation of the GraphRAG retrieval strategy."""

from __future__ import annotations

import os
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Mapping, Sequence

from vigovbot.graphrag.models import GraphProcedure, GraphRelationship
from vigovbot.graphrag.query_plan import GRAPH_PLAN_ENTITY_FIELDS, has_graph_entity_filters, normalize_graph_plan

_QUERY_TOKEN = re.compile(r"\d+(?:\.\d+)+|[\wÀ-ỹ]+", re.UNICODE)
_STOP_WORDS = frozenset(
    {
        "bao",
        "các",
        "cần",
        "cho",
        "có",
        "của",
        "để",
        "đến",
        "đối",
        "gì",
        "giấy",
        "hay",
        "hồ",
        "là",
        "làm",
        "mình",
        "nào",
        "người",
        "như",
        "ở",
        "phải",
        "quy",
        "thế",
        "thông",
        "thủ",
        "tôi",
        "tra",
        "trong",
        "tục",
        "và",
        "về",
        "với",
        "vui",
        "xin",
        "được",
    }
)

_PROCEDURE_QUERY = """
MATCH (procedure:Procedure)
WITH procedure, size([term IN $terms WHERE
    toLower(coalesce(procedure.procedure_name, '')) CONTAINS term
    OR toLower(coalesce(procedure.procedure_code, '')) = term
]) AS match_count
WHERE match_count > 0
ORDER BY match_count DESC, procedure.procedure_name
LIMIT $max_procedures
CALL (procedure) {
    OPTIONAL MATCH (procedure)-[relationship]->(entity)
    WITH relationship, entity
    ORDER BY type(relationship), coalesce(entity.canonical_name, entity.name, entity.procedure_name, entity.procedure_code)
    RETURN collect({
        relationship_type: type(relationship),
        entity_labels: labels(entity),
        entity_name: coalesce(entity.canonical_name, entity.name, entity.procedure_name, entity.procedure_code, '')
    })[..$max_relationships] AS relationships
}
RETURN procedure.procedure_code AS procedure_code,
       procedure.procedure_name AS procedure_name,
       relationships
ORDER BY match_count DESC, procedure_name
"""

_PLANNED_PROCEDURE_QUERY = """
MATCH (procedure:Procedure)
WHERE ($procedure_code = '' OR toLower(coalesce(procedure.procedure_code, '')) = $procedure_code)
  AND ($procedure_name = '' OR toLower(coalesce(procedure.procedure_name, '')) CONTAINS $procedure_name)
  AND ($agency = '' OR EXISTS {
      MATCH (procedure)-[]-(agency:Agency)
      WHERE toLower(coalesce(agency.canonical_name, agency.name, '')) CONTAINS $agency
  })
  AND ($legal_basis = '' OR EXISTS {
      MATCH (procedure)-[]-(legal_basis:LegalDocument)
      WHERE toLower(coalesce(legal_basis.canonical_name, legal_basis.name, '')) CONTAINS $legal_basis
  })
  AND ($field = '' OR EXISTS {
      MATCH (procedure)-[]-(field_node:Field)
      WHERE toLower(coalesce(field_node.canonical_name, field_node.name, '')) CONTAINS $field
  })
WITH procedure, size([term IN $terms WHERE
    toLower(coalesce(procedure.procedure_name, '')) CONTAINS term
    OR toLower(coalesce(procedure.procedure_code, '')) = term
]) AS match_count
ORDER BY match_count DESC, procedure.procedure_name
LIMIT $max_procedures
CALL (procedure) {
    OPTIONAL MATCH (procedure)-[relationship]->(entity)
    WITH relationship, entity,
         CASE WHEN size($relationship_types) = 0 OR type(relationship) IN $relationship_types
              THEN 0 ELSE 1 END AS focus_rank
    ORDER BY focus_rank, type(relationship),
             coalesce(entity.canonical_name, entity.name, entity.procedure_name, entity.procedure_code)
    RETURN collect({
        relationship_type: type(relationship),
        entity_labels: labels(entity),
        entity_name: coalesce(entity.canonical_name, entity.name, entity.procedure_name, entity.procedure_code, '')
    })[..$max_relationships] AS relationships
}
RETURN procedure.procedure_code AS procedure_code,
       procedure.procedure_name AS procedure_name,
       relationships
ORDER BY match_count DESC, procedure_name
"""

_CODED_PROCEDURE_QUERY = """
MATCH (procedure:Procedure)
WHERE procedure.procedure_code IN $procedure_codes
  AND ($procedure_code = '' OR toLower(coalesce(procedure.procedure_code, '')) = $procedure_code)
  AND ($procedure_name = '' OR toLower(coalesce(procedure.procedure_name, '')) CONTAINS $procedure_name)
  AND ($agency = '' OR EXISTS {
      MATCH (procedure)-[]-(agency:Agency)
      WHERE toLower(coalesce(agency.canonical_name, agency.name, '')) CONTAINS $agency
  })
  AND ($legal_basis = '' OR EXISTS {
      MATCH (procedure)-[]-(legal_basis:LegalDocument)
      WHERE toLower(coalesce(legal_basis.canonical_name, legal_basis.name, '')) CONTAINS $legal_basis
  })
  AND ($field = '' OR EXISTS {
      MATCH (procedure)-[]-(field_node:Field)
      WHERE toLower(coalesce(field_node.canonical_name, field_node.name, '')) CONTAINS $field
  })
WITH procedure,
     size([term IN $terms WHERE
        toLower(coalesce(procedure.procedure_name, '')) CONTAINS term
        OR toLower(coalesce(procedure.procedure_code, '')) = term
     ]) AS match_count
ORDER BY match_count DESC, procedure.procedure_name
LIMIT $max_procedures
CALL (procedure) {
    OPTIONAL MATCH (procedure)-[relationship]->(entity)
    WITH relationship, entity,
         CASE WHEN size($relationship_types) = 0 OR type(relationship) IN $relationship_types
              THEN 0 ELSE 1 END AS focus_rank
    ORDER BY focus_rank, type(relationship),
             coalesce(entity.canonical_name, entity.name, entity.procedure_name, entity.procedure_code)
    RETURN collect({
        relationship_type: type(relationship),
        entity_labels: labels(entity),
        entity_name: coalesce(entity.canonical_name, entity.name, entity.procedure_name, entity.procedure_code, '')
    })[..$max_relationships] AS relationships
}
RETURN procedure.procedure_code AS procedure_code,
       procedure.procedure_name AS procedure_name,
       relationships,
       match_count
ORDER BY match_count DESC, procedure_name
"""

_FULLTEXT_PROCEDURE_QUERY = """
CALL db.index.fulltext.queryNodes($fulltext_index, $fulltext_query) YIELD node AS procedure, score
WHERE procedure:Procedure
  AND ($procedure_code = '' OR toLower(coalesce(procedure.procedure_code, '')) = $procedure_code)
  AND ($procedure_name = '' OR toLower(coalesce(procedure.procedure_name, '')) CONTAINS $procedure_name)
  AND ($agency = '' OR EXISTS {
      MATCH (procedure)-[]-(agency:Agency)
      WHERE toLower(coalesce(agency.canonical_name, agency.name, '')) CONTAINS $agency
  })
  AND ($legal_basis = '' OR EXISTS {
      MATCH (procedure)-[]-(legal_basis:LegalDocument)
      WHERE toLower(coalesce(legal_basis.canonical_name, legal_basis.name, '')) CONTAINS $legal_basis
  })
  AND ($field = '' OR EXISTS {
      MATCH (procedure)-[]-(field_node:Field)
      WHERE toLower(coalesce(field_node.canonical_name, field_node.name, '')) CONTAINS $field
  })
WITH procedure, score
ORDER BY score DESC, procedure.procedure_name
LIMIT $max_procedures
CALL (procedure) {
    OPTIONAL MATCH (procedure)-[relationship]->(entity)
    WITH relationship, entity,
         CASE WHEN size($relationship_types) = 0 OR type(relationship) IN $relationship_types
              THEN 0 ELSE 1 END AS focus_rank
    ORDER BY focus_rank, type(relationship),
             coalesce(entity.canonical_name, entity.name, entity.procedure_name, entity.procedure_code)
    RETURN collect({
        relationship_type: type(relationship),
        entity_labels: labels(entity),
        entity_name: coalesce(entity.canonical_name, entity.name, entity.procedure_name, entity.procedure_code, '')
    })[..$max_relationships] AS relationships
}
RETURN procedure.procedure_code AS procedure_code,
       procedure.procedure_name AS procedure_name,
       relationships,
       score
ORDER BY score DESC, procedure_name
"""

_PROCEDURE_CODE_INDEX = "vigovbot_procedure_code"
_PROCEDURE_FULLTEXT_INDEX = "vigovbot_procedure_text"
_INDEX_STATEMENTS = (
    f"CREATE RANGE INDEX {_PROCEDURE_CODE_INDEX} IF NOT EXISTS FOR (procedure:Procedure) ON (procedure.procedure_code)",
    f"CREATE FULLTEXT INDEX {_PROCEDURE_FULLTEXT_INDEX} IF NOT EXISTS "
    "FOR (procedure:Procedure) ON EACH [procedure.procedure_name, procedure.procedure_code]",
)


def query_terms(query: str) -> list[str]:
    """Extract stable, non-trivial terms without sending raw user text to Cypher."""
    terms: list[str] = []
    for token in _QUERY_TOKEN.findall(query.lower()):
        if (len(token) < 3 and not token[0].isdigit()) or token in _STOP_WORDS or token in terms:
            continue
        terms.append(token)
    return terms[:12]


def normalize_procedure_codes(values: Sequence[object] | None, max_procedures: int) -> list[str]:
    """Keep stable vector metadata codes for an equality-filtered graph lookup."""
    if values is None:
        return []
    codes: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        code = value.strip()
        if code and len(code) <= 128 and code not in codes:
            codes.append(code)
        if len(codes) >= max_procedures:
            break
    return codes


def format_graph_context(procedures: list[GraphProcedure], max_chars: int) -> str:
    """Format bounded graph facts as inert prompt context, not executable instructions."""
    lines: list[str] = []
    for procedure in procedures:
        lines.append(f"[Thủ tục | {procedure.procedure_code}] {procedure.procedure_name}")
        for relationship in procedure.relationships:
            labels = "/".join(relationship.entity_labels) or "Thực thể"
            lines.append(f"- {relationship.relationship_type}: ({labels}) {relationship.entity_name}")
    return "\n".join(lines)[:max_chars].rstrip()


class Neo4jGraphRetriever:
    """Retrieve procedure-centred graph context from the confirmed Neo4j schema."""

    def __init__(self, config, *, driver=None):
        self.config = config
        self._driver = driver
        self._lock = threading.Lock()
        self._cache: OrderedDict[tuple[object, ...], tuple[float, tuple[GraphProcedure, ...]]] = OrderedDict()

    def _driver_or_connect(self):
        with self._lock:
            if self._driver is not None:
                return self._driver
            password = os.environ.get(self.config.password_env)
            if not password:
                raise RuntimeError(f"Chưa đặt biến môi trường {self.config.password_env} cho GraphRAG")
            try:
                from neo4j import GraphDatabase
            except ImportError as exc:
                raise RuntimeError("GraphRAG cần cài extra 'rag' chứa Neo4j driver") from exc
            self._driver = GraphDatabase.driver(self.config.uri, auth=(self.config.username, password))
            return self._driver

    def _cache_key(self, terms, plan, procedure_codes):
        return (
            tuple(terms),
            tuple(procedure_codes),
            tuple((field, plan[field]) for field in GRAPH_PLAN_ENTITY_FIELDS),
            tuple(plan["relationship_types"]),
        )

    def _get_cached(self, key):
        ttl = getattr(self.config, "cache_ttl_s", 0)
        if ttl <= 0:
            return None
        with self._lock:
            cached = self._cache.get(key)
            if cached is None:
                return None
            stored_at, procedures = cached
            if time.monotonic() - stored_at > ttl:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return list(procedures)

    def _remember(self, key, procedures):
        ttl = getattr(self.config, "cache_ttl_s", 0)
        limit = getattr(self.config, "cache_max_entries", 0)
        if ttl <= 0 or limit <= 0:
            return
        with self._lock:
            self._cache[key] = (time.monotonic(), tuple(procedures))
            self._cache.move_to_end(key)
            while len(self._cache) > limit:
                self._cache.popitem(last=False)

    @staticmethod
    def _fulltext_query(terms: Sequence[str]) -> str:
        return " OR ".join(f'"{term}"' for term in terms)

    @staticmethod
    def _missing_fulltext_index(exc: Exception) -> bool:
        return getattr(exc, "code", "") == "Neo.ClientError.Schema.IndexNotFound"

    def _run(self, cypher, parameters):
        driver = self._driver_or_connect()
        with driver.session(database=self.config.database) as session:
            records = session.run(cypher, **parameters, timeout=getattr(self.config, "query_timeout_s", 5.0))
            return [self._to_procedure(record) for record in records]

    def search(
        self,
        query: str,
        plan: Mapping[str, object] | None = None,
        procedure_codes: Sequence[object] | None = None,
    ) -> list[GraphProcedure]:
        terms = query_terms(query)
        try:
            normalized_plan = normalize_graph_plan(plan) if plan is not None else None
        except ValueError:
            normalized_plan = None
        use_plan = has_graph_entity_filters(normalized_plan)
        normalized_plan = normalized_plan if use_plan else None
        codes = normalize_procedure_codes(procedure_codes, self.config.max_procedures)
        if not terms and not normalized_plan and not codes:
            return []
        cache_plan = normalized_plan or {field: "" for field in GRAPH_PLAN_ENTITY_FIELDS} | {"relationship_types": []}
        cache_key = self._cache_key(terms, cache_plan, codes)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        parameters = {
            "terms": terms,
            "max_procedures": self.config.max_procedures,
            "max_relationships": self.config.max_relationships,
            "procedure_code": "",
            "procedure_name": "",
            "agency": "",
            "legal_basis": "",
            "field": "",
            "relationship_types": [],
        }
        if normalized_plan is not None:
            parameters.update({field: str(normalized_plan[field]).lower() for field in GRAPH_PLAN_ENTITY_FIELDS})
            parameters["relationship_types"] = normalized_plan["relationship_types"]
        if codes:
            procedures = self._run(_CODED_PROCEDURE_QUERY, {**parameters, "procedure_codes": codes})
            if not procedures and normalized_plan is not None:
                fallback_parameters = {
                    **parameters,
                    **{field: "" for field in GRAPH_PLAN_ENTITY_FIELDS},
                    "procedure_codes": codes,
                }
                procedures = self._run(_CODED_PROCEDURE_QUERY, fallback_parameters)
            source_rank = {code: position for position, code in enumerate(codes)}
            procedures.sort(
                key=lambda procedure: (
                    source_rank.get(procedure.procedure_code, len(source_rank)),
                    procedure.procedure_name,
                )
            )
        elif terms:
            try:
                procedures = self._run(
                    _FULLTEXT_PROCEDURE_QUERY,
                    {
                        **parameters,
                        "fulltext_index": _PROCEDURE_FULLTEXT_INDEX,
                        "fulltext_query": self._fulltext_query(terms),
                    },
                )
            except Exception as exc:
                if not self._missing_fulltext_index(exc):
                    raise
                cypher = _PLANNED_PROCEDURE_QUERY if normalized_plan is not None else _PROCEDURE_QUERY
                procedures = self._run(cypher, parameters)
        else:
            procedures = self._run(_PLANNED_PROCEDURE_QUERY, parameters)
        self._remember(cache_key, procedures)
        return procedures

    def provision_indexes(self) -> list[str]:
        """Create the optional indexes used by graph retrieval without changing graph facts."""
        driver = self._driver_or_connect()
        created = []
        with driver.session(database=self.config.database) as session:
            for statement in _INDEX_STATEMENTS:
                result = session.run(statement, timeout=getattr(self.config, "query_timeout_s", 5.0))
                consume = getattr(result, "consume", None)
                if consume is not None:
                    consume()
                created.append(statement.split(" IF NOT EXISTS", 1)[0])
        return created

    @staticmethod
    def _to_procedure(record: Mapping[str, object]) -> GraphProcedure:
        relationships = []
        for item in record.get("relationships", []):
            if not isinstance(item, Mapping) or not item.get("relationship_type"):
                continue
            relationships.append(
                GraphRelationship(
                    relationship_type=str(item["relationship_type"]),
                    entity_labels=tuple(str(label) for label in item.get("entity_labels", [])),
                    entity_name=str(item.get("entity_name", "")),
                )
            )
        return GraphProcedure(
            procedure_code=str(record.get("procedure_code", "")),
            procedure_name=str(record.get("procedure_name", "")),
            relationships=tuple(relationships),
        )

    def close(self) -> None:
        with self._lock:
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            self._cache.clear()
