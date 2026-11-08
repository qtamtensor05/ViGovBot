# QLoRA experiment report: qlora-rag-sft-2048-001

> Missing measurements are explicitly marked unavailable; no values were invented.

## Artifact availability

| Measurement | Artifact | Status |
|---|---|---|
| Training status and losses | `metrics\training_metrics.json` | available |
| Continuous metric history | `logs\training_events.jsonl` | available |
| Epoch timing | `logs\epoch_metrics.jsonl` | available |
| Model parameters | `metrics\parameter_report.json` | available |
| Environment, dependencies, GPU, Git and dataset hashes | `environment.json` | available |
| Effective hyperparameters | `config.yaml` | available |
| Test loss, perplexity and generation metrics | `evaluation_results_test.json` | unavailable |
| Baseline test predictions | `baseline_predictions_test.jsonl` | unavailable |
| Fine-tuned test predictions | `finetuned_predictions_test.jsonl` | unavailable |
| Checkpoint metadata | `checkpoint_metadata.json` | unavailable |
| Resume history | `logs\resume_history.jsonl` | available |
| Plot manifest | `plots\plot_manifest.json` | available |

## Training

```json
{
  "status": "failed",
  "stopping_reason": "exception",
  "error_type": "PermissionError",
  "error_message": "[WinError 5] Access is denied: 'outputs\\\\qlora\\\\qlora-rag-sft-2048-001\\\\live_status.json.12112.tmp' -> 'outputs\\\\qlora\\\\qlora-rag-sft-2048-001\\\\live_status.json'",
  "wall_clock_seconds": 26161.3325213,
  "global_step": 675,
  "best_checkpoint": "outputs/qlora/qlora-rag-sft-2048-001/checkpoints/checkpoint-600",
  "peak_gpu_allocated_bytes_measured": 13813004800,
  "peak_gpu_reserved_bytes_measured": 22624075776
}
```

## Evaluation (held-out test)

```json
{
  "status": "unavailable",
  "reason": "artifact not generated"
}
```

## Parameters

