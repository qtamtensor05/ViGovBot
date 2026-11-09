# Roadmap mốc nghiên cứu/demo ViGovBot

> Chốt ngày 2026-11-09. Roadmap này phân biệt nội dung đã hoàn thành,
> chưa hoàn thành và ngoài phạm vi; nó không phải cam kết phát triển tiếp.

## Đã hoàn thành trong mốc

| Hạng mục | Kết quả chốt | Bằng chứng canonical |
|---|---|---|
| Kiến trúc repository | Hợp nhất package `vigovbot`, CLI `vigov`, cấu hình theo domain và cây docs canonical | `src/vigovbot/`, `configs/`, `docs/` |
| Ingestion và corpus | PDF/OCR, làm sạch, chunk theo section, embedding BGE-M3, FAISS/SQLite và manifest | `src/vigovbot/ingestion/`, `src/vigovbot/retrieval/`, `configs/ingestion/` |
| Routing | PhoBERT bốn head, adapter/catalog arbitration, section intent và threshold v2 | `docs/reports/model-evaluation/router-benchmark-and-eda-report.md` |
| Hội thoại RAG | Signed state v3, menu làm rõ, giữ mã thủ tục và lọc evidence khác mã | `docs/guides/rag-multi-turn.md` |
| Training | Pipeline QLoRA 4-bit, masking nhiều lượt, checkpoint/resume và RAG-SFT | `src/vigovbot/training/`, `docs/training/` |
| Evaluation | Dataset v3, prediction có thể resume, retrieval/generation/routing metrics và RAG Judge | `result/`, `docs/reports/model-evaluation/` |
| Giao diện demo | CLI, web UI/API cục bộ và Docker profiles | `src/vigovbot/cli/`, `src/vigovbot/server/`, `compose.yaml` |
| Tái lập | Lock dependency, hướng dẫn setup, Docker, phục hồi PhoBERT/QLoRA | `locks/`, `docs/setup/`, `docs/guides/` |

## Chưa hoàn thành — backlog nếu mở giai đoạn mới

| Ưu tiên | Hạng mục | Tiêu chí hoàn thành đề xuất |
|---|---|---|
| P0 | Chạy lại benchmark hồi quy sau các thay đổi state/section intent | Chốt dataset, config, model revision; hoàn thành toàn bộ case và lưu artifact so sánh |
| P0 | Giảm invalid citation và unsupported answer | Định nghĩa gate trên tập cố định; chạy benchmark và phân tích ca lỗi |
| P0 | Cải thiện abstention | Tách answerable/unanswerable, báo precision/recall và không che khuất false refusal |
| P1 | Sửa các khiếm khuyết ingestion còn ghi nhận | Sửa nguồn/metadata, tái tạo corpus và xác minh retrieval theo mã thủ tục |
| P1 | Ablation `top_k` | Giữ cố định router, prompt, model và corpus; so sánh Top-5/10/15 theo recall, precision, generation và latency |
| P2 | Rà soát quyền dữ liệu và gói artifact | Công bố manifest, checksum, nguồn và điều kiện phân phối cho từng nhóm artifact |

## Ngoài phạm vi mốc đã đóng

- Production deployment, SLA, high availability và kiểm thử tải lớn.
- Xác thực người dùng, phân quyền, TLS, audit log và session store phân tán.
- Tự động bảo đảm hiệu lực pháp lý của nguồn thủ tục.
- Tối ưu cho thiết bị cấu hình yếu hoặc cam kết vận hành không GPU.
- Cross-encoder reranker online khi chưa có ablation chứng minh lợi ích so với độ trễ.

## Quy tắc mở lại roadmap

Khi bắt đầu giai đoạn mới, tạo branch từ tag
`vigovbot-research-v1`, chọn một outcome trong backlog và định nghĩa dataset,
metric, gate cùng artifact trước khi triển khai. Không đổi nội dung mốc đã
chốt để hợp thức hóa kết quả mới.
