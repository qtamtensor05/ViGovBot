# Báo cáo lọc nguy cơ data leak cho RAG-SFT

## Mục tiêu

Làm sạch train/validation trước khi huấn luyện và đánh giá trên hợp hai benchmark
`test_rag_pa1.jsonl` và `test_rag_pa2.jsonl`, không sửa dữ liệu nguồn hoặc test.

## Thực hiện

Policy `strict_procedure_and_content_disjoint` loại một case khi có ít nhất một
dấu hiệu mạnh: trùng test ID, standalone query, context ID, context text, đáp án
dài từ 200 ký tự chuẩn hóa hoặc mã thủ tục. Near-query dùng character 5-gram,
token-Jaccard prefilter và `SequenceMatcher` tại ngưỡng 0,92; đây chỉ là danh sách
ứng viên, không tự động kết luận leak khi khác thủ tục.

Câu hỏi cuối và đáp án ngắn trùng nhau chỉ được ghi nhận như template/fact hành
chính phổ biến. Chúng không bị loại nếu không có dấu hiệu mạnh khác.

## Kết quả

| Split | Ban đầu | Loại | Giữ lại |
|---|---:|---:|---:|
| Train | 1.931 | 68 | 1.863 |
| Validation | 827 | 41 | 786 |
| Tổng | 2.758 | 109 | 2.649 |

Các nguyên nhân có thể đồng thời xuất hiện trên cùng một case:

- Train: 53 cùng mã thủ tục, 5 trùng context ID/text, 4 trùng standalone query,
  14 trùng đáp án dài.
- Validation: 36 cùng mã thủ tục, 2 trùng context ID/text, 1 trùng standalone
  query, 7 trùng đáp án dài.
- Sau lọc: 0 trùng test ID, standalone query, context ID/text, đáp án dài và mã
  thủ tục với 1.216 test ID duy nhất của hợp PA1+PA2.
- Train và validation sạch vẫn có 0 ID trùng nhau.

Template không bị loại gồm 727/310 câu hỏi cuối trùng và 527/220 đáp án ngắn
trùng ở train/validation. Near-query được lưu tối đa 200 ứng viên mỗi split; các
ứng viên còn lại khác mã thủ tục nên không được tự động coi là rò rỉ nội dung.

Artifact truy vết nằm tại `Data/dataset_v3/fintuning_clean/`; RAG-SFT dẫn xuất
nằm tại `Data/dataset_v3/finetuning_rag_clean/`. Toàn bộ 2.649 structured target
đã qua parser runtime, và schema/split validation đạt. Chưa chạy training hoặc
đánh giá model mới.
