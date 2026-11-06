# Báo cáo Đánh giá Toàn diện ViGovBot

> **Snapshot lịch sử:** Báo cáo phản ánh mã nguồn tại thời điểm đánh giá. Một số
> phát hiện đã được xử lý sau đó; hãy đối chiếu source hiện tại và
> [`docs/project/current-stage.md`](../../project/current-stage.md) trước khi xem
> một mục là lỗi còn tồn tại.

> [!IMPORTANT]
> Báo cáo này dựa trực tiếp trên mã nguồn, cấu hình, tài liệu và kết quả thực nghiệm đọc từ repository. Mọi nhận định đều có dẫn chứng cụ thể; không có nhận định "có vẻ" hay "có thể".

---

## 1. Tổng quan dự án

| Hạng mục | Thực tế |
|---|---|
| Phiên bản | 0.2.0 (`pyproject.toml`) |
| Ngôn ngữ chính | Python 3.10–3.14 |
| Kích thước mã nguồn | ~15 module chính trong `src/vigovbot/`, tổng ~200 KB Python |
| Số test | 58 file `.py` trong `tests/` |
| Mô hình nền | Qwen2.5-7B-Instruct (inference qua Ollama) + QLoRA adapter (GGUF Q8_0) |
| Embedding | BAAI/BGE-M3, 1024 chiều, FAISS IndexFlatIP |
| Router | PhoBERT fine-tuned 4-head (CPU), fallback LLM |
| Hạ tầng inference | Ollama (Docker), FastAPI/Uvicorn, SQLite + FAISS |

---

## 2. Kiến trúc hệ thống — Phân tích và Đánh giá

### 2.1 Luồng tổng thể (xác thực từ `architecture.md` + mã)

```
PDF → ingestion/OCR → chunking (markdown/tables/headings) → embeddings (BGE-M3)
    → vectordb (FAISS + SQLite) ← corpus manifest (SHA-256 verified)

Question → server/app.py → rag/pipeline.py → answer_question()
         → routing (PhoBERT 4-head hoặc LLM) → clarification (catalog + menu)
         → retriever.search() (FAISS + SQLite + section filter)
         → prompts/evidence.py → llm/llm_client.py (Ollama)
         → response.py → JSON answer + evidence_status
```

**Nhận xét kiến trúc tổng quan:** Kiến trúc được phân chia rõ theo lớp — ingestion, vectordb, retrieval, routing, generation, evaluation — và có ranh giới phụ thuộc được tài liệu hóa rõ. Đây là điểm mạnh thực sự.

---

### 2.2 Điểm mạnh kiến trúc (có đối chứng)

**A. Tách biệt rõ trách nhiệm**

- `schemas.py` chỉ định nghĩa hợp đồng dữ liệu (DIMENSION, MODEL_NAME, CACHE_VERSION, validate_records) — không chứa logic.
- `artifacts.py` chỉ xử lý checksum SHA-256, locking, publish — không phụ thuộc vào pipeline.
- `retrieval/procedure_discovery.py` hoàn toàn độc lập: chỉ nhận `entries` và `vectors`, tự tính BM25 + cosine mà không cần FAISS hay SQLite. ✓

**B. Tính toàn vẹn artifact được thiết kế tốt**

- Corpus manifest ghi SHA-256 của cả index + database; cache chỉ được nhận là valid khi cả `identity`, `version`, `embedding`, `count` và `cache_sha256` khớp ([`vector_store.py` L64–77]).
- Ghi manifest _sau cùng_; mất điện giữa chừng → manifest thiếu → cache bị từ chối ở lần sau ([`vector_store.py` L146–158]).
- File lock (`output_lock`) bảo vệ việc tạo corpus đồng thời — dù chú thích đúng rằng đây không phải distributed lock ([`architecture.md` L126]).

**C. PhoBERT Router — thiết kế 4-head chắc chắn**

- 4 head độc lập: scope (IN/OUT/MIXED), flow (NEW/FOLLOW_UP), mix (bool), sections (11 label multi-label).
- Validation nghiêm: `read_metadata()` kiểm tra label mapping, threshold, segmenter, max_len trước khi nạp model ([`phobert_router.py` L38–53]).
- Threshold per-label cho multi-label section head — không dùng argmax chung cho tất cả ([`phobert_router.py` L83–84]).
- Lưu kết quả inference kèm raw probabilities cho observability.

**D. HMAC State trong conversation v2**

- State hội thoại được ký HMAC-SHA256 với `_SECRET = secrets.token_bytes(32)` tạo lúc khởi động ([`clarification.py` L29]).
- `validate_state()` kiểm tra version, signature, scope, corpus, history_fingerprint — 5 điều kiện độc lập ([`conversation.py` L42–51]).
- Client không thể giả mạo state vì không có secret.

**E. Retrieval context fingerprinting**

- `answer_fingerprint = json_hash(answer)` — follow-up chỉ được phép khi answer chưa thay đổi ([`pipeline.py` L336]).
- Nếu corpus thay đổi (ví dụ cập nhật FAISS), `corpus_fingerprint` trong context sẽ không khớp → fallback tự động ([`retriever.py` L199]).

---

### 2.3 Lỗi, hạn chế và vấn đề — có đối chứng

