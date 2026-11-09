# Báo cáo kết thúc mốc nghiên cứu/demo ViGovBot

> Ngày chốt: 2026-11-09  
> Mốc tham chiếu: `vigovbot-research-v1`

## 1. Mục tiêu và phạm vi

ViGovBot được xây dựng như một prototype nghiên cứu cho hỏi đáp thủ tục
hành chính tiếng Việt. Mốc nghiên cứu kiểm tra khả năng kết hợp ingestion có
cấu trúc, embedding và retrieval, PhoBERT bốn head, hội thoại nhiều lượt,
generation có ràng buộc bằng chứng và QLoRA trong một pipeline có thể đánh
giá lại. Mục tiêu không bao gồm chứng nhận production hoặc bảo đảm đúng
cho mọi câu hỏi.

## 2. Kết quả chính

### 2.1 Hệ thống và dữ liệu

Repository đã hợp nhất pipeline trong package `vigovbot`, CLI `vigov` và các nhóm
cấu hình ingestion, RAG và training. Pipeline bao phủ PDF/OCR, chunk theo section,
embedding BGE-M3, FAISS/SQLite, manifest/checksum, routing, state, generation, QLoRA
và evaluation. Dataset v3 tách dữ liệu fine-tuning, PA1 và router; artifact
đánh giá canonical được lưu trong `result/`.

### 2.2 Routing

Benchmark router v2 trên 1.246 mẫu ghi nhận Scope Accuracy 96,95%, Flow Accuracy
98,80%, Catalog Codes Exact Match 91,81%, Action Accuracy 91,33% và Strict E2E
Accuracy 74,08%. So với baseline threshold v1, Strict E2E Accuracy tăng 6,99
điểm phần trăm. Kết quả này chỉ áp dụng cho dataset và artifact đã chốt;
nó không chứng minh khả năng khái quát sang phân phối truy vấn khác.

### 2.3 So sánh model PA1

Benchmark PA1 gồm 638 case và sáu cấu hình. Trong snapshot đã lưu,
QLoRA v2 + RAG hoàn thành 637/638 prediction và đạt EM 20,41%, key-fact
coverage 38,78%, citation precision 50,52% cùng citation recall 53,43%. Cấu hình
này là ứng viên phù hợp nhất để tiếp tục hardening nếu mở giai đoạn mới,
nhưng không thắng trên mọi tiêu chí. RAG thuần cao hơn về Judge semantic
correctness và answer relevancy; QLoRA v1 + RAG cao hơn về source groundedness
và retrieved-context faithfulness.

## 3. Bằng chứng và khả năng truy vết

| Kết luận | Bằng chứng | Trạng thái |
|---|---|---|
| Router v2 cải thiện action và Strict E2E so với v1 | `result/router_threshold-v1-baseline/`, `result/router_threshold-v2-calibrated/` | Được artifact hỗ trợ |
| Sáu cấu hình PA1 đã có báo cáo so sánh | `result/eval-*`, `docs/reports/model-evaluation/all-models.md` | Được artifact hỗ trợ |
| QLoRA v2 + RAG dẫn đầu EM/key facts/citation coverage trong snapshot | `docs/reports/model-evaluation/qlora-v2-rag.md` | Được artifact hỗ trợ, có ranh giới metric |
| Luồng state/menu giữ mã thủ tục và lọc evidence khác mã | `src/vigovbot/rag/conversation.py`, `tests/test_four_head_routing.py` | Được source test hỗ trợ; không thay thế benchmark toàn hệ |
| Hệ thống sẵn sàng production | Không có bằng chứng tải, HA, auth/TLS hoặc vận hành dài hạn | Không được hỗ trợ |

## 4. Giới hạn

- Invalid citation của QLoRA v2 + RAG là 30,35% trong snapshot PA1; citation recall
  không nên được đọc riêng như bằng chứng trích dẫn đáng tin cậy.
- Abstention correct thấp và unsupported answer còn cao trong các cấu hình RAG.
- Prediction QLoRA v2 + RAG thiếu một case do HTTP 502; các metric phụ thuộc
  prediction hợp lệ dùng mẫu số 637 hoặc 596 tùy rubric.
- Các thay đổi state/section intent sau benchmark chưa được bao phủ bằng một
  lần chạy lại toàn bộ model.
- Chất lượng phụ thuộc vào độ mới của nguồn, OCR, chunking, retrieval,
  prompt và model; repository không tự bảo đảm hiệu lực pháp lý của dữ liệu.

## 5. Cách tái lập

1. Checkout tag `vigovbot-research-v1` và đọc `docs/setup/environments.md` để
   chọn môi trường phù hợp.
2. Cài dependency từ lock tương ứng trong `locks/`; không suy ra môi trường
   model/GPU từ source test.
3. Khôi phục corpus, PhoBERT và QLoRA theo các hướng dẫn trong `docs/guides/`.
   Dataset, checkpoint và model lớn có thể không được Git theo dõi; cần đối
   chiếu manifest/checksum trước khi chạy.
4. Chạy test không phụ thuộc model, sau đó chạy preflight cho profile đã chọn.
5. Nếu lặp lại benchmark, chốt dataset, config, model revision và metric contract;
   lưu prediction, case score, summary và lỗi cùng một run.

## 6. Kết luận

Mốc nghiên cứu đã tạo ra một prototype RAG tiếng Việt có pipeline, artifact
và bộ đánh giá có thể truy vết. Bằng chứng hiện có đủ để chốt mốc demo
và xác định backlog kỹ thuật, nhưng chưa đủ để tuyên bố production. Tag
`vigovbot-research-v1` là điểm tham chiếu cho mốc này; mọi giai đoạn sau nên
phát triển trên branch mới và giữ nguyên artifact của mốc để so sánh.

