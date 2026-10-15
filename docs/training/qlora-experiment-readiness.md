# QLoRA experiment logging readiness

Ngày audit: 2026-10-14. Cấu hình mục tiêu: `configs/training/environments/rtx5060ti_16gb.yaml`.
Audit này không chạy full training và không tải model weights. Trạng thái “verified”
nghĩa là đường thu thập/schema đã được kiểm thử bằng fixture; giá trị thực chỉ xuất
hiện sau training/evaluation và tuyệt đối không được suy diễn từ fixture.

| Dữ liệu/metric | Cách thu thập | Artifact | Trạng thái xác minh |
|---|---|---|---|
| Train loss, validation loss, step, epoch, UTC timestamp | callback ghi append-only ở mỗi `on_log` | `training_events.jsonl`, TensorBoard | Verified |
| Learning rate, gradient norm | log thực từ Hugging Face Trainer | `training_events.jsonl`, TensorBoard | Verified |
| Best validation loss/checkpoint/step, early-stop reason | Trainer state và bộ đếm EarlyStopping | `training_metrics.json`, `checkpoint_metadata.json` | Verified; giá trị chờ full run |
| Tổng thời gian, thời gian epoch/bước, throughput | wall clock callback/Trainer runtime | `epoch_metrics.jsonl`, `timing_report.json` | Verified |
| GPU allocated/reserved hiện tại và peak | `torch.cuda.memory_*` tại log interval và cuối run | `training_events.jsonl`, `training_metrics.json`, TensorBoard | Verified; utilization ngoài CUDA allocator ghi unavailable |
| Tổng/trainable LoRA/frozen/% trainable | đếm trực tiếp `model.parameters()` | `parameter_report.json` | Verified |
| Hyperparameter, seed, dependency, GPU, Git, dataset hash | snapshot config và preflight provenance | `config.yaml`, `environment.json` | Verified |
| Token-weighted train/validation loss và perplexity | evaluate teacher-forced trên best model, theo target token | `training_metrics.json` | Verified; chờ full run |
| Token-weighted test loss/perplexity | evaluate độc lập trên test | `evaluation_results_test.json` | Verified; chờ lệnh post-training |
| Baseline và fine-tuned prediction trên cùng test set | hai model dùng cùng danh sách record trong một invocation | `baseline_predictions_test.jsonl`, `finetuned_predictions_test.jsonl` | Verified; chờ post-training |
| EM, normalized EM, Precision, Recall, F1, ROUGE-1/2/L, BLEU, chrF | metric theo mẫu và aggregate/corpus | prediction JSONL và `evaluation_results_test.json` | Verified |
| Question/reference/generated answer/metric mỗi mẫu | writer JSONL/CSV theo split | `*_predictions_test.jsonl`, `*.csv` | Verified |
| Baseline vs fine-tuned, cải thiện tuyệt đối | so sánh aggregate sau generation | `evaluation_results_test.json` | Verified |
| Plot từ measurement thực | plot đọc event JSONL/evaluation artifact; manifest ghi lý do thiếu | `plots/*.png`, `plot_manifest.json` | Verified bằng fixture; plot thật chờ run |
| Training/early-stop/checkpoint/resume history | callback + Trainer state, append-only | `training_metrics.json`, `checkpoint_history.jsonl`, `checkpoint_metadata.json`, `resume_history.jsonl` | Verified |
| Báo cáo và metric thiếu | bảng availability; không điền giả | `experiment_report.json`, `summary_report.md` | Verified |

## Tách training và đánh giá hậu kỳ

Training chỉ tính validation teacher-forced theo cadence cấu hình. Baseline-versus-
fine-tuned generation không nằm trong callback validation và chỉ chạy khi người dùng
gọi `training.evaluate` sau training. Mỗi split có tên artifact riêng, tránh validation
ghi đè kết quả test.

## Lệnh

```powershell
.\.venv-qlora\Scripts\python.exe -m training.readiness --config configs/training/environments/rtx5060ti_16gb.yaml
.\.venv-qlora\Scripts\python.exe -m training.evaluate --run_dir <RUN_DIR> --split test
.\.venv-qlora\Scripts\python.exe -m training.plot --run_dir <RUN_DIR>
.\.venv-qlora\Scripts\python.exe -m training.report --run_dir <RUN_DIR>
```

Thứ tự hậu kỳ khuyến nghị là evaluate → plot → report. Nếu evaluation chưa chạy,
plot/report phải ghi rõ phần tương ứng là `unavailable`, không tạo số liệu thay thế.

## Kết luận audit

**READY** về cơ chế logging/reporting trước training, với điều kiện readiness command
trên máy đích trả về `READY`. Các measurement của full run vẫn là “chưa có” cho tới
khi training/evaluation thật hoàn tất; fixture chỉ kiểm chứng contract, không phải bằng
chứng chất lượng mô hình.