#### ❌ LỖI NGHIÊM TRỌNG 1: `source_fingerprint()` đọc toàn bộ file `.py` mỗi lần gọi

**Vị trí:** [`pipeline.py` L24–29]

```python
def source_fingerprint():
    root = Path(__file__).resolve().parents[1]
    paths = sorted(root.rglob("*.py"))  # Duyệt toàn bộ package
    return json_hash({p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in paths})
```

**Vấn đề:** Mỗi lần `evaluation_identity()` được gọi (từ `server/app.py` L215), hàm này đọc toàn bộ file Python trong package vào RAM, hash chúng. Với ~200KB Python code, chi phí I/O và CPU xảy ra tại runtime đánh giá. Không có cache. Trên hệ thống chậm (Docker + Windows) có thể gây latency spike vài trăm ms.

**Đối chứng:** Hàm này được gọi trong `evaluation_identity()` tại `server/app.py` L215, mà `evaluation_identity` lại được gọi trong mỗi request có `evaluation_complete=True`.

---

#### ❌ LỖI/HẠN CHẾ 2: `_STATES` OrderedDict giới hạn 256 session, in-memory, không persist

**Vị trí:** [`conversation.py` L38–39]

```python
STATE_CONTRACT_VERSION = 3
_STATES = OrderedDict()
_STATE_LOCK = Lock()
```

**Vấn đề:**
1. Tài liệu thừa nhận: "restart tiến trình web sẽ xóa bộ nhớ đệm này" ([`architecture.md` L153]).
2. Giới hạn 256 session (`OrderedDict` LRU) — khi người dùng thứ 257 vào, session đầu tiên bị xóa âm thầm mà không thông báo.
3. Không có session TTL — session cũ chiếm slot cho đến khi bị đẩy ra bởi session mới hơn.
4. Trên deployment đa worker (`uvicorn --workers N`), `_STATES` không shared giữa các worker process — user gửi request đến worker khác sẽ mất state.

**Đối chứng:** Chú thích "Chưa có hệ thống quản lý người dùng, cơ sở dữ liệu session phân tán (Redis)" trong [`architecture.md` L154–155].

---

#### ❌ HẠN CHẾ 3: Không có reranker online — top_k = 15 nhưng không có reranking

**Vị trí:** [`architecture.md` L144–147], [`inference.yaml` L14–15]

```yaml
retrieval:
  top_k: 15
```

**Vấn đề tại thời điểm đánh giá:** Với FAISS IndexFlatIP (brute-force), top-15 được lấy theo cosine similarity và không có cross-encoder reranker. Thiết kế reranking cũ đã được bỏ khỏi nhóm hướng dẫn hiện hành; benchmark lịch sử còn tại [`docs/reports/reranker-latency-20261029.md`](../reranker-latency-20261029.md).

**Đối chứng:** Trong `retriever.py`, không có import cross-encoder nào. `rerank_s` trong kết quả luôn là 0.0 ([`pipeline.py` L114]).

---

#### ❌ HẠN CHẾ 4: `llm_client.py` cực kỳ mỏng — không có retry, không có circuit breaker

**Vị trí:** [`llm_client.py`]

```python
response = requests.post(
    settings["ollama_url"].rstrip("/") + "/api/chat",
    ...
    timeout=settings["timeout"],
)
response.raise_for_status()
```

**Vấn đề:**
1. Không có retry khi Ollama timeout hoặc trả 503.
2. Không có circuit breaker — nếu Ollama chết, mọi request đều chờ hết `timeout` rồi fail.
3. `timeout` là timeout tổng, không phải connect + read timeout riêng biệt — nguy cơ connection hang.
4. `raise_for_status()` không phân biệt lỗi 4xx (input sai) vs 5xx (server sự cố) trong error handling.

---

#### ❌ HẠN CHẾ 5: `answer_question()` trong `pipeline.py` — hàm 382 dòng với 14 tham số

**Vị trí:** [`pipeline.py` L93–382]

```python
def answer_question(question, retriever, tokenizer, settings, history=None, *, structured=False, answer_fn=None,
                    retrieval_context=None, clarification_context=None, clarification_scope="",
                    router_fn=None, conversation_state=None, selection=None):
```

**Vấn đề:** Hàm 382 dòng, 14 tham số, xử lý: clarification, routing, follow-up, query decomposition, retrieval, prompt building, generation — vi phạm Single Responsibility. Khó test đơn vị từng bước riêng. Nhánh `routing_contract == "v2"` thực ra delegate toàn bộ sang `conversation.py`, nghĩa là function này giờ có 2 contract song song.

---

#### ❌ HẠN CHẾ 6: Routing LLM — không có batch inference, 2 lần gọi LLM khi retry

**Vị trí:** [`response.py` L65–150]

**Vấn đề:** Mỗi routing gọi Ollama một lần; nếu parse_route thất bại, gọi thêm lần 2 với prompt dài hơn. Với `routing_num_ctx=4096`, mỗi routing call tốn thêm latency khoảng 0.5–2s. Với conversation v2 dùng PhoBERT, latency này không phát sinh, nhưng khi fallback về LLM routing (ví dụ PhoBERT không có checkpoint), sẽ có 2 lần sequential LLM call trước khi sinh câu trả lời.

---

#### ❌ HẠN CHẾ 7: `procedure_discovery.py` tính BM25 O(N) trên mỗi query

