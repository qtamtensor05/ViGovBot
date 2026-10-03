# Module `vigovbot.rag`

## Trách nhiệm

`vigovbot.rag` là lớp điều phối use case của hệ thống. Module kết nối corpus,
encoder truy vấn, bộ truy hồi, bộ tạo prompt, Ollama và pipeline đánh giá. Module
không thực hiện trích xuất PDF, tạo embedding tài liệu hoặc xây dựng FAISS index.

## Vị trí trong kiến trúc

```text
RAGConfig
   │
   ├── prepare_corpus() ──> FAISS index + metadata SQLite
   │
   ├── routing_messages() ──> LLM router ──> new/follow-up/clarify/abstain
   │                                             │
   ├── load_encoder() ────> Retriever <──────────┘
   │                            │
   ├── AutoTokenizer ──> build_messages() ──> xét bằng chứng + sinh JSON
   │                                              │
   └── web/CLI/evaluation <───────────────────────┘
              │
              ├── ask: câu trả lời và nguồn
              ├── web: Qwen base so với Qwen + RAG
              └── evaluate/run: prediction, metric và báo cáo
```

`rag` phụ thuộc vào các module `vectordb`, `embeddings`, `retrieval`, `prompts`,
`llm` và `evaluation`. Các module này không phụ thuộc ngược vào `rag`.

## Thành phần

| File | Vai trò |
|---|---|
| `config.py` | Mô hình cấu hình Pydantic, kiểm tra trường và phân giải đường dẫn tương đối |
| `pipeline.py` | Điều phối chuẩn bị corpus, phiên inference, hỏi đáp và đánh giá |
| `routing.py` | Prompt, JSON Schema và validator cho định tuyến hội thoại/đầu ra có cấu trúc |
| `__main__.py` | Giao diện CLI cho `prepare`, `ask`, `web`, `smoke`, `evaluate`, `report`, `run` |
| `version.py` | Phiên bản pipeline dùng trong manifest thí nghiệm |

## Đầu vào

### Cấu hình

`load_config(path)` đọc YAML và trả về `RAGConfig` gồm bảy nhóm:

| Nhóm | Nội dung |
|---|---|
| `data` | Corpus, bộ test, cache, thư mục kết quả và chế độ legacy |
| `embedding` | Tên model, revision và thiết bị của encoder truy vấn |
| `llm` | Model Ollama, tokenizer, ngân sách context và tham số sinh |
| `retrieval` | `top_k` và giới hạn token của từng chunk |
| `conversation` | Bật/tắt phân loại phạm vi, quan hệ hội thoại và xét bằng chứng |
| `web` | Danh sách provider/model, chế độ `base`/`rag` và cờ debug routing |
| `evaluation` | Số ca smoke test, giới hạn bộ test và cấu hình BERTScore |

Các đường dẫn trong cấu hình được phân giải tương đối từ thư mục chứa file YAML.
Trường không được khai báo trong schema bị từ chối.

### Corpus

Corpus chuẩn gồm `tthc_unified.index`, `tthc_unified_metadata.json` và
`corpus_manifest.json`. `prepare()` xác minh checksum, số lượng vector, model và
revision trước khi nạp encoder. Corpus legacy chỉ được chấp nhận khi
`data.allow_legacy_corpus` được bật rõ ràng.

### Câu hỏi và bộ test

- `ask` nhận một chuỗi câu hỏi không rỗng qua tham số `question`.
- `smoke`, `evaluate`, `report` và `run` nhận bộ test từ `dataset_path` hoặc
  `dataset_zip`.
- Bộ test cũ chuyển `question.text` vào inference; runner v4 chuyển câu hỏi và lịch sử theo chế độ đã chọn. Ground truth được sử dụng sau
  khi sinh câu trả lời, trong bước đánh giá.

## Lệnh điều phối và đầu ra