```json
{
  "total_parameters": 4393342464,
  "trainable_lora_parameters": 40370176,
  "frozen_parameters": 4352972288,
  "trainable_percentage": 0.918894357332759,
  "parameter_reduction_vs_full_finetuning": 0.9908110564266724,
  "total_base_model_parameters": 4352972288,
  "trainable_parameter_names": [
    "base_model.model.model.layers.0.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.0.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.0.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.0.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.0.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.0.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.0.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.0.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.0.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.0.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.0.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.0.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.0.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.0.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.1.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.1.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.1.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.1.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.1.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.1.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.1.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.1.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.1.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.1.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.1.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.1.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.1.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.1.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.2.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.2.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.2.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.2.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.2.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.2.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.2.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.2.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.2.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.2.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.2.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.2.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.2.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.2.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.3.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.3.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.3.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.3.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.3.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.3.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.3.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.3.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.3.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.3.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.3.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.3.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.3.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.3.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.4.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.4.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.4.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.4.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.4.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.4.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.4.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.4.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.4.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.4.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.4.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.4.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.4.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.4.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.5.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.5.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.5.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.5.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.5.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.5.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.5.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.5.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.5.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.5.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.5.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.5.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.5.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.5.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.6.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.6.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.6.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.6.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.6.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.6.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.6.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.6.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.6.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.6.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.6.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.6.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.6.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.6.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.7.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.7.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.7.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.7.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.7.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.7.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.7.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.7.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.7.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.7.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.7.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.7.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.7.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.7.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.8.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.8.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.8.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.8.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.8.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.8.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.8.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.8.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.8.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.8.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.8.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.8.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.8.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.8.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.9.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.9.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.9.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.9.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.9.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.9.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.9.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.9.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.9.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.9.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.9.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.9.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.9.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.9.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.10.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.10.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.10.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.10.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.10.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.10.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.10.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.10.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.10.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.10.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.10.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.10.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.10.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.10.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.11.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.11.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.11.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.11.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.11.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.11.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.11.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.11.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.11.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.11.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.11.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.11.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.11.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.11.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.12.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.12.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.12.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.12.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.12.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.12.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.12.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.12.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.12.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.12.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.12.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.12.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.12.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.12.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.13.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.13.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.13.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.13.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.13.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.13.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.13.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.13.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.13.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.13.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.13.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.13.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.13.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.13.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.14.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.14.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.14.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.14.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.14.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.14.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.14.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.14.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.14.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.14.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.14.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.14.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.14.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.14.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.15.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.15.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.15.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.15.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.15.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.15.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.15.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.15.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.15.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.15.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.15.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.15.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.15.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.15.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.16.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.16.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.16.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.16.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.16.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.16.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.16.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.16.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.16.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.16.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.16.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.16.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.16.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.16.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.17.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.17.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.17.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.17.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.17.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.17.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.17.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.17.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.17.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.17.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.17.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.17.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.17.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.17.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.18.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.18.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.18.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.18.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.18.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.18.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.18.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.18.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.18.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.18.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.18.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.18.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.18.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.18.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.19.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.19.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.19.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.19.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.19.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.19.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.19.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.19.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.19.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.19.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.19.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.19.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.19.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.19.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.20.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.20.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.20.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.20.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.20.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.20.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.20.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.20.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.20.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.20.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.20.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.20.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.20.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.20.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.21.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.21.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.21.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.21.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.21.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.21.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.21.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.21.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.21.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.21.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.21.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.21.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.21.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.21.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.22.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.22.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.22.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.22.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.22.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.22.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.22.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.22.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.22.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.22.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.22.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.22.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.22.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.22.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.23.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.23.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.23.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.23.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.23.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.23.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.23.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.23.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.23.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.23.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.23.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.23.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.23.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.23.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.24.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.24.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.24.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.24.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.24.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.24.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.24.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.24.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.24.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.24.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.24.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.24.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.24.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.24.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.25.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.25.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.25.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.25.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.25.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.25.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.25.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.25.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.25.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.25.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.25.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.25.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.25.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.25.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.26.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.26.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.26.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.26.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.26.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.26.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.26.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.26.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.26.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.26.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.26.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.26.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.26.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.26.mlp.down_proj.lora_B.default.weight",
    "base_model.model.model.layers.27.self_attn.q_proj.lora_A.default.weight",
    "base_model.model.model.layers.27.self_attn.q_proj.lora_B.default.weight",
    "base_model.model.model.layers.27.self_attn.k_proj.lora_A.default.weight",
    "base_model.model.model.layers.27.self_attn.k_proj.lora_B.default.weight",
    "base_model.model.model.layers.27.self_attn.v_proj.lora_A.default.weight",
    "base_model.model.model.layers.27.self_attn.v_proj.lora_B.default.weight",
    "base_model.model.model.layers.27.self_attn.o_proj.lora_A.default.weight",
    "base_model.model.model.layers.27.self_attn.o_proj.lora_B.default.weight",
    "base_model.model.model.layers.27.mlp.gate_proj.lora_A.default.weight",
    "base_model.model.model.layers.27.mlp.gate_proj.lora_B.default.weight",
    "base_model.model.model.layers.27.mlp.up_proj.lora_A.default.weight",
    "base_model.model.model.layers.27.mlp.up_proj.lora_B.default.weight",
    "base_model.model.model.layers.27.mlp.down_proj.lora_A.default.weight",
    "base_model.model.model.layers.27.mlp.down_proj.lora_B.default.weight"
  ],
  "quantized_model_memory_footprint_bytes_measured": 7785437440,
  "fp16_bf16_baseline_bytes": 8786684928,
  "quantized_weight_bytes_estimate": 2196671232,
  "estimated_weight_memory_savings_fraction": 0.75,
  "note": "Estimates cover model weights, not activations, optimizer states, CUDA kernels, or fragmentation."
}
```

## Environment and provenance

