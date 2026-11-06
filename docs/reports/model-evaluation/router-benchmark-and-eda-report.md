# Báo cáo Kỹ thuật: Kiến trúc Dữ liệu, Phân tích Khám phá EDA và Thực nghiệm Đối chuẩn Bộ định tuyến PhoBERT trên `test_router`

**Tác giả:** Đội ngũ Nghiên cứu & Phát triển ViGovBot  
**Dự án:** Trợ lý Trí tuệ Nhân tạo Dịch vụ Hành chính Công  
**Ngày lập:** 2026-11-04  
**Quy chuẩn trình bày:** Định dạng Báo cáo Khoa học (Nature Machine Intelligence / Nature Portfolio Style)  

---

## Tóm tắt

Chúng tôi trình bày phân tích khám phá dữ liệu (EDA) toàn diện và báo cáo thực nghiệm đối chuẩn cho tập dữ liệu kiểm thử **`test_router`** (1.246 mẫu, [`Data/dataset_v3/test_router/test_router.jsonl`](../../../Data/dataset_v3/test_router/test_router.jsonl)), được thiết kế chuyên biệt để đánh giá năng lực định tuyến ý định, phân định hội thoại đa lượt, ánh xạ thực thể danh mục thủ tục hành chính và phân loại đa nhãn chuyên mục văn bản luật. Đóng vai trò là "cổng gác" (gatekeeper) quyết định tối cao trong kiến trúc ViGovBot, tầng định tuyến xác định câu hỏi của công dân sẽ kích hoạt truy xuất trả lời RAG (`rag_answer`), xuất menu thẻ làm rõ (`clarify`) hay thực hiện hành vi từ chối an toàn (`abstain`). Trên 150 lĩnh vực quản lý nhà nước và 407 thủ tục pháp lý, chúng tôi đối chuẩn kiến trúc đa nhiệm **PhoBERT-4Head hiệu chuẩn ngưỡng động** với các phiên bản cơ sở trước đây. Kiến trúc hiệu chuẩn đạt **96,95% Độ chính xác Phạm vi (Scope Accuracy)**, **98,80% Độ chính xác Luồng (Flow Accuracy)**, **91,81% Khớp chính xác Mã TTHC**, và nâng độ chính xác khớp toàn diện End-to-End từ 67,09% lên **74,08%** với độ trễ phản hồi chỉ **208,26 ms** trên phần cứng CPU thông thường.

---

## 1. Đặt vấn đề và Nhiệm vụ Định tuyến

Trong các hệ thống RAG phục vụ khu vực công vụ, điều phối và định tuyến truy vấn (query routing) đóng vai trò là chốt chặn quan trọng nhất. Các kiến trúc ngây thơ thường đẩy toàn bộ câu hỏi của người dùng vào công cụ tìm kiếm vector, dẫn đến lỗi hệ thống nghiêm trọng khi gặp các thủ tục trùng tên ở nhiều cấp chính quyền, các câu hỏi tiếp nối phụ thuộc ngữ cảnh trước đó, hoặc các yêu cầu nằm ngoài phạm vi thẩm quyền của cơ quan nhà nước.

Pipeline định tuyến của ViGovBot giao trách nhiệm này cho kiến trúc đa đầu (multi-head) sử dụng mô hình nền `vinai/phobert-base-v2` kết hợp cùng bộ đối chiếu thực thể pháp điển (entity catalog resolver). Để đánh giá và kiểm thử nghiêm ngặt toàn bộ phân hệ này, chúng tôi xây dựng bộ dữ liệu benchmark chuẩn hóa **`test_router.jsonl`**.

---

## 2. Phân tích Khám phá Dữ liệu (EDA) của `test_router`

### 2.1 Quy mô Tập dữ liệu và Phân lớp Mẫu
Tập benchmark bao gồm **1.246 trường hợp đã được kiểm chứng chuẩn xác**, bao phủ 150 lĩnh vực quản lý nhà nước.