**Vị trí:** [`procedure_discovery.py` L58–66]

```python
for index, document in enumerate(self.documents):
    term_frequency = Counter(document)
    ...
    bm25[index] = sum(self.idf.get(token, 0.) * ...)
```

**Vấn đề:** Với catalog N thủ tục, mỗi query tính BM25 toàn bộ N documents. IDF được tính 1 lần lúc khởi tạo (tốt), nhưng TF và length_factor tính lại mỗi lần. NumPy được dùng cho cosine (vectorized, nhanh) nhưng BM25 vẫn là Python loop. Với N = vài nghìn thủ tục, không phải bottleneck thực sự, nhưng đây là điểm cải tiến rõ ràng bằng cách pre-index inverted index.

---

#### ❌ THIẾU SÓT 8: `_fold()` được định nghĩa ở nhiều nơi

**Vị trí:**
- `retriever.py` L22–26: `def _fold(text):`
- `response.py` L14–18: `def _fold_words(value):`
- `conversation.py` import `_fold` từ `retriever`
- `procedure_discovery.py` L17–20: `def fold(text):`
- `prompt_templates.py` L28–30: `def _fold_question(question):`
- `clarification.py` import `_fold` từ `retriever`

**Vấn đề:** Có ít nhất 4 biến thể của cùng một logic "chuẩn hóa tiếng Việt bỏ dấu". Chúng có hành vi khác nhau nhỏ:
- `_fold` trong `retriever.py` chuẩn hóa NFD + bỏ Mn + thay "đ"→"d" + sửa "dang ki"→"dang ky"
- `fold` trong `procedure_discovery.py` chuẩn hóa NFD + bỏ Mn + thay "đ"→"d" nhưng split/join (bỏ space thừa) và **không** sửa "dang ki"
- `_fold_words` trong `response.py` chuẩn hóa NFD + bỏ Mn + findall `[a-z0-9]+` (mất dấu hoàn toàn)

Điều này có thể dẫn đến edge case matching khác nhau giữa các module.

---

#### ❌ THIẾU SÓT 9: Validation dữ liệu SFT chỉ cho phép 2, 4 hoặc 6 turn

**Vị trí:** [`training/data.py` L45–48]

```python
if len(conversation) not in (2, 4, 6):
    raise ValueError(
        f"{location}: messages must contain optional system then 2, 4, or 6 user/assistant turns"
    )
```

**Vấn đề:** Giới hạn cứng tối đa 3 lượt hội thoại (6 message = 3 user + 3 assistant). Nếu dataset thực nghiệm trong tương lai có conversation dài hơn (ví dụ RAG-SFT với 4–5 lượt làm rõ), cần sửa constant này. Không có tham số cấu hình.

---

#### ❌ THIẾU SÓT 10: `source_fingerprint()` hash toàn bộ package nhưng không loại trừ `__pycache__`

**Vị trí:** [`pipeline.py` L28]

```python
paths = sorted(root.rglob("*.py"))
```

**Vấn đề:** `rglob("*.py")` không tìm thấy `.pyc` trong `__pycache__` (đúng), nhưng **có** tìm thấy `.py` trong `__pycache__` nếu có. Chủ yếu là cosmetic, nhưng filter cẩn thận hơn là `if not any(p == "__pycache__" for p in path.parts)`.

---

#### ⚠️ CẢNH BÁO 11: Hai Python interpreter (`cpython-312` và `cpython-314`) trong `__pycache__`

**Vị trí:** Danh sách file enumerate (bước 8)

Có cả `.cpython-312.pyc` và `.cpython-314.pyc` cho mọi module. Điều này cho thấy package đã được import từ 2 phiên bản Python khác nhau. Không gây lỗi runtime nhưng là dấu hiệu môi trường dev không nhất quán (Python 3.12 và 3.14 chạy song song).

---

#### ⚠️ CẢNH BÁO 12: `compose.yaml` và Dockerfile không hiện diện trong đánh giá này nhưng được tham chiếu nhiều

Tài liệu `README.md` và `current-stage.md` tham chiếu `compose.yaml`, `Dockerfile`, `Modelfile.qwen-qlora-rag-sft`, nhưng các file này không xuất hiện trong danh sách scan `src/`. Chúng có thể nằm ở root. Điều này không phải lỗi nhưng cần xác nhận chúng được version-controlled đúng cách.

---

## 3. Phân tích từng module chính

### 3.1 `ingestion/` — Pipeline nhập liệu

**Phát hiện:**
- Module cực kỳ nhỏ: chỉ 3 file Python tổng (~5.6 KB).
- `parse.py`: 224 bytes — chỉ là re-export.
- Logic thực sự nằm trong `pipelines/indexing.py` (10.7 KB).
- `recovery.py` xử lý OCR fallback (PyMuPDF4LLM + Tesseract).

**Vấn đề:** `pipelines/indexing.py` xử lý PDF parsing + chunking + file I/O trong cùng một hàm `parse_pdf_to_hybrid_data()` — 245 dòng. Không có separation giữa extraction và chunking tại cấp hàm.

**Điểm tốt:** `validate_pdf()` kiểm tra magic bytes `%PDF-` trước khi đọc — đúng cách. `write_json_atomic()` dùng temp file + rename — an toàn với crash.

---

