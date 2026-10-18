"""Shared scheduling, bounded retry and progress events for evaluation adapters.

Adapters own wire formats, persistence and conversation state. The default makes
one attempt, preserving historical request counts; retries require explicit opt-in.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import logging
import math
import time

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    backoff_seconds: float = 1.0
    max_delay_seconds: float = 60.0

    def __post_init__(self):
        if type(self.max_attempts) is not int or self.max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        if any(not math.isfinite(value) or value < 0
               for value in (self.backoff_seconds, self.max_delay_seconds)):
            raise ValueError("Retry delays must be finite and non-negative")

    def manifest(self):
        return asdict(self)


def _retry_delay(error, policy, attempt):
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None) or getattr(error, "status_code", None)
    if status not in {429, 502, 503, 504} and not isinstance(error, (TimeoutError, ConnectionError)):
        return None
    delay = min(policy.backoff_seconds * (2 ** min(attempt - 1, 30)), policy.max_delay_seconds)
    headers = getattr(response, "headers", {}) or {}
    try:
        retry_after = float(headers.get("Retry-After", delay))
        if math.isfinite(retry_after):
            delay = min(max(0.0, retry_after), policy.max_delay_seconds)
    except (ValueError, TypeError):
        pass
    return delay


class ExecutionEngine:
    def __init__(self, retry_policy: RetryPolicy | None = None, *, sleep=time.sleep):
        self.retry_policy = retry_policy or RetryPolicy()
        self.sleep = sleep

    def call(self, function, *args, **kwargs):
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                return function(*args, **kwargs)
            except Exception as error:
                delay = _retry_delay(error, self.retry_policy, attempt)
                if delay is None or attempt == self.retry_policy.max_attempts:
                    raise
                LOG.info("evaluation retry attempt=%s delay_seconds=%s", attempt, delay)
                self.sleep(delay)

    def map(self, function, jobs, *, concurrency=1):
        """Yield completed jobs; sequential mode preserves stateful adapter ordering."""
        if type(concurrency) is not int or concurrency < 1:
            raise ValueError("concurrency must be a positive integer")
        jobs = list(jobs)
        if concurrency == 1:
            for completed, job in enumerate(jobs, 1):
                result = function(job)
                LOG.info("evaluation progress completed=%s total=%s", completed, len(jobs))
                yield result
        else:
            with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="eva") as executor:
                futures = [executor.submit(function, job) for job in jobs]
                for completed, future in enumerate(as_completed(futures), 1):
                    result = future.result()
                    LOG.info("evaluation progress completed=%s total=%s", completed, len(jobs))
                    yield result