```json
{
  "python": "3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]",
  "platform": "Windows-10-10.0.19045-SP0",
  "disk_free_bytes": 567501676544,
  "packages": {
    "torch": "2.9.1+cu130",
    "transformers": "4.57.3",
    "peft": "0.18.0",
    "trl": "0.26.2",
    "accelerate": "1.12.0",
    "bitsandbytes": "0.49.0",
    "safetensors": "0.7.0"
  },
  "cuda_available": true,
  "cuda_version": "13.0",
  "gpu": "NVIDIA GeForce RTX 5060 Ti",
  "vram_bytes": 17074421760,
  "vram_free_bytes": 15911092224,
  "compute_capability": [
    12,
    0
  ],
  "compiled_architectures": [
    "sm_75",
    "sm_80",
    "sm_86",
    "sm_90",
    "sm_100",
    "sm_120"
  ],
  "bf16_supported": true,
  "compatibility": {
    "pytorch": "ok",
    "bitsandbytes": "installed; runtime 4-bit kernel must be verified by GPU smoke training"
  },
  "git_commit": "afcf332a356e8f343409771f35206d6c7211a941",
  "dataset_hashes": {
    "train": "d07dc6cf68dadb449a781eaafe7c8d6070a20f7d1025b070a56d958471607341",
    "validation": "e8e61c7f3cfdf2f22192c2aec61ffb9470bb894125552459b71abc4da622a80c"
  },
  "effective_config": {
    "model": {
      "name": "Qwen/Qwen2.5-7B-Instruct",
      "trust_remote_code": false,
      "max_seq_length": 2048
    },
    "data": {
      "splits": {
        "train": "Data/dataset_v3/finetuning_rag_clean/train_rag_sft_2048.jsonl",
        "validation": "Data/dataset_v3/finetuning_rag_clean/validation_rag_sft_2048.jsonl",
        "test": null
      },
      "output_dir": "outputs/qlora",
      "near_duplicate_threshold": 0.92
    },
    "quantization": {
      "load_in_4bit": true,
      "bnb_4bit_quant_type": "nf4",
      "bnb_4bit_use_double_quant": true,
      "bnb_4bit_compute_dtype": "bfloat16"
    },
    "lora": {
      "r": 16,
      "alpha": 32,
      "dropout": 0.05,
      "bias": "none",
      "target_modules": [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj"
      ]
    },
    "training": {
      "num_train_epochs": 3.0,
      "per_device_train_batch_size": 1,
      "per_device_eval_batch_size": 1,
      "gradient_accumulation_steps": 8,
      "learning_rate": 5e-05,
      "weight_decay": 0.01,
      "lr_scheduler_type": "cosine",
      "warmup_ratio": 0.03,
      "max_grad_norm": 1.0,
      "gradient_checkpointing": true,
      "dataloader_num_workers": 0,
      "dataloader_pin_memory": true,
      "optim": "paged_adamw_8bit",
      "seed": 42,
      "logging_steps": 10,
      "eval_strategy": "steps",
      "eval_steps": 100,
      "save_strategy": "steps",
      "save_steps": 100,
      "save_total_limit": 3,
      "load_best_model_at_end": true,
      "metric_for_best_model": "eval_loss",
      "greater_is_better": false
    },
    "early_stopping": {
      "enabled": true,
      "patience": 2,
      "threshold": 0.001
    },
    "reporting": {
      "tensorboard": true,
      "save_csv": true,
      "save_json": true,
      "generate_plots": true
    },
    "execution": {
      "approved": true,
      "max_samples": null,
      "max_steps": -1,
      "artifact_label": "rtx5060ti_16gb_rag_sft"
    },
    "evaluation": {
      "generation": {
        "max_new_tokens": 512,
        "temperature": 0.0
      }
    }
  },
  "preflight_suggestions_not_applied": [
    {
      "setting": "quantization.bnb_4bit_compute_dtype",
      "suggested": "bfloat16"
    },
    {
      "setting": "training.per_device_train_batch_size",
      "suggested": 1,
      "reason": "Conservative estimate for 15.9 GiB; validate with smoke mode"
    },
    {
      "setting": "training.gradient_accumulation_steps",
      "suggested": 8
    }
  ],
  "memory_estimates": {
    "estimated_peak_vram_gib_range": [
      12.0,
      21.0
    ],
    "basis": "Heuristic QLoRA range for a 7B model; includes approximate weights/activations but varies by kernels and sequence mix.",
    "is_estimate": true
  },
  "effective_precision": {
    "compute_dtype": "torch.bfloat16",
    "bf16": true,
    "fp16": false
  }
}
```

## Checkpoint metadata

```json
{
  "status": "unavailable",
  "reason": "artifact not generated"
}
```

## Plots

```json
{
  "plots": {
    "training_loss.png": {
      "status": "generated",
      "source": "training_events.jsonl",
      "fields": [
        "loss"
      ]
    },
    "validation_loss.png": {
      "status": "generated",
      "source": "training_events.jsonl",
      "fields": [
        "eval_loss"
      ]
    },
    "combined_loss.png": {
      "status": "generated",
      "source": "training_events.jsonl",
      "fields": [
        "loss",
        "eval_loss"
      ]
    },
    "learning_rate.png": {
      "status": "generated",
      "source": "training_events.jsonl",
      "fields": [
        "learning_rate"
      ]
    },
    "gradient_norm.png": {
      "status": "generated",
      "source": "training_events.jsonl",
      "fields": [
        "grad_norm"
      ]
    },
    "gpu_memory.png": {
      "status": "generated",
      "source": "training_events.jsonl",
      "fields": [
        "gpu_allocated_bytes",
        "gpu_reserved_bytes"
      ]
    },
    "time_per_epoch.png": {
      "status": "generated",
      "source": "training_events.jsonl",
      "fields": [
        "epoch_duration_seconds"
      ]
    },
    "throughput.png": {
      "status": "generated",
      "source": "training_events.jsonl",
      "fields": [
        "train_samples_per_second",
        "train_steps_per_second",
        "train_tokens_per_second"
      ]
    },
    "parameter_proportions.png": {
      "status": "generated",
      "source": "parameter_report.json"
    },
    "evaluation_comparison.png": {
      "status": "unavailable",
      "reason": "post-training test evaluation not run"
    }
  }
}
```
