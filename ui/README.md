# ViGovBot Next.js UI

Giao diện này gọi FastAPI của ViGovBot; không kết nối trực tiếp Neo4j và không
chứa mật khẩu graph. FastAPI phải được chạy trước, mặc định tại cổng `8000`.

## Chạy cục bộ

```bash
cp .env.example .env.local
npm run dev
```

Mở `http://127.0.0.1:3000`. Muốn đổi endpoint, đặt
`NEXT_PUBLIC_API_BASE_URL` trong `.env.local`, ví dụ khi API chạy cổng khác.

## API cần có

- `GET /api/models`
- `POST /api/chat`
- `POST /api/chat/stream`
- `GET /api/health`

Khởi động backend GraphRAG từ gốc repository:

```bash
uv run --extra rag python -m vigovbot rag --config configs/rag-graph.yaml api --port 8000
```

`mode: graphrag` hiển thị ngữ cảnh procedure/agency/legal document được backend
truy vấn từ Neo4j. `mode: rag` chỉ dùng vector retrieval.

## Tiến độ hỏi đáp

UI gửi câu hỏi tới `POST /api/chat/stream` và đọc Server-Sent Events (SSE) qua
`fetch`. Backend lần lượt phát event `progress` cho các pha hàng đợi, phân tích
câu hỏi, truy xuất vector, truy xuất Neo4j, Qwen sinh câu trả lời và kiểm tra đầu
ra; event `result` giữ cùng mảng `results` như `POST /api/chat`. Nhờ đó UI hiện
được công việc đang chạy cùng thời gian chờ, còn `POST /api/chat` vẫn dành cho
client cần một JSON hoàn chỉnh.

Khi `conversation.routing_enabled: true`, Qwen sinh JSON có schema và câu trả lời
chỉ được hiển thị sau khi parser kiểm tra cấu trúc/bằng chứng. UI không hiển thị
token JSON dở dang như câu trả lời cuối vì chúng có thể bị retry hoặc bị từ chối.

UI mặc định chọn một mode GraphRAG khi mode này có mặt. Có thể chọn thêm mode Vector
RAG để so sánh, nhưng backend cố ý chạy tuần tự để giữ một phiên model/Ollama ổn định;
thời gian chờ khi đó là tổng thời gian của các mode đã chọn.