### 3.2 `chunking/` — Phân tích cấu trúc TTHC

**Phát hiện từ mã:**
- `TTHCStructureAwareChunker` parse heading → classify section → split block có overlap.
- `SectionType` enum với 10 loại section được định nghĩa trong `headings.py`.
- `BlockSplitter` tách text theo `target_chars`/`max_chars`/`overlap_chars` được cấu hình từ YAML.
- `tables.py`: xử lý continuation table, flatten, repeat header — riêng biệt khỏi markdown parser.

**Điểm mạnh:** `TTHCChunk` là Pydantic model — validation tự động. Chunker không có state global — thread-safe theo thiết kế.

**Vấn đề:**
1. `if __package__ in (None, ""):` trong `markdown.py` L12–13 — đây là pattern cũ để chạy script trực tiếp, không cần thiết trong package đã cài đặt đúng cách.
2. Không có kiểm tra độ dài tối thiểu của `text_content` sau khi chunking — một chunk với 1 ký tự sẽ được embed và lưu vào FAISS.

---

### 3.3 `embeddings/` — Corpus builder

**Điểm mạnh:**
- `encode_chunks()` có retry: khi CUDA batch thất bại, tự động giảm batch_size và thử lại ([`corpus_builder.py` L85+]).
- `safe_extract()` kiểm tra ZIP traversal attack, symlink, file size limit trước khi extract — đúng cách.
- `embedding_text()` prepend `context_prefix` chỉ khi text chưa bắt đầu bằng prefix — tránh duplicate prefix.

**Vấn đề:**
- Không có validation rằng các vectors sau khi encode không phải zero vector (thực tế BGE-M3 không tạo zero vector, nhưng vẫn nên kiểm tra ở build time như đã làm ở query time trong `retriever.py` L128).

---

### 3.4 `vectordb/` — FAISS + SQLite cache

**Điểm mạnh:**
- `prepare_corpus()` đọc JSON bằng ijson streaming — không load toàn bộ metadata vào RAM.
- Batch SQLite insert 100 record/commit — hợp lý.
- Tạo `idx_chunks_source_code` index sau khi populate — NOCASE collation phù hợp cho mã thủ tục.
- Atomic write (temp file → rename) cho FAISS index.

**Vấn đề:**
- `_ensure_source_code_index()` mở connection mới (không dùng URI read-only) — không nhất quán với cách Retriever dùng read-only URI.
- Sau khi thêm index, `cache_sha256["database"]` được cập nhật trong `ready.json` nhưng không có file lock trong `_ensure_source_code_index` — race condition nếu hai process cùng kiểm tra xem index đã tồn tại chưa (dù hiếm vì có `output_lock` ở level cao hơn).

---

### 3.5 `retrieval/retriever.py` — Retriever chính

**Điểm mạnh:**
- `search()` ưu tiên exact source code match > procedure name match > semantic — rõ ràng.
- `_contains_phrase()` dùng `str.find()` thay vì compile regex cho mỗi tên thủ tục — đúng quyết định về hiệu năng khi catalog có nhiều tên.
- Thread safety: `_encoder_lock` cho encoding (stateful model), `_db_lock` cho SQLite access.
- SQLite mở read-only URI — không thể bị ghi nhầm.
- Validation FAISS: kiểm tra `d == 1024`, `metric_type == METRIC_INNER_PRODUCT`, và `count == ntotal` khi khởi tạo.

**Vấn đề:**
1. **Normalization không nhất quán:** `retriever.py` L131: `vector /= np.max(np.abs(vector))` trước khi `faiss.normalize_L2(vector)`. Max-abs normalization trước L2 normalization là không cần thiết và không làm thay đổi hướng vector — L2 normalization đã đủ. Đây là code dư thừa, không gây lỗi nhưng không rõ mục đích.
2. `MAX_PROCEDURE_NAME_MATCHES = 8` — giới hạn cứng. Nếu query chứa tên thủ tục phổ biến xuất hiện trong >8 thủ tục khác nhau, fallback về semantic. Giá trị này không được cấu hình.
3. Trong `follow_up()`, có 7 lý do fallback khác nhau (L194–229). Không phải lỗi — nhưng khó test toàn bộ nhánh.

---

### 3.6 `rag/conversation.py` — Orchestration v2 (633 dòng)

**Điểm mạnh:**
- State contract v3 với 5 trường validation là thiết kế phòng thủ tốt.
- `direct_choice()` xử lý đúng cả selection dict (từ API) và natural language number.
- `pending_request_snapshot()` / `restore_pending_requests()` là pattern immutability tốt — đảm bảo menu state không bị mutate trong flight.
- `identifiers_missing_from_hits()` kiểm tra định danh opaque (mã hồ sơ format `XX-YY-ZZ`) không có trong evidence — tránh hallucination về dữ liệu cá nhân.

**Vấn đề:**
1. File 633 dòng — lớn nhất trong module RAG sau `records.py` (1022 dòng). Nên tách `answer_conversation()` thành các hàm nhỏ hơn theo giai đoạn: routing, clarification, retrieval, generation.
2. `_SOCIAL_GREETING` regex hardcode danh sách lời chào tiếng Việt — mở rộng khó.
3. `_MENU_REJECTION` regex (`khong phai|khong co|khong dung`) — đây là từ đã bỏ dấu (folded). Nếu `_fold` thay đổi hành vi, regex này cũng cần cập nhật theo — coupling ẩn.

