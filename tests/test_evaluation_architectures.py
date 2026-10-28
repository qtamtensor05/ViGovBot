"""Architecture-specific output and scoring applicability, without model runs."""
import unittest
from jsonschema import ValidationError
from tests.schema_fixtures import scored, metric, validator


def architecture_case(architecture):
    row = scored()
    row["architecture"] = architecture
    if architecture.startswith("finetuned"):
        row["execution"]["model_config"].update(
            base_model="fixture-base", model_revision="base-revision", adapter_revision="adapter-revision")
    if architecture in {"base", "finetuned"}:
        row["evaluation_context"]["requested_cutoffs"] = []
        row["provenance"].update(corpus_revision=None, index_revision=None)
        row["execution"].update(retrieval=None, retrieval_skip_reason="Architecture has no retrieval",
                                query_processing=None)
        row["execution"]["generation"].update(prompt_contexts=[], citations=[],
                                              prompt_messages=[{"role": "user", "content": "Lệ phí?"}])
        row["execution"]["telemetry"].update(retrieval_latency_ms=None, query_processing_latency_ms=None)
        row["evaluation_results"].update(relevance_contract=None, metric_contracts=None)
        row["evaluation_results"]["metrics"] = {"generation": {"token_f1": metric(1)}}
    return row


class ArchitectureContractTests(unittest.TestCase):
    def test_four_configurations(self):
        for architecture in ("base", "finetuned", "rag", "finetuned_rag"):
            row = architecture_case(architecture)
            with self.subTest(architecture=architecture):
                validator("evaluation_case").validate(row)
                validator("prediction").validate({k: v for k, v in row.items()
                                                   if k not in {"golden", "evaluation_results"}})

    def test_no_retrieval_models_cannot_receive_retrieval_scores(self):
        for architecture in ("base", "finetuned"):
            for group in ("retrieval", "citation", "groundedness"):
                row = architecture_case(architecture)
                row["evaluation_results"]["metrics"][group] = {"score": metric(0)}
                with self.subTest(architecture=architecture, group=group), self.assertRaises(ValidationError):
                    validator("evaluation_case").validate(row)
                row["evaluation_results"]["metrics"][group]["score"] = metric(None, "not_applicable")
                validator("evaluation_case").validate(row)

    def test_base_cannot_sneak_in_context_or_retrieval(self):
        for field in ("retrieval", "generation"):
            row = architecture_case("base")
            row["execution"][field] = scored()["execution"][field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validator("evaluation_case").validate(row)

    def test_finetuned_requires_revision_and_adapter_or_checkpoint(self):
        for architecture in ("finetuned", "finetuned_rag"):
            row = architecture_case(architecture)
            config = row["execution"]["model_config"]
            del config["adapter_revision"]
            with self.assertRaises(ValidationError):
                validator("evaluation_case").validate(row)
            config["checkpoint_revision"] = "checkpoint-revision"
            validator("evaluation_case").validate(row)
            config["checkpoint_revision"] = None
            with self.assertRaises(ValidationError):
                validator("evaluation_case").validate(row)

    def test_base_retrieval_scope_is_invalid(self):
        row = architecture_case("base")
        row["evaluation_scope"] = "retrieval"
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)

    def test_no_routing_metric_or_output(self):
        row = scored()
        row["execution"]["query_processing"]["actual_route"] = "rag_search"
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)
        del row["execution"]["query_processing"]["actual_route"]
        row["evaluation_results"]["metrics"]["query_processing"] = {"route_accuracy": metric(1)}
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)

    def test_generation_correctness_remains_applicable_to_base(self):
        row = architecture_case("base")
        row["evaluation_results"]["metrics"]["generation"]["semantic_correctness"] = metric(0.8)
        validator("evaluation_case").validate(row)

    def test_retrieval_only_cannot_score_generation_performance(self):
        row = scored("retrieval")
        row["evaluation_results"]["metrics"]["performance"] = {"total_tokens": metric(0)}
        with self.assertRaises(ValidationError):
            validator("evaluation_case").validate(row)
        row["evaluation_results"]["metrics"]["performance"]["total_tokens"] = metric(None, "not_applicable")
        validator("evaluation_case").validate(row)
