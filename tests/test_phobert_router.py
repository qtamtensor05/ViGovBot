"""PhoBERT wire contract and conversation behavior without heavyweight dependencies."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vigovbot.rag.phobert_router import LABEL_MAP, HEAD_KEYS, read_metadata, encode_segments, decode_probabilities
from vigovbot.rag.classification import parse_classification
from vigovbot.rag.config import ConversationConfig, load_config
from vigovbot.rag.conversation import answer_conversation
from vigovbot.retrieval.retriever import extract_source_codes
from tests.test_follow_up_retrieval import fixture_retriever
from tests.test_clarification import add_procedure
from tests.tokenizer_fixtures import CharacterTokenizer


def metadata():
    return dict(labels={t: list(m) for t, m in LABEL_MAP.items()}, head_keys=HEAD_KEYS,
                thresholds=[.5] * 11, max_len=128, segmenter="pyvi", input_mode="full", dropout=.1)


def prediction(sections=(), scope="IN_SCOPE", flow="NEW", mix=False, p_out=None):
    if p_out is None:
        p_out = .7 if scope == "OUT_OF_SCOPE" else .05
    return dict(scope=scope, flow=flow, mix=mix, sections=list(sections),
                encoded_length=20, probabilities={"scope": {"Ngoài phạm vi": p_out}})


class PhoBERTContractTests(unittest.TestCase):
    def test_metadata_rejects_missing_thresholds_wrong_labels_and_preprocessing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meta.json"
            good = metadata()
            path.write_text(json.dumps(good), encoding="utf-8")
            self.assertEqual(read_metadata(path), good)
            bad_values = [dict(thresholds=[]), dict(thresholds=[float("nan")] * 11),
                          dict(segmenter="none"), dict(input_mode="question_only"), dict(max_len=0),
                          dict(head_keys={}), dict(labels={})]
            for changes in bad_values:
                with self.subTest(changes=changes):
                    path.write_text(json.dumps({**good, **changes}), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        read_metadata(path)

    def test_encoding_normalizes_segments_and_keeps_empty_context_separators(self):
        tokenizer = Mock(cls_token_id=0, sep_token_id=2)
        tokenizer.encode.side_effect = lambda text, **_: list(range(10, 10 + len(text)))
        segmenter = Mock(side_effect=lambda text: text)
        ids = encode_segments(tokenizer, [" e\u0301  a ", "", ""], segmenter, 128)
        segmenter.assert_called_once_with("é a")
        self.assertEqual(ids, [0, 10, 11, 12, 2, 2, 2, 2, 2])
        # Longest-first truncation preserves the short context and six separators.
        ids = encode_segments(tokenizer, ["abcdef", "xy", "z"], lambda x: x, 11)
        self.assertEqual(ids, [0, 10, 11, 2, 2, 10, 11, 2, 2, 10, 2])

    def test_decode_respects_saved_label_order_thresholds_and_empty_sections(self):
        meta = metadata()
        meta["labels"]["phạm_vi"].reverse()
        probabilities = dict(scope=[.05, .05, .9], flow=[.1, .9], mix=[.9, .1], sections=[0.] * 11)
        meta["thresholds"][7] = .7
        probabilities["sections"][7] = .6
        result = decode_probabilities(probabilities, meta)
        self.assertEqual((result["scope"], result["flow"], result["sections"]), ("IN_SCOPE", "FOLLOW_UP", []))
        probabilities["sections"][7] = .7
        probabilities["sections"][6] = .5
        self.assertEqual(decode_probabilities(probabilities, meta)["sections"], ["RESULT", "FEE"])

    def test_profiles_select_phobert_with_resolved_local_checkpoint(self):
        for name in ("inference.yaml", "inference-docker.yaml", "inference-docker-ollama.yaml"):
            cfg = load_config(Path("configs/rag") / name)
            self.assertEqual(cfg.conversation.routing_backend, "phobert")
            self.assertTrue(cfg.conversation.routing_phobert_path.is_absolute())
            self.assertTrue(cfg.conversation.procedure_aliases_path.is_file())
        with self.assertRaises(ValueError):
            ConversationConfig(routing_backend="phobert", routing_contract="v1")
        with self.assertRaises(ValueError):
            ConversationConfig(routing_phobert_threads=0)


class PhoBERTConversationTests(unittest.TestCase):
    def setUp(self):
        self.retriever = fixture_retriever()
        self.addCleanup(self.retriever.close)
        add_procedure(self.retriever, "1.000894", "Thủ tục đăng ký kết hôn",
                      sections=("submission_deadline_fee", "legal_basis", "required_documents",
                                "procedure_step"))
        add_procedure(self.retriever, "1.116405", "Cấp, cấp đổi, cấp lại thẻ căn cước",
                      sections=("metadata_identity",))
        self.settings = dict(routing_backend="phobert", routing_phobert_path="unused", num_ctx=16000,
                             num_predict=512, top_k=5, max_chunk_tokens=1200)
        self.model = Mock(identity={"heads.pt": "verified-hash"})
        self.answer = Mock(return_value=(json.dumps(dict(answer="Trả lời", action="answer",
                                                        evidence_status="sufficient")), {}, .1))
        self.llm_router = Mock(side_effect=AssertionError("LLM routing must not run"))
        self.history, self.state = [], None

    def search(self, query, top_k, section_types=None):
        codes = extract_source_codes(query)
        hits = [json.loads(r[0]) for r in self.retriever.db.execute("SELECT payload FROM chunks")]
        return [h for h in hits if (not codes or h["source_code"] in codes)
                and (not section_types or h["section_type"] in section_types)][:top_k]

    def ask(self, question, predictions):
        self.model.predict.side_effect = copy.deepcopy(predictions)
        with (patch("vigovbot.rag.phobert_router.get_router", return_value=self.model),
              patch.object(self.retriever, "search", side_effect=self.search)):
            result = answer_conversation(question, self.retriever, CharacterTokenizer(), self.settings,
                                         history=self.history, conversation_state=self.state,
                                         answer_fn=self.answer, router_fn=self.llm_router)
        self.state = result["conversation_state"]
        self.history.extend([dict(role="user", content=question), dict(role="assistant", content=result["prediction"])])
        parse_classification(json.dumps(result["classification"]))
        return result

    def test_fee_and_follow_up_use_checkpoint_sections_and_signed_procedure(self):
        result = self.ask("Phí và lệ phí cho thủ tục đăng kí kết hôn là bao nhiêu", [prediction(["FEE"])])
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.000894"})
        self.assertEqual(result["routing_backend"], "phobert")
        self.assertEqual(result["raw_routing"]["checkpoint"], self.model.identity)
        result = self.ask("Căn cứ pháp lí?", [prediction(["LEGAL_BASIS"], flow="FOLLOW_UP")])
        self.assertEqual({h["section_type"] for h in result["retrieved"]}, {"legal_basis"})
        self.assertEqual(self.model.predict.call_args.args[1:], ("Trả lời", "Thủ tục đăng ký kết hôn"))
        self.llm_router.assert_not_called()

    def test_stateless_follow_up_recovers_unique_user_history_identity(self):
        self.history = [
            {"role": "user", "content": "Tôi đang tìm hiểu Cấp, cấp đổi, cấp lại thẻ căn cước (mã 1.116405)."},
            {"role": "assistant", "content": "Bạn muốn xem nội dung nào của thủ tục này?"},
        ]
        result = self.ask("Còn cơ quan có thẩm quyền thì sao?", [
            prediction(["AUTHORITY"], flow="FOLLOW_UP"),
        ])
        self.assertEqual(result["actual_route"], "rag_search")
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.116405"})
        self.assertEqual({h["section_type"] for h in result["retrieved"]}, {"metadata_identity"})
        self.assertEqual(result["conversation_state"]["selected"], ["1.116405"])
        self.assertIn({"type": "history_identity_recovery", "outcome": "accepted",
                       "source_code": "1.116405"}, result["raw_routing"]["adapter_decisions"])

    def test_stateless_follow_up_recovers_unique_name_without_code(self):
        self.history = [
            {"role": "user", "content": "Tôi đang tìm hiểu Cấp, cấp đổi, cấp lại thẻ căn cước."},
            {"role": "assistant", "content": "Bạn muốn xem nội dung nào?"},
        ]
        result = self.ask("Còn cơ quan có thẩm quyền thì sao?", [
            prediction(["AUTHORITY"], flow="FOLLOW_UP"),
        ])
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.116405"})

    def test_invalid_signed_state_falls_back_to_verified_user_history(self):
        self.history = [
            {"role": "user", "content": "Tôi đang tìm hiểu mã (1.116405)."},
            {"role": "assistant", "content": "Bạn muốn xem nội dung nào?"},
        ]
        self.state = {"version": 2, "signature": "invalid"}
        result = self.ask("Còn cơ quan có thẩm quyền thì sao?", [
            prediction(["AUTHORITY"], flow="FOLLOW_UP"),
        ])
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.116405"})

    def test_stateless_new_named_question_does_not_inherit_history_identity(self):
        self.history = [
            {"role": "user", "content": "Tôi đang tìm hiểu mã (1.116405)."},
            {"role": "assistant", "content": "Bạn muốn xem nội dung nào?"},
        ]
        result = self.ask("Hồ sơ thủ tục đăng ký kết hôn", [prediction(["DOSSIER"], flow="NEW")])
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.000894"})

    def test_stateless_follow_up_rejects_ambiguous_assistant_only_and_numeric_history(self):
        histories = [
            [{"role": "user", "content": "Toi hoi ma (1.000894) va (1.116405)."},
             {"role": "assistant", "content": "Ban muon xem muc nao?"}],
            [{"role": "user", "content": "Toi can ho tro."},
             {"role": "assistant", "content": "Co the ban hoi ma 1.116405."}],
        ]
        for history in histories:
            with self.subTest(history=history):
                self.history, self.state = history, None
                result = self.ask("Con co quan thi sao?", [prediction(["AUTHORITY"], flow="FOLLOW_UP")])
                self.assertEqual(result["action"], "clarify")
                self.assertEqual(result["retrieved"], [])
        self.history = [
            {"role": "user", "content": "Toi dang tim hieu ma (1.116405)."},
            {"role": "assistant", "content": "1. Co quan thuc hien\n2. Ho so"},
        ]
        self.state = None
        result = self.ask("2", [prediction(["DOSSIER"], flow="FOLLOW_UP")])
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["retrieved"], [])

    def test_newer_unknown_code_blocks_inheritance_from_older_user_history(self):
        self.history = [
            {"role": "user", "content": "Toi dang tim hieu ma (1.116405)."},
            {"role": "assistant", "content": "Ban muon xem muc nao?"},
            {"role": "user", "content": "Khong, toi hoi ma (9.999999)."},
            {"role": "assistant", "content": "Ban vui long noi noi dung can xem."},
        ]
        result = self.ask("Con co quan thi sao?", [prediction(["AUTHORITY"], flow="FOLLOW_UP")])
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["retrieved"], [])

    def test_explicit_section_overrides_checkpoint_but_not_out_of_scope(self):
        result = self.ask("Căn cứ pháp lý thủ tục đăng ký kết hôn", [prediction(["DOSSIER"])])
        self.assertEqual(result["classification"]["sections"], ["LEGAL_BASIS"])
        self.assertEqual({h["section_type"] for h in result["retrieved"]}, {"legal_basis"})
        self.assertIn({
            "type": "explicit_section_override",
            "outcome": "accepted",
            "predicted_sections": ["DOSSIER"],
            "explicit_sections": ["LEGAL_BASIS"],
        }, result["raw_routing"]["adapter_decisions"])
        result = self.ask("Viết thơ", [prediction(scope="OUT_OF_SCOPE")])
        self.assertEqual(result["actual_route"], "out_of_scope")
        self.assertEqual(result["retrieved"], [])

    def test_explicit_follow_ups_change_section_and_keep_signed_procedure(self):
        result = self.ask("Thủ tục đăng ký kết hôn cần những giấy tờ nào", [prediction(["DOSSIER"])])
        self.assertEqual({h["section_type"] for h in result["retrieved"]}, {"required_documents"})

        result = self.ask("Trình tự thực hiện của thủ tục này là gì", [
            prediction(["DOSSIER"], flow="FOLLOW_UP"),
        ])
        self.assertEqual(result["classification"]["sections"], ["PROCEDURE"])
        self.assertEqual({h["section_type"] for h in result["retrieved"]}, {"procedure_step"})
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.000894"})

        result = self.ask("Căn cứ pháp lý của thủ tục này là gì", [
            prediction(["DOSSIER"], flow="FOLLOW_UP"),
        ])
        self.assertEqual(result["classification"]["sections"], ["LEGAL_BASIS"])
        self.assertEqual({h["section_type"] for h in result["retrieved"]}, {"legal_basis"})
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.000894"})

    def test_exact_corpus_identity_overrides_false_out_of_scope_without_adding_sections(self):
        result = self.ask("Đăng ký kết hôn", [prediction(scope="OUT_OF_SCOPE")])
        self.assertEqual(result["classification"]["scope"], "IN_SCOPE")
        self.assertEqual(result["classification"]["sections"], [])
        self.assertEqual(result["menu"]["kind"], "section")
        self.assertEqual(result["raw_routing"]["adapter_decisions"], [{
            "type": "catalog_scope_arbitration",
            "outcome": "catalog_identity_overrode_out_of_scope",
            "p_out_of_scope": .7,
            "override_band": [.5, .85],
        }])

    def test_high_confidence_out_of_scope_is_not_overridden_by_catalog_identity(self):
        result = self.ask("Đăng ký kết hôn chỉ là câu đùa", [
            prediction(scope="OUT_OF_SCOPE", p_out=.85),
        ])
        self.assertEqual(result["actual_route"], "out_of_scope")
        self.assertEqual(result["classification"]["scope"], "OUT_OF_SCOPE")
        self.assertEqual(result["raw_routing"]["adapter_decisions"][0], {
            "type": "catalog_scope_arbitration",
            "outcome": "kept_out_of_scope",
            "p_out_of_scope": .85,
            "override_band": [.5, .85],
        })

    def test_high_confidence_out_of_scope_can_only_open_confirmation_menu(self):
        self.retriever._procedure_discovery_lock = Mock()
        self.retriever.discover_procedures = Mock(return_value=[
            {"code": "1.000894", "name": "Thủ tục đăng ký kết hôn", "gated_score": .81},
            {"code": "1.000001", "name": "Cấp hộ chiếu", "gated_score": .70},
        ])
        result = self.ask("làm đăng ký", [prediction(scope="OUT_OF_SCOPE", p_out=.96)])
        self.assertEqual(result["actual_route"], "clarify")
        self.assertTrue(result["menu"]["confirmation"])
        self.assertIn("Có phải bạn muốn", result["prediction"])
        self.answer.assert_not_called()
        self.model.reset_mock()
        result = self.ask("1", [])
        self.model.predict.assert_not_called()
        self.assertEqual(result["classification"]["scope"], "IN_SCOPE")
        self.assertEqual(result["menu"]["kind"], "section")

    def test_curated_alias_is_the_only_direct_high_confidence_scope_override(self):
        add_procedure(self.retriever, "1.115978", "Đổi, cấp lại Giấy phép lái xe")
        with tempfile.TemporaryDirectory() as directory:
            alias_file = Path(directory) / "aliases.yaml"
            alias_file.write_text(
                'version: 1\nprocedures:\n  "1.115978":\n    - đổi bằng lái xe máy\n', encoding="utf-8")
            self.settings["procedure_aliases_path"] = alias_file
            result = self.ask("đổi bằng lái xe máy", [prediction(scope="OUT_OF_SCOPE", p_out=.99)])
        self.assertEqual(result["classification"]["scope"], "IN_SCOPE")
        self.assertEqual(result["menu"]["kind"], "section")
        self.assertEqual(result["conversation_state"]["selected"], ["1.115978"])
        self.assertEqual(result["raw_routing"]["adapter_decisions"][0]["outcome"],
                         "curated_alias_overrode_out_of_scope")

    def test_alias_mention_does_not_bypass_high_confidence_out_of_scope(self):
        add_procedure(self.retriever, "1.115978", "Đổi, cấp lại Giấy phép lái xe")
        with tempfile.TemporaryDirectory() as directory:
            alias_file = Path(directory) / "aliases.yaml"
            alias_file.write_text(
                'version: 1\nprocedures:\n  "1.115978":\n    - đổi bằng lái xe máy\n', encoding="utf-8")
            self.settings["procedure_aliases_path"] = alias_file
            result = self.ask("đổi bằng lái xe máy chỉ là câu đùa", [
                prediction(scope="OUT_OF_SCOPE", p_out=.99),
            ])
        self.assertEqual(result["actual_route"], "out_of_scope")
        self.assertEqual(result["raw_routing"]["adapter_decisions"][0]["outcome"], "kept_out_of_scope")

    def test_confirmation_rejection_keeps_out_of_scope_without_retrieval(self):
        self.retriever._procedure_discovery_lock = Mock()
        self.retriever.discover_procedures = Mock(return_value=[
            {"code": "1.000894", "name": "Thủ tục đăng ký kết hôn", "gated_score": .81},
            {"code": "1.000001", "name": "Cấp hộ chiếu", "gated_score": .70},
        ])
        self.ask("làm đăng ký", [prediction(scope="OUT_OF_SCOPE", p_out=.96)])
        result = self.ask("không phải", [])
        self.assertEqual(result["actual_route"], "out_of_scope")
        self.assertEqual(result["action"], "abstain")
        self.assertEqual(result["retrieved"], [])

    def test_empty_sections_create_text_menu_and_number_skips_model(self):
        result = self.ask("Đăng ký kết hôn", [prediction()])
        self.assertEqual(result["menu"]["kind"], "section")
        number = next(i for i, o in enumerate(result["menu"]["options"], 1) if o["id"] == "FEE")
        self.model.reset_mock()
        result = self.ask(str(number), [])
        self.model.predict.assert_not_called()
        self.assertEqual(result["routing_backend"], "clarification")
        self.assertEqual({h["section_type"] for h in result["retrieved"]}, {"submission_deadline_fee"})

    def test_specific_question_without_section_searches_all_exact_procedure_chunks(self):
        result = self.ask("Đối tượng thực hiện của thủ tục đăng ký kết hôn là gì?", [prediction()])
        self.assertEqual(result["actual_route"], "rag_search")
        self.assertIsNone(result["menu"])
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.000894"})
        self.assertEqual(result["classification"]["sections"], [])
        self.assertNotIn("Mục dữ liệu:", result["retrieval_query"])

    def test_duplicate_names_offer_candidates(self):
        add_procedure(self.retriever, "2.000894", "Thủ tục đăng ký kết hôn")
        result = self.ask("Hồ sơ đăng ký kết hôn", [prediction(["DOSSIER"])])
        self.assertEqual({o["id"] for o in result["menu"]["options"]}, {"1.000894", "2.000894"})
        self.answer.assert_not_called()

    def test_explicit_code_resolves_one_of_duplicate_names_without_menu(self):
        name = "Tách thửa hoặc hợp thửa đất"
        add_procedure(self.retriever, "1.115201", name)
        add_procedure(self.retriever, "1.115490", name)

        result = self.ask(
            "Cho mình nội dung bước 2 khi thực hiện Tách thửa hoặc hợp thửa đất "
            "(mã 1.115490, tỉnh Thanh Hóa).",
            [prediction(["PROCEDURE"])],
        )

        self.assertEqual(result["actual_route"], "rag_search")
        self.assertIsNone(result["menu"])
        self.assertEqual({hit["source_code"] for hit in result["retrieved"]}, {"1.115490"})

    def test_result_searches_all_sections_of_selected_procedure(self):
        result = self.ask("Kết quả đăng ký kết hôn", [prediction(["RESULT"])])
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.000894"})
        self.assertEqual({h["section_type"] for h in result["retrieved"]},
                         {"submission_deadline_fee", "legal_basis", "required_documents",
                          "procedure_step"})
        self.assertIn("Mục dữ liệu: result", result["retrieval_query"])

    def test_new_question_does_not_inherit_previous_selected_procedure(self):
        self.ask("Phí đăng ký kết hôn", [prediction(["FEE"])])
        result = self.ask("Hồ sơ cấp hộ chiếu", [prediction(["DOSSIER"])])
        self.assertEqual({h["source_code"] for h in result["retrieved"]}, {"1.000001"})

    def test_unverified_follow_up_and_multiple_procedures_ask_for_clarification(self):
        result = self.ask("Còn lệ phí?", [prediction(["FEE"], flow="FOLLOW_UP")])
        self.assertEqual(result["action"], "clarify")
        result = self.ask("Hồ sơ hộ chiếu và lệ phí kết hôn", [prediction(["DOSSIER", "FEE"], mix=True)])
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["retrieved"], [])
        self.answer.assert_not_called()

    def test_mixed_scope_only_sends_supported_clause_to_generation(self):
        result = self.ask("Phí đăng ký kết hôn; viết thơ", [prediction(["FEE"], scope="MIXED_SCOPE"),
                                                          prediction(["FEE"]), prediction(scope="OUT_OF_SCOPE")])
        self.assertEqual(result["action"], "partial")
        self.assertNotIn("viết thơ", result["retrieval_query"])
        self.assertNotIn("viết thơ", json.dumps(self.answer.call_args.args[0], ensure_ascii=False))
        self.llm_router.assert_not_called()

    def test_mixed_scope_natural_conjunctions_use_selective_rewrite_and_reclassify(self):
        for connector in ("nhưng", "với lại", "tiện thể cho tôi hỏi thêm", "còn việc"):
            with self.subTest(connector=connector):
                self.history, self.state = [], None
                self.model.reset_mock(side_effect=True)
                self.answer.reset_mock()
                self.llm_router.reset_mock(side_effect=True)
                self.llm_router.return_value = (json.dumps({"query": "Phí đăng ký kết hôn"}), {}, .05)
                result = self.ask(f"Phí đăng ký kết hôn {connector} viết thơ", [
                    prediction(scope="MIXED_SCOPE"), prediction(["FEE"]),
                ])
                self.assertEqual(result["action"], "partial")
                self.assertIn("Phí đăng ký kết hôn", result["retrieval_query"])
                self.assertNotIn("viết thơ", json.dumps(self.answer.call_args.args[0], ensure_ascii=False))
                self.assertEqual(result["raw_routing"]["mixed_scope_rewrite"]["outcome"], "accepted_after_phobert")
                self.assertEqual(len(result["raw_routing"]["predictions"]), 2)
                self.llm_router.assert_called_once()
                messages, call_settings = self.llm_router.call_args.args
                self.assertIn("Lệ phí đăng ký kết hôn", messages[0]["content"])
                self.assertEqual(call_settings["num_predict"], 128)
                self.assertEqual(call_settings["temperature"], 0)

    def test_mixed_scope_rewrite_rejects_nonextractive_candidate(self):
        self.llm_router.side_effect = None
        self.llm_router.return_value = (json.dumps({"query": "Thủ tục xin cấp thị thực"}), {}, .05)
        result = self.ask("Phí đăng ký kết hôn nhưng viết thơ", [prediction(scope="MIXED_SCOPE")])
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["raw_routing"]["mixed_scope_rewrite"]["outcome"],
                         "non_extractive_or_dropped_qualifier")
        self.assertEqual(len(result["raw_routing"]["predictions"]), 1)
        self.answer.assert_not_called()

    def test_mixed_scope_rewrite_candidate_must_pass_phobert_scope(self):
        self.llm_router.side_effect = None
        self.llm_router.return_value = (json.dumps({"query": "viết thơ"}), {}, .05)
        result = self.ask("Phí đăng ký kết hôn nhưng viết thơ", [
            prediction(scope="MIXED_SCOPE"), prediction(scope="OUT_OF_SCOPE"),
        ])
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["raw_routing"]["mixed_scope_rewrite"]["outcome"],
                         "reclassification_rejected")
        self.assertEqual(len(result["raw_routing"]["predictions"]), 2)
        self.answer.assert_not_called()

    def test_mixed_scope_rewrite_llm_failure_keeps_clarification_and_skips_retrieval(self):
        self.llm_router.side_effect = RuntimeError("router unavailable")
        result = self.ask("Phí đăng ký kết hôn nhưng viết thơ", [prediction(scope="MIXED_SCOPE")])
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["raw_routing"]["mixed_scope_rewrite"]["outcome"], "rewrite_failed")
        self.assertEqual(result["retrieved"], [])
        self.answer.assert_not_called()

    def test_mixed_scope_multiple_split_parts_do_not_use_single_query_rewriter(self):
        result = self.ask("Phí đăng ký kết hôn; Hồ sơ đăng ký kết hôn; viết thơ", [
            prediction(scope="MIXED_SCOPE"), prediction(["FEE"]), prediction(["DOSSIER"]),
            prediction(scope="OUT_OF_SCOPE"),
        ])
        self.assertEqual(result["action"], "clarify")
        self.assertFalse(result["raw_routing"]["mixed_scope_fallback_allowed"])
        self.llm_router.assert_not_called()
        self.answer.assert_not_called()

    def test_mixed_scope_rewrite_cannot_drop_a_narrowing_qualifier(self):
        self.llm_router.side_effect = None
        self.llm_router.return_value = (json.dumps({"query": "Phí đăng ký kết hôn"}), {}, .05)
        result = self.ask("Phí đăng ký kết hôn cho người nước ngoài nhưng viết thơ", [
            prediction(scope="MIXED_SCOPE"),
        ])
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["raw_routing"]["mixed_scope_rewrite"]["outcome"],
                         "non_extractive_or_dropped_qualifier")
        self.model.predict.assert_called_once()
        self.answer.assert_not_called()

    def test_missing_checkpoint_never_falls_back_to_llm(self):
        with patch("vigovbot.rag.phobert_router.get_router", side_effect=FileNotFoundError("checkpoint")):
            with self.assertRaises(FileNotFoundError):
                answer_conversation("Hồ sơ?", self.retriever, CharacterTokenizer(), self.settings,
                                    answer_fn=self.answer, router_fn=self.llm_router)
        self.llm_router.assert_not_called()
        self.answer.assert_not_called()