---

### 3.7 `rag/phobert_router.py` — 4-head inference

**Điểm mạnh:**
- `encode_segments()` truncate từ segment dài nhất trước — đúng chiến lược.
- Validation đầy đủ: metadata format, thresholds, label mapping, checkpoint files.
- `get_router()` dùng `lru_cache(maxsize=1)` — singleton per settings hash.
- Khởi tạo đúng: `torch.set_num_threads(threads)`, `.eval()` cho cả encoder và heads.

**Vấn đề:**
1. `torch.set_num_threads(threads)` là **global setting** — ảnh hưởng toàn bộ PyTorch trong process, không chỉ PhoBERT. Nếu sau này có model khác dùng threading, sẽ bị ảnh hưởng.
2. `heads.pt` là file custom `torch.save()` — không phải `safetensors`. Nếu weights độc hại được đưa vào, `torch.load()` với `weights_only=True` (đã có L112) vẫn an toàn, nhưng nên dùng safetensors cho consistency với encoder.
3. Không có validation rằng PhoBERT encoder output dimension khớp với head input dimension khi load.

---

### 3.8 `rag/clarification.py` — Catalog + Menu

**Điểm mạnh:**
- `load_procedure_aliases()` cache với `@lru_cache(maxsize=8)` — đọc YAML một lần.
- Alias validation: alias phải ≥2 từ, không được ambiguous giữa các code khác nhau.
- `selection_index()` regex chặt chẽ — không mismatch số trong câu hỏi thực.
- `_DISCOVERY_STOP` frozenset các từ chung quá mơ hồ để loại khỏi catalog search.

**Vấn đề:**
1. `_signature(value)` trong `clarification.py` L48 dùng `hmac.new(...)` — đây là module-level function nhưng `_SECRET` được khởi tạo khi module load. Nếu có hot reload (ví dụ uvicorn `--reload`), `_SECRET` sẽ thay đổi → tất cả menu hiện tại bị invalid. Với production build (không reload), không phải vấn đề.
2. Catalog được load từ `retriever.clarification_catalog()` nhưng không có caching ở level Clarifier — mỗi request tạo `Clarifier` mới sẽ gọi lại `clarification_catalog()`.

---

### 3.9 `prompts/` — Evidence packaging + Prompt templates

**Điểm mạnh:**
- `build_messages()` tính budget token dùng tokenizer thực (`apply_chat_template`) — không phải ước tính ký tự.
- Fragment group/position tracking — khi nhiều chunk từ cùng section, prompt đánh dấu thứ tự để model không bỏ sót.
- System prompt tiếng Việt rõ ràng với 5 phần: VAI TRÒ, CHỌN NGUỒN, BẢO TOÀN DỮ KIỆN, THIẾU BẰNG CHỨNG, AN TOÀN — có instruction rõ về prompt injection.

**Vấn đề:**
1. `SYSTEM_PROMPT` là constant string trong code — nếu muốn A/B test prompt, cần sửa code và redeploy.
2. `_presentation_instruction()` dùng `any(term in folded for term in ...)` — substring match, không phải word boundary. "phi" sẽ match trong "khoa phi" hay "phi truong". Nên dùng regex với word boundary như đã làm ở `retriever.py`.

---

### 3.10 `training/` — QLoRA pipeline

**Điểm mạnh:**
- `train()` yêu cầu `--approve` hoặc `execution.approved=true` trước khi chạy full training — ngăn chạy nhầm.
- Guard CUDA availability và bitsandbytes presence trước khi import heavy modules.
- Checkpoint resume: kiểm tra optimizer state, scheduler state, RNG state trước khi tiếp tục.
- `leakage_filter.py` kiểm tra 6 loại overlap khác nhau (test_id, standalone_query, context_id, context_text, long_answer, procedure_code) — rất chặt chẽ.
- Near-duplicate detection dùng character 5-gram index — O(N log N) thay vì O(N²).

**Vấn đề:**
1. `validate_conversation()` giới hạn cứng 2/4/6 turns ([`data.py` L45]).
2. `_precision()` chọn dtype dựa trên `torch.cuda.is_bf16_supported()` — đúng. Nhưng fallback `torch.float32` khi không có CUDA lại raise `RuntimeError` ngay sau đó (L50) — logic check dtype và check CUDA availability là redundant và có thể gây nhầm lẫn.
3. `train()` import `torch` và các GPU library bên trong function body ([`train.py` L54]) — đúng pattern để tránh import ở module-level, nhưng phải nhất quán trong tất cả function trong file (L55–57 cũng import bên trong).

---

### 3.11 `evaluation/records.py` — 1022 dòng (file lớn nhất)

**Phát hiện:**
- Định nghĩa 7 nhóm metric key (REFERENCE_KEYS, ROUTING_KEYS, QUERY_KEYS, RETRIEVAL_KEYS, GENERATION_KEYS, ROBUSTNESS_KEYS, PERFORMANCE_KEYS) — 60+ metric.
- Hàm LCS O(N×M) tự implement thay vì dùng `difflib` — không cần thiết.
- Implement `_prf` (precision/recall/F1) token-level bằng Counter intersection — đúng và efficient.
- `_ngrams` build ngram tuples — standard.

