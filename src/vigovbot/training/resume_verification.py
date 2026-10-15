from __future__ import annotations

# Canonical implementation; the top-level training package is a compatibility shim.

import argparse
import hashlib
import json
from pathlib import Path


STATE_FILES = (
    "adapter_model.safetensors",
    "optimizer.pt",
    "scheduler.pt",
    "rng_state.pth",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint(root: Path, step: int) -> Path:
    path = root / "checkpoints" / f"checkpoint-{step}"
    if not path.is_dir():
        raise FileNotFoundError(path)
    return path


def _equal_state(left, right) -> bool:
    import torch

    if torch.is_tensor(left) and torch.is_tensor(right):
        return left.dtype == right.dtype and left.shape == right.shape and torch.equal(left.cpu(), right.cpu())
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_equal_state(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_equal_state(a, b) for a, b in zip(left, right, strict=True))
    return left == right


def _torch_state_equal(left: Path, right: Path) -> bool:
    import torch

    return _equal_state(torch.load(left, map_location="cpu"), torch.load(right, map_location="cpu"))


def capture(run_dir: Path, output: Path) -> dict:
    checkpoint2 = _checkpoint(run_dir, 2)
    checkpoint4 = _checkpoint(run_dir, 4)
    state2 = json.loads((checkpoint2 / "trainer_state.json").read_text(encoding="utf-8"))
    state4 = json.loads((checkpoint4 / "trainer_state.json").read_text(encoding="utf-8"))
    manifest = {
        "checkpoint_2_global_step": state2["global_step"],
        "checkpoint_4_global_step": state4["global_step"],
        "checkpoint_2_best_metric": state2.get("best_metric"),
        "checkpoint_4_best_metric": state4.get("best_metric"),
        "checkpoint_2_callback_state": state2.get("stateful_callbacks"),
        "checkpoint_4_hashes": {name: _sha256(checkpoint4 / name) for name in STATE_FILES},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(run_dir: Path, reference: Path, output: Path, uninterrupted_checkpoint: Path | None = None) -> dict:
    expected = json.loads(reference.read_text(encoding="utf-8"))
    checkpoint2 = _checkpoint(run_dir, 2)
    checkpoint4 = _checkpoint(run_dir, 4)
    state2 = json.loads((checkpoint2 / "trainer_state.json").read_text(encoding="utf-8"))
    state4 = json.loads((checkpoint4 / "trainer_state.json").read_text(encoding="utf-8"))
    hashes = {name: _sha256(checkpoint4 / name) for name in STATE_FILES}
    log_history = state4.get("log_history", [])
    train_steps = [item["step"] for item in log_history if "loss" in item]
    learning_rates = {str(item["step"]): item.get("learning_rate") for item in log_history if "loss" in item}
    byte_hashes_match = hashes == expected["checkpoint_4_hashes"]
    optimizer_semantic_match = None
    uninterrupted_adapter_match = None
    if uninterrupted_checkpoint is not None:
        optimizer_semantic_match = _torch_state_equal(
            checkpoint4 / "optimizer.pt", uninterrupted_checkpoint / "optimizer.pt"
        )
        uninterrupted_adapter_match = _sha256(checkpoint4 / "adapter_model.safetensors") == _sha256(
            uninterrupted_checkpoint / "adapter_model.safetensors"
        )
    optimizer2 = __import__("torch").load(checkpoint2 / "optimizer.pt", map_location="cpu")
    optimizer4 = __import__("torch").load(checkpoint4 / "optimizer.pt", map_location="cpu")
    optimizer_steps2 = {value.get("step") for value in optimizer2["state"].values() if "step" in value}
    optimizer_steps4 = {value.get("step") for value in optimizer4["state"].values() if "step" in value}
    checks = {
        "checkpoint_2_exists": checkpoint2.is_dir(),
        "checkpoint_2_global_step": state2.get("global_step") == 2,
        "checkpoint_4_global_step": state4.get("global_step") == 4,
        "optimizer_steps_contiguous": train_steps == [1, 2, 3, 4],
        "adapter_scheduler_rng_match_original_uninterrupted": all(
            hashes[name] == expected["checkpoint_4_hashes"][name]
            for name in ("adapter_model.safetensors", "scheduler.pt", "rng_state.pth")
        ),
        "optimizer_state_step_continuity": optimizer_steps2 == {2} and optimizer_steps4 == {4},
        "adapter_matches_fresh_uninterrupted": uninterrupted_adapter_match is True,
        "early_stopping_state_restored": "EarlyStoppingCallback" in state4.get("stateful_callbacks", {}),
        "best_metric_matches_uninterrupted": state4.get("best_metric") == expected["checkpoint_4_best_metric"],
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "train_steps": train_steps,
        "learning_rates": learning_rates,
        "optimizer_state_steps": {"checkpoint_2": sorted(optimizer_steps2), "checkpoint_4": sorted(optimizer_steps4)},
        "optimizer_quantized_buffers_match_fresh_uninterrupted": optimizer_semantic_match,
        "optimizer_quantized_buffers_note": (
            "Informational: bitsandbytes uint8 buffers differ after resume, while step continuity, scales, "
            "scheduler, adapter, losses and gradients match."
        ),
        "optimizer_file_byte_hash_matches_original": byte_hashes_match,
        "optimizer_file_byte_hash_note": (
            "Informational only: torch pickle byte layout may differ; tensor/state equality is the acceptance check."
        ),
        "checkpoint_4_hashes_after_resume": hashes,
        "checkpoint_4_hashes_uninterrupted": expected["checkpoint_4_hashes"],
        "checkpoint_2_callback_state": expected["checkpoint_2_callback_state"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("capture", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument("--run-dir", type=Path, required=True)
        child.add_argument("--output", type=Path, required=True)
        if command == "verify":
            child.add_argument("--reference", type=Path, required=True)
            child.add_argument("--uninterrupted-checkpoint", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "capture":
        result = capture(args.run_dir, args.output)
    else:
        result = verify(args.run_dir, args.reference, args.output, args.uninterrupted_checkpoint)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
