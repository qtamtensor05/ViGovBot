# GraphRAG với Neo4j, FastAPI và Next.js

## Mục tiêu và ranh giới

GraphRAG là đường đi **hybrid**: BGE-M3/FAISS vẫn truy hồi các trích đoạn nguồn,
sau đó Neo4j bổ sung procedure, cơ quan xử lý và căn cứ pháp lý liên quan. Nó không
thay thế vector RAG, không ghi Neo4j trong lúc trả lời và không đưa mật khẩu/driver
Neo4j vào Next.js.

| Mode | Hành vi |
|---|---|
| `base` | Gọi model trực tiếp, không retrieval |
| `rag` | Chỉ vector RAG hiện có |
| `graphrag` | Vector RAG + graph context từ Neo4j |

Khi `graph.enabled: false`, driver Neo4j không được tạo; `base` và `rag` hoạt động
như trước. Khi graph không khả dụng, chỉ kết quả model `graphrag` báo lỗi, không làm
ngừng API hoặc các mode còn lại.

## Schema Neo4j đã xác nhận

Dump local hiện có các node `Procedure`, `Agency`, `LegalDocument`, `Field` và quan
hệ `LEGAL_BASIS`, `CONTAINS`, `HANDLED_BY`, `AUTHORIZED_BY`, `COORDINATED_BY`,
`DELEGATED_TO`. Truy vấn GraphRAG chỉ bắt đầu ở `Procedure`, giới hạn số procedure/
quan hệ bằng YAML và dùng Cypher parameterized; không nội suy nguyên câu hỏi vào
Cypher.

## Lập kế hoạch truy vấn

Router Qwen hiện có đồng thời phân loại hội thoại và trả `graph_plan`; không tạo
thêm lượt gọi model. Plan chỉ gồm `procedure_code`, `procedure_name`, `agency`,
`legal_basis`, `field` và danh sách relationship được ưu tiên. Sau khi kiểm tra kiểu,
độ dài và whitelist nhãn quan hệ, Neo4j dùng plan để lọc procedure và node lân cận
theo các nhãn đã xác nhận. Cypher vẫn chỉ nhận parameterized values.

GraphRAG ưu tiên vector-first: BGE-M3/FAISS trả các `source_code` trước, rồi Neo4j
chỉ mở neighbourhood của các `Procedure.procedure_code` tương ứng. Khi metadata
không có mã, truy vấn dùng full-text index của Neo4j; nếu index chưa được tạo thì
mới fallback sang token scan cũ. `relationship_types` chỉ ưu tiên quan hệ trong
context trả về, không tự khẳng định chúng là bằng chứng cho câu trả lời.

Để tránh một lượt Qwen chỉ dùng cho định tuyến ở các truy vấn rõ ràng, pipeline bỏ
qua router cho mã thủ tục có dạng số chấm và câu hỏi độc lập đủ dài có keyword thủ
tục (ví dụ `quy trình`, `hồ sơ`, `thời hạn`). Câu ngắn hoặc bắt đầu bằng đại từ/cụm
nối tiếp vẫn phải qua router để được hỏi làm rõ. Khi một entity plan lọc rỗng mã đã
được vector xác nhận, retriever bỏ entity filter đó và giữ candidate theo mã.

## Cấu hình

`configs/rag-graph.yaml` là cấu hình mẫu. Phần `graph` chỉ chứa endpoint, database,
tên user và **tên biến môi trường** chứa mật khẩu:

```yaml
graph:
  enabled: true
  uri: bolt://127.0.0.1:7687
  database: neo4j
  username: neo4j
  password_env: NEO4J_PASSWORD
  max_procedures: 3
  max_relationships: 6
  max_context_chars: 2400
  query_timeout_s: 5
  wait_timeout_s: 6
  cache_ttl_s: 120
  cache_max_entries: 128
```

Đặt `NEO4J_PASSWORD` trong `.env` hoặc môi trường shell, không ghi mật khẩu vào YAML
hay `ui/.env.local`. `max_context_chars` bị chặn trước khi đưa dữ liệu graph vào
prompt để giữ ngân sách context của model. `query_timeout_s` giới hạn Cypher tại
Neo4j; `wait_timeout_s` giới hạn thời gian request API chờ graph trước khi tiếp tục
với vector RAG. Cache chỉ giữ graph context bất biến trong bộ nhớ process.

## Chạy local

Từ gốc repository:

```bash
uv pip install -e ".[rag,dev]"
docker compose up -d
uv run --extra rag python -m vigovbot rag --config configs/rag-graph.yaml graph-index
uv run --extra rag python -m vigovbot rag --config configs/rag-graph.yaml api --port 8000
```

Sau đó ở terminal khác:

```bash
cd ui
cp .env.example .env.local
npm run dev
```

Mở `http://127.0.0.1:3000`. Next.js gọi FastAPI ở `NEXT_PUBLIC_API_BASE_URL`
(mặc định `http://127.0.0.1:8000`); FastAPI chỉ cho phép các origin local cổng 3000.

FastAPI duy trì cùng contract với web server cũ:

- `GET /api/health`
- `GET /api/models`
- `POST /api/chat`
- `POST /api/chat/stream`

`/api/chat/stream` nhận đúng payload của `/api/chat` nhưng trả Server-Sent Events:
`progress` chứa `stage`, `label`, và model đang chạy; `result` chứa mảng `results`
cùng contract cũ; `error` chỉ dùng khi lỗi hạ tầng không thể tạo result. Next.js
dùng endpoint này để hiện pha vector/Neo4j/Qwen cùng thời gian chờ. Đầu ra có schema
vẫn chỉ xuất hiện sau khi được xác thực, tránh hiển thị JSON hoặc bằng chứng chưa hợp
lệ như một câu trả lời hoàn chỉnh.

Lệnh cũ `vigovbot rag ... web` vẫn chạy `ThreadingHTTPServer` và không bị thay thế.
Lệnh mới `api` chạy FastAPI cho Next.js.

## Kiểm chứng

```bash
python -m unittest tests.test_graphrag tests.test_server tests.test_fastapi_server tests.test_rag_config_cli -v
cd ui && npm run lint && npm run build
```

Các test GraphRAG dùng driver Neo4j mô phỏng; chúng không sửa graph. Kiểm thử tích hợp
thật cần Neo4j/Ollama/corpus tương thích và nên thực hiện với thư mục output riêng.
`graph-index` chỉ tạo range index `vigovbot_procedure_code` và full-text index
`vigovbot_procedure_text` nếu chưa có; không ghi hoặc thay đổi dữ liệu thủ tục.