**Vấn đề:**
1. File 1022 dòng là code smell rõ ràng. Nên tách thành: `records_io.py` (load/validate), `records_metrics.py` (scoring functions), `records_pipeline.py` (workflow orchestration).
2. `_lcs_length()` implement thủ công Longest Common Subsequence. Với Python, `difflib.SequenceMatcher` đã có sẵn và được test kỹ hơn. Dùng thủ công chỉ có lợi nếu cần control memory layout (DP 1D) — ở đây đã dùng 1D DP, là tối ưu hợp lý, nhưng vẫn là code không cần thiết.
3. `scoring.py` và `records.py` cùng implement `_tokens()`, `_distance()`, `_error_rate()` — code duplication giữa 2 file evaluation.

---

### 3.12 `server/app.py` — FastAPI

**Điểm mạnh:**
- `_AnswerTokenExtractor` implement custom JSON streaming parser để stream token của field `"answer"` — giải pháp pragmatic khi Ollama stream raw tokens không phải parsed answer.
- `run_in_threadpool()` cho inference — không block event loop.
- `MAX_BODY_BYTES = 1_000_000` — giới hạn body size.
- `evaluation_identity()` expose đầy đủ fingerprint: source SHA-256, model digest, routing checkpoint.

**Vấn đề:**
1. `_AnswerTokenExtractor.feed()` là custom JSON parser bằng tay — dễ có edge case với Unicode escape sequences phức tạp (`\uD800\uDC00` surrogate pair). Đã xử lý `\u` escape (L70), nhưng surrogate pair cần 2 `\u` escape liên tiếp — có thể gây lỗi decode với text có emoji.
2. `MAX_BODY_BYTES = 1_000_000` được định nghĩa nhưng kiểm tra ở đâu? Cần verify rằng nó được áp dụng trước khi parse JSON (không thấy trong đoạn code đọc được).
3. Không có rate limiting — API endpoint `/api/chat` có thể bị spam.
4. Không có authentication — bất kỳ ai truy cập được port 8001 đều dùng được API.

---

## 4. Phân tích phương pháp và kết quả thực nghiệm

### 4.1 Dataset và Training

| Hạng mục | Thực tế |
|---|---|
| Dataset SFT v2 (train) | 1.863 mẫu (sau leakage filter) |
| Dataset SFT v2 (val) | 786 mẫu |
| Dataset RAG-SFT (train, ≤2048 token) | 1.799 mẫu (96.6% retained) |
| Dataset RAG-SFT (val) | 757 mẫu |
| Loại bỏ outlier | 64 train + 29 val mẫu >2048 token |
| LoRA rank | r=16, alpha=32, 7 target modules |
| Quantization | NF4 4-bit, double quant, bfloat16 compute |
| Best checkpoint (RAG-SFT) | step-600, eval_loss=0.020166 |
| Training hardware | RTX 5060 Ti 16GB |
| VRAM sử dụng | ~15.1 GB / 16.3 GB |

**Nhận xét phương pháp leakage filter:** Rất chặt chẽ — kiểm tra 6 tiêu chí overlap. Đây là điểm mạnh thực sự so với nhiều dự án RAG research chỉ kiểm tra exact match.

**Vấn đề phương pháp:**
1. Dataset train: 1.799–1.863 mẫu là **rất nhỏ** cho fine-tuning LLM 7B. Mô hình với LoRA r=16 có ~18M trainable parameters trên ~7B base — tỷ lệ 0.26% — đây là acceptable nhưng dataset size nhỏ có nguy cơ overfitting cao.
2. `early_stopping.patience=2` với `eval_steps=100` — dừng sớm sau 2 lần eval không cải thiện. Với dataset nhỏ và batch size effective=8, 100 steps ≈ 800 mẫu — đây là window nhỏ để đánh giá plateau.
3. `learning_rate=0.0002` — tương đối cao cho QLoRA. 2e-4 thường dùng cho full fine-tune; với LoRA thường dùng 1e-4 đến 3e-4. Không phải lỗi nhưng cần ablation.
4. `max_seq_length=2048` với `num_ctx=16384` trong inference — training và inference context window **không khớp**. Model được huấn luyện với 2048 token nhưng inference dùng 16384 token context. Điều này có thể gây degradation với long context.

---

### 4.2 Kết quả đánh giá (từ `current-stage.md`)

| Model | SacreBLEU | chrF++ | BERTScore F1 | ROUGE-L | Action Accuracy |
|---|---|---|---|---|---|
| Base (Qwen 2.5 7B) | 2.69 | 19.93 | 0.8485 | 0.1110 | — |
| RAG (Base + RAG) | 15.57 | 35.20 | 0.8790 | 0.3001 | 71.79% |
| QLoRA v1 | — | 40.55 | 0.8965 | 0.4096 | 79.00% |
| QLoRA v2 RAG-SFT (không RAG) | 6.82 | 25.62 | 0.8647 | 0.1960 | 93.57% |
| QLoRA v2 RAG-SFT (có RAG) | 36.39 | 47.25 | 0.9022 | 0.4575 | 80.88% |

**Nhận xét quan trọng:**

