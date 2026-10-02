# Hướng dẫn vận hành pipeline RAG

Tài liệu quy định quy trình tạo corpus, khởi tạo hệ thống truy hồi, thực hiện truy
vấn và chạy đánh giá đối với package `vigovbot` phiên bản 0.2.0. Các lệnh được
thực thi từ thư mục gốc repository. Kết quả kiểm chứng được quản lý riêng tại
[báo cáo kiểm chứng](verification.md).

## 1. Tổng quan

ViGovBot là pipeline tra cứu thủ tục hành chính tiếng Việt theo mô hình **Retrieval-Augmented Generation (RAG)**: tìm các đoạn tài liệu liên quan trước, sau đó đưa chúng cùng câu hỏi vào mô hình sinh câu trả lời.

Hệ thống hiện chạy bằng CLI Python hoặc notebook Colab, hỗ trợ hỏi đáp từng câu và đánh giá theo bộ câu hỏi. Mã xử lý chính nằm trong `src/vigovbot/`; các module `src/*` cũ được giữ để tương thích.

| Thành phần | Cách sử dụng hiện tại |
|---|---|
| Nguồn tri thức | PDF thủ tục hành chính, trích xuất thành Markdown; hỗ trợ OCR |
| Chia tài liệu | Chia theo cấu trúc mục, sau đó tách thành các chunk nhỏ có thông tin thủ tục |
| Mô hình embedding | `BAAI/bge-m3`, dùng `SentenceTransformer`, vector dense 1024 chiều |
| Chỉ mục tìm kiếm | FAISS `IndexFlatIP`, vector chuẩn hóa L2 |
| Nội dung và metadata khi truy vấn | SQLite, tra theo vị trí vector trong FAISS |
| Mô hình sinh | `qwen2.5:7b` chạy qua Ollama |
| Tokenizer tính ngân sách prompt | `Qwen/Qwen2.5-7B-Instruct` |
| Cách giao tiếp với LLM | HTTP `POST /api/chat`, `stream: false` |

Đây là RAG một lượt với truy hồi dense. Luồng hiện tại không dùng BM25/hybrid search, reranker, viết lại câu hỏi, agent hay bộ nhớ hội thoại. Pipeline không có bước huấn luyện, fine-tune, QLoRA hoặc API web.

## 2. Kiến trúc và luồng dữ liệu

```mermaid
flowchart TD
    subgraph A[Chuẩn bị kho tri thức]
        P[PDF] --> X[Trích xuất / OCR và làm sạch Markdown]
        X --> C[Chia mục và tạo JSON chunk]
        C --> E[BGE-M3: embedding tài liệu]
        E --> N[Chuẩn hóa L2]
        N --> F[FAISS + metadata JSON + corpus manifest]
    end
    F --> S[Prepare: cache FAISS và metadata SQLite]
    subgraph B[Hỏi đáp]
        Q[Câu hỏi tiếng Việt] --> QE[BGE-M3 và chuẩn hóa L2]
        QE --> R[FAISS: lấy top 5 chunk]
        R --> D[SQLite: lấy nội dung và nguồn]
        D --> T[Ghép prompt trong ngân sách token]
        T --> L[Qwen2.5-7B qua Ollama]
        L --> O[Câu trả lời + nguồn + thời gian xử lý]
    end
    S --> R
    S --> D
```

### 2.1. Trích xuất và chia chunk

Lệnh `ingest` đọc PDF theo `configs/pipeline.yaml`, dùng cấu hình trích xuất tại `configs/ingestion.yaml` và cấu hình chia đoạn tại `configs/chunking.yaml`.

