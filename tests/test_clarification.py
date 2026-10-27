"""Metadata menus and multi-turn selection against a real in-memory corpus."""
import json
import unittest
from unittest.mock import Mock, patch

from tests.test_follow_up_retrieval import fixture_retriever
from vigovbot.rag.clarification import Clarifier


def add_procedure(retriever, code, name="Đăng ký tạm trú", sections=("procedure_step", "required_documents")):
    for section in sections:
        row = retriever.db.execute("SELECT COALESCE(MAX(row_id),0)+1 FROM chunks").fetchone()[0]
        payload = dict(chunk_id=f"c{row}", source_code=code, procedure_name=name, section_type=section,
                       text_content="|**Cấp thực hiện**|Xã|\n|**Cơ quan thực hiện**|Công an xã|")
        retriever.db.execute("INSERT INTO chunks VALUES (?,?,?)", (row, f"c{row}", json.dumps(payload)))


class ClarifierTests(unittest.TestCase):
    def setUp(self):
        self.retriever = fixture_retriever()
        self.addCleanup(self.retriever.close)
        add_procedure(self.retriever, "1.000003", sections=("procedure_step", "required_documents", "metadata_identity", "custom_section"))
        self.clarifier = Clarifier(self.retriever, "rag-a")

    def history(self, menu, question="Đăng ký tạm trú"):
        return [{"role": "user", "content": question},
                {"role": "assistant", "content": self.clarifier.render(menu)}]

    def test_bare_name_normalization_and_all_metadata_sections(self):
        for question in ("Thủ tục đăng kí tạm trú ở Việt Nam", "dang ky tam tru", "1.000003"):
            menu = self.clarifier.inspect(question)
            self.assertEqual(menu["kind"], "section")
            self.assertEqual(menu["sections"], ["metadata_identity", "procedure_step", "required_documents", "custom_section"])
            text = self.clarifier.render(menu)
            self.assertIn("custom_section", text)
            self.assertNotIn("Cách thức nộp", text)

    def test_explicit_goals_and_overview_do_not_ask(self):
        for question in ("Hồ sơ đăng ký tạm trú", "Phí và thời hạn đăng ký tạm trú",
                         "Tổng quan đăng ký tạm trú", "Hướng dẫn toàn bộ đăng ký tạm trú"):
            self.assertIsNone(self.clarifier.inspect(question))

    def test_plural_discovery_includes_variants_instead_of_choosing_exact_name(self):
        base = "Cấp lại chứng chỉ kiểm định viên"
        add_procedure(self.retriever, "2.000066", base)
        for i, suffix in enumerate(("hết hạn", "bị thu hồi", "bị hỏng", "bị mất", "sửa đổi", "bổ sung"), 1):
            add_procedure(self.retriever, f"2.00010{i}", base + " đối với trường hợp " + suffix)
        add_procedure(self.retriever, "2.000200", "Cấp chứng chỉ kiểm định viên")
        del self.retriever._clarification_catalog
        self.clarifier = Clarifier(self.retriever)
        for prefix in ("Các thủ tục", "Những thủ tục", "Danh sách thủ tục", "Liệt kê các thủ tục", "Tất cả các thủ tục"):
            menu = self.clarifier.inspect(prefix + " " + base)
            self.assertEqual(menu["kind"], "procedure")
            self.assertEqual(menu["codes"][0], "2.000066")
            self.assertEqual(len(menu["codes"]), 5)
            self.assertTrue(menu["more"])
            self.assertEqual(menu["goal"], "")
            self.assertNotIn("2.000200", menu["codes"])
            chosen, _ = self.clarifier.consume("2", menu)
            self.assertEqual(chosen["kind"], "section")
        self.assertEqual(self.clarifier.inspect("Thủ tục " + base)["kind"], "section")
        self.assertEqual(self.clarifier.inspect("Các thủ tục mã 2.000066")["kind"], "section")
        self.assertIsNone(self.clarifier.inspect("Hồ sơ " + base))
        self.assertIsNone(self.clarifier.inspect("Tổng quan " + base))
        menu = self.clarifier.inspect("Hồ sơ các thủ tục " + base)
        _, query = self.clarifier.consume("2", menu)
        self.assertIn("ho so", query)

    def test_section_words_inside_procedure_name_are_not_a_goal(self):
        add_procedure(self.retriever, "1.000005", "Cấp bản sao hồ sơ")
        del self.retriever._clarification_catalog
        self.clarifier = Clarifier(self.retriever)
        self.assertEqual(self.clarifier.inspect("Thủ tục cấp bản sao hồ sơ")["kind"], "section")
        self.assertIsNone(self.clarifier.inspect("Hồ sơ cấp bản sao hồ sơ"))

    def test_duplicate_names_require_selection_even_with_goal(self):
        add_procedure(self.retriever, "1.000004")
        del self.retriever._clarification_catalog
        self.clarifier = Clarifier(self.retriever)
        menu = self.clarifier.inspect("Hồ sơ đăng ký tạm trú")
        self.assertEqual(menu["kind"], "procedure")
        self.assertEqual(menu["codes"], ["1.000003", "1.000004"])
        self.assertIn("Công an xã", self.clarifier.render(menu))
        next_menu, query = self.clarifier.consume("2", menu)
        self.assertIsNone(next_menu)
        self.assertIn("Hồ sơ", query)
        self.assertIn("1.000004", query)
        self.assertIsNone(self.clarifier.inspect(query))

    def test_number_name_code_and_invalid_choices(self):
        menu = self.clarifier.menu("procedure", ["1.000001", "1.000003"])
        for answer in ("2", "Tôi chọn thủ tục 2", "Tôi chọn đăng kí tạm trú", "1.000003"):
            next_menu, query = self.clarifier.consume(answer, menu)
            self.assertEqual(next_menu["kind"], "section")
            self.assertEqual(next_menu["codes"], ["1.000003"])
            self.assertIsNone(query)
        for answer in ("0", "99", "mục 8"):
            self.assertEqual(self.clarifier.consume(answer, menu), (menu, None))
        sections = self.clarifier.menu("section", ["1.000003"])
        for answer in ("3", "hồ sơ", "Tôi muốn biết giấy tờ", "toàn bộ"):
            follow_menu, query = self.clarifier.consume(answer, sections)
            self.assertIsNone(follow_menu)
            self.assertIn("1.000003", query)
        _, query = self.clarifier.consume("Trình tự thực hiện và hồ sơ", sections)
        self.assertIn("Trình tự thực hiện và hồ sơ", query)
        from vigovbot.retrieval.retriever import preferred_section_types
        self.assertEqual(set(preferred_section_types(query)), {"procedure_step", "required_documents"})

    def test_new_subject_drops_pending_section(self):
        menu = self.clarifier.menu("section", ["1.000003"])
        self.assertEqual(self.clarifier.consume("Hồ sơ cấp hộ chiếu", menu), (None, None))
        self.assertEqual(self.clarifier.consume("Phí 9.999999", menu), (None, None))
        self.assertEqual(self.clarifier.consume("Thời tiết hôm nay", menu), (None, None))
        self.assertEqual(self.clarifier.consume("Hồ sơ nhập quốc tịch", menu), (None, None))
        self.assertEqual(self.clarifier.consume("Trình tự thực hiện nhập quốc tịch", menu), (None, None))

    def test_copied_numbered_section_matches_current_label(self):
        menu = self.clarifier.menu("section", ["1.000001"])
        for question in ("2. Cách thức nộp, thời hạn và phí", r"2\. Cách thức nộp, thời hạn và phí"):
            next_menu, query = self.clarifier.consume(question, menu)
            self.assertIsNone(next_menu)
            self.assertIn("Mã thủ tục: 1.000001", query)
            self.assertIn("Mục dữ liệu: submission_deadline_fee", query)
        self.assertEqual(self.clarifier.consume("1. Cách thức nộp, thời hạn và phí", menu), (menu, None))

    def test_copied_procedure_labels_include_code_and_authority_without_inventing_goal(self):
        menu = self.clarifier.menu("procedure", ["1.000001", "1.000003"])
        for label in self.clarifier.procedure_labels("1.000003"):
            for question in (f"2. {label}", f"2\\. {label}", label):
                with self.subTest(question=question):
                    selected, query = self.clarifier.consume(question, menu)
                    self.assertEqual(selected["kind"], "section")
                    self.assertEqual(selected["codes"], ["1.000003"])
                    self.assertIsNone(query)
                    selected, query = self.clarifier.consume(question, {**menu, "goal": "hồ sơ"})
                    self.assertIsNone(selected)
                    self.assertIn("hồ sơ", query)
                    self.assertNotIn("Cấp thực hiện", query)
        full = self.clarifier.procedure_labels("1.000003")[-1]
        for question in (f"1. {full}", f"2. {full.replace('1.000003', '1.000001')}",
                         f"2. {full.replace('Xã', 'Tỉnh')}"):
            self.assertEqual(self.clarifier.consume(question, menu), (menu, None))

    def test_recover_old_no_candidate_failure_but_not_new_subject(self):
        menu = self.clarifier.menu("section", ["1.000001"])
        history = self.history(menu)
        failure = self.clarifier.render(self.clarifier.menu("procedure", [], "hồ sơ"))
        history += [{"role": "user", "content": "2. Cách thức nộp, thời hạn và phí"},
                    {"role": "assistant", "content": failure},
                    {"role": "user", "content": "Hồ sơ, giấy tờ của thủ tục"},
                    {"role": "assistant", "content": failure}]
        self.assertEqual(self.clarifier.pending(history, None), menu)
        history[-2]["content"] = "Hồ sơ nhập quốc tịch"
        self.assertIsNone(self.clarifier.pending(history, None))

    def test_context_binds_history_corpus_model_and_cannot_be_forged(self):
        menu = self.clarifier.inspect("Đăng ký tạm trú")
        history = self.history(menu)
        context = self.clarifier.context(menu, [], history[0]["content"])
        self.assertIsNotNone(self.clarifier.pending(history, context))
        self.assertIsNone(self.clarifier.pending(history, {**context, "codes": ["1.000001"]}))
        self.assertIsNone(self.clarifier.pending(history[:-1], context))
        other_history = [{"role": "user", "content": "khác"}, *history]
        self.assertIsNone(self.clarifier.pending(other_history, context))
        self.assertIsNone(Clarifier(self.retriever, "rag-b").pending(history, context))
        self.clarifier.catalog = {**self.clarifier.catalog, "new": {}}
        self.assertIsNone(self.clarifier.pending(history, context))

    def test_legacy_history_rebuilds_menu_from_metadata(self):
        for menu in (self.clarifier.menu("procedure", ["1.000001", "1.000003"], "hồ sơ"),
                     self.clarifier.menu("section", ["1.000003"])):
            history = self.history(menu)
            self.assertEqual(self.clarifier.pending(history, None), menu)
            history[-1]["content"] = history[-1]["content"].replace("1.000003", "9.999999")
            self.assertIsNone(self.clarifier.pending(history, None))

    def test_semantic_candidates_need_name_overlap_and_confirmation(self):
        menu = self.clarifier.inspect("Xin đăng ký nơi tạm trú", hits=[
            {"source_code": "1.000001"}, {"source_code": "1.000003"}])
        self.assertEqual(menu["kind"], "procedure")
        self.assertEqual(menu["codes"], ["1.000003"])
        empty = self.clarifier.inspect("Thủ tục không tồn tại", hits=[{"source_code": "1.000001"}])
        self.assertEqual(empty["codes"], [])
        self.assertIn("Chưa tìm thấy", self.clarifier.render(empty))

    def test_limit_specific_name_and_unknown_code(self):
        for i in range(4, 10):
            add_procedure(self.retriever, f"1.00000{i}")
        add_procedure(self.retriever, "1.000010", "Đăng ký tạm trú cho người nước ngoài")
        del self.retriever._clarification_catalog
        self.clarifier = Clarifier(self.retriever)
        menu = self.clarifier.inspect("Đăng ký tạm trú")
        self.assertEqual(len(menu["codes"]), 5)
        self.assertTrue(menu["more"])
        self.assertEqual(self.clarifier.matches("Đăng ký tạm trú cho người nước ngoài"), ["1.000010"])
        self.assertIsNone(self.clarifier.inspect("Hồ sơ 9.999999"))