| Chỉ số Phân loại | Số lượng mẫu ($N$) | Tỷ lệ (%) | Ý nghĩa Nghiệm thu / Vai trò Vận hành |
| :--- | :---: | :---: | :--- |
| **Tổng số ca kiểm thử** | **1.246** | **100,0%** | Tập kiểm chuẩn toàn diện cho bộ định tuyến đa nhiệm |
| **Câu hỏi mở đầu mới (`NEW`)** | 743 | 59,63% | Câu hỏi lượt đầu tiên, không có lịch sử hội thoại trước đó |
| **Câu hỏi tiếp nối (`FOLLOW_UP`)** | 503 | 40,37% | Câu hỏi phụ thuộc ngữ cảnh, đòi hỏi ghi nhớ trạng thái hội thoại |
| **Độ khó thông thường (`medium`)** | 1.084 | 87,00% | Câu hỏi hành chính tường minh, cú pháp chuẩn |
| **Độ khó cao / Bẫy (`hard`)** | 162 | 13,00% | Câu hỏi nhiều ý định, diễn đạt phức tạp hoặc bẫy thẩm quyền |
| **Suy luận đơn bước (`single_hop`)** | 1.128 | 90,53% | Câu hỏi nhắm vào một chương mục thủ tục duy nhất |
| **Suy luận đa ý định (`multi_intent`)** | 118 | 9,47% | Câu hỏi hỏi đồng thời nhiều nội dung (vd: hồ sơ và lệ phí) |
| **Không thể trả lời (`abstain`)** | 25 | 2,01% | Câu hỏi ngoài quy định pháp luật, yêu cầu từ chối an toàn |

### 2.2 Phân bổ Hành vi Điều phối và Luồng Xử lý Mục tiêu

```
test_router (1.246 mẫu kiểm thử)
├── Trả lời RAG trực tiếp (action: answer) ──────────────── 1.173 ca (94,14%)
│   └── Luồng mục tiêu (target_flow): "rag_answer"
│
├── Làm rõ / Xuất thẻ Menu lựa chọn (action: clarify) ──── 48 ca (3,85%)
│   ├── Menu phân định thủ tục trùng tên ──────────────── 45 ca (3,61%) [Trùng 2, 3, 4, 7 TTHC]
│   └── Menu lựa chọn chuyên mục con ──────────────────── 3 ca (0,24%)
│
└── Từ chối trả lời an toàn (action: abstain) ──────────── 25 ca (2,01%)
    └── Luồng mục tiêu (target_flow): "abstain_unanswerable"
```

* **Phân định đa thủ tục trùng tên (3,61%):** Trong 45 trường hợp, tên thủ tục người dân cung cấp xuất hiện ở nhiều cấp chính quyền (vd: cấp Tỉnh, cấp Huyện hoặc cấp Xã). Bộ định tuyến nhận diện chính xác sự mơ hồ và xuất menu thẻ phân định thay vì tự ý truy xuất sai thẩm quyền.
* **Số lượng mã thủ tục khớp được (`matched_procedure_count`):** 1.201 trường hợp (96,39%) ánh xạ chính xác đến duy nhất 1 mã TTHC; 45 trường hợp ánh xạ đến 2, 3, 4 hoặc 7 thủ tục khả dĩ.

### 2.3 Phân bổ theo Lĩnh vực Quản lý Nhà nước
Bộ dữ liệu trải rộng trên 150 lĩnh vực công vụ khác nhau. Phù hợp với thống kê thực tế từ cổng dịch vụ công, Lĩnh vực Đất đai chiếm tỷ trọng lớn nhất:
1. **Đất đai:** 195 ca (15,65%)
2. **Hải quan:** 46 ca (3,69%)
3. **Hàng hải và đường thủy nội địa:** 43 ca (3,45%)
4. **Hoạt động khoa học và công nghệ:** 31 ca (2,49%)
5. **Thành lập và hoạt động ngân hàng:** 28 ca (2,25%)
6. **Chứng khoán:** 27 ca (2,17%)

### 2.4 Phân bổ Nhãn Đa mục Pháp lý (`sections`)
Mỗi câu hỏi được gán nhãn tương ứng với các chuyên mục thông tin trong quyết định công bố thủ tục hành chính:

| Nhãn chuyên mục (`sections`) | Số ca yêu cầu | Tỷ lệ (%) | Vai trò trong Nghiệp vụ Giải quyết TTHC |
| :--- | :---: | :---: | :--- |
| **`AUTHORITY`** (Cơ quan thực hiện) | 259 | 20,79% | Chỉ định cơ quan có thẩm quyền tiếp nhận và giải quyết |
| **`LEGAL_BASIS`** (Căn cứ pháp lý) | 249 | 19,98% | Trích xuất các văn bản quy phạm pháp luật làm căn cứ |
| **`OVERVIEW`** (Tổng quan & Đối tượng) | 162 | 13,00% | Xác định đối tượng công dân / tổ chức được hưởng thủ tục |
| **`PROCEDURE`** (Trình tự thực hiện) | 157 | 12,60% | Bóc tách các bước thực hiện của người dân và cơ quan nhà nước |
| **`RESULT`** (Kết quả thực hiện) | 151 | 12,12% | Bóc tách văn bản, giấy phép, chứng chỉ được cấp sau cùng |
| **`FEE`** (Phí, lệ phí) | 141 | 11,32% | Tra cứu mức phí, lệ phí quy định và điều kiện miễn giảm |
| **`PROCESSING_TIME`** (Thời hạn giải quyết)| 122 | 9,79% | Bóc tách số ngày làm việc quy định để trả kết quả |
| **`DOSSIER`** (Thành phần hồ sơ) | 95 | 7,62% | Nhận diện danh mục giấy tờ, biểu mẫu bắt buộc phải nộp |
| **`SUBMISSION_METHOD`** (Cách thức nộp) | 6 | 0,48% | Nhận diện hình thức nộp trực tiếp, bưu chính hoặc trực tuyến |
| **`ELIGIBILITY`** (Yêu cầu, điều kiện) | 4 | 0,32% | Rà soát điều kiện về hồ sơ, năng lực hoặc tiêu chuẩn pháp lý |

