from tests.dependencies import skip_missing_dependency
import unittest


class DependencyGuardTests(unittest.TestCase):
    def test_known_external_dependency_skips(self):
        with self.assertRaisesRegex(unittest.SkipTest, "filelock"):
            skip_missing_dependency(ModuleNotFoundError(name="filelock"))

    def test_internal_and_unknown_dependencies_remain_errors(self):
        for name in ("vigovbot.missing", "unknown_library", "pydantic.missing"):
            with self.assertRaises(ModuleNotFoundError):
                skip_missing_dependency(ModuleNotFoundError(name=name))