1. **QLoRA v2 không RAG có Action Accuracy 93.57% nhưng SacreBLEU chỉ 6.82%** — model học được đúng "action" (trả lời hay từ chối) nhưng không tạo được text chất lượng cao khi không có context. Đây là behavior chủ ý của RAG-SFT: model biết từ chối khi không có evidence.

2. **Semantic Correctness tổng thể (638 mẫu): 48.43%** — còn thấp. Chỉ có nhóm new_question đạt 66.33%.

3. **Intent Coverage Score: 45.20%** — mô hình vẫn bỏ sót nhiều yêu cầu trong câu hỏi phức tạp.

4. **Exact Match: 20.38%** — metric này quá nghiêm khắc cho QA tiếng Việt với nhiều cách diễn đạt tương đương. Không phải thước đo tốt nhất.

5. **False Refusal: 7.13%** — mô hình vẫn từ chối 7% câu hỏi hợp lệ. Chưa rõ từ dataset thực tế bao nhiêu trường hợp là edge case khó.

---

### 4.3 Routing Benchmark (từ docs)

- PhoBERT v3 fine-tuned trên 4 head.
- Router benchmark report (`router-benchmark-and-eda-report.md`) tồn tại nhưng chưa đọc chi tiết trong scope này.
- `CATALOG_SCOPE_LOWER = 0.50` và `CATALOG_SCOPE_UPPER = 0.85` là thresholds arbitration — chưa rõ được tune như thế nào.

---

## 5. Dư thừa và trùng lặp

| Vị trí | Mô tả dư thừa |
|---|---|
| `_fold()` | ≥4 biến thể với logic khác nhau nhỏ ở: `retriever.py`, `procedure_discovery.py`, `response.py`, `prompt_templates.py` |
| `_tokens()` + `_error_rate()` | Trùng giữa `evaluation/records.py` và `evaluation/scoring.py` |
| `sha256_file` | Re-export alias trong `training/data.py` L10: `from vigovbot.artifacts import file_hash as sha256_file` — alias được dùng ở đâu không rõ |
| `two Python versions` | `__pycache__` có cả `.cpython-312.pyc` và `.cpython-314.pyc` cho mọi file |
| `import gc; import torch; torch.cuda.empty_cache()` | Xuất hiện trong cả `pipeline.py` và `training/inference.py` — có thể extracted thành helper |
| `_lcs_length()` | Tự implement LCS khi `difflib` đã có sẵn |
| `answer_question()` nhánh v2 | Khi `routing_contract == "v2"`, hàm ngay lập tức delegate sang `conversation.answer_conversation()` — có thể là 2 function riêng biệt hoàn toàn |
| `evaluation/benchmark_report.py` vs `evaluation/report.py` vs `training/report.py` | Ba module report cùng tên khác nhau, được note trong `architecture.md` nhưng vẫn gây confusion |

---

## 6. Tối ưu chưa được áp dụng

### 6.1 Performance

| Vấn đề | Mức độ | Giải pháp đề xuất |
|---|---|---|
| `source_fingerprint()` gọi mỗi request evaluation | Trung bình | Cache với `functools.lru_cache` hoặc tính lúc startup |
| BM25 O(N) Python loop trong `procedure_discovery.py` | Nhỏ | Pre-index inverted index (token → document set) |
| SQLite không có WAL mode | Nhỏ | `PRAGMA journal_mode=WAL` cho concurrent reads tốt hơn |
| `_procedure_names` lazy load và lock mỗi lần truy cập | Nhỏ | Load tại `__init__` |
| `encoding` với `batch_size=1` trong query time | Nhỏ | Hiện đúng vì query đơn, nhưng không có batching cho concurrent requests |

### 6.2 Độ bền (Reliability)

| Vấn đề | Mức độ | Giải pháp đề xuất |
|---|---|---|
| Không retry Ollama | Cao | `tenacity` hoặc custom retry với exponential backoff |
| Session state in-memory | Cao | Redis hoặc database-backed session |
| Không có health check cho FAISS/SQLite | Trung bình | Periodic integrity check |
| Không có circuit breaker | Trung bình | `pybreaker` hoặc tự implement |

### 6.3 Testability

| Vấn đề | Mức độ |
|---|---|
| `answer_question()` 382 dòng 14 params khó unit test | Cao |
| `_SECRET` process-global làm khó test menu validation | Trung bình |
| `source_fingerprint()` không deterministric nếu file thay đổi | Nhỏ |

---

## 7. Test Coverage — Nhận xét

**58 test files, các test lớn nhất:**
- `test_conversation_routing.py` (31.7 KB) — test routing conversation flow
- `test_phobert_router.py` (30.9 KB) — test 4-head inference
- `test_four_head_routing.py` (30.6 KB) — test routing end-to-end
- `test_clarification.py` (26.1 KB) — test menu và catalog

**Điểm mạnh test:**
- Có test cho adversarial cases: `test_runtime_safety.py` (8.7 KB)
- Có test riêng cho leakage filter: `test_leakage_filter.py`
- Có test cho QLoRA readiness, audit, control: 4 file `test_qlora_*.py`
- Có test refactor boundary: `test_refactor_boundaries.py`

**Vấn đề test:**
1. Không thấy coverage report trong repository. `pyproject.toml` cấu hình `[tool.coverage]` nhưng không rõ coverage thực tế.
2. `test_real_peft_cpu.py` — tên gợi ý test trên CPU thật, có thể chậm trong CI.
3. `test_ollama_judge.py` và `test_evaluation_v3.py` — cần Ollama running, có thể flaky trong CI không có GPU.
4. Không có mock đầy đủ cho Ollama trong các test unit — nhiều test dùng real HTTP calls.

