from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EarlyStoppingState:
    patience: int
    threshold: float
    best_loss: float | None = None
    best_step: int | None = None
    bad_evaluations: int = 0
    stopped_step: int | None = None

    def update(self, loss: float, step: int) -> bool:
        if self.best_loss is None or loss < self.best_loss - self.threshold:
            self.best_loss, self.best_step, self.bad_evaluations = loss, step, 0
            return False
        self.bad_evaluations += 1
        if self.bad_evaluations >= self.patience:
            self.stopped_step = step
            return True
        return False


def select_best_checkpoint(log_history: list[dict]) -> tuple[int, float] | None:
    observed = [(int(item["step"]), float(item["eval_loss"])) for item in log_history if "eval_loss" in item]
    return min(observed, key=lambda item: item[1]) if observed else None