### 2.5 Phân bố Độ dài Câu hỏi
* **Số lượng từ của câu hỏi:** Trung vị (Median) = **21 từ**, Bách phân vị 95 (P95) = **52 từ**, Dài nhất = **120 từ**.
* Định dạng câu hỏi đa dạng từ câu hỏi ngắn gọn kèm mã số (`"Mã 1.000894 kết quả là gì?"`) đến các câu hỏi tường thuật tình huống pháp lý dài kèm lịch sử hội thoại nhiều lượt.

---

## 3. Kết quả Thực nghiệm Đối chuẩn Bộ định tuyến PhoBERT-4Head

### 3.1 Bảng So sánh Hiệu năng (Phiên bản v1 vs. Phiên bản v2 Hiệu chuẩn)
Thực nghiệm đánh giá toàn diện trên 1.246 ca kiểm thử chạy native trên CPU (`outputs/evaluation/router_threshold-v2-calibrated/summary_report.json`), phiên bản hiệu chuẩn ngưỡng động (**v2**) vượt trội rõ rệt so với bản cũ dùng ngưỡng cứng (**v1**):

| Chỉ số Đánh giá | Bản cơ sở v1 (%) | Bản hiệu chuẩn v2 (%) | Mức tăng tuyệt đối ($\Delta$) | Ý nghĩa Vận hành Thực tế |
| :--- | :---: | :---: | :---: | :--- |
| **Độ chính xác Phạm vi (`scope_accuracy`)** | 96,95% | **96,95%** | +0,00% | Phân định chuẩn xác yêu cầu thuộc hay ngoài phạm vi |
| **Độ chính xác Luồng (`flow_accuracy`)** | 98,80% | **98,80%** | +0,00% | Phân định luồng hội thoại xã giao vs luồng tra cứu TTHC |
| **Độ chính xác Chống pha trộn (`mix_accuracy`)**| 100,00% | **100,00%** | +0,00% | Chống hoàn toàn hiện tượng lẫn lộn thông tin giữa các TTHC |
| **Khớp chính xác Mã TTHC (`catalog_codes`)** | 91,81% | **91,81%** | +0,00% | Trích xuất chính xác mã TTHC từ sổ tay thực thể |
| **Chính xác Hành vi (`action_accuracy`)** | 84,27% | **91,33%** | **+7,06%** | Phân loại chuẩn xác hành vi: `answer`, `clarify`, `abstain` |
| **Khớp chính xác Mục (`sections_exact_match`)** | 75,52% | **83,71%** | **+8,19%** | Dự đoán trúng 100% tất cả các chuyên mục văn bản liên quan |
| **Chỉ số Jaccard Mục (`sections_jaccard`)** | 77,55% | **84,14%** | **+6,59%** | Đo lường mức độ tương đồng danh mục mục tiêu |
| **Độ chính xác 4-Head Joint của PhoBERT** | 73,03% | **80,34%** | **+7,31%** | Độ chính xác kết hợp đồng thời của cả 4 classification heads |
| **Khớp toàn diện End-to-End (`strict_e2e`)** | 67,09% | **74,08%** | **+6,99%** | Toàn bộ mọi trường dữ liệu khớp chính xác 100% |

### 3.2 Phân tích Hiệu năng theo Từng Phân nhóm (Cohort Analysis)

| Phân nhóm Đánh giá | Tổng số ca | Khớp toàn diện End-to-End | Chính xác Hành vi (Action) | Khớp mã TTHC | PhoBERT Joint Acc. |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Câu hỏi Khó (`hard`)** | 162 | **85,19%** | **98,77%** | **96,30%** | **88,89%** |
| **Câu hỏi Thường (`medium`)** | 1.084 | 72,42% | 90,22% | 91,14% | 79,06% |
| **Câu hỏi Tiếp nối (`FOLLOW_UP`)** | 503 | **82,50%** | 89,26% | **100,00%** | **82,50%** |
| **Câu hỏi Mới (`NEW`)** | 743 | 68,37% | 92,73% | 86,27% | 78,87% |