| Lệnh | Xử lý | Giá trị trả về / artifact |
|---|---|---|
| `prepare` | Xác minh corpus và tạo cache SQLite | `count`, đường dẫn `database` |
| `ask` | Truy hồi, tạo prompt và gọi Ollama cho một câu hỏi | Kết quả chi tiết của `answer_question()` |
| `web` | Nạp tài nguyên một lần và phục vụ UI/API cục bộ | `/`, `/api/health`, `/api/models`, `/api/chat` |
| `smoke` | Chạy một tập con nhỏ, in từng prediction | Số ca smoke test đã chạy |
| `evaluate` | Sinh hoặc tiếp tục prediction cho bộ test | `raw_predictions.jsonl`, `errors.jsonl`, số ca hoàn thành |
| `report` | Kiểm tra manifest của lượt chạy và tính metric | Các file metric, biểu đồ và `summary.json` |
| `run` | Thực hiện smoke, evaluate và report trong một lượt | Báo cáo tổng hợp |

`answer_question()` trả về cấu trúc:

| Trường | Ý nghĩa |
|---|---|
| `prediction` | Nội dung trả lời do Ollama sinh |
| `action`, `evidence_status` | Hành động và mức bằng chứng của kết quả có cấu trúc |
| `routing`, `retrieval_query` | Quyết định router và truy vấn độc lập thực tế |
| `routing_attempts`, `fallback_reason`, `decision_reason` | Phân biệt route hợp lệ với fallback kỹ thuật |
| `retrieved` | Danh sách nguồn truy hồi rút gọn gồm ID, điểm và mã nguồn |
| `context_used` | Nội dung nguồn thực tế đã được đưa vào prompt |
| `prompt_tokens_estimated` | Số token prompt ước tính bằng tokenizer |
| `routing_s`, `retrieval_s` | Thời gian định tuyến và truy hồi |
| `generation_s` | Thời gian sinh câu trả lời |
| `latency_s` | Tổng thời gian xử lý |
| `raw_ollama` | Payload phản hồi nguyên bản từ Ollama |

## Vòng đời tài nguyên

`inference_session()` sở hữu encoder, tokenizer và `Retriever` trong phạm vi một
context manager. Khi kết thúc, kết nối SQLite được đóng, tham chiếu encoder được
giải phóng, CUDA cache được dọn nếu có và model Ollama được yêu cầu unload.
Web dùng tài nguyên này xuyên suốt vòng đời server. SQLite read-only cho phép
truy cập từ thread request; khóa trong `Retriever` tuần tự hóa encoder, FAISS,
SQLite và `close()`, còn `ChatApplication` tuần tự hóa các model/lượt chat.

Các lệnh ghi kết quả sử dụng khóa `.pipeline.lock`; prediction và báo cáo có khóa
riêng tại module đánh giá. Manifest lượt chạy lưu cấu hình, fingerprint mã nguồn,
checksum corpus/bộ test, revision embedding, digest Ollama và thông tin runtime.
Kết quả cũ không được tiếp tục nếu các thông tin này không còn khớp.

## Ràng buộc và lỗi

- Model/revision của encoder truy vấn phải khớp manifest corpus.
- Router dùng JSON Schema theo nhánh và retry một lần khi JSON sai; hai lần sai
  trả `routing_fallback` và không truy hồi.
- `mode: base` gọi provider trực tiếp; `mode: rag` chạy router, retrieval và xét
  bằng chứng. Hai lựa chọn có history riêng ở client web.
- `num_ctx` phải lớn hơn `num_predict + 256`.
- `ask` không phụ thuộc bộ test; các lệnh đánh giá bắt buộc có bộ test.
- `report` chỉ chạy trên kết quả có `run_manifest.json` tương thích.
- Phiên đánh giá không có prediction thành công được xem là lỗi.
- Lỗi từng ca đánh giá được ghi vào `errors.jsonl` thay vì làm mất kết quả đã có.

## Tài liệu liên quan

- [RAG nhiều lượt và đánh giá qa_test_v4](../../../docs/rag-multi-turn.md)
- [Kiến trúc hệ thống](../../../docs/architecture.md)
- [Hướng dẫn vận hành pipeline RAG](../../../docs/trien-khai-rag-co-ban.md)
- [Đặc tả embedding và corpus](../../../EMBEDDING.md)
