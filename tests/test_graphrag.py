import unittest
from types import SimpleNamespace

from vigovbot.graphrag import Neo4jGraphRetriever, empty_graph_plan, format_graph_context
from vigovbot.graphrag.retriever import normalize_procedure_codes, query_terms


class GraphRAGTests(unittest.TestCase):
    def test_query_terms_keep_meaningful_vietnamese_and_procedure_codes(self):
        terms = query_terms("Thủ tục hải quan 1.000005 cần giấy tờ gì?")
        self.assertEqual(terms, ["hải", "quan", "1.000005"])

    def test_normalize_procedure_codes_preserves_vector_rank_and_deduplicates(self):
        codes = normalize_procedure_codes([" 1.000005 ", "1.000005", 4, "1.000014", ""], 3)
        self.assertEqual(codes, ["1.000005", "1.000014"])

    def test_search_maps_bounded_procedure_neighbourhood(self):
        calls = {}

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def run(self, cypher, **parameters):
                calls["cypher"] = cypher
                calls["parameters"] = parameters
                return [
                    {
                        "procedure_code": "1.000005",
                        "procedure_name": "Thủ tục hải quan",
                        "relationships": [
                            {"relationship_type": "HANDLED_BY", "entity_labels": ["Agency"], "entity_name": "Chi cục"},
                            {
                                "relationship_type": "LEGAL_BASIS",
                                "entity_labels": ["LegalDocument"],
                                "entity_name": "Luật",
                            },
                        ],
                    }
                ]

        class Driver:
            def session(self, **kwargs):
                calls["session"] = kwargs
                return Session()

            def close(self):
                calls["closed"] = True

        config = SimpleNamespace(
            database="neo4j",
            max_procedures=3,
            max_relationships=6,
            max_context_chars=2400,
            password_env="NEO4J_PASSWORD",
            uri="bolt://127.0.0.1:7687",
            username="neo4j",
        )
        retriever = Neo4jGraphRetriever(config, driver=Driver())
        procedures = retriever.search("Thủ tục hải quan")
        self.assertEqual(calls["session"], {"database": "neo4j"})
        self.assertIn("db.index.fulltext.queryNodes", calls["cypher"])
        self.assertEqual(calls["parameters"]["terms"], ["hải", "quan"])
        self.assertEqual(calls["parameters"]["fulltext_query"], '"hải" OR "quan"')
        self.assertEqual(calls["parameters"]["timeout"], 5.0)
        self.assertEqual(procedures[0].relationships[0].entity_name, "Chi cục")
        context = format_graph_context(procedures, 2400)
        self.assertIn("[Thủ tục | 1.000005]", context)
        self.assertIn("HANDLED_BY: (Agency) Chi cục", context)
        retriever.close()
        self.assertTrue(calls["closed"])

    def test_search_uses_validated_entity_plan_and_prioritizes_requested_relationships(self):
        calls = {}

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def run(self, cypher, **parameters):
                calls["cypher"] = cypher
                calls["parameters"] = parameters
                return []

        class Driver:
            def session(self, **kwargs):
                return Session()

        config = SimpleNamespace(
            database="neo4j",
            max_procedures=3,
            max_relationships=6,
            password_env="NEO4J_PASSWORD",
            uri="bolt://127.0.0.1:7687",
            username="neo4j",
        )
        plan = {
            "procedure_code": "1.000005",
            "procedure_name": "Cấp hộ chiếu",
            "agency": "Bộ Công an",
            "legal_basis": "Luật Xuất cảnh",
            "field": "Hộ tịch",
            "relationship_types": ["HANDLED_BY", "LEGAL_BASIS"],
        }
        retriever = Neo4jGraphRetriever(config, driver=Driver())
        retriever.search("Cơ quan nào cấp hộ chiếu?", plan)

        self.assertIn("agency:Agency", calls["cypher"])
        self.assertIn("legal_basis:LegalDocument", calls["cypher"])
        self.assertIn("field_node:Field", calls["cypher"])
        self.assertEqual(calls["parameters"]["procedure_code"], "1.000005")
        self.assertEqual(calls["parameters"]["procedure_name"], "cấp hộ chiếu")
        self.assertEqual(calls["parameters"]["relationship_types"], ["HANDLED_BY", "LEGAL_BASIS"])
        self.assertNotIn("Cơ quan nào cấp hộ chiếu?", calls["cypher"])

    def test_search_uses_fulltext_when_plan_is_invalid_or_empty(self):
        calls = {}

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def run(self, cypher, **parameters):
                calls["cypher"] = cypher
                calls["parameters"] = parameters
                return []

        class Driver:
            def session(self, **kwargs):
                return Session()

        config = SimpleNamespace(
            database="neo4j",
            max_procedures=3,
            max_relationships=6,
            password_env="NEO4J_PASSWORD",
            uri="bolt://127.0.0.1:7687",
            username="neo4j",
        )
        retriever = Neo4jGraphRetriever(config, driver=Driver())
        retriever.search("Thủ tục hải quan", {**empty_graph_plan(), "agency": []})

        self.assertIn("db.index.fulltext.queryNodes", calls["cypher"])
        self.assertEqual(calls["parameters"]["terms"], ["hải", "quan"])
        self.assertEqual(calls["parameters"]["agency"], "")

    def test_search_uses_vector_procedure_codes_before_fulltext(self):
        calls = {}

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def run(self, cypher, **parameters):
                calls["cypher"] = cypher
                calls["parameters"] = parameters
                return []

        class Driver:
            def session(self, **kwargs):
                return Session()

        config = SimpleNamespace(
            database="neo4j",
            max_procedures=3,
            max_relationships=6,
            password_env="NEO4J_PASSWORD",
            uri="bolt://127.0.0.1:7687",
            username="neo4j",
        )
        retriever = Neo4jGraphRetriever(config, driver=Driver())
        retriever.search("Các bước thực hiện?", procedure_codes=["1.000005", "1.000014"])

        self.assertIn("procedure.procedure_code IN $procedure_codes", calls["cypher"])
        self.assertNotIn("db.index.fulltext.queryNodes", calls["cypher"])
        self.assertEqual(calls["parameters"]["procedure_codes"], ["1.000005", "1.000014"])

    def test_vector_codes_fall_back_when_entity_plan_overfilters(self):
        calls = []

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def run(self, cypher, **parameters):
                calls.append(parameters)
                if parameters["field"]:
                    return []
                return [{"procedure_code": "1.000005", "procedure_name": "Thủ tục", "relationships": []}]

        class Driver:
            def session(self, **kwargs):
                return Session()

        config = SimpleNamespace(
            database="neo4j",
            max_procedures=3,
            max_relationships=6,
            password_env="NEO4J_PASSWORD",
            uri="bolt://127.0.0.1:7687",
            username="neo4j",
        )
        plan = {**empty_graph_plan(), "field": "xuất khẩu khí qua đường ống"}
        result = Neo4jGraphRetriever(config, driver=Driver()).search(
            "Quy trình xuất khẩu khí qua đường ống", plan, ["1.000005"]
        )

        self.assertEqual([item.procedure_code for item in result], ["1.000005"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["field"], "xuất khẩu khí qua đường ống")
        self.assertEqual(calls[1]["field"], "")

    def test_search_caches_immutable_graph_results(self):
        calls = {"run": 0}

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def run(self, cypher, **parameters):
                calls["run"] += 1
                return [{"procedure_code": "1.000005", "procedure_name": "Thủ tục", "relationships": []}]

        class Driver:
            def session(self, **kwargs):
                return Session()

        config = SimpleNamespace(
            database="neo4j",
            max_procedures=3,
            max_relationships=6,
            password_env="NEO4J_PASSWORD",
            uri="bolt://127.0.0.1:7687",
            username="neo4j",
            cache_ttl_s=60,
            cache_max_entries=2,
        )
        retriever = Neo4jGraphRetriever(config, driver=Driver())

        first = retriever.search("Thủ tục hải quan")
        second = retriever.search("Thủ tục hải quan")

        self.assertEqual(calls["run"], 1)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)

    def test_search_falls_back_when_fulltext_index_is_missing(self):
        calls = {"cypher": []}

        class MissingIndex(RuntimeError):
            code = "Neo.ClientError.Schema.IndexNotFound"

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def run(self, cypher, **parameters):
                calls["cypher"].append(cypher)
                if "db.index.fulltext.queryNodes" in cypher:
                    raise MissingIndex()
                return []

        class Driver:
            def session(self, **kwargs):
                return Session()

        config = SimpleNamespace(
            database="neo4j",
            max_procedures=3,
            max_relationships=6,
            password_env="NEO4J_PASSWORD",
            uri="bolt://127.0.0.1:7687",
            username="neo4j",
        )
        retriever = Neo4jGraphRetriever(config, driver=Driver())
        retriever.search("Thủ tục hải quan")

        self.assertEqual(len(calls["cypher"]), 2)
        self.assertIn("MATCH (procedure:Procedure)", calls["cypher"][-1])

    def test_provision_indexes_does_not_write_graph_data(self):
        calls = []

        class Result:
            def consume(self):
                return None

        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def run(self, cypher, **parameters):
                calls.append((cypher, parameters))
                return Result()

        class Driver:
            def session(self, **kwargs):
                return Session()

        config = SimpleNamespace(
            database="neo4j",
            max_procedures=3,
            max_relationships=6,
            password_env="NEO4J_PASSWORD",
            uri="bolt://127.0.0.1:7687",
            username="neo4j",
        )
        result = Neo4jGraphRetriever(config, driver=Driver()).provision_indexes()

        self.assertEqual(len(result), 2)
        self.assertTrue(all(cypher.startswith("CREATE ") for cypher, _ in calls))
        self.assertTrue(all("timeout" in parameters for _, parameters in calls))
