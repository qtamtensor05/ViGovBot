from tests.dependencies import skip_missing_dependency  # noqa: F401
import unittest
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
