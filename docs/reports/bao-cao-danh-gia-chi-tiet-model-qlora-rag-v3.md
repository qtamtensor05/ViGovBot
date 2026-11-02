# Báo cáo kết quả đánh giá mô hình QLoRA + RAG v3

> Run `eval-qlora-rag-v3` · mô hình `qwen-rag-qlora` · kiến trúc `finetuned_rag`

## Mục tiêu

Đánh giá cấu hình kết hợp adapter QLoRA với routing và retrieval, đo riêng độ gần đáp án, chất lượng truy xuất, hành vi và hiệu năng.

## Thiết lập đánh giá

| Hạng mục | Giá trị |
|---|---|
| Tập test | `Data/dataset_v3/test_rag/test_rag_pa1.jsonl` |
| Quy mô | 638 mẫu; SHA-256 `f62867a7a0af3cba543c9602392a82e7c4f5912fe1e97b0b22e3c7b4bf1b3583` |
| Mô hình | Qwen2.5-7B-Instruct + adapter `checkpoint-300` |
| Pipeline | Routing + hybrid retrieval + reranking + QLoRA generation |
| Sinh | temperature 0, seed 42, `num_ctx=8192`, `num_predict=512`, `top_k=15` |
| Độ phủ file prediction | 638 dòng / 638 ID duy nhất |
| Kết quả thực thi trong file | 635 success / 3 error |

File có đủ toàn bộ 638 case. Ba ID `GOLDEN_V3_005699`, `GOLDEN_V3_006086` và `GOLDEN_V3_006644` là bản ghi lỗi HTTP 502: `generation=null`, không có latency và các metric generation tương ứng là `null`. Do đó “638 case trong file” là đúng, nhưng chỉ 635 case có câu trả lời model trong artifact hiện tại.

## Cấu hình máy và phạm vi chứng cứ

Preflight QLoRA ghi Windows 10 build 19045, Python 3.11.9, PyTorch 2.9.1+cu130, CUDA 13.0 và RTX 5060 Ti 15,90 GiB VRAM, compute capability 12.0, BF16 khả dụng. CPU, RAM, VRAM đỉnh và GPU utilization là `NOT VERIFIED`. Manifest không lưu machine ID; cấu hình trên là hồ sơ cùng đợt output, không phải phép đo phần cứng gắn với từng mẫu.

## Kết quả

| Nhóm | Chỉ số | Kết quả |
|---|---|---:|
| Retrieval | Recall@5 / nDCG@5 / MRR@5 | 0,7811 / 0,6812 / 0,6474 |
| Routing | Route accuracy | 0,8425 |
| Nội dung | Key-fact coverage | 0,3108 |
| Ngữ nghĩa | BERTScore F1 | 0,8914 |
| Từ vựng | ROUGE-1 / ROUGE-2 / ROUGE-L F1 | 0,4278 / 0,3736 / 0,4093 |
| Ký tự | chrF | 41,0177 |
| Ngữ nghĩa | METEOR / cosine | 0,4114 / 0,6476 |
| Hành vi | Action accuracy / abstention correctness | 0,7937 / 0,4634 |
| Định dạng | Format compliance | 1,0000 |
| Hiệu năng | Tổng độ trễ / retrieval / TTFT | 8.829,66 / 52,04 / 2.894,18 ms |
| Hiệu năng | Tốc độ sinh | 45,13 token/s |
| Độ dài | Prompt / completion trung bình | 3.243,82 / 195,96 token |
| Ổn định | OOM / timeout | 0 / 0 |

Citation precision, recall và invalid-citation rate lần lượt là 0,3140, 0,3190 và 0,1237 trên 594 mẫu hợp lệ. Đây là metric citation theo scorer, không thay thế groundedness/faithfulness từ judge.

## Nhận định

QLoRA + RAG đạt key-fact coverage và abstention correctness cao nhất. So với RAG, route accuracy tăng nhẹ nhưng Recall@5 và nDCG@5 giảm nhẹ; vì vậy cải thiện phần sinh/hành vi không thể quy toàn bộ cho retrieval. So với QLoRA độc lập, các chỉ số tương đồng giảm nhưng độ phủ key fact và khả năng abstain tăng mạnh. Tổng độ trễ nằm giữa QLoRA và RAG. Ba lỗi thực thi cần được chạy bù trước khi coi run hoàn chỉnh.

## Hạn chế

- Chưa có judgment cho QLoRA+RAG; không suy groundedness từ citation hoặc similarity.
- Artifact có đủ 638 ID nhưng vẫn ghi 635 prediction success và 3 placeholder error; cần artifact thay thế ba dòng lỗi nếu đã chạy bù thành công.
- Metric retrieval và routing có denominator riêng.
- Giữ `failed-attempts.jsonl` và sidecar run để bảo toàn lịch sử lỗi.
- Nguồn: `outputs/evaluation/eval-qlora-rag-v3` và `outputs/qlora/best_adapter`.

