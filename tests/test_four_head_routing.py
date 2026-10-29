"""Four-head contract and conversation regressions without a running model."""
import copy
import json
import unittest
from unittest.mock import Mock, patch

from tests.tokenizer_fixtures import CharacterTokenizer
from tests.test_follow_up_retrieval import fixture_retriever
from tests.test_clarification import add_procedure
from vigovbot.rag.classification import parse_classification, classify
from vigovbot.rag.conversation import answer_conversation, direct_choice
from vigovbot.rag.sections import available_sections, explicit_section_intents


def route(procedure="Cấp hộ chiếu", sections=None, **overrides):
    sections = [] if sections is None else sections
    value = dict(scope="IN_SCOPE", conversation="NEW", mixed_procedures=False, sections=sections,
                 query=procedure, needs_clarification=False, clarification="",
                 requests=[dict(procedure=procedure, query=procedure, sections=sections)])
    value.update(overrides)
    return value


class FourHeadTests(unittest.TestCase):
    def setUp(self):
        self.retriever = fixture_retriever()
        self.addCleanup(self.retriever.close)
        self.settings = dict(num_ctx=16000, num_predict=512, routing_num_ctx=12000,
                             routing_num_predict=768, top_k=5, max_chunk_tokens=1200,
                             routing_model="router-base", routing_base_url="http://router:11434")
        self.tokenizer = CharacterTokenizer()
        self.router = Mock()
        self.answer = Mock(return_value=(json.dumps(dict(answer="Réponse", action="answer",
                                                        evidence_status="sufficient")), {}, .1))
        self.history = []
        self.state = None

    def ask(self, question, classification=None, **kwargs):
        if classification is not None:
            self.router.return_value = (json.dumps(classification), {}, .1)
        with patch.object(self.retriever, "search", side_effect=self.search):
            result = answer_conversation(question, self.retriever, self.tokenizer, self.settings,
                                         history=self.history, conversation_state=self.state,
                                         answer_fn=self.answer, router_fn=self.router, **kwargs)
        self.history += [dict(role="user", content=question), dict(role="assistant", content=result["prediction"])]
        self.state = result["conversation_state"]
        return result

    def search(self, query, top_k, **kwargs):
        from vigovbot.retrieval.retriever import extract_source_codes
        codes = extract_source_codes(query)
        return [json.loads(row[0]) for row in self.retriever.db.execute("SELECT payload FROM chunks")
                if not codes or json.loads(row[0])["source_code"] in codes][:top_k]

    def test_prefixed_catalog_identity_survives_missing_menu_and_router_prefix(self):
        add_procedure(self.retriever, "1.000894", "Thủ tục đăng ký kết hôn",
                      sections=("submission_deadline_fee", "legal_basis"))
        for field, section in (("Phí và lệ phí", "FEE"), ("Căn cứ pháp lí", "LEGAL_BASIS")):
            for prefix in ("cho thủ tục ", ""):
                with self.subTest(field=field, prefix=prefix):
                    self.history, self.state = [], None
                    question = field + " " + prefix + "đăng kí kết hôn là bao nhiêu"
                    classification = route("Đăng ký kết hôn", [section], query=question,
                                           requests=[dict(procedure="Đăng ký kết hôn", query=question,
                                                          sections=[section])])
                    result = self.ask(question, classification)
                    self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.000894"})
                    self.assertEqual(result["conversation_state"]["selected"], ["1.000894"])
                    self.assertIsNone(result["menu"])
                    self.assertEqual(result["action"], "answer")

    def test_explicit_identity_wins_over_wrong_router_procedure(self):
        add_procedure(self.retriever, "1.000894", "Thủ tục đăng ký kết hôn",
                      sections=("submission_deadline_fee",))
        result = self.ask("Phí cho thủ tục đăng kí kết hôn", route("Cấp hộ chiếu", ["FEE"]))
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.000894"})
        self.assertNotIn("Cấp hộ chiếu", result["retrieval_query"])

    def test_prefixed_duplicate_names_still_require_procedure_choice(self):
        for code in ("1.000894", "2.000894"):
            add_procedure(self.retriever, code, "Thủ tục đăng ký kết hôn",
                          sections=("submission_deadline_fee",))
        result = self.ask("Lệ phí đăng ký kết hôn", route("Đăng ký kết hôn", ["FEE"]))
        self.assertEqual({o["id"] for o in result["menu"]["options"]}, {"1.000894", "2.000894"})
        self.answer.assert_not_called()

    def test_legal_li_follow_up_overrides_stale_fee_section(self):
        self.ask("Cấp hộ chiếu", route())
        result = self.ask("Căn cứ pháp lí", route(sections=["FEE"], conversation="FOLLOW_UP"))
        self.assertEqual(result["classification"]["sections"], ["LEGAL_BASIS"])
        self.assertIn("legal_basis", result["retrieval_query"])
        self.assertNotIn("submission_deadline_fee", result["retrieval_query"])

    def test_direct_menu_number_and_button_skip_router(self):
        first = self.ask("Cấp hộ chiếu", route())
        self.assertEqual(first["menu"]["kind"], "section")
        ids = [o["id"] for o in first["menu"]["options"]]
        self.assertIn("OVERVIEW", ids)
        self.assertIn("FEE", ids)
        self.router.reset_mock()
        result = self.ask("số 2")
        self.router.assert_not_called()
        self.assertEqual(result["classification"]["sections"], [ids[1]])
        self.assertEqual(result["routing_attempts"], 0)
        self.assertIsNone(result["menu"])
        first = self.ask("Cấp hộ chiếu", route())
        result = self.ask("1", selection=dict(menu_id=first["menu"]["id"], option_id="OVERVIEW"))
        self.assertEqual(result["classification"]["sections"], ["OVERVIEW"])

    def test_bare_name_does_not_accept_invented_sections(self):
        result = self.ask("Cấp hộ chiếu", route(sections=["DOSSIER", "FEE"]))
        self.assertEqual(result["classification"]["sections"], [])
        self.assertEqual(result["menu"]["kind"], "section")
        self.answer.assert_not_called()

    def test_section_selection_replaces_bare_procedure_query(self):
        first = self.ask("Cấp hộ chiếu", route())
        index = next(i for i, option in enumerate(first["menu"]["options"], 1) if option["id"] == "DOSSIER")
        result = self.ask(str(index))
        self.assertEqual(result["classification"]["requests"][0]["query"], "Hồ sơ, giấy tờ")
        self.assertIn("Hồ sơ, giấy tờ", result["retrieval_query"])

    def test_procedure_list_uses_catalog_before_semantic_fallback(self):
        base = "Cấp lại chứng chỉ kiểm định viên"
        add_procedure(self.retriever, "2.000066", base)
        add_procedure(self.retriever, "1.000187", base + " trong trường hợp hết hạn")
        if hasattr(self.retriever, "_clarification_catalog"):
            del self.retriever._clarification_catalog
        self.history, self.state = [], None
        self.router.return_value = (json.dumps(route("UNRELATED_ENGLISH_NAME", ["FEE"])), {}, .1)
        with patch.object(self.retriever, "search") as semantic:
            result = answer_conversation(
                "Các thủ tục cấp lại chứng chỉ kiểm định viên", self.retriever, self.tokenizer, self.settings,
                history=[], conversation_state=None, answer_fn=self.answer, router_fn=self.router)
        self.assertEqual(result["menu"]["kind"], "procedure")
        self.assertEqual({o["id"] for o in result["menu"]["options"]}, {"2.000066", "1.000187"})
        semantic.assert_not_called()

    def test_catalog_discovery_overrides_false_out_of_scope(self):
        add_procedure(self.retriever, "1.100001", "Giao đất, cho thuê đất không thông qua đấu giá")
        add_procedure(self.retriever, "1.100002", "Chuyển hình thức giao đất, cho thuê đất")
        if hasattr(self.retriever, "_clarification_catalog"):
            del self.retriever._clarification_catalog
        self.history, self.state = [], None
        outside = route(scope="OUT_OF_SCOPE", sections=[], query="", requests=[])
        result = self.ask("Các thủ tục liên quan đến thuê đất", outside)
        self.assertEqual(result["classification"]["scope"], "IN_SCOPE")
        self.assertEqual(result["menu"]["kind"], "procedure")
        self.assertEqual({o["id"] for o in result["menu"]["options"]}, {"1.100001", "1.100002"})
        self.answer.assert_not_called()

    def test_catalog_discovery_ranks_school_creation_above_unrelated_land_name(self):
        add_procedure(self.retriever, "1.200001", "Thành lập hoặc cho phép thành lập trường tiểu học")
        add_procedure(self.retriever, "1.200002", "Thành lập trường cao đẳng")
        add_procedure(self.retriever, "1.200003",
                      "Đăng ký đất đối với thành viên hộ gia đình thành lập doanh nghiệp trong trường hợp thay đổi")
        add_procedure(self.retriever, "1.200004", "Giải thể trường theo đề nghị của tổ chức thành lập trường")
        if hasattr(self.retriever, "_clarification_catalog"):
            del self.retriever._clarification_catalog
        from vigovbot.rag.clarification import Clarifier
        codes = Clarifier(self.retriever).discover("Thủ tục thành lập trường")
        self.assertEqual(codes[:2], ["1.200002", "1.200001"])
        self.assertEqual(codes[-1], "1.200004")

    def test_natural_question_uses_router_and_new_drops_old_subject(self):
        self.ask("Cấp hộ chiếu", route())
        self.router.reset_mock()
        result = self.ask("Hồ sơ cấp giấy khai sinh?", route("Cấp giấy khai sinh", ["DOSSIER"]))
        self.assertEqual(self.router.call_count, 1)
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"2.000002"})
        self.assertIsNone(result["menu"])

    def test_follow_up_uses_verified_state_and_missing_state_clarifies(self):
        self.ask("Cấp hộ chiếu", route())
        result = self.ask("Còn lệ phí?", route(sections=["FEE"], conversation="FOLLOW_UP"))
        self.assertEqual(result["conversation_state"]["selected"], ["1.000001"])
        self.history, self.state = [], None
        result = self.ask("Còn lệ phí?", route(sections=["FEE"], conversation="FOLLOW_UP"))
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["retrieved"], [])

    def test_explicit_section_follow_up_overrides_stale_model_section(self):
        self.ask("Cấp hộ chiếu", route())
        self.ask("Lệ phí thì sao?", route(sections=["FEE"], conversation="FOLLOW_UP"))
        result = self.ask("Trình tự thực hiện", route(sections=["FEE"], conversation="FOLLOW_UP"))
        self.assertEqual(result["classification"]["sections"], ["PROCEDURE"])
        self.assertIn("procedure_step", result["retrieval_query"])
        self.assertNotIn("submission_deadline_fee", result["retrieval_query"])

    def test_section_keyword_mapping_is_explicit_and_multilabel(self):
        self.assertEqual(explicit_section_intents("Trình tự thực hiện"), ["PROCEDURE"])
        self.assertEqual(explicit_section_intents("Hồ sơ gồm gì, lệ phí bao nhiêu?"), ["DOSSIER", "FEE"])
        self.assertEqual(explicit_section_intents("trường hợp khác"), [])

    def test_invalid_choice_tampered_and_expired_state(self):
        first = self.ask("Cấp hộ chiếu", route())
        self.router.reset_mock()
        invalid = self.ask("99")
        self.assertEqual(invalid["menu"]["id"], first["menu"]["id"])
        self.router.assert_not_called()
        self.state["selected"] = ["2.000002"]
        result = self.ask("2")
        self.assertEqual(result["decision_reason"], "expired_selection")
        self.assertIsNone(result["menu"])

    def test_rejecting_or_confirming_procedure_menu_never_selects_an_item(self):
        for index in range(4, 10):
            add_procedure(self.retriever, f"1.00000{index}",
                          f"Đăng ký tạm trú trường hợp {index}")
        if hasattr(self.retriever, "_clarification_catalog"):
            del self.retriever._clarification_catalog
        self.history, self.state = [], None
        first = self.ask("Các thủ tục đăng ký tạm trú", route("Đăng ký tạm trú"))
        self.assertEqual(first["menu"]["kind"], "procedure")
        first_ids = {option["id"] for option in first["menu"]["options"]}
        self.router.reset_mock()
        rejected = self.ask("Không phải mấy cái trên")
        self.router.assert_not_called()
        self.assertEqual(rejected["menu"]["kind"], "procedure")
        self.assertTrue(first_ids.isdisjoint(option["id"] for option in rejected["menu"]["options"]))
        self.assertEqual(rejected["conversation_state"]["selected"], [])
        confirmed = self.ask("Đúng rồi")
        self.router.assert_not_called()
        self.assertEqual(confirmed["menu"]["kind"], "procedure")
        self.assertEqual(confirmed["conversation_state"]["selected"], [])

    def test_other_variant_after_generic_answer_opens_alternatives(self):
        base = "Cấp lại chứng chỉ kiểm định viên"
        add_procedure(self.retriever, "2.000066", base)
        add_procedure(self.retriever, "1.000187", base + " trong trường hợp hết hạn")
        add_procedure(self.retriever, "1.000183", base + " đối với trường hợp bị mất")
        if hasattr(self.retriever, "_clarification_catalog"):
            del self.retriever._clarification_catalog
        self.history, self.state = [], None
        answered = self.ask("Trình tự " + base, route(base, ["PROCEDURE"]))
        self.assertEqual(answered["conversation_state"]["selected"], ["2.000066"])
        self.router.reset_mock()
        result = self.ask("trường hợp khác")
        self.router.assert_not_called()
        self.assertEqual(result["menu"]["kind"], "procedure")
        self.assertEqual({o["id"] for o in result["menu"]["options"]}, {"1.000187", "1.000183"})

    def test_copied_label_must_match_number_and_natural_text_is_not_choice(self):
        first = self.ask("Cấp hộ chiếu", route())
        menu = first["menu"]
        self.assertEqual(direct_choice("1. " + menu["options"][1]["label"], menu), (None, True))
        self.assertEqual(direct_choice("Tôi cần hồ sơ, giấy tờ", menu), (None, False))
        self.assertEqual(direct_choice(menu["options"][0]["label"], menu)[0], menu["options"][0])

    def test_text_client_exact_history_can_select_without_state(self):
        self.ask("Cấp hộ chiếu", route())
        self.state = None
        self.router.reset_mock()
        result = self.ask("1")
        self.router.assert_not_called()
        self.assertEqual(result["actual_route"], "rag_search")

    def test_multiple_procedures_keep_section_pairings(self):
        value = route(sections=["DOSSIER", "FEE"], mixed_procedures=True, requests=[
            dict(procedure="Cấp giấy khai sinh", query="Hồ sơ cấp giấy khai sinh", sections=["DOSSIER"]),
            dict(procedure="Cấp hộ chiếu", query="Phí cấp hộ chiếu", sections=["FEE"])])
        result = self.ask("Hồ sơ cấp giấy khai sinh và phí hộ chiếu", value)
        queries = result["actual_sub_queries"]
        self.assertIn("required_documents", queries[0]["query"])
        self.assertNotIn("submission_deadline_fee", queries[0]["query"])
        self.assertIn("Mục dữ liệu: fee", queries[1]["query"])
        self.assertEqual(set(result["conversation_state"]["selected"]), {"1.000001", "2.000002"})

    def test_ambiguous_request_preserves_other_request_through_menu(self):
        add_procedure(self.retriever, "2.000003", "Cấp giấy khai sinh")
        value = route(sections=["DOSSIER", "FEE"], mixed_procedures=True, requests=[
            dict(procedure="Cấp giấy khai sinh", query="Hồ sơ cấp giấy khai sinh", sections=["DOSSIER"]),
            dict(procedure="Cấp hộ chiếu", query="Phí cấp hộ chiếu", sections=["FEE"])])
        result = self.ask("Hồ sơ khai sinh và phí hộ chiếu", value)
        self.assertEqual(result["menu"]["kind"], "procedure")
        self.router.reset_mock()
        result = self.ask("2")
        self.router.assert_not_called()
        self.assertEqual(len(result["actual_sub_queries"]), 2)
        self.assertEqual(set(result["conversation_state"]["selected"]), {"2.000003", "1.000001"})

    def test_scope_and_missing_source(self):
        result = self.ask("Thời tiết?", route(scope="OUT_OF_SCOPE", sections=[], query="", requests=[]))
        self.assertEqual(result["actual_route"], "out_of_scope")
        self.answer.assert_not_called()
        result = self.ask("Phí hộ chiếu và thời tiết?", route(sections=["FEE"], scope="MIXED_SCOPE"))
        self.assertEqual(result["action"], "partial")
        self.assertIn("ngoài phạm vi", result["prediction"])
        result = self.ask("Hồ sơ 9.999999", route("9.999999", ["DOSSIER"]))
        self.assertEqual(result["evidence_status"], "missing")
        self.assertEqual(result["classification"]["scope"], "IN_SCOPE")

    def test_identifier_absent_from_evidence_abstains_after_retrieval(self):
        question = ("Ma lich gan voi ho so HS-1000001-20261030-149 ngay 09/11/2026 "
                    "co hop le khong? Cho minh gio va quay tiep nhan thuc te.")
        result = self.ask(question, route("C?p h? chi?u", ["FEE"]))
        self.assertEqual(result["action"], "abstain")
        self.assertEqual(result["evidence_status"], "missing")
        self.assertEqual(result["decision_reason"], "identifier_not_in_evidence")
        self.assertIn("HS-1000001-20261030-149", result["prediction"])
        self.assertTrue(result["retrieved"])
        self.answer.assert_not_called()

    def test_identifier_present_in_evidence_is_not_forced_to_abstain(self):
        from vigovbot.rag.conversation import identifiers_missing_from_hits
        question = "Trang thai giao dich GD-ABC-2026 la gi?"
        self.assertEqual(identifiers_missing_from_hits(
            question, [{"text_content": "He thong ghi nhan GD-ABC-2026 da hoan tat."}]), [])
        self.assertEqual(identifiers_missing_from_hits(
            question, [{"text_content": "Quy trinh xu ly giao dich chung."}]), ["GD-ABC-2026"])

    def test_standalone_greeting_does_not_continue_previous_procedure(self):
        self.ask("C?p h? chi?u", route())
        self.router.reset_mock()
        self.answer.reset_mock()
        result = self.ask("Xin chao buoi chieu")
        self.assertEqual(result["decision_reason"], "social_greeting")
        self.assertEqual(result["actual_route"], "out_of_scope")
        self.assertEqual(result["prediction"],
                         "Xin chào! Tôi có thể hỗ trợ tra cứu thủ tục hành chính Việt Nam.")
        self.router.assert_not_called()
        self.answer.assert_not_called()

    def test_contract_retry_and_separate_router_settings_no_stream_leak(self):
        router = Mock(side_effect=[("{}", {}, 0), (json.dumps(route()), {}, 0)])
        settings = {**self.settings, "model": "answer-only", "token_callback": Mock(), "routing_early_exit": True}
        value, trace = classify("Cấp hộ chiếu", [], None, self.tokenizer, settings, router)
        self.assertEqual(trace["attempts"], 2)

        self.assertEqual(value["conversation"], "NEW")
        for call in router.call_args_list:
            self.assertEqual(call.args[1]["model"], "router-base")
            self.assertEqual(call.args[1]["ollama_url"], "http://router:11434")
            self.assertNotIn("token_callback", call.args[1])
        router = Mock(return_value=("{}", {}, 0))
        value, trace = classify("test", [], None, self.tokenizer, settings, router)
        self.assertTrue(value["needs_clarification"])
        self.assertEqual(trace["attempts"], 2)

    def test_outside_schema_forbids_retrieval_fields(self):
        from vigovbot.rag.classification import routing_schema
        outside = routing_schema()["anyOf"][0]["properties"]
        self.assertEqual(outside["scope"]["enum"], ["OUT_OF_SCOPE"])
        self.assertEqual(outside["requests"]["maxItems"], 0)
        self.assertEqual(outside["sections"]["maxItems"], 0)
        self.assertEqual(outside["query"]["enum"], [""])

    def test_validator_and_corpus_mapping(self):
        for changes in ({"mixed_procedures": "false"}, {"sections": ["UNKNOWN"]},
                        {"conversation": "ambiguous"}, {"needs_clarification": True}):
            value = copy.deepcopy(route()); value.update(changes)
            with self.assertRaises(ValueError):
                parse_classification(json.dumps(value))
        self.assertEqual(available_sections([]), ["OVERVIEW"])
        labels = available_sections(["submission_deadline_fee"])
        self.assertTrue({"FEE", "PROCESSING_TIME", "SUBMISSION_METHOD"} <= set(labels))
        self.assertNotIn("DOSSIER", labels)

    def test_sql_section_filter_does_not_borrow_other_fields(self):
        class Vector:
            def __matmul__(self, other):
                return 1.0
        self.retriever.index.reconstruct.return_value = Vector()
        hits = self.retriever._search_source_codes(
            ["1.000001"], [Vector()], 5, ["required_documents"], strict_sections=True)
        self.assertEqual([h["chunk_id"] for h in hits], ["c0"])
        missing = self.retriever._search_source_codes(
            ["1.000001"], [Vector()], 5, ["legal_basis"], strict_sections=True)
        self.assertEqual(missing, [])

    def test_state_cannot_cross_model_or_history(self):
        self.ask("Cấp hộ chiếu", route())
        from vigovbot.rag.conversation import validate_state
        corpus = self.state["corpus"]
        self.assertIsNone(validate_state(self.state, self.history, "other-model", corpus))
        self.assertIsNone(validate_state(self.state, [], "", corpus))
        self.assertIsNone(validate_state(self.state, self.history, "", "other-corpus"))


if __name__ == "__main__":
    unittest.main()