- PDF đầu vào mặc định: `Data/pdf`; giới hạn kích thước mỗi PDF: 20 MB.
- OCR được bật, ngôn ngữ `vie+eng`, DPI 300, chế độ `full: true`; cần Tesseract/tessdata tương ứng khi thực hiện OCR.
- Markdown được làm sạch rồi chia theo các mục như trình tự thực hiện, thành phần hồ sơ, cách thức/thời hạn/phí và căn cứ pháp lý.
- Cấu hình chunk: mục tiêu 1.200 ký tự, tối đa 1.500 ký tự, overlap 100 ký tự và nội dung tối thiểu 10 ký tự. Việc chia còn phụ thuộc ranh giới mục, khối văn bản và bảng; không phải mọi chunk đều có cùng độ dài.
- Chunk có prefix dạng `[Thủ tục: ... | Mã TTHC: ... | Mục: ...]`. Giới hạn tối đa tính cả prefix; prefix có thể được rút gọn để vừa ngân sách.

Mỗi chunk gồm `chunk_id`, `source_file`, `source_code`, `procedure_name`, `section_type`, `context_prefix`, `text_content` và `parent_section`. Nội dung `text_content` đã chứa prefix. Pipeline embedding chỉ bổ sung prefix nếu chưa có, tránh lặp lại.

Đầu ra bình thường là `outputs/metadata/<tên-PDF>.json`. Báo cáo xử lý nằm trong `outputs/metadata/reports/`; tài liệu cần rà soát được đưa vào `outputs/metadata/review/`. Cần đọc báo cáo và kiểm tra các trường hợp thiếu trang hoặc metadata trước khi đưa vào kho tri thức.

### 2.2. Embedding và tạo chỉ mục

Lệnh `embed` đọc toàn bộ JSON chunk từ một thư mục hoặc ZIP, tạo vector BGE-M3,
chuẩn hóa L2 và xây dựng FAISS `IndexFlatIP` trong cùng một pipeline. Corpus gồm:

```text
Data/vector/unified/
    tthc_unified.index
    tthc_unified_metadata.json
    corpus_manifest.json
```

Với vector tài liệu và câu hỏi đều có độ dài L2 bằng 1, tích vô hướng mà FAISS trả về tương đương cosine similarity. Điểm càng lớn thì vector càng gần nhau; đây không phải xác suất câu trả lời đúng. `IndexFlatIP` thực hiện tìm kiếm chính xác trên các vector trong chỉ mục.

Manifest ghi model, revision thực tế được phân giải thành commit SHA, số bản ghi và
checksum. Ba artifact chỉ được công bố sau khi toàn bộ pipeline hoàn thành.

### 2.3. Chuẩn bị cache truy vấn

Lệnh `rag prepare` xác minh corpus, sao chép index vào cache và chuyển metadata JSON sang SQLite bằng cách đọc theo luồng. Cache nằm dưới `outputs/rag_cache/<định-danh>/`, gồm index, `metadata.sqlite` và `ready.json`.

`row_id` trong SQLite chính là vị trí vector, bắt đầu từ 0. Hệ thống kiểm tra số dòng, chiều vector, loại metric và checksum để tránh dùng nhầm index với metadata. SQLite chỉ giữ các trường cần truy hồi; `parent_section` không được đưa vào cache, nên luồng hỏi đáp không tự mở rộng chunk thành toàn bộ mục cha.

### 2.4. Xử lý một câu hỏi

1. Nạp BGE-M3 cùng model/revision với corpus. Nếu `embedding.revision: null` và corpus có manifest hợp lệ, hệ thống lấy revision từ manifest.
2. Encode câu hỏi thành vector 1024 chiều, chuẩn hóa L2 rồi tìm tối đa `top_k = 5` kết quả.
3. Tra SQLite để lấy nội dung chunk và thông tin nguồn của từng kết quả.
4. Ghép system prompt, câu hỏi và các trích đoạn theo thứ tự truy hồi; dùng tokenizer Qwen để giới hạn độ dài.
5. Gọi Ollama để sinh câu trả lời tiếng Việt.
6. Trả về JSON gồm câu trả lời, kết quả truy hồi, phần ngữ cảnh thực sự đã dùng và thời gian xử lý.

