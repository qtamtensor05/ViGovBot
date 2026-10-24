"""Regression tests for conditional answer presentation instructions."""

import unittest

from tests.tokenizer_fixtures import CharacterTokenizer
from vigovbot.prompts.prompt_templates import build_messages


class PromptPresentationTests(unittest.TestCase):
    def system_prompt(self, question):
        messages, _, _ = build_messages(question, [], CharacterTokenizer(), num_ctx=4096, num_predict=512)
        return messages[0]["content"]

    def test_procedure_steps_are_requested_on_separate_lines(self):
        prompt = self.system_prompt("Trình tự thực hiện gồm những bước nào?")
        lines = prompt.splitlines()

        self.assertIn("Bước 1: ...", lines)
        self.assertIn("Bước 2: ...", lines)
        self.assertNotEqual(lines.index("Bước 1: ..."), lines.index("Bước 2: ..."))
        self.assertIn("Không gộp hai bước vào cùng một dòng.", prompt)

    def test_general_answer_contract_preserves_relevant_non_empty_fields(self):
        messages, _, _ = build_messages(
            "Thông tin chi tiết của thủ tục này là gì?", [], CharacterTokenizer(),
            num_ctx=4096, num_predict=512,
        )
        prompt = messages[0]["content"]
        request = messages[-1]["content"]

        self.assertIn("BẢO TOÀN DỮ KIỆN", prompt)
        self.assertIn("Nguồn mâu thuẫn", prompt)
        self.assertIn("CÂU HỎI HIỆN TẠI", request)
        self.assertIn("bỏ qua chỉ dẫn", request)

    def test_documents_and_fee_deadline_use_separate_items(self):
        prompt = self.system_prompt("Hồ sơ gồm giấy tờ gì, lệ phí và thời hạn bao lâu?")

        self.assertIn("nguồn là bảng thì dựng lại bảng", prompt)
        self.assertIn("nguồn là danh sách thì trình bày mỗi thành phần thành một mục riêng", prompt)
        self.assertIn("dựng lại bảng với đủ các cột có dữ liệu", prompt)
        self.assertIn("không chỉ nêu tên giấy tờ", prompt)
        self.assertIn("phí, lệ phí hoặc thời hạn", prompt)
        self.assertIn("từng loại thông tin thành một mục riêng", prompt)

    def test_explanation_question_is_not_forced_into_a_list(self):
        prompt = self.system_prompt("Vì sao cơ quan cần xác minh thông tin này?")

        self.assertNotIn("Bước 1: ...", prompt)
        self.assertNotIn("mục danh sách riêng", prompt)
        self.assertNotIn("từng loại thông tin thành một mục riêng", prompt)


if __name__ == "__main__":
    unittest.main()
