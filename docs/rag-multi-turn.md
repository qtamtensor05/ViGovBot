# Đánh giá RAG nhiều lượt với qa_test_v4

RAG nhận `history` là danh sách các cặp `{"role": "user", "content": "..."}` /
`{"role": "assistant", "content": "..."}`. Mặc định, mỗi câu hỏi đi qua bước phân
loại bằng LLM hiện tại, kể cả lượt đầu. Bước này chỉ nhận câu hỏi và lịch sử.

## Điều hướng hội thoại và xét bằng chứng

```text
Câu hỏi + lịch sử → Phân loại phạm vi và quan hệ ngữ cảnh
  ├─ Ngoài phạm vi → Thông báo phạm vi hỗ trợ (abstain)
  ├─ Mơ hồ → Hỏi làm rõ (clarify)
  ├─ Câu hỏi mới → Truy vấn gốc, không kèm lịch sử
  └─ Hỏi tiếp → Truy vấn độc lập đã giải quyết ngữ cảnh
                       ↓
                 Truy hồi tài liệu
                       ↓
        Xét bằng chứng trong prompt và sinh câu trả lời
```

Router trả `scope` (`in_scope` / `out_of_scope`) và `relation`
(`new_question` / `follow_up` / `ambiguous`). Câu hỏi mới dùng nguyên câu hỏi người
dùng để tránh router vô tình đưa chủ đề cũ vào truy vấn. Câu hỏi tiếp dùng `query`
đã được router viết lại, ưu tiên thông tin người dùng sửa hoặc bổ sung gần nhất.
Prompt trả lời chỉ nhận truy vấn đã giải quyết và tài liệu; không đưa lại các câu
trả lời cũ hoặc chủ đề cũ. Lịch sử đầy đủ vẫn được giữ cho router ở lượt kế tiếp.

Nhánh mơ hồ/ngoài phạm vi không truy hồi và không gọi LLM sinh câu trả lời lần hai.
Nếu không có trích đoạn nào thực sự vào prompt, hệ thống trả `abstain` trực tiếp.
Nếu có tài liệu, bước sinh trả JSON với `answer`, `action`, `evidence_status`:

| evidence_status | action | Xử lý |
|---|---|---|
| sufficient | answer | Đủ bằng chứng cho toàn bộ câu hỏi |
| partial | partial | Trả lời phần có bằng chứng, nêu phần thiếu |
| missing | abstain | Không tìm thấy bằng chứng phù hợp |
| contradictory_premise | correct_premise | Có bằng chứng bác bỏ tiền đề |
| ambiguous | clarify | Cần làm rõ đối tượng sau khi đọc tài liệu |

Đánh giá bằng chứng diễn ra trong cùng lần gọi sinh câu trả lời; không có model
judge riêng. Code kiểm tra schema và sự nhất quán giữa action/evidence_status,
không thể chứng minh nội dung là đúng. Chất lượng phân loại và bằng chứng vẫn cần
đo với mô hình thật. JSON hoặc nhãn sai được ghi lỗi, không tự đổi thành `answer`.

Prompt tính lịch sử trong ngân sách token của router; vượt giới hạn sẽ báo lỗi,
không âm thầm cắt mất thông tin. Lượt trả lời thông thường cần hai lần gọi LLM
(phân loại kiêm viết lại, rồi xét bằng chứng kiêm trả lời).

```yaml
conversation:
  routing_enabled: true
```

Đặt `false` để chạy đối chứng với cơ chế cũ: có lịch sử thì viết lại truy vấn,
đưa lịch sử vào prompt, không phân loại trước truy hồi. Dùng thư mục output riêng
cho mỗi cấu hình. Embedding và FAISS không thay đổi.

## Chạy đánh giá

Dùng môi trường đã cài `vigovbot[rag]`, Ollama và corpus tương thích với cấu hình
`rag_config.yaml`. Từ thư mục gốc repository, chạy:

```powershell
python -m vigovbot.evaluation.multiturn --config rag_config.yaml --view Data/qa_test_v4/rag_tthc_v4_1/views_balanced.json --split test --mode free_running --output-dir outputs/v4_free_running
```