class ClarificationPipelineTests(unittest.TestCase):
    def setUp(self):
        from tests.dependencies import skip_missing_dependency
        try:
            from vigovbot.rag.pipeline import answer_question
        except ModuleNotFoundError as exc:
            skip_missing_dependency(exc)
        from tests.tokenizer_fixtures import CharacterTokenizer
        self.answer_question = answer_question
        self.tokenizer = CharacterTokenizer()
        self.retriever = fixture_retriever()
        self.addCleanup(self.retriever.close)
        add_procedure(self.retriever, "1.000003")
        self.settings = dict(top_k=5, num_ctx=8192, num_predict=512, max_chunk_tokens=1200,
                             routing_num_ctx=8192, routing_num_predict=128)

    def call(self, question, history=None, context=None, route=None, scope="a", retrieval_context=None):
        route = route or dict(scope="in_scope", relation="new_question", query=question, clarification="")
        def llm(messages, settings):
            output = (dict(answer="Thông tin theo nguồn", action="answer", evidence_status="sufficient")
                      if settings.get("response_schema_name") == "answer" else route)
            return json.dumps(output), {}, .01
        answer = Mock(side_effect=llm)
        result = self.answer_question(question, self.retriever, self.tokenizer, self.settings,
                                      history=history, clarification_context=context, clarification_scope=scope,
                                      retrieval_context=retrieval_context,
                                      answer_fn=answer)
        return result, answer

    def test_marriage_copied_fee_then_documents_keeps_procedure_despite_new_question_router(self):
        add_procedure(self.retriever, "1.000894", "Thủ tục đăng ký kết hôn", sections=(
            "metadata_identity", "procedure_step", "required_documents", "submission_deadline_fee", "legal_basis", "other"))
        question = "Thủ tục đăng ký kết hôn"
        result, _ = self.call(question)
        history = [{"role": "user", "content": question}, {"role": "assistant", "content": result["prediction"]}]
        fee = json.loads(self.retriever.db.execute(
            "SELECT payload FROM chunks WHERE json_extract(payload,'$.source_code')='1.000894' "
            "AND json_extract(payload,'$.section_type')='submission_deadline_fee'").fetchone()[0])
        for choice in ("4. Cách thức nộp, thời hạn và phí", r"4\. Cách thức nộp, thời hạn và phí"):
            with patch.object(self.retriever, "search", return_value=[fee]) as search:
                selected, answer = self.call(choice, history, result["clarification_context"])
            self.assertEqual(selected["action"], "answer")
            self.assertIn("1.000894", search.call_args.args[0])
            self.assertEqual(answer.call_count, 1)
            follow_history = [*history, {"role": "user", "content": choice},
                              {"role": "assistant", "content": selected["prediction"]}]
            with patch.object(self.retriever, "search", side_effect=AssertionError("must keep known procedure")):
                docs, _ = self.call("Hồ sơ, giấy tờ của thủ tục", follow_history,
                                    retrieval_context=selected["retrieval_context"])
            self.assertEqual(docs["action"], "answer")
            self.assertEqual(docs["routing"]["relation"], "follow_up")
            self.assertEqual(docs["retrieval_strategy"], "procedure_direct")
            self.assertEqual({h["source_code"] for h in docs["retrieved"]}, {"1.000894"})
            self.assertEqual({h["section_type"] for h in docs["retrieved"]}, {"required_documents"})

    def test_full_procedure_option_advances_to_sections_without_router_or_generation(self):
        codes = ["2.000037", "1.000187", "1.000183", "1.002551", "1.000180"]
        for code in codes:
            add_procedure(self.retriever, code, f"Cấp lại Chứng chỉ kiểm định viên {code}",
                          sections=("metadata_identity", "required_documents"))
        clarifier = Clarifier(self.retriever, "a")
        question = "Thủ tục cấp lại chứng chỉ kiểm địng viên"
        menu = clarifier.menu("procedure", codes)
        history = [{"role": "user", "content": question},
                   {"role": "assistant", "content": clarifier.render(menu)}]
        context = clarifier.context(menu, [], question)
        for index in (5, 1):
            label = clarifier.render(menu).splitlines()[index].replace(f"{index}.", f"{index}\\.", 1)
            for hint in (context, None):
                with patch.object(self.retriever, "search", side_effect=AssertionError("must not retrieve yet")):
                    result, llm = self.call(label, history, hint)
                self.assertEqual(result["decision_reason"], "section_required")
                self.assertEqual(result["clarification_context"]["codes"], [codes[index - 1]])
                llm.assert_not_called()

    def test_section_menu_skips_vectors_and_generation_then_answers_choice(self):
        with patch.object(self.retriever, "search", side_effect=AssertionError("not needed")):
            result, answer = self.call("Thủ tục đăng kí tạm trú ở Việt Nam")
        self.assertEqual(result["decision_reason"], "section_required")
        self.assertEqual(answer.call_count, 1)
        history = [{"role": "user", "content": "Thủ tục đăng kí tạm trú ở Việt Nam"},
                   {"role": "assistant", "content": result["prediction"]}]
        payload = json.loads(self.retriever.db.execute(
            "SELECT payload FROM chunks WHERE json_extract(payload,'$.source_code')='1.000003' "
            "AND json_extract(payload,'$.section_type')='required_documents'").fetchone()[0])
        for context in (result["clarification_context"], None):
            with patch.object(self.retriever, "search", return_value=[payload]) as search:
                follow, answer = self.call("2", history, context)
            self.assertEqual(follow["action"], "answer")
            self.assertIn("Hồ sơ", search.call_args.args[0])
            self.assertIn("1.000003", search.call_args.args[0])
            self.assertIsNone(follow["clarification_context"])
            self.assertEqual(answer.call_count, 1)

    def test_router_ambiguous_can_still_offer_real_sections(self):
        result, _ = self.call("Đăng ký tạm trú", route=dict(scope="in_scope", relation="ambiguous",
                                                          query="", clarification="Bạn muốn hỏi gì?"))
        self.assertEqual(result["decision_reason"], "section_required")

    def test_fasttext_new_question_still_passes_metadata_gate(self):
        routed = (dict(scope="in_scope", relation="new_question", query="Đăng ký tạm trú", clarification=""),
                  {"backend": "fasttext", "accepted": True}, .01, 0, 0, None)
        with patch("vigovbot.rag.pipeline.resolve_route", return_value=routed):
            result, answer = self.call("Đăng ký tạm trú")
        self.assertEqual(result["decision_reason"], "section_required")
        answer.assert_not_called()

    def test_invalid_signed_selection_does_not_reuse_another_model(self):
        result, _ = self.call("Đăng ký tạm trú")
        history = [{"role": "user", "content": "Đăng ký tạm trú"},
                   {"role": "assistant", "content": result["prediction"]}]
        with patch.object(self.retriever, "search", side_effect=AssertionError("invalid selection")):
            follow, answer = self.call("2", history, result["clarification_context"], scope="b")
        self.assertEqual(follow["action"], "clarify")
        self.assertIn("không còn hợp lệ", follow["prediction"])
        answer.assert_not_called()

    def test_semantic_menu_and_no_match_do_not_generate(self):
        for hits in ([{"source_code": "1.000003"}], []):
            with patch.object(self.retriever, "search", return_value=hits):
                result, answer = self.call("Đăng ký nơi tạm trú")
            self.assertEqual(result["action"], "clarify")
            self.assertEqual(result["decision_reason"], "procedure_required")
            self.assertEqual(answer.call_count, 1)

    def test_out_of_scope_is_not_a_procedure_menu(self):
        result, _ = self.call("Viết thơ", route=dict(scope="out_of_scope", relation="new_question", query="", clarification=""))
        self.assertEqual(result["decision_reason"], "out_of_scope")
        self.assertIsNone(result["clarification_context"])

    def test_mixed_menu_preserves_only_supported_goal_and_scope(self):
        add_procedure(self.retriever, "1.000004")
        question = "Hồ sơ đăng ký tạm trú và viết thơ"
        result, _ = self.call(question, route=dict(scope="mixed", relation="new_question",
                                                  query="Hồ sơ đăng ký tạm trú", clarification=""))
        self.assertNotIn("viết thơ", result["prediction"])
        self.assertIn("ngoài phạm vi", result["prediction"])
        self.assertEqual(result["clarification_context"]["goal"], "Hồ sơ đăng ký tạm trú")

    def test_unknown_section_can_be_selected_without_another_menu(self):
        add_procedure(self.retriever, "1.000004", "Thủ tục đặc biệt", sections=("custom_section",))
        result, _ = self.call("Thủ tục đặc biệt")
        history = [{"role": "user", "content": "Thủ tục đặc biệt"},
                   {"role": "assistant", "content": result["prediction"]}]
        payload = json.loads(self.retriever.db.execute(
            "SELECT payload FROM chunks WHERE json_extract(payload,'$.source_code')='1.000004'").fetchone()[0])
        with patch.object(self.retriever, "search", return_value=[payload]) as search:
            follow, _ = self.call("1", history, result["clarification_context"])
        self.assertEqual(follow["action"], "answer")
        from vigovbot.retrieval.retriever import preferred_section_types
        self.assertIn("custom_section", preferred_section_types(search.call_args.args[0]))

    def test_two_stage_menu_retains_context_and_invalid_number_repeats(self):
        add_procedure(self.retriever, "1.000004")
        result, _ = self.call("Đăng ký tạm trú")
        history = [{"role": "user", "content": "Đăng ký tạm trú"},
                   {"role": "assistant", "content": result["prediction"]}]
        repeated, answer = self.call("99", history, result["clarification_context"])
        self.assertEqual(repeated["prediction"], result["prediction"])
        answer.assert_not_called()
        history += [{"role": "user", "content": "99"}, {"role": "assistant", "content": repeated["prediction"]}]
        section, answer = self.call("2", history, repeated["clarification_context"])
        self.assertEqual(section["decision_reason"], "section_required")
        self.assertEqual(section["clarification_context"]["codes"], ["1.000004"])
        answer.assert_not_called()

    def test_http_normal_menu_then_stream_selection(self):
        import sqlite3
        import threading
        from types import SimpleNamespace
        import requests
        from tests.http_server import HTTPServer
        from vigovbot.server.app import ChatApplication, create_asgi_app
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.retriever.db.commit()
        self.retriever.db.backup(connection)
        self.retriever.db.close()
        self.retriever.db = connection
        model = SimpleNamespace(id="rag", label="RAG", provider="openai_compatible", mode="rag",
                                model="fixture", base_url="http://unused", api_key_env=None)
        config = SimpleNamespace(web=SimpleNamespace(models=[model]), inference_settings=lambda: self.settings)
        app = ChatApplication(config, self.retriever, self.tokenizer)
        server = HTTPServer(("127.0.0.1", 0), create_asgi_app(app))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def llm(messages, settings):
            output = (dict(answer="Hồ sơ theo nguồn", action="answer", evidence_status="sufficient")
                      if settings.get("response_schema_name") == "answer" else
                      dict(scope="in_scope", relation="new_question", query="Đăng ký tạm trú", clarification=""))
            return json.dumps(output), {}, .01
        payload = json.loads(connection.execute(
            "SELECT payload FROM chunks WHERE json_extract(payload,'$.source_code')='1.000003' "
            "AND json_extract(payload,'$.section_type')='required_documents'").fetchone()[0])
        try:
            url = f"http://127.0.0.1:{server.server_port}"
            with patch("vigovbot.server.app.answerer_for", return_value=llm), \
                    patch.object(self.retriever, "search", return_value=[payload]):
                response = requests.post(url + "/api/chat", json={"question": "Đăng ký tạm trú"}, timeout=10)
                self.assertEqual(response.status_code, 200)
                result = response.json()["results"][0]
                self.assertEqual(result["action"], "clarify")
                history = [{"role": "user", "content": "Đăng ký tạm trú"},
                           {"role": "assistant", "content": result["answer"]}]
                response = requests.post(url + "/api/chat/stream", json={
                    "question": "2", "histories": {"rag": history},
                    "clarification_contexts": {"rag": result["clarification_context"]}}, timeout=10)
                self.assertEqual(response.status_code, 200)
                events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
                final = next(e["result"] for e in events if e["type"] == "model_result")
                self.assertEqual(final["action"], "answer")
                self.assertIsNone(final["clarification_context"])
                self.assertEqual(final["sources"][0]["source_code"], "1.000003")
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
