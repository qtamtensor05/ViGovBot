# Báo cáo kết quả đánh giá mô hình QLoRA v3

> Run `eval-qlora-v3` · mô hình `qwen-qlora` · kiến trúc `finetuned` · adapter `checkpoint-300`

## Mục tiêu

Đánh giá Qwen2.5-7B-Instruct sau fine-tuning QLoRA ở chế độ không truy xuất, nhằm tách tác động của adapter khỏi tác động của RAG.

## Thiết lập đánh giá

| Hạng mục | Giá trị |
|---|---|
| Tập test | `Data/dataset_v3/test_rag/test_rag_pa1.jsonl` |
| Quy mô | 638 mẫu; SHA-256 `f62867a7a0af3cba543c9602392a82e7c4f5912fe1e97b0b22e3c7b4bf1b3583` |
| Mô hình nền | `Qwen/Qwen2.5-7B-Instruct` |
| Adapter | `outputs/qlora/best_adapter`, revision `checkpoint-300` |
| Lượng tử hóa | 4-bit NF4; giải mã greedy |
| Sinh | temperature 0, seed 42, `num_ctx=8192`, `num_predict=512` |
| Thực thi | 638/638 thành công |

## Cấu hình máy và phạm vi chứng cứ

Preflight ghi Windows 10 build 19045, Python 3.11.9, CUDA 13.0, PyTorch 2.9.1+cu130 và RTX 5060 Ti 15,90 GiB VRAM, compute capability 12.0, BF16 khả dụng. Run không ghi CPU/RAM và không đo VRAM đỉnh/GPU utilization nên các mục đó là `NOT VERIFIED`. Đây là cấu hình được chứng minh cho preflight/nạp QLoRA; manifest đánh giá không có machine ID để ràng buộc tuyệt đối từng request.

## Kết quả

| Nhóm | Chỉ số | Kết quả |
|---|---|---:|
| Ngữ nghĩa | BERTScore F1 | 0,9119 |
| Từ vựng | ROUGE-1 / ROUGE-2 / ROUGE-L F1 | 0,4719 / 0,3774 / 0,4482 |
| Ký tự | chrF | 45,3621 |
| Ngữ nghĩa | METEOR / embedding cosine | 0,4755 / 0,7166 |
| Nội dung | Key-fact coverage | 0,1302 |
| Hành vi | Action accuracy / abstention correctness | 0,9357 / 0,0000 |
| Định dạng | Format compliance | 1,0000 |
| Hiệu năng | Tổng độ trễ / TTFT | 5.720,39 / 318,97 ms |
| Hiệu năng | Tốc độ sinh | 13,32 token/s |
| Độ dài | Prompt / completion trung bình | 171,53 / 77,88 token |
| Ổn định | OOM / timeout | 0 / 0 |

Route accuracy bằng 0 và retrieval metrics bằng `null` vì cấu hình bỏ qua routing/retrieval; không được diễn giải là lỗi.

## Nhận định

QLoRA đạt cao nhất trong bốn cấu hình về BERTScore, ROUGE-1, ROUGE-L, chrF, METEOR và cosine. So với Base, câu trả lời ngắn hơn rõ rệt nhưng gần đáp án tham chiếu hơn. TTFT thấp nhất trong khi token/s thấp nhất; điều này có thể do runtime cục bộ, chiều dài đầu ra và cách đo khác với Ollama. Adapter cải thiện khả năng khớp đáp án miền, nhưng abstention vẫn bằng 0 và key-fact coverage thấp hơn QLoRA+RAG, nên chưa chứng minh mô hình tự ghi nhớ đầy đủ tri thức pháp lý.

## Hạn chế

- Không có truy xuất, trích dẫn hay phép đo groundedness.
- Chỉ số tương đồng cao có thể phản ánh phong cách/mẫu câu học được; cần đánh giá thủ công tính đúng pháp lý.
- Nguồn: `outputs/evaluation/eval-qlora-v3` và `outputs/qlora/best_adapter`.

