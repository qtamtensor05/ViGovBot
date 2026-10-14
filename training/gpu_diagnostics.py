from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path


def _nvidia_smi() -> dict[str, str | int]:
    fields = "name,driver_version,memory.total,memory.free,compute_cap"
    result = subprocess.run(
        ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
    )
    values = [value.strip() for value in result.stdout.strip().split(",")]
    return {
        "name": values[0],
        "driver_version": values[1],
        "memory_total_mib": int(values[2]),
        "memory_free_mib": int(values[3]),
        "compute_capability": values[4],
    }


def run_diagnostics() -> dict:
    import bitsandbytes as bnb
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    device = torch.device("cuda:0")
    torch.cuda.reset_peak_memory_stats(device)

    matrix = torch.randn(1024, 1024, device=device)
    product = matrix @ matrix
    torch.cuda.synchronize(device)

    layer = bnb.nn.Linear4bit(
        128,
        64,
        bias=True,
        compute_dtype=torch.bfloat16,
        compress_statistics=True,
        quant_type="nf4",
    ).to(device)
    inputs = torch.randn(8, 128, device=device, dtype=torch.bfloat16, requires_grad=True)
    loss = layer(inputs).float().square().mean()
    loss.backward()
    torch.cuda.synchronize(device)
    quant_state = getattr(layer.weight, "quant_state", None)

    parameter = torch.nn.Parameter(torch.randn(8192, device=device))
    optimizer = bnb.optim.PagedAdamW8bit([parameter], lr=1e-3, min_8bit_size=1)
    optimizer.zero_grad(set_to_none=True)
    optimizer_loss = parameter.square().mean()
    optimizer_loss.backward()
    optimizer.step()
    torch.cuda.synchronize(device)
    optimizer_state = optimizer.state[parameter]

    return {
        "status": "PASS",
        "python": sys.version,
        "platform": platform.platform(),
        "nvidia_smi": _nvidia_smi(),
        "pytorch": {
            "version": torch.__version__,
            "cuda_runtime": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "gpu": torch.cuda.get_device_name(device),
            "compute_capability": list(torch.cuda.get_device_capability(device)),
            "bf16_supported": torch.cuda.is_bf16_supported(),
            "compiled_architectures": torch.cuda.get_arch_list(),
            "matrix_multiplication_shape": list(product.shape),
        },
        "bitsandbytes": {
            "version": bnb.__version__,
            "nf4_forward_backward": bool(torch.isfinite(loss).item() and inputs.grad is not None),
            "loss": float(loss.detach()),
            "double_quantization": bool(quant_state is not None and getattr(quant_state, "nested", False)),
            "compute_dtype": str(layer.compute_dtype),
            "weight_storage_dtype": str(layer.weight.dtype),
            "paged_adamw_8bit_step": bool(torch.isfinite(optimizer_loss).item()),
            "optimizer_state_dtypes": {
                key: str(value.dtype) for key, value in optimizer_state.items() if torch.is_tensor(value)
            },
        },
        "peak_memory": {
            "allocated_bytes": torch.cuda.max_memory_allocated(device),
            "reserved_bytes": torch.cuda.max_memory_reserved(device),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_diagnostics()
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
