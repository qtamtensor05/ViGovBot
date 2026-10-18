from tests.dependencies import skip_missing_dependency  # noqa: F401
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from vigovbot.evaluation.execution import ExecutionEngine, RetryPolicy


class ExecutionTests(unittest.TestCase):
    def test_default_never_retries_and_programming_errors_are_not_retried(self):
        for policy, error in [(None, TimeoutError()), (RetryPolicy(3), ValueError("invalid"))]:
            function = Mock(side_effect=error)
            with self.assertRaises(type(error)):
                ExecutionEngine(policy).call(function)
            self.assertEqual(function.call_count, 1)

    def test_rate_limit_retry_after_is_bounded(self):
        error = RuntimeError("rate limited")
        error.response = SimpleNamespace(status_code=429, headers={"Retry-After": "999"})
        function = Mock(side_effect=[error, {"answer": "ok"}])
        sleep = Mock()
        result = ExecutionEngine(RetryPolicy(2, max_delay_seconds=3), sleep=sleep).call(function)
        self.assertEqual(result, {"answer": "ok"})
        sleep.assert_called_once_with(3)

    def test_retry_exhaustion_and_invalid_policy(self):
        function = Mock(side_effect=TimeoutError())
        with self.assertRaises(TimeoutError):
            ExecutionEngine(RetryPolicy(2, 0), sleep=Mock()).call(function)
        self.assertEqual(function.call_count, 2)
        for kwargs in ({"max_attempts": 0}, {"max_attempts": True}, {"backoff_seconds": float("nan")}):
            with self.assertRaises(ValueError):
                RetryPolicy(**kwargs)

    def test_scheduler_preserves_sequential_state_and_parallel_results(self):
        seen = []
        def step(value):
            seen.append(value)
            return len(seen)
        self.assertEqual(list(ExecutionEngine().map(step, [1, 2, 3])), [1, 2, 3])
        self.assertEqual(seen, [1, 2, 3])
        self.assertEqual(sorted(ExecutionEngine().map(lambda x: x * 2, [1, 2, 3], concurrency=2)), [2, 4, 6])

    def test_all_adapters_apply_shared_retry_policy(self):
        try:
            from vigovbot.evaluation.runner import evaluate_cases
            from vigovbot.evaluation.multiturn import evaluate_multiturn
            from vigovbot.evaluation.benchmark_runner import run_queries
        except ModuleNotFoundError as error:
            skip_missing_dependency(error)
        policy = RetryPolicy(2, 0)
        query = {"id": "a", "question": "q", "history": [], "conversation_id": None, "turn_index": None}
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            legacy = Mock(side_effect=[TimeoutError(), {"prediction": "ok"}])
            rows = evaluate_cases([{"id": "a", "question": {"text": "q"}, "ground_truth": {"answer": "gold"}}],
                                  root / "legacy", {"settings": {"model": "fake"}}, legacy, retry_policy=policy)
            self.assertEqual(rows[0]["prediction"], "ok")
            multi = Mock(side_effect=[TimeoutError(), {"prediction": "ok"}])
            report = evaluate_multiturn([query], root / "multi", {}, multi, retry_policy=policy)
            self.assertEqual(report["successful"], 1)
            # Resume reads persisted output without invoking the model again.
            evaluate_multiturn([query], root / "multi", {}, multi, retry_policy=policy)
            self.assertEqual(multi.call_count, 2)
            benchmark = Mock(side_effect=[TimeoutError(), {"answer": "ok"}])
            report = run_queries([query], benchmark, root / "benchmark.jsonl", retry_policy=policy)
            self.assertEqual(report["successful"], 1)
            for function in (legacy, multi, benchmark):
                self.assertEqual(function.call_count, 2)