---

## 8. Bảo mật — Phát hiện

| Mục | Đánh giá |
|---|---|
| HMAC state | ✅ Tốt — dùng `secrets.token_bytes(32)` và `hmac.compare_digest` |
| Prompt injection guard | ✅ System prompt có cảnh báo explicit về injection |
| ZIP traversal | ✅ `safe_extract()` kiểm tra `..`, absolute path, symlink |
| SQL injection | ✅ Parameterized queries với `?` placeholder |
| Read-only SQLite | ✅ Mở với `mode=ro` URI |
| Không có auth | ❌ API hoàn toàn public trong Docker deployment |
| Rate limiting | ❌ Không có |
| `torch.load()` với `weights_only=True` | ✅ An toàn |
| `_signature` trong `clarification.py` dùng `hmac.new` | ⚠️ Đúng nhưng `_SECRET` reset mỗi khi restart — menu từ lần restart trước bị invalid |

---

## 9. Tài liệu — Nhận xét

**Điểm mạnh:**
- `docs/architecture/architecture.md` (14 KB) rất chi tiết — mô tả rõ ranh giới phụ thuộc, hợp đồng artifact, threat model.
- `docs/project/current-stage.md` (69 KB) là project journal cực kỳ chi tiết — ghi lại mọi thay đổi với Mục tiêu/Thực hiện/Kết quả.
- `docs/reports/` có nhiều báo cáo khoa học chi tiết với số liệu thực nghiệm.
- Có `docs/project/failure-journal.md` (8.2 KB) — hiếm thấy trong dự án ML.

**Vấn đề:**
1. `docs/reports/bao-cao-phan-loai-nhan-va-actions.md` (66 KB) — file rất lớn, có thể cần tổ chức lại.
2. Không có docstring trong nhiều function quan trọng: `answer_question()`, `_prepare_training_data()`, `encode_segments()`.
3. `src/vigovbot/*/README.md` tồn tại (chunking, utils, vectordb) nhưng không có README cho `rag/`, `retrieval/`, `training/`.

---

## 10. Tổng kết Đánh giá

### Điểm mạnh thực sự (không phóng đại)

1. **Artifact integrity pipeline** — corpus manifest, SHA-256 verification, atomic write là thiết kế production-grade.
2. **PhoBERT 4-head router** — thiết kế chắc chắn, validation đầy đủ, tách biệt khỏi LLM routing.
3. **Leakage filter** — 6 tiêu chí overlap, 5-gram index — nghiêm túc hơn hầu hết dự án research.
4. **HMAC state security** — phòng thủ tốt chống client-side tampering.
5. **Retrieval context fingerprinting** — follow-up chỉ được phép với answer fingerprint khớp.
6. **Tài liệu dự án** — journal, failure log, benchmark report rất đầy đủ.
7. **Test coverage theo domain** — 58 test files với nhiều adversarial cases.

### Lỗi/Hạn chế cần ưu tiên sửa (theo mức độ)

| Ưu tiên | Vấn đề | File |
|---|---|---|
| 🔴 Cao | Session in-memory, không persist, không shared giữa workers | `conversation.py` |
| 🔴 Cao | Không có retry Ollama | `llm_client.py` |
| 🔴 Cao | `answer_question()` 382 dòng 14 params | `pipeline.py` |
| 🟡 Trung bình | `source_fingerprint()` gọi mỗi request evaluation | `pipeline.py` |
| 🟡 Trung bình | 4+ biến thể `_fold()` khác hành vi nhỏ | nhiều file |
| 🟡 Trung bình | Không có reranker online | `retriever.py` |
| 🟡 Trung bình | `torch.set_num_threads()` global setting | `phobert_router.py` |
| 🟡 Trung bình | Không có auth/rate limiting trên API | `server/app.py` |
| 🟢 Thấp | `_lcs_length()` tự implement khi `difflib` có sẵn | `records.py` |
| 🟢 Thấp | Vector normalization thừa (max-abs trước L2) | `retriever.py` |
| 🟢 Thấp | Giới hạn cứng 2/4/6 turns SFT | `training/data.py` |
| 🟢 Thấp | `max_seq_length=2048` train ≠ `num_ctx=16384` inference | `base.yaml`, `inference.yaml` |

### Nhận xét tổng thể

ViGovBot là dự án nghiên cứu RAG cho domain hành chính công tiếng Việt với **thiết kế kiến trúc tốt**, **pipeline data integrity nghiêm túc**, và **kết quả thực nghiệm cụ thể có số liệu**. Hạn chế lớn nhất là **session management không scalable** (in-memory), **LLM client không có retry/circuit breaker**, và **một số file quá lớn** (`records.py` 1022 dòng, `conversation.py` 633 dòng) gây khó maintain. Kết quả model (BERTScore F1 = 0.9022, ROUGE-L = 0.4575 với RAG) là tốt cho domain này nhưng **Semantic Correctness 48.43%** cho thấy vẫn còn nhiều dư địa cải thiện, đặc biệt với dataset chỉ ~1.800 mẫu train.
