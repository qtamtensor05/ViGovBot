import unittest

import numpy as np

from vigovbot.retrieval.procedure_discovery import ProcedureDiscovery


class ProcedureDiscoveryTests(unittest.TestCase):
    def test_missing_negative_qualifier_is_penalized_asymmetrically(self):
        discovery = ProcedureDiscovery([
            {"code": "foreign", "name": "Đổi bằng lái xe của người nước ngoài", "aliases": []},
            {"code": "general", "name": "Đổi cấp lại giấy phép lái xe",
             "aliases": ["đổi bằng lái xe máy"]},
        ], np.asarray([[1., 0.], [1., 0.]], dtype=np.float32))
        candidates = discovery.search("đổi bằng lái xe máy", np.asarray([1., 0.]))
        self.assertEqual(candidates[0]["code"], "general")
        foreign = next(candidate for candidate in candidates if candidate["code"] == "foreign")
        self.assertEqual(foreign["qualifier_penalty"], .5)
        self.assertEqual(foreign["missing_qualifiers"], ["người nước ngoài"])

    def test_qualifier_present_does_not_receive_penalty(self):
        discovery = ProcedureDiscovery([
            {"code": "foreign", "name": "Đổi bằng lái xe của người nước ngoài", "aliases": []},
            {"code": "general", "name": "Đổi giấy phép lái xe", "aliases": []},
        ], np.asarray([[1., 0.], [.7, .3]], dtype=np.float32))
        candidates = discovery.search("đổi bằng lái xe người nước ngoài", np.asarray([1., 0.]))
        foreign = next(candidate for candidate in candidates if candidate["code"] == "foreign")
        self.assertEqual(foreign["qualifier_penalty"], 1.0)
        self.assertEqual(foreign["missing_qualifiers"], [])


if __name__ == "__main__":
    unittest.main()
