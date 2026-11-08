# Kết quả theo dõi và báo cáo training QLoRA v2

Thư mục này lưu bằng chứng của run `qlora-rag-sft-2048-001`, tách khỏi artifact
mô hình dùng cho triển khai tại `model/qlora_v2/`.

## Nội dung

- `logs/`: sự kiện training, thời gian epoch và TensorBoard event.
- `metrics/`: tham số, log từng step và telemetry training.
- `plots/`: biểu đồ loss, learning rate, VRAM và throughput.
- `reports/`: báo cáo tóm tắt thực nghiệm ở Markdown và JSON.
- `config.yaml`: snapshot cấu hình của run.
- `dataset_report.json`: thống kê dữ liệu training.
- `environment.json`: snapshot môi trường thực thi.
- `live_status.json`, `state.json`: trạng thái cuối của tiến trình training.

Thư mục này không chứa trọng số model, tokenizer hoặc adapter triển khai.
