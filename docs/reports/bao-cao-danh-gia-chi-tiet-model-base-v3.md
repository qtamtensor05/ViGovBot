# Báo cáo kết quả đánh giá mô hình Base v3

> Run `eval-base-v3` · mô hình `qwen-base` · kiến trúc `base` · rà soát ngày 02/11/2026

## Mục tiêu

Đánh giá Qwen2.5-7B-Instruct ở chế độ sinh trực tiếp, không truy xuất và không nạp QLoRA adapter, trên tập test v3. Điểm tương đồng văn bản không được xem là bằng chứng độc lập về tính đúng pháp lý.

## Thiết lập đánh giá

| Hạng mục | Giá trị |
|---|---|
| Tập test | `Data/dataset_v3/test_rag/test_rag_pa1.jsonl` |
| Quy mô | 638 mẫu, split `test` |
| SHA-256 | `f62867a7a0af3cba543c9602392a82e7c4f5912fe1e97b0b22e3c7b4bf1b3583` |
| Endpoint | `http://127.0.0.1:8000/api/chat` |
| Sinh | `qwen2.5:7b`, temperature 0, seed 42, `num_ctx=8192`, `num_predict=512` |
| Truy xuất | Không áp dụng (`architecture_without_retrieval`) |
| Thực thi | 638/638 thành công |

## Cấu hình máy và phạm vi chứng cứ

Hồ sơ phần cứng cùng đợt output ghi Windows 10 build 19045, Python 3.11.9, PyTorch 2.9.1+cu130, CUDA 13.0 và NVIDIA GeForce RTX 5060 Ti với khoảng 15,90 GiB VRAM, hỗ trợ BF16. Telemetry của run ghi thiết bị `cuda`, nhưng không xuất tên GPU, VRAM đỉnh hoặc mức sử dụng GPU theo từng mẫu. CPU và RAM là `NOT VERIFIED`. Preflight và run cùng tham chiếu cây output trên tài khoản `ezycloudx-admin`, nhưng manifest không chứa machine ID để ràng buộc tuyệt đối toàn bộ 638 mẫu với một host.

## Kết quả

| Nhóm | Chỉ số | Kết quả |
|---|---|---:|
| Ngữ nghĩa | BERTScore F1 | 0,8479 |
| Từ vựng | ROUGE-1 / ROUGE-2 / ROUGE-L F1 | 0,1700 / 0,0779 / 0,1117 |
| Ký tự | chrF | 20,9224 |
| Ngữ nghĩa | METEOR / embedding cosine | 0,2487 / 0,5392 |
| Nội dung | Key-fact coverage | 0,0153 |
| Hành vi | Action accuracy | 0,9357 |
| Hành vi | Abstention correctness | 0,0000 |
| Định dạng | Format compliance | 1,0000 |
| Hiệu năng | Tổng độ trễ / TTFT trung bình | 6.642,85 / 2.214,66 ms |
| Hiệu năng | Tốc độ sinh | 72,02 token/s |
| Độ dài | Prompt / completion trung bình | 172,52 / 311,64 token |
| Ổn định | OOM / timeout | 0 / 0 |

`Route accuracy = 0` không phải lỗi định tuyến: Base bỏ qua routing nhưng scorer vẫn ghi 0. Các metric retrieval không áp dụng và được lưu `null`.

## Nhận định

Base hoàn tất toàn bộ tập test và giữ đúng định dạng, nhưng độ phủ key fact rất thấp và không từ chối đúng các câu cần abstain. Câu trả lời dài nhất trong bốn cấu hình, trong khi ROUGE-1 F1 chỉ 0,1700. Đây là baseline tham số, không phù hợp để dùng riêng cho câu trả lời thủ tục cần căn cứ hiện hành.

## Hạn chế

- Không có phép đo groundedness/faithfulness vì không dùng nguồn truy xuất.
- VRAM đỉnh, GPU utilization, CPU và RAM không được run ghi lại.
- BERTScore, ROUGE, METEOR và cosine không tự xác nhận sự thật pháp lý.
- Nguồn: các artifact trong `outputs/evaluation/eval-base-v3`.