Mặc định đầu vào là `Data/qa_test_v4/rag_tthc_v4_1/runner_queries.jsonl`.
Có thể đổi bằng `--queries`. Runner này dùng `--view` và `--split`, không dùng
`evaluation.max_cases` hoặc dataset cũ trong YAML. Không giới hạn số lượt để tránh
cắt giữa hội thoại; để chạy thử, tạo view JSON gồm ID của một vài hội thoại đầy đủ.

- `free_running`: các ca có `conversation_id` sử dụng câu trả lời mô hình ở lượt
  trước; kiểm tra thứ tự liên tục từ lượt 1. Một lượt lỗi chặn các lượt sau của cùng
  hội thoại, các hội thoại khác vẫn chạy.
- `reference_history`: dùng `history` của từng ca trong bộ test. Đây là đánh giá
  với lịch sử tham chiếu, cần báo cáo riêng. Đổi `--mode reference_history` và dùng
  thư mục đầu ra mới.
- Các ca độc lập (`conversation_id=null`) giữ lịch sử tình huống có sẵn ở cả hai
  chế độ, đúng hành vi của `run_http.py` trong bộ v4; không nối lịch sử giữa các ca.

Runner không đọc `cases.jsonl`, đáp án hiện tại, required facts hoặc evidence.
Mô hình tự sinh `answer` và nhãn `action` dưới dạng JSON; JSON sai được ghi lỗi.
`predictions.jsonl` tương thích evaluator v4 và có `history_mode`, truy vấn viết lại,
ID hội thoại, số lượt, thời gian cùng thông tin truy hồi. Các trường `routing`,
`decision_reason`, `evidence_status` giúp kiểm tra từng quyết định. `routing_seconds`
đo bước phân loại, `retrieval_seconds` chỉ đo tìm kiếm, `generation_seconds` đo sinh
câu trả lời; `latency_seconds` đo toàn bộ lượt. Nhánh không thực hiện tìm kiếm/sinh
có thời gian tương ứng bằng 0. Evaluator v4 giữ các trường bổ sung nhưng chưa tổng
hợp riêng độ chính xác router; không dùng nhãn action làm nhãn đúng cho relation.

Chạy lại cùng lệnh sẽ tiếp tục từ các dòng đã lưu, dựng lại lịch sử từ câu trả lời
đã sinh. Các dòng lỗi đã lưu được giữ nguyên; muốn thử lại lỗi hãy dùng thư mục
đầu ra mới. Manifest ngăn trộn cấu hình, dữ liệu, mã nguồn hoặc chế độ khác nhau.
Lệnh trả exit code 1 nếu có ca lỗi.

## Chấm bằng evaluator có sẵn

```powershell
python Data/qa_test_v4/rag_tthc_v4_1/evaluate.py --cases Data/qa_test_v4/rag_tthc_v4_1/cases.jsonl --predictions outputs/v4_free_running/predictions.jsonl --view Data/qa_test_v4/rag_tthc_v4_1/views_balanced.json --split test --out outputs/v4_free_running/scores.json
```

Cài dependencies của evaluator từ `Data/qa_test_v4/rag_tthc_v4_1/requirements.txt`.
Thêm `--judgments` để tính các chỉ số cần đánh giá ngữ nghĩa, trong đó có
conversation behavior success; nhãn action tự khai không chứng minh câu trả lời đúng.

Corpus hiện tại dùng `chunk_id`, chưa ánh xạ sang `unit_id` chuẩn của v4. Runner
ghi `retrieved_chunk_ids`, không giả định chúng là `retrieved_unit_ids`. Do đó
không diễn giải điểm Recall/MRR/Hit Rate do evaluator trả về cho output này trước
khi bổ sung ánh xạ bằng chứng đã kiểm duyệt.

## Hỏi nối tiếp ngoài đánh giá

```powershell
python -m vigovbot.rag --config rag_config.yaml ask --question "Còn lệ phí thì sao?" --history history.json
```

`history.json` là mảng message user/assistant trước câu hỏi hiện tại. Python API:
`answer_question(question, retriever, tokenizer, settings, history=history)`.
Các lời gọi không truyền history vẫn hợp lệ và được phân loại như lượt đầu.
`clarify`/`abstain` là kết quả hợp lệ: runner lưu câu trả lời và tiếp tục lượt kế
tiếp. Chỉ lỗi kỹ thuật/đầu ra sai schema mới chặn các lượt phụ thuộc.