System prompt yêu cầu chỉ dựa trên trích đoạn, không tự suy đoán phí/thời hạn/cơ quan/quy định, nói rõ khi thiếu thông tin và bỏ qua chỉ dẫn nằm trong tài liệu. Nguồn được lưu riêng, không bắt buộc LLM liệt kê trong câu trả lời. Đây là hướng dẫn cho mô hình, không phải cơ chế bảo đảm tuyệt đối rằng câu trả lời luôn đúng.

## 3. Tham số RAG đang dùng

`configs/inference.yaml` dùng cho hỏi đáp; các tham số không khai báo lấy mặc định từ `src/vigovbot/rag/config.py`. `configs/rag.yaml` khai báo thêm dữ liệu và đầu ra đánh giá.

| Tham số | Giá trị mặc định / cấu hình hiện tại | Ý nghĩa |
|---|---|---|
| `embedding.model` | `BAAI/bge-m3` | Encoder cho câu hỏi |
| `embedding.device` | `cpu` | Dành VRAM cho Qwen; có thể đổi khi đủ tài nguyên |
| `llm.model` | `qwen2.5:7b` | Tên model trong Ollama |
| `llm.ollama_url` | `http://localhost:11434` | Địa chỉ Ollama |
| `llm.temperature` | `0.0` | Giảm tính ngẫu nhiên |
| `llm.seed` | `42` | Seed gửi cho Ollama |
| `llm.num_ctx` | `8192` | Cửa sổ ngữ cảnh yêu cầu |
| `llm.num_predict` | `512` | Số token sinh tối đa |
| `llm.timeout` | `300` giây | Timeout HTTP khi sinh câu trả lời |
| `llm.keep_alive` | `10m` | Tham số giữ model gửi trong request; pipeline yêu cầu dỡ model khi đóng phiên |
| `retrieval.top_k` | `5` | Số chunk truy hồi tối đa |
| `retrieval.max_chunk_tokens` | `1200` | Giới hạn token của mỗi chunk đưa vào prompt |
| `data.allow_legacy_corpus` | `false` | Mặc định yêu cầu corpus có provenance/manifest |

Ngân sách prompt là `8192 - 512 - 256 = 7424` token, trong đó 256 token được dự phòng cho template Ollama. Ngân sách này bao gồm system prompt, câu hỏi và trích đoạn. Chunk có thể bị cắt ngắn hoặc không được đưa vào khi hết chỗ. `max_chunk_tokens` tính bằng **token**, khác với tham số chunking tính bằng **ký tự**.

## 4. Triển khai trên máy cục bộ

### 4.1. Chuẩn bị môi trường

Repository khai báo Python 3.10–3.14. Ví dụ sau dùng PowerShell và gọi trực tiếp Python trong venv, không cần kích hoạt môi trường:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[pdf,embedding,vector,rag,evaluation]"
.venv\Scripts\python -m vigovbot --help
```

Linux/macOS thay `.venv\Scripts\python` bằng `.venv/bin/python`. Cách dùng dependency lock theo nền tảng được mô tả trong [Môi trường và tái lập](environments.md).

Cài Ollama và tải model bằng lệnh:

```powershell
ollama pull qwen2.5:7b
ollama list
```

Ollama cần phục vụ tại địa chỉ cấu hình. Nếu dịch vụ chưa chạy, mở terminal riêng và chạy `ollama serve`. Lần đầu chạy pipeline cần mạng để tải BGE-M3, tokenizer Qwen và, nếu tạo báo cáo đánh giá, model BERTScore. OCR cần cài riêng Tesseract cùng dữ liệu ngôn ngữ Việt/Anh.

### 4.2. Tạo corpus từ PDF

Đặt PDF vào `Data/pdf`, rồi chạy:

```powershell
.venv\Scripts\python -m vigovbot ingest --config configs/pipeline.yaml
```

Kiểm tra JSON và báo cáo trong `outputs/metadata`. Pipeline embedding có thể nhận
trực tiếp thư mục này hoặc một ZIP chỉ chứa các JSON chunk đã rà soát. Không đưa
`reports/` và `review/` vào nguồn embedding.

```powershell
.venv\Scripts\python -m vigovbot embed outputs/metadata --output-dir Data/vector/unified-new
```

Ví dụ sử dụng `unified-new` vì pipeline từ chối ghi đè corpus đã tồn tại. Với dữ
liệu lớn, điều chỉnh `--batch-size`, `--device` và tài nguyên máy. Pipeline nhận
một nguồn dữ liệu và công bố trực tiếp corpus hoàn chỉnh.

Đổi `data.unified_source` trong cấu hình cần chạy thành `../Data/vector/unified-new`. Các đường dẫn trong YAML được tính từ **thư mục chứa YAML**, còn đường dẫn truyền trực tiếp qua CLI được tính theo thư mục làm việc.

### 4.3. Dùng corpus có sẵn trong workspace

Tại thời điểm kiểm tra, `Data/vector/unified/` có `tthc_unified.index` và `tthc_unified_metadata.json`, nhưng chưa có `corpus_manifest.json`. Vì vậy, cấu hình mặc định `allow_legacy_corpus: false` sẽ không chấp nhận bộ dữ liệu này.

Có thể tạo lại corpus theo bước 4.2 để có manifest và revision xác minh được. Nếu cần chạy bộ hiện có, tạo file riêng `configs/inference-local.yaml`:

```yaml
data:
  unified_source: ../Data/vector/unified
  cache_dir: ../outputs/rag_cache_legacy
  allow_legacy_corpus: true
