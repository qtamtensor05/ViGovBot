import re
import threading
import unittest

from vigovbot.retrieval.retriever import Retriever, _contains_phrase, preferred_section_types


def _retriever(names, levels=None):
    retriever = Retriever.__new__(Retriever)
    retriever._db_lock = threading.Lock()
    retriever._procedure_names = tuple(names)
    retriever._procedure_levels = dict(levels or {})
    return retriever


CAP_MOI = ("1.000148", "cap chung chi kiem dinh vien")
CAP_LAI = ("2.000066", "cap lai chung chi kiem dinh vien")


class ProcedureNameMatchTests(unittest.TestCase):
    def test_question_without_diacritics_style_matches_full_name(self):
        retriever = _retriever([CAP_MOI, CAP_LAI])
        self.assertEqual(
            retriever._procedure_name_codes("thủ tục cấp chứng chỉ kiểm định viên"), ["1.000148"]
        )
        self.assertEqual(
            retriever._procedure_name_codes("CẤP CHỨNG CHỈ KIỂM ĐỊNH VIÊN"), ["1.000148"]
        )

    def test_reissue_question_matches_only_reissue_procedure(self):
        retriever = _retriever([CAP_MOI, CAP_LAI])
        self.assertEqual(
            retriever._procedure_name_codes("thủ tục cấp lại chứng chỉ kiểm định viên"), ["2.000066"]
        )

    def test_question_without_procedure_name_returns_empty(self):
        retriever = _retriever([CAP_MOI])
        self.assertEqual(
            retriever._procedure_name_codes("Cần những giấy tờ gì để cấp bản sao hộ tịch?"), []
        )

    def test_short_phrase_does_not_match_longer_procedure_name(self):
        retriever = _retriever([CAP_MOI])
        self.assertEqual(retriever._procedure_name_codes("kiểm định viên cần gì"), [])

    def test_embedded_partial_word_does_not_match(self):
        retriever = _retriever([CAP_MOI])
        self.assertEqual(retriever._procedure_name_codes("cấp chứng chỉ kiểm định viênx"), [])

    def test_too_many_matches_falls_back_to_semantic_search(self):
        names = [(f"9.00000{i}", f"thu tuc mau {i}") for i in range(9)]
        retriever = _retriever(names)
        question = " ".join(name for _, name in names)
        self.assertEqual(retriever._procedure_name_codes(question), [])


class WordBoundaryTests(unittest.TestCase):
    def test_matches_whole_phrase_only(self):
        phrase = "cap chung chi kiem dinh vien"
        self.assertTrue(_contains_phrase("thu tuc cap chung chi kiem dinh vien", phrase))
        self.assertTrue(_contains_phrase("cap chung chi kiem dinh vien", phrase))
        self.assertFalse(_contains_phrase("cap chung chi kiem dinh vienx", phrase))
        self.assertFalse(_contains_phrase("xcap chung chi kiem dinh vien", phrase))

    def test_matches_later_occurrence_after_partial_one(self):
        self.assertTrue(_contains_phrase("cap cap chung chi kiem dinh vien", "cap chung chi kiem dinh vien"))

    def test_equivalent_to_regex_on_sample_pairs(self):
        samples = [
            ("a cap chung chi kiem dinh vien b", "cap chung chi kiem dinh vien"),
            ("cap chung chi kiem dinh vien", "cap chung chi kiem dinh vien"),
            ("cap chung chi kiem dinh vien1", "cap chung chi kiem dinh vien"),
            ("_cap chung chi kiem dinh vien", "cap chung chi kiem dinh vien"),
            ("tang cap chung chi", "cap chung"),
            ("cap-chung chi", "cap chung"),
        ]
        for folded, phrase in samples:
            expected = re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", folded) is not None
            self.assertEqual(_contains_phrase(folded, phrase), expected, (folded, phrase))


class DuplicateNameTests(unittest.TestCase):
    DUP = [
        ("1.000148", "cap chung chi kiem dinh vien"),
        ("2.000140", "cap chung chi kiem dinh vien"),
    ]

    def test_broader_implementation_level_does_not_choose_for_user(self):
        retriever = _retriever(
            self.DUP, {"1.000148": {"Tỉnh", "Bộ"}, "2.000140": {"Tỉnh"}}
        )
        self.assertEqual(
            retriever._procedure_name_codes("thủ tục cấp chứng chỉ kiểm định viên"), ["1.000148", "2.000140"]
        )

    def test_equal_implementation_levels_keep_both_codes(self):
        retriever = _retriever(self.DUP, {"1.000148": {"Tỉnh"}, "2.000140": {"Tỉnh"}})
        self.assertEqual(
            sorted(retriever._procedure_name_codes("thủ tục cấp chứng chỉ kiểm định viên")),
            ["1.000148", "2.000140"],
        )

    def test_missing_level_metadata_keeps_both_codes(self):
        retriever = _retriever(self.DUP)
        self.assertEqual(
            sorted(retriever._procedure_name_codes("thủ tục cấp chứng chỉ kiểm định viên")),
            ["1.000148", "2.000140"],
        )

    def test_duplicate_group_over_threshold_falls_back(self):
        names = [(f"9.00000{i}", "thu tuc trung ten") for i in range(9)]
        retriever = _retriever(names, {code: {"Tỉnh"} for code, _ in names})
        self.assertEqual(retriever._procedure_name_codes("thu tuc trung ten"), [])


class SectionIntentTests(unittest.TestCase):
    def test_documents_keyword_still_maps_to_required_documents(self):
        self.assertEqual(preferred_section_types("thành phần hồ sơ gồm gì"), ("required_documents",))

    def test_plain_procedure_question_has_no_section_priority(self):
        self.assertEqual(preferred_section_types("thủ tục cấp chứng chỉ kiểm định viên"), ())


if __name__ == "__main__":
    unittest.main()