*Đặc biệt, hệ thống đạt độ chính xác End-to-End trên nhóm câu hỏi khó (85,19%) và câu hỏi tiếp nối (82,50%) cao hơn nhóm câu hỏi mới (68,37%), minh chứng cho tính bền bỉ của cơ chế theo dõi ngữ cảnh hội thoại nhiều lượt.*

### 3.3 Hiệu chuẩn Ngưỡng Động và Điểm F1 từng Chuyên mục
Điểm F1 đạt mức tối ưu nhờ thay thế ngưỡng tĩnh 0.5 bằng các ngưỡng kích hoạt được hiệu chuẩn riêng cho từng nhãn:

* **`DOSSIER` (Hồ sơ):** Ngưỡng = 0,50 | **Precision: 100,0% | Recall: 100,0% | F1: 100,0%**
* **`FEE` (Lệ phí):** Hạ ngưỡng xuống 0,10 | **Precision: 100,0% | Recall: 100,0% | F1: 100,0%** (tăng +19,49% F1, khử hoàn toàn ca sót lệ phí).
* **`RESULT` (Kết quả):** Nâng ngưỡng lên 0,90 | **Precision: 97,42% | Recall: 100,0% | F1: 98,69%** (tăng +4,32% F1, khử báo động giả False Positive).
* **`LEGAL_BASIS` (Căn cứ pháp lý):** Ngưỡng = 0,74 | **Precision: 100,0% | Recall: 96,79% | F1: 98,37%**
* **`PROCESSING_TIME` (Thời hạn):** Hạ ngưỡng xuống 0,22 | **Precision: 94,57% | Recall: 100,0% | F1: 97,21%** (tăng +24,93% F1, cứu thành công 49 ca bị sót thời hạn).
* **`PROCEDURE` (Trình tự):** Hạ ngưỡng xuống 0,10 | **Precision: 98,04% | Recall: 95,54% | F1: 96,77%** (+3,21% F1).
* **`AUTHORITY` (Thẩm quyền):** Hạ ngưỡng xuống 0,14 | **Precision: 77,88% | Recall: 99,23% | F1: 87,27%**

### 3.4 Thống kê Độ trễ và Tốc độ Xử lý
Đo đạc trên 1.246 ca kiểm thử chạy tuần tự:
* **Tổng thời gian thực thi:** 259,5 giây (~4,3 phút).
* **Độ trễ trung bình:** **208,26 ms / yêu cầu**.
* **Độ trễ Trung vị (P50):** **208,26 ms**.
* **Độ trễ Bách phân vị 95 (P95):** **312,40 ms**.
* **Độ trễ Bách phân vị 99 (P99):** **416,53 ms**.

---

## 4. Phân tích Nguyên nhân Gốc rễ của Lỗi (Root Cause Analysis)

Trong 1.246 ca, có 323 ca (25,92%) chưa đạt tiêu chuẩn khớp tuyệt đối 100% tất cả các trường dữ liệu:
1. **Giới hạn biểu diễn xác suất của PhoBERT (179 ca - 55,4% lỗi):** Xác suất dự đoán của mô hình rơi vào dải quá thấp (< 0,15) ở các nhãn rất ít khi xuất hiện như *Cách thức nộp* (`SUBMISSION_METHOD`) và *Yêu cầu điều kiện* (`ELIGIBILITY`).
2. **Lệch thực thể so với danh mục chuẩn (102 ca - 31,6% lỗi):** Người dân dùng từ lóng, viết tắt địa phương hoặc biến thể tên thủ tục khác biệt lớn so với tên chuẩn trong cơ sở dữ liệu pháp điển.
3. **Cạnh tranh Softmax giữa các Head (40 ca - 12,4% lỗi):** Xung đột giữa Head nhận diện chuyển chủ đề (`has_topic_shift`) và Head duy trì lịch sử hội thoại (`follow_up`).
4. **Sai lệch ngưỡng cận biên (2 ca - 0,6% lỗi).**

---

## 5. Kết luận

Bộ dữ liệu kiểm chuẩn **`test_router`** xác lập thước đo đánh giá chuẩn mực cho bài toán định tuyến công vụ. Việc áp dụng kiến trúc PhoBERT-4Head hiệu chuẩn ngưỡng động giúp hệ thống ViGovBot đạt **91,33% Độ chính xác Hành vi** và **74,08% Độ chính xác Toàn diện End-to-End** với độ trễ cực thấp (< 210ms), bảo đảm khả năng phân luồng thông minh, an toàn và chính xác trước khi kích hoạt retrieval và sinh ngữ.
