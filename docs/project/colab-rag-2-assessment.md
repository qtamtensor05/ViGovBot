# Đánh giá mẫu Colab RAG mới — 2026-10-04

## Phạm vi và bằng chứng

Chỉ xét `C:/Users/quangTam/Downloads/2000_main_smoke_rag_2-20261003T171220Z-1-001.zip`.
Không dùng ZIP đầu để chấm hoặc kết luận. ZIP mới chứa config, notebook_run và
23 dòng predictions; không có scores, comparison hoặc `.run.json`. Metadata:
commit `4538217da1d787e53ef275626125e57c3755882a`, Qwen 2.5 7B, free_running,
top_k=5, num_ctx=8192, num_predict=512, embedding CPU; limit=0 là cấu hình chạy,
không chứng minh đã chạy xong. Không có log runtime nên không xác định được vì
sao artifact dừng ở 23 dòng (ngắt thủ công, lỗi notebook hay bản sao lúc đang chạy).

Đối chiếu cả 23 ID và câu hỏi với
`Data/qa_test_v4/rag_tthc_proportional_2000/cases.jsonl`: đều khớp. Nhãn dưới đây
lấy từ snapshot dataset cục bộ, không phải xác minh pháp luật hiện hành hay
human judgment độc lập. ZIP không có cases để xác nhận checksum dataset Colab.

| Chỉ số trên 23 dòng đã lưu | Kết quả |
| --- | ---: |
| Thành công kỹ thuật | 12/23 (52,17%) |
| Lỗi generation trực tiếp | 4/23 (17,39%) |
| Bị chặn do lượt trước thất bại | 7/23 (30,43%) |
| Action khớp nhãn tham chiếu, gồm cả lỗi | 4/23 (17,39%) |
| Action khớp trong 12 lượt thành công | 4/12 (33,33%) |
| Fallback routing trong các kết quả lưu được | 0 |

4 nhãn đúng là 000031, 000032, 000139, 000140. Đúng nhãn không đồng nghĩa
đủ/đúng nội dung. Tổng latency từng dòng khoảng 221,76 giây; không phải wall
time toàn job vì không có run report. Không ngoại suy mẫu đầu sang 2.000 câu.

## Lỗi có bằng chứng

1. 000033, 000084, 000211, 000271 bị `Evidence status and action do not match`.
   Router đã có schema nhưng generation vẫn chỉ dùng JSON mode. Validator
   phát hiện thiếu/sai `evidence_status` hoặc cặp evidence/action không hợp lệ.
   ZIP không lưu raw generation của lượt lỗi nên không xác định được chính xác
   cặp giá trị nào của từng ca. Không được tự đổi nhãn để biến lỗi thành thành công.
2. 000034 bị chặn sau 000033; 000212–000214 sau 000211; 000272–000274 sau
   000271. Đây là bảo vệ tính toàn vẹn free_running, không phải 7 lỗi model độc lập.
3. 000142 nói hồ sơ cá nhân đã được tiếp nhận/đang chờ xử lý dù chỉ có trích đoạn
   quy trình chung. 000141 trả cơ quan nhưng bỏ yêu cầu trạng thái hồ sơ, gán answer
   thay vì partial. Query của 000141 vẫn có cả hai ý: lỗi quan sát nằm ở generation,
   không có bằng chứng router đã bỏ ý ở ca này.
4. 000059 và 000263 hỏi kiểm chứng cơ quan nhưng bị out_of_scope; 000107 và
   000191 bị yêu cầu làm rõ dù nhãn tham chiếu là correct_premise. 000072 và
   000180 có truy vấn gộp hai thủ tục, đáp án chỉ chọn một thủ tục thay vì làm rõ.
5. 000031 hỏi căn cứ pháp lý: đáp án chỉ nêu một nghị định rồi chuyển sang hồ sơ.
   Context được lưu có nhiều chunk từ khóa/hồ sơ, thiếu mục căn cứ pháp lý đầy đủ.
   Đây là hạn chế retrieval và generation cần đánh giá tiếp trên corpus thật.

Không có unit mapping nên chưa chấm recall/MRR đáng tin cậy; không có judgments
nên không công bố điểm correctness/faithfulness. Không coi absence của raw
routing trên 4 lỗi generation là bằng chứng router những lượt đó hoàn hảo.

## Sửa trong mã nguồn

- Schema generation chỉ cho phép năm cặp evidence/action hợp lệ; validator
  vẫn hoạt động. Thử lại một lần với cùng bằng chứng và lỗi validator, chỉ khi
  đủ context. Nếu vẫn lỗi, giữ là lỗi và lưu diagnostics có giới hạn độ dài.
- Adapter giữ diagnostics routing/generation; runner ghi `blocked_by_id` và
  phân biệt lỗi trực tiếp với lượt bị chặn. Không thay history bằng đáp án chuẩn.
- Prompt nhấn mạnh trạng thái hồ sơ cá nhân không có trong tài liệu quy trình,
  câu hỏi hỗn hợp phải trả phần biết và nêu phần thiếu; câu kiểm chứng tiền đề
  sai vẫn in_scope; nhiều thủ tục chưa rõ phải làm rõ. Giữ câu hỏi gốc bên cạnh
  truy vấn follow-up để giảm nguy cơ mất ý trong các trường hợp viết lại khác.
- Pipeline version 5; provider OpenAI-compatible bọc schema đáp án riêng với routing.

## Kiểm chứng và chạy tiếp

Kiểm thử offline xác nhận schema, retry thành công/thất bại, giữ cùng evidence,
giới hạn context, diagnostics và không tiếp tục chuỗi free-running đã lỗi.
Các thay đổi prompt là biện pháp cải thiện, chưa chứng minh đã sửa được lỗi ngữ
nghĩa của Qwen. Ollama local tại localhost:11434 không hoạt động khi kiểm tra;
chưa chạy lại model thật hay Colab GPU, chưa đo lại chất lượng retrieval.

Khi chạy Colab: dùng commit chứa bản sửa, RUN_NAME mới, thử LIMIT=23 hoặc 30
trước; kiểm tra diagnostics và đọc thủ công các ca nêu trên. Chỉ chạy toàn bộ
khi smoke ổn. Cần output mới vì runner chưa hỗ trợ resume; không sửa đè ZIP gốc.