embedding:
  model: BAAI/bge-m3
  revision: null
  device: cpu
llm:
  model: qwen2.5:7b
  ollama_url: http://localhost:11434
```

Chế độ legacy vẫn kiểm tra cấu trúc index và metadata nhưng không xác minh được model/revision đã tạo vector tài liệu. Khi thiếu manifest, `revision: null` không thể tự khôi phục revision gốc. Chi tiết tại [Migration dữ liệu cũ](migration.md).

### 4.4. Chuẩn bị và hỏi đáp

Với corpus mới đã cập nhật trong `configs/inference.yaml`:

```powershell
.venv\Scripts\python -m vigovbot rag --config configs/inference.yaml prepare
.venv\Scripts\python -m vigovbot rag --config configs/inference.yaml ask --question "Cần những giấy tờ gì để cấp bản sao hộ tịch?"
```

Nếu dùng corpus cũ theo bước 4.3, thay đường dẫn cấu hình trong cả hai lệnh bằng `configs/inference-local.yaml`. `prepare` chỉ chuẩn bị corpus/cache, chưa tải encoder hoặc gọi LLM; `ask` cũng tự chuẩn bị/kiểm tra cache trước khi truy vấn. Hỏi đáp không cần bộ câu hỏi đánh giá.

Kết quả `ask` được in dưới dạng JSON:

| Trường | Nội dung |
|---|---|
| `prediction` | Câu trả lời của Qwen |
| `retrieved` | Các chunk đã tìm được, kèm ID, điểm, file và mã thủ tục |
| `context_used` | Nguồn và phần văn bản thực sự đưa vào prompt sau khi cắt token |
| `prompt_tokens_estimated` | Số token prompt ước tính bằng tokenizer Qwen |
| `retrieval_s`, `generation_s`, `latency_s` | Thời gian truy hồi, sinh và xử lý câu hỏi; không gồm toàn bộ thời gian khởi tạo CLI/model |
| `raw_ollama` | Phản hồi gốc từ Ollama |

`retrieved` có thể nhiều nội dung hơn `context_used`; khi kiểm tra căn cứ câu trả lời, cần xem phần thực sự được đưa vào prompt.

## 5. Chạy đánh giá

Chuẩn bị `Data/qa_test/dataset.jsonl` hoặc cấu hình `dataset_zip`. Kiểm tra `unified_source`, chế độ legacy nếu cần và chọn `output_dir` phù hợp trong `configs/rag.yaml`.

```powershell
.venv\Scripts\python -m vigovbot rag --config configs/rag.yaml smoke
.venv\Scripts\python -m vigovbot rag --config configs/rag.yaml run
```

`smoke` thử tối đa 5 câu theo cấu hình hiện tại. `run` thực hiện chuẩn bị, smoke test, đánh giá rồi tạo báo cáo. Có thể dùng riêng `evaluate` để sinh kết quả và `report` để tính metric/tạo báo cáo. `max_cases: null` nghĩa là dùng toàn bộ bộ dữ liệu đã nạp; có thể đặt số nhỏ khi thử nghiệm.

Đầu ra mặc định ở `outputs/qwen2_5_7b_rag_results`, có manifest lần chạy, kết quả dự đoán, lỗi nếu có, `case_metrics.jsonl`, `case_metrics.csv`, `summary.json` và báo cáo theo nhóm. Metric gồm exact match, accuracy chuẩn hóa, BLEU-4, ROUGE, BERTScore, source recall@k và thời gian xử lý. BERTScore mặc định dùng `xlm-roberta-large` trên CPU, batch size 1.

Manifest gắn kết quả với code, cấu hình, dữ liệu, corpus, môi trường và digest model Ollama. Chọn thư mục đầu ra mới khi thay đổi thí nghiệm để không trộn kết quả không tương thích.

## 6. Colab và giới hạn hiện tại

Notebook tạo corpus: `ipynb/build_corpus.ipynb`; notebook RAG:
`ipynb/base_rag/lqwen2_5_7B_rag.ipynb`. Notebook cài package từ checkout và tạo
cấu hình riêng. Cần chọn `GIT_REF` đã có trên GitHub và chuyển đủ ba artifact
corpus giữa các môi trường.

Các điểm cần tính đến khi sử dụng:

- Truy hồi hiện lấy top-k mà chưa có ngưỡng điểm tối thiểu hoặc reranker. Câu hỏi ngoài kho tri thức vẫn có thể nhận các chunk ít liên quan; việc từ chối trả lời chủ yếu dựa vào prompt và hành vi LLM.
- Lỗi OCR, thiếu trang, chunk bị cắt hoặc dữ liệu thủ tục chưa cập nhật đều có thể làm câu trả lời thiếu/sai. Pipeline không tự kiểm chứng hiệu lực của nội dung nguồn.
- SQLite giúp đọc metadata theo nhu cầu, nhưng FAISS vẫn nạp chỉ mục vào RAM; bước tạo corpus giữ metadata và ma trận vector trong RAM. Cần tính tài nguyên theo corpus và model thực tế, chưa có cấu hình RAM/VRAM tối thiểu được đảm bảo trong mã nguồn.
- Chưa có dịch vụ web, xác thực người dùng, lịch sử hội thoại hoặc triển khai production đi kèm. Cách triển khai hiện có là CLI/notebook cùng tiến trình Ollama.

## 7. Đối chiếu với mã nguồn

| Nội dung | File chính |
|---|---|
| Entry point CLI | [cli.py](../src/vigovbot/cli.py) |
| Trích xuất và xuất JSON | [indexing.py](../src/vigovbot/pipelines/indexing.py) |
| Chunking theo cấu trúc | [markdown.py](../src/vigovbot/chunking/markdown.py) |
| Tạo embedding và corpus FAISS | [corpus_builder.py](../src/vigovbot/embeddings/corpus_builder.py) |
| Cache SQLite | [vector_store.py](../src/vigovbot/vectordb/vector_store.py) |
| Truy hồi | [retriever.py](../src/vigovbot/retrieval/retriever.py) |
| Prompt và ngân sách token | [prompt_templates.py](../src/vigovbot/prompts/prompt_templates.py) |
| Gọi Ollama | [llm_client.py](../src/vigovbot/llm/llm_client.py) |
| Điều phối RAG | [pipeline.py](../src/vigovbot/rag/pipeline.py) |
| Giá trị cấu hình mặc định | [config.py](../src/vigovbot/rag/config.py) |
