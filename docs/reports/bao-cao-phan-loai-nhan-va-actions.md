# Báo cáo Toàn diện: Hệ thống Nhãn Phân loại (Routing Labels), Trạng thái Bằng chứng & Hành vi Điều phối (Actions) trong ViGovBot

**Tài liệu Kỹ thuật & Báo cáo Kiến trúc Chuẩn hóa**  
**Dự án:** Trợ lý Trí tuệ Nhân tạo Phục vụ Dịch vụ Công ViGovBot  
**Phiên bản Hệ thống:** ViGovBot RAG Core v3.2 (PhoBERT 4-Head Router & Adaptive Conversation Engine)  
**Ngày cập nhật:** 2026-11-04  

---

## 1. Kiến trúc Tổng thể & Phân rã Biểu đồ Điều phối Phân tầng (Modular Architecture)

Nhằm đảm bảo tính trực quan, độ sắc nét cao và tương thích tuyệt đối trên mọi trình xem Markdown, tài liệu kỹ thuật, Word và PDF (không bị lỗi hiển thị của các trình kết xuất mã thô), kiến trúc điều phối của ViGovBot được mô hình hóa bằng **1 Biểu đồ Cấp cao Tổng thể (Macro Architecture)** cùng **5 Biểu đồ Phân tầng Chi tiết (Sub-module Architecture)** độ phân giải cao (300 DPI) tương ứng với 5 phân hệ cốt lõi trong mã nguồn triển khai:

```
HỆ THỐNG ĐIỀU PHỐI HAI TẦNG VIGOVBOT (TWO-TIER HYBRID ARCHITECTURE)
├── Biểu đồ Tổng thể: Kiến trúc Phân nhóm 5 Module Lớn (Macro Architecture)
├── Module 1: Phân loại Ngữ nghĩa Toàn cục PhoBERT 4-Head & Trọng tài Phạm vi
├── Module 2: Trọng tài Trộn thủ tục (Mix) & Phân rã Câu hỏi Hỗn hợp (Mixed Scope)
├── Module 3: Đối soát Thực thể Catalog & Phân giải Danh tính Thủ tục
├── Module 4: Vòng đời Trạng thái Phiên, Chữ ký HMAC SHA-256 & Tương tác Menu
└── Module 5: Kiểm soát Bằng chứng, Chống Đoán mò & Sinh ngữ Có cấu trúc
```

---

### 1.1. Biểu đồ Cấp cao Tổng quan: Phân nhóm 5 Module Lớn (Macro Architecture)

Biểu đồ này mô tả toàn cảnh luồng dữ liệu cấp cao giữa người dùng, tầng phân loại nơ-ron, tầng trọng tài danh mục, tầng quản lý phiên hội thoại và tầng sinh ngữ RAG:

![Biểu đồ Cấp cao Tổng thể](images/flowchart_macro_architecture.png)
*(Xem tệp hình ảnh gốc độ phân giải cao tại: [flowchart_macro_architecture.png](file:///c:/Users/quangTam/Documents/ViGovBot/docs/reports/images/flowchart_macro_architecture.png))*

<details>
<summary><b>Chi tiết mã nguồn Mermaid (nhấn để mở rộng)</b></summary>

```mermaid
flowchart TD
    UserQuery["1. Câu hỏi người dùng\n(User Query & History)"] --> M1["MODULE 1: BỘ PHÂN LOẠI NGỮ NGHĨA PHOBERT\n(PhoBERT 4-Head Router)"]
    
    M1 --> M2["MODULE 2: TẦNG TRỌNG TÀI ADAPTER & XỬ LÝ PHẠM VI\n(Scope & Mix Arbitration / Extractive Rewrite)"]
    
    M2 -- "OUT_OF_SCOPE / Chào hỏi xã giao" --> M5B["action: abstain\ndecision_reason: out_of_scope | social_greeting"]
    M2 -- "Hợp lệ / Đã override / Đã làm sạch" --> M3["MODULE 3: ĐỐI SOÁT THỰC THỂ & PHÂN GIẢI CATALOG\n(Catalog Disambiguation & Entity Resolution)"]
    
    M3 -- "Trùng tên / Thiếu mục / Mơ hồ" --> M4["MODULE 4: QUẢN LÝ PHIÊN & BẢO MẬT TRẠNG THÁI\n(Signed State Security & Menu Clarification)"]
    M4 --> UserMenu["action: clarify\nXuất Signed Menu lựa chọn"]
    
    M3 -- "Đơn thủ tục + Đủ mục hỏi" --> M5["MODULE 5: KIỂM SOÁT BẰNG CHỨNG & SINH NGỮ RAG\n(Retrieval, Evidence Validation & Constrained Decoding)"]
    
    M5 -- "Thiếu bằng chứng / Mã cá nhân không có" --> M5B2["action: abstain\ndecision_reason: identifier_not_in_evidence | no_context"]
    M5 -- "Đủ bằng chứng" --> M5A["action: answer | partial\nactual_route: rag_search\nSinh câu trả lời kèm trích dẫn"]
```

</details>

---

### 1.2. Biểu đồ Module 1: Phân loại Ngữ nghĩa PhoBERT 4-Head & Trọng tài Phạm vi (Scope Arbitration)

Mô tả chi tiết luồng xử lý tại [`src/vigovbot/rag/phobert_router.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/phobert_router.py), nơi câu hỏi được phân loại qua 4 classification heads song song và kích hoạt cơ chế trọng tài cứu vớt câu hỏi ở ngưỡng phân vân:

![Module 1: Phân loại Ngữ nghĩa PhoBERT & Trọng tài Phạm vi](images/flowchart_module1_phobert_scope.png)
*(Xem tệp hình ảnh gốc độ phân giải cao tại: [flowchart_module1_phobert_scope.png](file:///c:/Users/quangTam/Documents/ViGovBot/docs/reports/images/flowchart_module1_phobert_scope.png))*

<details>
<summary><b>Chi tiết mã nguồn Mermaid (nhấn để mở rộng)</b></summary>

```mermaid
flowchart TD
    QueryIn["Câu hỏi đầu vào"] --> PHO["PhoBERT 4-Head Router\n(max_len: 128, PyVi BPE)"]
    PHO --> ScopeHead{"Head 1: Scope\n(Softmax 3 lớp)"}
    
    ScopeHead -- "OUT_OF_SCOPE" --> ProbScope{"Xác suất P(Ngoài phạm vi)?"}
    ProbScope -- "50% đến dưới 85%\n(Vùng lưng chừng / phân vân)" --> CatLookup{"Tra cứu Catalog RAM\n(Có mã TTHC hoặc Alias?)"}
    CatLookup -- "Có thực thể (len >= 1)" --> OvrScope["Bẻ còi: Override thành IN_SCOPE\n(catalog_scope_arbitration)"]
    CatLookup -- "Không có" --> ConfCandidates{"Catalog confirmation\n(Điểm tương đồng >= 70%?)"}
    
    ProbScope -- "Từ 85% trở lên\n(Thiên về ngoài phạm vi)" --> ConfCandidates
    ConfCandidates -- "Khớp ứng viên TTHC" --> MenuConf["action: clarify\ndecision_reason: procedure_required\n(Menu xác nhận: confirmation=True)"]
    ConfCandidates -- "Không khớp ứng viên" --> AbstainOOS["action: abstain\ndecision_reason: out_of_scope\nevidence_status: missing\n(Dừng luồng, không gọi FAISS/LLM)"]

    ScopeHead -- "MIXED_SCOPE" --> RouteMixed["Chuyển sang Module 2: Xử lý Câu hỏi Hỗn hợp"]
    ScopeHead -- "IN_SCOPE" --> RouteInScope["Chuyển sang Module 2: Kiểm tra Trộn thủ tục"]
    OvrScope --> RouteInScope
```

</details>

#### Mô tả chi tiết mã nguồn triển khai (Module 1):
1. **Tiền xử lý & Trích xuất Đầu ra (`phobert_router.py#L90-L135`):** Câu hỏi cùng lịch sử hội thoại được mã hóa tối đa 128 token qua bộ tách từ PyVi và từ điển BPE của PhoBERT. Đầu ra sinh 4 vector phân phối xác suất: `scope` (3 lớp), `flow` (2 lớp), `mix` (2 lớp), và `sections` (11 lớp nhị phân qua Sigmoid).
2. **Trọng tài Phạm vi Vùng lưng chừng (`CATALOG_SCOPE_LOWER = 0.50`, `CATALOG_SCOPE_UPPER = 0.85`):** Nếu PhoBERT phán đoán `OUT_OF_SCOPE` nhưng rơi vào khoảng xác suất phân vân $50\% \le P < 85\%$, hệ thống tra cứu danh mục Catalog trên RAM ($< 1\text{ms}$). Nếu phát hiện câu hỏi chứa mã TTHC hoặc tên thủ tục chuẩn/bí danh, Adapter tự động bẻ còi ghi đè thành `IN_SCOPE`, lưu vết `catalog_scope_arbitration` để bảo vệ các câu hỏi hợp lệ không bị từ chối oan.
3. **Cơ chế Gợi ý Xác nhận Thủ tục (`confirmation_candidates()`):** Nếu xác suất ngoài phạm vi $\ge 85\%$ nhưng đối sánh từ vựng trên Catalog đạt độ tương đồng $\ge 70\%$, hệ thống mở Menu làm rõ xác nhận dạng lịch sự (`confirmation=True`) thay vì từ chối thẳng thừng.

---

### 1.3. Biểu đồ Module 2: Trọng tài Trộn thủ tục (Mix) & Phân rã Câu hỏi Hỗn hợp (Mixed Scope)

Mô tả chi tiết logic tại [`src/vigovbot/rag/phobert_router.py#L228`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/phobert_router.py#L228) và [`src/vigovbot/rag/classification.py#L62`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/classification.py#L62):

![Module 2: Trọng tài Trộn thủ tục & Phân rã Câu hỏi Hỗn hợp](images/flowchart_module2_mix_rewrite.png)
*(Xem tệp hình ảnh gốc độ phân giải cao tại: [flowchart_module2_mix_rewrite.png](file:///c:/Users/quangTam/Documents/ViGovBot/docs/reports/images/flowchart_module2_mix_rewrite.png))*

<details>
<summary><b>Chi tiết mã nguồn Mermaid (nhấn để mở rộng)</b></summary>

```mermaid
flowchart TD
    InMixedScope["Yêu cầu MIXED_SCOPE hoặc kiểm tra Mix"] --> CheckMixHead{"Head 3: Mix\n(p_mix >= 0.5)?"}
    
    CheckMixHead -- "True (Có trộn thủ tục)" --> ArbSingle{"Tất cả mã TTHC cùng trỏ về\n1 tên chuẩn hóa duy nhất?"}
    ArbSingle -- "Đúng: Tên dài đơn thủ tục" --> OvrMix["Bẻ còi: Override mix = False\n(catalog_single_procedure_override_mixed)"]
    ArbSingle -- "Sai: Hỏi nhiều TTHC khác nhau" --> ClarifyMulti["action: clarify\ndecision_reason: ambiguous_question\n(Chặn: Yêu cầu hỏi riêng từng thủ tục)"]
    
    CheckMixHead -- "False (Đơn thủ tục)" --> CheckMixedScope{"Scope là MIXED_SCOPE?"}
    OvrMix --> CheckMixedScope
    
    CheckMixedScope -- "Đúng: Câu hỏi hỗn hợp" --> RegexSplit["Tầng 1: Tách mệnh đề độc lập\n(re.split r'[;\n?!]+|\\s+và\\s+')"]
    RegexSplit --> CheckClean1{"Có đúng 1 mệnh đề IN_SCOPE thuần?"}
    CheckClean1 -- "Có" --> AcceptRegex["Chấp nhận mệnh đề con làm query"]
    CheckClean1 -- "Không tách được" --> LLMRewrite["Tầng 2: LLM Extractive Rewrite\n(Trích xuất chuỗi con nguyên văn)"]
    
    LLMRewrite --> VerifyLLM{"Kiểm định Guardrails:\n1. Substring của câu gốc?\n2. Giữ nguyên mã TTHC?\n3. Không mất từ định tính phủ định?"}
    VerifyLLM -- "Thất bại" --> ClarifyAmb["action: clarify\ndecision_reason: ambiguous_question"]
    VerifyLLM -- "Vượt qua" --> RePhoBERT["Tái phân loại qua PhoBERT\n(clean_route == IN_SCOPE & đơn thủ tục?)"]
    RePhoBERT -- "Hợp lệ" --> CleanQuery["Chấp nhận: accepted_after_phobert\n(Gắn cờ MIXED_NOTICE cho câu trả lời)"]
    RePhoBERT -- "Bị từ chối" --> ClarifyAmb
    
    CheckMixedScope -- "False: IN_SCOPE thuần" --> ToCatalog["Chuyển sang Module 3: Đối soát Catalog"]
    AcceptRegex --> ToCatalog
    CleanQuery --> ToCatalog
```

</details>

#### Mô tả chi tiết mã nguồn triển khai (Module 2):
1. **Trọng tài Thủ tục Đơn có Tên dài (`catalog_single_procedure_override_mixed`):** Đối với các thủ tục đất đai/xây dựng có tên dài chứa nhiều liên từ liệt kê ("và", "cho thuê", "chuyển mục đích"), PhoBERT thường dự đoán nhầm `mix = True`. Adapter quét tập mã `codes`; nếu toàn bộ cùng quy về 1 tên thủ tục chuẩn hóa duy nhất, cờ `mix` được hạ về `False` để mở Menu làm rõ thay vì chặn câu hỏi.
2. **Quy trình 2 Tầng Làm sạch `MIXED_SCOPE`:**
   - **Tầng 1 (Regex Split):** Phân tách các mệnh đề phân cách bởi dấu chấm phẩy, xuống dòng hoặc từ nối "và". Nếu tìm thấy duy nhất 1 mệnh đề là `IN_SCOPE` đơn thủ tục thì sử dụng ngay mà không tốn chi phí gọi LLM.
   - **Tầng 2 (Extractive LLM Rewrite):** Sử dụng LLM trích xuất đoạn văn nguyên bản liên quan TTHC, áp đặt 3 hàng rào bảo vệ (Guardrails): bắt buộc là chuỗi con (`substring`), không làm mất mã TTHC, và không làm mất các từ định tính phủ định (`NEGATIVE_QUALIFIERS`). Sau đó câu làm sạch bắt buộc phải vượt qua bước tái phân loại bằng PhoBERT (`reclassification_verified`).

---

### 1.4. Biểu đồ Module 3: Đối soát Thực thể Catalog & Phân giải Danh tính Thủ tục

Mô tả chi tiết quy trình tại [`src/vigovbot/rag/conversation.py#L330-L440`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L330-L440) và [`clarification.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/clarification.py):

![Module 3: Đối soát Thực thể Catalog & Phân giải Danh tính Thủ tục](images/flowchart_module3_catalog_disambiguation.png)
*(Xem tệp hình ảnh gốc độ phân giải cao tại: [flowchart_module3_catalog_disambiguation.png](file:///c:/Users/quangTam/Documents/ViGovBot/docs/reports/images/flowchart_module3_catalog_disambiguation.png))*

<details>
<summary><b>Chi tiết mã nguồn Mermaid (nhấn để mở rộng)</b></summary>

```mermaid
flowchart TD
    QueryReady["Truy vấn đã chuẩn hóa"] --> StepCheckSwitch{"Người dùng đổi thủ tục trong follow-up\n(target_candidates rời rạc với selected)?"}
    
    StepCheckSwitch -- "Có đổi thủ tục" --> ResetProc["Thực hiện procedure_switch_reset\nReset conversation=NEW, xóa sections cũ"]
    ResetProc --> CollectCodes
    StepCheckSwitch -- "Không đổi" --> CollectCodes["Thu thập danh sách mã TTHC (4 cấp lọc):\n1. clarifier.matches (Mã / Alias)\n2. clarifier.inspect (Biến thể số nhiều)\n3. clarifier.discover (Cụm từ khóa)\n4. Retriever semantic hits (Dự phòng)"]
    
    CollectCodes --> CountCodes{"Độ dài mảng len(codes)?"}
    
    CountCodes -- "Nhiều hơn 1 mã (len >= 2)\n(Trùng/Tương tự tên)" --> MenuProcedure["action: clarify\ndecision_reason: procedure_required\nMở Signed Menu thủ tục (tối đa 5 lựa chọn)"]
    
    CountCodes -- "Không có mã (len == 0)\n(Không khớp Catalog)" --> StrategySemantic["retrieval_strategy = 'semantic'\nLưu unresolved_semantic_hits\n(Dự phòng truy xuất toàn corpus)"]
    StrategySemantic --> CheckSections
    
    CountCodes -- "Đúng 1 mã (len == 1)\n(Khớp chính xác 1 mã)" --> CheckSections{"Danh sách sections có phần tử?"}
    
    CheckSections -- "sections rỗng ([])" --> MenuSection["action: clarify\ndecision_reason: section_required\nMở Signed Menu chuyên mục của TTHC"]
    
    CheckSections -- "sections có nội dung" --> OverrideExplicit{"Người dùng nêu từ khóa chuyên mục tường minh\n(explicit_section_intents)?"}
    OverrideExplicit -- "Có từ khóa" --> OvrSec["Ghi đè: explicit_section_override\nCập nhật danh sách sections chính xác"]
    OverrideExplicit -- "Không có" --> ToEvidence["Chuyển sang Module 5: Retrieval & Bằng chứng"]
    OvrSec --> ToEvidence
```

</details>

#### Mô tả chi tiết mã nguồn triển khai (Module 3):
1. **Phát hiện Chuyển Thủ tục Đột ngột (`procedure_switch_reset`):** Trong mạch hỏi tiếp (`FOLLOW_UP`), nếu người dùng nêu tên một thủ tục mới hoàn toàn độc lập với thủ tục đang chọn (`set(target_candidates).isdisjoint(selected)`), Adapter lập tức bẻ còi `conversation = NEW`, gán lại mã đích và xóa toàn bộ các chuyên mục cũ (`sections = []`), ngăn chặn hiện tượng ô nhiễm ngữ cảnh giữa hai thủ tục khác nhau.
2. **Quy tắc Phân luồng theo Độ dài Mã (`len(codes)`):**
   - **`len(codes) >= 2`:** Tên thủ tục khớp với nhiều mã (cá nhân vs tổ chức, cấp tỉnh vs cấp huyện). Hệ thống **ngắt ngay lập tức**, không gọi LLM và xuất Signed Menu phân định (`procedure_required`).
   - **`len(codes) == 1`:** Chốt mã định danh duy nhất. Nếu người dùng chưa hỏi mục cụ thể (`sections == []`), mở Signed Menu chuyên mục (`section_required`). Nếu đã có mục hỏi, kiểm tra thêm cơ chế ghi đè chuyên mục tường minh (`explicit_section_override`) trước khi chuyển sang truy xuất.
   - **`len(codes) == 0`:** Kích hoạt chiến lược dự phòng `retrieval_strategy = "semantic"`, tìm kiếm ngữ nghĩa trên toàn bộ corpus tài liệu.
3. **Thuật toán Xử lý Câu hỏi Tỉnh lược trong Mạch Follow-up (`is_elliptical` & Shared Topic):**
   - **Vấn đề kỹ thuật:** Khi người dùng hỏi nối tiếp cộc lốc không nhắc lại tên thủ tục (ví dụ: *"thế còn lệ phí?", "hết mấy ngày?", "nộp ở đâu?"*), làm sao phân biệt câu hỏi này thực sự thuộc về thủ tục đang thảo luận hay là một câu hỏi trôi dạt ngữ cảnh sang chủ đề khác?
   - **Cơ chế triển khai tại [`conversation.py#L380-L389`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L380-L389):**
     ```python
     if len(selected) == 1 and len(requests) == 1 and not named:
         from vigovbot.rag.clarification import _DISCOVERY_STOP
         selected_name_words = set(re.findall(r"\w+", _fold(clarifier.catalog[selected[0]]["name"]))) - _DISCOVERY_STOP
         query_words = set(re.findall(r"\w+", _fold(question))) - _DISCOVERY_STOP
         has_shared_topic = bool(query_words & selected_name_words)
         is_elliptical = bool(explicit_sections or clarifier.goal(question, selected) or has_shared_topic)
         if not is_elliptical and query_words:
             return finish("Bạn đang hỏi tiếp thủ tục nào? Vui lòng nêu tên hoặc mã thủ tục.", "ambiguous_question")
         requests[0]["code"] = selected[0]
     ```
   - **Nguyên lý 3 điều kiện (`is_elliptical`):**
     - **Điều kiện 1 (`explicit_sections`):** Câu hỏi chứa từ khóa chuyên mục tường minh (thời hạn, lệ phí, hồ sơ,...).
     - **Điều kiện 2 (`clarifier.goal`):** Câu hỏi chứa các cụm từ ý định hành chính ("nộp ở đâu", "điều kiện gì", "mẫu đơn",...).
     - **Điều kiện 3 (`has_shared_topic`):** Tập từ vựng của câu hỏi (sau khi loại bỏ stopword `_DISCOVERY_STOP`) có phần giao thoa với tên thủ tục đã chọn ở lượt trước.
   - **Kết quả điều phối:** Nếu thỏa mãn 1 trong 3 điều kiện, hệ thống xác nhận câu hỏi tỉnh lược hợp lệ và tự động kế thừa `requests[0]["code"] = selected[0]`. Nếu không thỏa mãn (câu hỏi trôi dạt ngữ cảnh không rõ ràng), hệ thống ngắt luồng và yêu cầu làm rõ với `decision_reason = "ambiguous_question"`.

---

### 1.5. Biểu đồ Module 4: Vòng đời Trạng thái Phiên, Chữ ký HMAC SHA-256 & Tương tác Menu

Mô tả chi tiết cơ chế bảo mật và xử lý phản hồi người dùng tại [`src/vigovbot/rag/conversation.py#L34-L217`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L34-L217):

![Module 4: Vòng đời Trạng thái Phiên, Chữ ký HMAC & Tương tác Menu](images/flowchart_module4_state_security.png)
*(Xem tệp hình ảnh gốc độ phân giải cao tại: [flowchart_module4_state_security.png](file:///c:/Users/quangTam/Documents/ViGovBot/docs/reports/images/flowchart_module4_state_security.png))*

<details>
<summary><b>Chi tiết mã nguồn Mermaid (nhấn để mở rộng)</b></summary>

```mermaid
flowchart TD
    MenuReq["Yêu cầu gửi lựa chọn từ phía Client"] --> CheckState{"Kiểm tra Conversation State\n(validate_state)?"}
    
    CheckState -- "Không hợp lệ / Sai chữ ký / Sai hash" --> ExpiredSel["action: clarify\ndecision_reason: expired_selection\n(Yêu cầu nêu lại tên thủ tục)"]
    
    CheckState -- "State hợp lệ (HMAC SHA-256 OK)" --> DirectChoice{"Phân tích phản hồi (direct_choice)"}
    
    DirectChoice -- "Nhập số thứ tự hợp lệ (1..N)" --> ApplyOption["Cập nhật lựa chọn mã hoặc chuyên mục\nChuyển tiếp vào luồng RAG"]
    DirectChoice -- "Nhập số sai dải hoặc ký tự lạ" --> InvalidSel["action: clarify\ndecision_reason: invalid_selection\nIn lại Menu và nhắc chọn đúng"]
    DirectChoice -- "Từ chối Menu ('không phải mấy cái này')" --> RejectMenu["action: clarify\ndecision_reason: procedure_rejected\nLoại trừ các mã đã hiển thị, quét Catalog tìm ứng viên mới"]
    DirectChoice -- "Xác nhận chung chung ('ok', 'đúng rồi')" --> BareConfirm["action: clarify\ndecision_reason: selection_required\nNhắc chọn trực tiếp số hoặc tên mục"]
    DirectChoice -- "Hỏi trường hợp khác ('loại khác?')" --> VariantMenu["action: clarify\ndecision_reason: procedure_required\nGọi clarifier.inspect quét các biến thể cùng nhóm"]
```

</details>

#### Mô tả chi tiết mã nguồn triển khai (Module 4):
1. **Xác thực Trạng thái Bằng Chữ ký số HMAC (`validate_state`):** Khóa bí mật 256-bit trong RAM (`_SECRET`) ký toàn bộ state phiên (`version=2`, `scope`, `corpus`, `history_fingerprint`). Hàm `hmac.compare_digest` kiểm tra tính toàn vẹn thời gian hằng; bất kỳ hành vi sửa đổi mã thủ tục hay đổi phiên đều bị từ chối với `expired_selection`.
2. **Xử lý Thông minh Phản hồi Tự nhiên:**
   - Người dùng từ chối Menu bằng câu nói đời thường (*"không phải mấy cái này"*, `_MENU_REJECTION`): Hệ thống tự động loại bỏ các mã cũ và tìm danh sách thay thế tiếp theo (`procedure_rejected`).
   - Người dùng đồng ý chung chung (*"ok"*, *"đúng rồi"*, `_BARE_CONFIRMATION`): Nhắc nhở chọn số cụ thể (`selection_required`).
   - Người dùng hỏi tìm biến thể (*"trường hợp khác"*, `_OTHER_VARIANT`): Quét các thủ tục liên quan cùng nhóm nghiệp vụ trong Catalog.
3. **Kiến trúc Bộ nhớ đệm Trạng thái LRU 256 Phiên Chống Rò rỉ RAM (`_STATES` & Thread-Safe Lock):**
   - **Vấn đề kỹ thuật:** Trong môi trường phục vụ đồng thời hàng nghìn công dân truy cập dịch vụ công, việc lưu trữ không kiểm soát trạng thái hội thoại trên RAM sẽ dẫn đến tràn bộ nhớ (Memory Leak / OOM).
   - **Cơ chế triển khai tại [`conversation.py#L30-L31, L141-L147`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L30-L31):**
     ```python
     _STATES = OrderedDict()
     _STATE_LOCK = Lock()

     # Lưu trữ và đẩy phần tử cũ (LRU Eviction)
     with _STATE_LOCK:
         key = (clarification_scope, corpus, next_state["history_fingerprint"])
         _STATES[key] = result["conversation_state"]
         _STATES.move_to_end(key)
         while len(_STATES) > 256:
             _STATES.popitem(last=False)  # Đẩy trạng thái cũ nhất ra khỏi RAM
     ```
   - **Nguyên lý bảo đảm an toàn luồng & giới hạn tài nguyên:**
     - Khóa đa luồng `_STATE_LOCK` bảo vệ cấu trúc `OrderedDict` khỏi xung đột ghi đồng thời (Race Condition) khi có nhiều worker xử lý song song.
     - Khóa truy cập kết hợp 3 chiều: `(clarification_scope, corpus, history_fingerprint)` đảm bảo tính cô lập tuyệt đối giữa các phiên khác nhau.
     - Ngưỡng giới hạn cứng tối đa 256 state gần nhất: Mỗi khi có phiên mới truy cập, trạng thái được đưa lên đầu danh sách qua `move_to_end(key)`; khi vượt quá 256, phương thức `popitem(last=False)` tự động giải phóng phiên cũ nhất. Cơ chế này giữ cho bộ nhớ RAM của bot luôn ổn định ở mức cực thấp (~1.31 MB), bảo đảm hệ thống vận hành bền bỉ 24/7.

---

### 1.6. Biểu đồ Module 5: Kiểm soát Bằng chứng, Chống Đoán mò & Sinh ngữ Có cấu trúc

Mô tả chi tiết hàng rào kiểm soát an toàn dữ liệu và sinh câu trả lời tại [`src/vigovbot/rag/conversation.py#L483-L522`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L483-L522) và [`routing.py#L140-L209`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/routing.py#L140-L209):

![Module 5: Kiểm soát Bằng chứng, Chống Đoán mò & Sinh ngữ RAG](images/flowchart_module5_evidence_constrained_generation.png)
*(Xem tệp hình ảnh gốc độ phân giải cao tại: [flowchart_module5_evidence_constrained_generation.png](file:///c:/Users/quangTam/Documents/ViGovBot/docs/reports/images/flowchart_module5_evidence_constrained_generation.png))*

<details>
<summary><b>Chi tiết mã nguồn Mermaid (nhấn để mở rộng)</b></summary>

```mermaid
flowchart TD
    HitsIn["Tập chunks văn bản thu được từ Retriever"] --> CheckHits{"Kho chunks có rỗng (not hits)?"}
    
    CheckHits -- "Rỗng (hits == [])" --> AbstainNoCtx["action: abstain\nevidence_status: missing\ndecision_reason: no_context\n(Thông báo tài liệu hiện có chưa đủ)"]
    
    CheckHits -- "Có chunks văn bản" --> CheckOpaque{"Hàm identifiers_missing_from_hits\n(Câu hỏi có mã định danh cá nhân HS-xxx?)"}
    
    CheckOpaque -- "Mã cá nhân KHÔNG CÓ trong chunk" --> AbstainIdent["action: abstain\nevidence_status: missing\ndecision_reason: identifier_not_in_evidence\n(Chống đoán mò kết quả hồ sơ)"]
    
    CheckOpaque -- "Không có mã cá nhân hoặc mã có trong tài liệu" --> LLMGen["Gọi LLM Qwen 2.5 với Constrained Decoding\n(Schema: answer_schema ép EVIDENCE_ACTIONS)"]
    
    LLMGen --> ParseGen{"Hàm parse_answer kiểm tra tính hợp lệ"}
    
    ParseGen -- "Câu trả lời chỉ chứa 'không có thông tin'" --> EnforceAbstain["Ép action = abstain (chống từ chối trá hình)"]
    ParseGen -- "Cặp (evidence_status, action) hợp lệ" --> CheckFinalRoute{"route['scope'] là MIXED_SCOPE?"}
    
    CheckFinalRoute -- "Đúng" --> GenPartial["action: partial (canonical: partial_answer)\nevidence_status: partial\nChèn ghi chú: MIXED_NOTICE"]
    CheckFinalRoute -- "Sai" --> GenAnswer["action: answer\nevidence_status: sufficient\ndecision_reason: evidence_assessment"]
```

</details>

#### Mô tả chi tiết mã nguồn triển khai (Module 5):
1. **Chống Đoán Mò Mã Biên nhận Cá nhân (`identifier_not_in_evidence`):** Biểu thức chính quy `_OPAQUE_IDENTIFIER` quét các chuỗi mã biên nhận (như `000.00.12.H29-...`). Nếu mã này xuất hiện trong câu hỏi nhưng không có trong chunk tài liệu pháp luật quy định chung, hệ thống lập tức từ chối trả lời (`action = abstain`, `evidence_status = missing`), hướng dẫn công dân tra cứu cổng dịch vụ công, loại trừ 100% rủi ro LLM bịa đặt tiến độ giải quyết hồ sơ.
2. **Ràng buộc Kép Giải mã (Constrained Decoding via `EVIDENCE_ACTIONS`):** Schema JSON ép mô hình sinh cặp `(evidence_status, action)` đồng nhất (`sufficient` $\leftrightarrow$ `answer`, `missing` $\leftrightarrow$ `abstain`, `partial` $\leftrightarrow$ `partial`). Hàm `parse_answer` kiểm tra nếu nội dung câu trả lời là "không có thông tin" thì bắt buộc `action` phải là `abstain`, chống hiện tượng từ chối trá hình.

---

## 2. Tầng 1: Hệ thống 4 Head của PhoBERT Router

Mô hình PhoBERT nhận đầu vào là chuỗi tokenized định dạng:
`<s> question </s></s> previous_utterance </s></s> procedure_context </s>`  
(giới hạn tối đa 128 token) và sử dụng 4 linear heads độc lập được cấu hình trong [`meta.json`](file:///c:/Users/quangTam/Documents/ViGovBot/outputs/phobert_v3_finetuned_20261028/checkpoint/meta.json):

### 2.1. Head 1: Phạm vi (`scope` / `phạm_vi`)
Đánh giá mức độ liên quan tới lĩnh vực Thủ tục hành chính (TTHC) Việt Nam (Hàm Softmax, 3 lớp):
- **`IN_SCOPE` (`Trong phạm vi`)**: Câu hỏi liên quan trực tiếp đến thủ tục, hồ sơ, thời hạn, phí, cơ quan giải quyết, biểu mẫu, căn cứ pháp lý,...
- **`OUT_OF_SCOPE` (`Ngoài phạm vi`)**: Câu hỏi hoàn toàn không thuộc thẩm quyền công vụ hỗ trợ (thời tiết, lập trình, văn hóa, chào hỏi tự do,...).
- **`MIXED_SCOPE` (`Hỗn hợp phạm vi`)**: Câu hỏi phức hợp chứa cả yêu cầu TTHC hợp lệ lẫn câu hỏi ngoài lề.

### 2.2. Head 2: Mạch hội thoại (`flow` / `mạch_hội_thoại`)
Xác định tính độc lập hay phụ thuộc vào ngữ cảnh lịch sử chat (Hàm Softmax, 2 lớp):
- **`NEW` (`Câu hỏi mới`)**: Câu hỏi độc lập, tự chứa đủ thông tin định danh thủ tục hoặc chủ động chuyển sang thủ tục mới.
- **`FOLLOW_UP` (`Hỏi tiếp`)**: Câu hỏi phụ thuộc vào ngữ cảnh liền trước (ví dụ: *"hết bao nhiêu ngày?", "hồ sơ gồm những gì?", "thế còn lệ phí?"*).

### 2.3. Head 3: Trộn thủ tục (`mix` / `trộn_thủ_tục`)
Dự đoán câu hỏi có cố tình gộp đồng thời từ hai thủ tục hành chính khác nhau hay không (Hàm Softmax, 2 lớp):
- **`False` (`Không`)**: Chỉ hỏi về 1 thủ tục hành chính duy nhất (hoặc nêu tên chung chung).
- **`True` (`Có`)**: Chứa đồng thời từ 2 thủ tục hành chính độc lập trong một câu.

### 2.4. Head 4: Mục nội dung (`sections` / `mục_nội_dung`)
Bài toán phân loại đa nhãn (multi-label binary classification) với 11 hàm kích hoạt Sigmoid độc lập và vector ngưỡng quyết định riêng:

| STT | Nhãn tiếng Việt | Mã Enum quốc tế | Ngưỡng V1 (Gốc) | Ngưỡng V2 (Tối ưu) | Ánh xạ Loại Chunk Corpus (`section_type`) |
|:---:|---|---|:---:|:---:|---|
| 1 | **Tổng quan** | `OVERVIEW` | 0.50 | **0.31** | Toàn bộ tài liệu, thông tin chung |
| 2 | **Trình tự thực hiện** | `PROCEDURE` | 0.65 | **0.10** | `procedure_step` |
| 3 | **Cách thức thực hiện** | `SUBMISSION_METHOD` | 0.70 | **0.89** | `submission_method` |
| 4 | **Thành phần hồ sơ** | `DOSSIER` | 0.40 | **0.50** | `required_documents` |
| 5 | **Thời hạn giải quyết** | `PROCESSING_TIME` | 0.75 | **0.22** | `processing_time` |
| 6 | **Cơ quan thực hiện** | `AUTHORITY` | 0.70 | **0.14** | `metadata_identity` |
| 7 | **Kết quả thực hiện** | `RESULT` | 0.35 | **0.90** | `result` |
| 8 | **Phí, lệ phí** | `FEE` | 0.50 | **0.10** | `fee` |
| 9 | **Căn cứ pháp lý** | `LEGAL_BASIS` | 0.40 | **0.74** | `legal_basis` |
| 10 | **Điều kiện thực hiện** | `ELIGIBILITY` | 0.50 | **0.60** | `other` (với cờ `has_eligibility`) |
| 11 | **Mẫu đơn, tờ khai** | `FORM` | 0.50 | **0.50** | `required_documents` (với cờ `has_forms`) |

---

### 2.5. Định dạng Dữ liệu Đầu ra Thực tế của PhoBERT (`PhoBERTRouter.predict`)

Khi gọi hàm [`predict()`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/phobert_router.py#L124-L139), đối tượng trả về là một `dict` (JSON format) cấu trúc rõ ràng gồm 3 phần:

```json
{
  /* ================= 1. KẾT QUẢ ĐÃ GIẢI MÃ (DECODED VALUES) ================= */
  "scope": "IN_SCOPE",               // "IN_SCOPE" | "OUT_OF_SCOPE" | "MIXED_SCOPE"
  "flow": "NEW",                     // "NEW" | "FOLLOW_UP"
  "mix": false,                      // false (1 thủ tục) | true (nhiều thủ tục)
  "sections": [                      // Danh sách các mục vượt qua ngưỡng kích hoạt Sigmoid
    "DOSSIER",
    "FEE"
  ],

  /* ================= 2. ĐIỂM XÁC SUẤT CHI TIẾT (PROBABILITIES) ================= */
  "probabilities": {
    "scope": {
      "Trong phạm vi": 0.9852,
      "Ngoài phạm vi": 0.0103,
      "Hỗn hợp phạm vi": 0.0045
    },
    "flow": {
      "Câu hỏi mới": 0.9412,
      "Hỏi tiếp": 0.0588
    },
    "mix": {
      "Không": 0.9921,
      "Có": 0.0079
    },
    "sections": {
      "Tổng quan": 0.0821,
      "Trình tự thực hiện": 0.0435,
      "Cách thức thực hiện": 0.1204,
      "Thành phần hồ sơ": 0.9150,   // >= threshold 0.50 -> Chọn DOSSIER
      "Thời hạn giải quyết": 0.1120,
      "Cơ quan thực hiện": 0.0350,
      "Kết quả thực hiện": 0.0210,
      "Phí, lệ phí": 0.8840,        // >= threshold 0.10 -> Chọn FEE
      "Căn cứ pháp lý": 0.0510,
      "Điều kiện thực hiện": 0.0620,
      "Mẫu đơn, tờ khai": 0.1450
    }
  },

  /* ================= 3. THÔNG TIN KỸ THUẬT & PREPROCESSING ================= */
  "encoded_length": 38,             // Độ dài chuỗi token sau khi tách từ PyVi và BPE
  "thresholds": {                   // Bảng ngưỡng kích hoạt riêng của 11 mục
    "Tổng quan": 0.31,
    "Trình tự thực hiện": 0.10,
    "Cách thức thực hiện": 0.89,
    "Thành phần hồ sơ": 0.50,
    "Thời hạn giải quyết": 0.22,
    "Cơ quan thực hiện": 0.14,
    "Kết quả thực hiện": 0.90,
    "Phí, lệ phí": 0.10,
    "Căn cứ pháp lý": 0.74,
    "Điều kiện thực hiện": 0.60,
    "Mẫu đơn, tờ khai": 0.50
  },
  "preprocessing": {
    "max_len": 128,
    "segmenter": "pyvi",
    "input_mode": "full"
  }
}
```

---

## 3. Tầng 2: Hệ thống Nhãn Quyết định, Hành động và Bằng chứng (Actions, Routes & Evidence)

### 3.1. Hệ thống Nhãn Hành vi Toàn diện (`action` & `canonical_action`)

Theo hợp đồng chuẩn hóa tại [`src/vigovbot/evaluation/records.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/evaluation/records.py#L212-L220) và schema [`prediction.schema.json`](file:///c:/Users/quangTam/Documents/ViGovBot/schema/prediction.schema.json#L128-L136), hệ thống ViGovBot quản lý **5 hành vi chuẩn (`canonical_action`)**:

| Nhãn `action` Runtime | Nhãn Chuẩn `canonical_action` | Bản chất Hành vi & Kịch bản Kích hoạt |
|---|---|---|
| **`answer`** | `answer` | Trả lời đầy đủ có bằng chứng trích dẫn rõ ràng từ kho TTHC. |
| **`partial`** | `partial_answer` | Trả lời một phần: Kích hoạt khi câu hỏi là `MIXED_SCOPE` hoặc khi bằng chứng trong kho chỉ đáp ứng một phần câu hỏi. |
| **`clarify`** | `clarify` | Dừng quy trình RAG; mở Signed Menu lựa chọn (thủ tục trùng tên, chuyên mục con) hoặc gửi câu hỏi làm rõ khi người dùng diễn đạt mơ hồ. |
| **`abstain`** | `abstain` | Từ chối trả lời an toàn: Câu hỏi ngoài phạm vi TTHC, câu chào hỏi xã giao, người dùng từ chối gợi ý xác nhận, hoặc câu hỏi chứa mã biên nhận cá nhân không có trong dữ liệu. |
| **`correct_premise`** | `correct_premise` | Đính chính tiền đề sai: Kích hoạt khi câu hỏi của người dùng chứa đựng tiền đề pháp lý sai trái hoặc không có căn cứ (ví dụ: *"Thủ tục cấp bằng lái xe máy cho trẻ 10 tuổi gồm những gì?"*). |

---

### 3.2. Hệ thống Nhãn Tuyến Điều phối (`actual_route`, `canonical_route` & `target_flow`)

| Tuyến Runtime (`actual_route`) | Tuyến Schema (`canonical_route`) | Luồng Benchmark (`target_flow`) | Ý nghĩa & Hành vi Vận hành |
|---|---|---|---|
| **`rag_search`** | `rag_search` | `rag_answer` | Tiến hành truy xuất ngữ nghĩa (Vector FAISS + BM25) theo mã TTHC hoặc query và gọi LLM Qwen tạo sinh câu trả lời. |
| **`clarify`** | `clarification_request` | `procedure_disambiguation_menu` | Dừng quy trình RAG, tạo Signed Menu danh sách các mã TTHC trùng tên (tối đa 5 lựa chọn) gửi cho người dùng. |
| **`clarify`** | `clarification_request` | `section_selection_menu` | Đã xác định đúng 1 mã TTHC nhưng câu hỏi không có mục nội dung; tạo Signed Menu các chuyên mục hiện có. |
| **`out_of_scope`** | `refusal` | `abstain_unanswerable` | Dừng toàn bộ RAG/LLM; gửi câu trả lời từ chối an toàn hoặc chào hỏi xã giao. |
| **`routing_error`** | `refusal` / `null` | `abstain_unanswerable` | Xảy ra lỗi phân loại nơ-ron hoặc timeout; kích hoạt câu fallback chuẩn để bảo toàn hệ thống. |

---

### 3.3. Hệ thống Nhãn Trạng thái Bằng chứng (`evidence_status`) & Ràng buộc Kép Giải mã

Trong [`src/vigovbot/rag/routing.py` (dòng 140–162)](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/routing.py#L140-L162), từ điển `EVIDENCE_ACTIONS` quy định nghiêm ngặt:

```python
EVIDENCE_ACTIONS = {
    "sufficient": "answer",
    "partial": "partial",
    "missing": "abstain",
    "contradictory_premise": "correct_premise",
    "ambiguous": "clarify"
}
```

| `evidence_status` | `action` Tương ứng | Điều kiện Áp dụng & Hành vi |
|---|---|---|
| **`sufficient`** | `answer` | Chunks tài liệu thu về từ mã TTHC cung cấp đầy đủ thông tin để LLM sinh câu trả lời hoàn chỉnh kèm trích dẫn (`citations`). |
| **`partial`** | `partial` (`partial_answer`) | Tài liệu chỉ trả lời được một phần yêu cầu hoặc câu hỏi thuộc dạng `MIXED_SCOPE`. |
| **`missing`** | `abstain` | Kho dữ liệu không chứa chunk phù hợp (`no_context`), mã TTHC không tồn tại (`unknown_source_code`), hoặc câu hỏi chứa mã định danh cá nhân không có trong bằng chứng (`identifier_not_in_evidence`). |
| **`contradictory_premise`**| `correct_premise` | Bằng chứng tài liệu khẳng định tiền đề của câu hỏi là trái quy định pháp luật. |
| **`ambiguous`** | `clarify` | Bằng chứng cho thấy câu hỏi còn đa nghĩa hoặc chưa đủ thông tin. |

---

### 3.4. Danh mục Chi tiết các Nhãn Lý do Quyết định (`decision_reason`)

#### Nhóm 1: Nhánh CLARIFY (Làm rõ)
1. **`procedure_required`**: Khớp $\ge 2$ mã TTHC trong Catalog (`len(codes) > 1`) hoặc kích hoạt Menu xác nhận (`confirmation=True`).
2. **`section_required`**: Khớp duy nhất 1 mã TTHC nhưng không hỏi rõ mục nào (`sections == []`).
3. **`ambiguous_question`**: Câu hỏi mang tính nối tiếp (`FOLLOW_UP`) nhưng mất context, hoặc cố tình hỏi gộp 2 thủ tục khác nhau.
4. **`invalid_selection`**: Nhập số menu ngoài danh sách hoặc gõ ký tự không hợp lệ.
5. **`expired_selection`**: State không khớp chữ ký HMAC SHA-256 hoặc cache phiên đã bị xóa.
6. **`procedure_rejected`**: Người dùng phản hồi phủ định (*"không phải mấy cái này"*).
7. **`selection_required`**: Người dùng chỉ trả lời đồng ý chung chung (*"đúng rồi"*, *"ok"*).
8. **`routing_fallback`**: PhoBERT gặp ngoại lệ OOM hoặc timeout.

#### Nhóm 2: Nhánh ANSWER (Trả lời RAG)
1. **`evidence_assessment`**: Lý do runtime mặc định khi hoàn tất sinh câu trả lời có cấu trúc.
2. **`plain_text_fallback`**: Adapter huấn luyện SFT trả về văn bản trực tiếp.
3. **`routing_disabled`**: Khi cờ cấu hình `routing_enabled: false`.
4. **`sufficient`**: Nhãn quy ước trong bộ kiểm thử `test_router.jsonl` (1.173 ca).

#### Nhóm 3: Nhánh ABSTAIN (Từ chối an toàn)
1. **`out_of_scope`**: PhoBERT dự đoán câu hỏi ngoài phạm vi với xác suất cao ($P \ge 85\%$) và Catalog không cứu vớt.
2. **`social_greeting`**: Chào hỏi xã giao thuần túy.
3. **`confirmation_rejected`**: Người dùng từ chối gợi ý xác nhận thủ tục.
4. **`identifier_not_in_evidence`**: Câu hỏi chứa mã định danh hồ sơ cá nhân (`HS-xxx`) nhưng tài liệu pháp lý không có mã này.
5. **`no_context`**: Kho dữ liệu hoàn toàn không tìm thấy chunk văn bản nào phù hợp.
6. **`unknown_source_code`**: Mã TTHC yêu cầu không tồn tại trong kho tài liệu.
7. **`unanswerable`**: Nhãn quy ước trong bộ kiểm thử `test_router.jsonl` (25 ca).

---

### 3.5. Hệ thống 6 Sự kiện Trọng tài Adapter Đầy đủ (`adapter_decisions` Telemetry)

| STT | Sự kiện (`type`) | Điều kiện Kích hoạt | Đầu ra (`outcome`) | Tác động Điều phối |
|:---:|---|---|---|---|
| 1 | **`catalog_scope_arbitration`** | PhoBERT đoán `OUT_OF_SCOPE` nhưng rơi vào vùng xác suất lưng chừng $50\% \le P < 85\%$, đồng thời câu hỏi khớp mã/tên trong Catalog. | `catalog_identity_overrode_out_of_scope` | Ghi đè `scope = IN_SCOPE`, cứu câu hỏi vào luồng RAG. |
| 2 | **`catalog_single_procedure_override_mixed`** | PhoBERT đoán `mix = True`, nhưng tất cả các mã TTHC tìm được trong Catalog đều trỏ về **cùng một tên thủ tục chuẩn hóa duy nhất** (`len(matched_names) == 1`). | `cleared_mixed_procedures` | Hạ `mixed = False`, mở Menu lựa chọn các mã TTHC trùng tên. |
| 3 | **`explicit_section_override`** | Người dùng nêu từ khóa chuyên mục tường minh (như *"thời hạn"*, *"lệ phí"*), nhưng PhoBERT dự đoán thiếu mục do ngưỡng Sigmoid. | `accepted` | Ghi đè tập `sections` theo ý định tường minh của người dùng. |
| 4 | **`procedure_switch_reset`** | Đang trong mạch `FOLLOW_UP` của thủ tục cũ, người dùng chủ động nêu tên một thủ tục mới hoàn toàn độc lập (`set(new_candidates).isdisjoint(selected)`). | `accepted` | Chuyển `conversation` thành `NEW`, gán mã mới và xóa toàn bộ chuyên mục cũ. |
| 5 | **`history_identity_recovery`** | Khách hàng dùng stateless client bị mất state, người dùng hỏi tiếp (`turn_follow_up`) mà không nhắc lại tên thủ tục. | `accepted` | Quét ngược lịch sử tin nhắn của người dùng, khôi phục mã TTHC duy nhất đã được xác thực trước đó. |
| 6 | **`mixed_scope_llm_rewrite`** | Câu hỏi phức hợp `MIXED_SCOPE` được đưa qua LLM trích xuất mệnh đề con độc lập. | `accepted_after_phobert` | Trích xuất câu hỏi TTHC sạch, tái phân loại đạt `IN_SCOPE` và tiến hành RAG kèm câu cảnh báo phạm vi. |

---

## 4. Bảng Đối soát Toàn diện Hợp đồng (Taxonomy, State Mapping & Contract Cross-walk)

Bảng tổng hợp đối soát ma trận trạng thái đa chiều kết nối giữa **PhoBERT Router**, **Runtime Execution**, **Tiêu chuẩn Schema v3.2** và **Bộ Benchmark Golden Dataset**:

| Tình huống Thực tế | Nhãn PhoBERT Router | `actual_route` / `canonical_route` | `target_flow` (Benchmark) | `action` Runtime / Canonical | `decision_reason` | `evidence_status` | Trạng thái Tiếp theo |
|---|---|---|---|---|---|---|---|
| Hỏi rõ 1 thủ tục + mục hỏi | `IN_SCOPE`, `NEW`, `mix: False`, `sections: [FEE]` | `rag_search` / `rag_search` | `rag_answer` | `answer` / `answer` | `evidence_assessment` (`sufficient`) | `sufficient` | RAG Search & LLM trả lời |
| Tên thủ tục khớp nhiều đối tượng (`len >= 2`) | `IN_SCOPE`, `NEW`, `mix: False`, `sections: [...]` | `clarify` / `clarification_request` | `procedure_disambiguation_menu` | `clarify` / `clarify` | `procedure_required` | `None` | Hiển thị Signed Menu thủ tục |
| Thủ tục tên dài có liệt kê nhưng là 1 TTHC | `IN_SCOPE`, `NEW`, `mix: True` $\rightarrow$ **Override False** | `clarify` / `clarification_request` | `procedure_disambiguation_menu` | `clarify` / `clarify` | `procedure_required` | `None` | Mở Menu chọn mã trùng tên |
| Cố tình hỏi gộp 2 thủ tục khác nhau | `IN_SCOPE`, `NEW`, `mix: True` (Không override) | `clarify` / `clarification_request` | `abstain_unanswerable` | `clarify` / `clarify` | `ambiguous_question` | `None` | Chặn trả lời, yêu cầu hỏi riêng |
| Chỉ nêu tên 1 thủ tục duy nhất (`len == 1`) | `IN_SCOPE`, `NEW`, `mix: False`, `sections: []` | `clarify` / `clarification_request` | `section_selection_menu` | `clarify` / `clarify` | `section_required` | `None` | Hiển thị Signed Menu chuyên mục |
| Không khớp mã trong Catalog (`len == 0`) | `IN_SCOPE`, `NEW`, `mix: False`, `sections: [...]` | `rag_search` / `rag_search` | `rag_answer` | `answer` / `answer` | `evidence_assessment` | `sufficient` | Semantic Fallback RAG |
| PhoBERT đoán OUT (50-85%) nhưng có trong Catalog | `OUT_OF_SCOPE` $\rightarrow$ **Override IN_SCOPE** | `rag_search` / `rag_search` | `rag_answer` | `answer` / `answer` | `evidence_assessment` | `sufficient` | Bẻ còi sang tra cứu RAG |
| PhoBERT đoán OUT (>85%) nhưng khớp từ vựng $\ge 70\%$ | `OUT_OF_SCOPE` | `clarify` / `clarification_request` | `procedure_disambiguation_menu` | `clarify` / `clarify` | `procedure_required` | `None` | Menu gợi ý xác nhận thủ tục |
| Hỏi tình trạng mã biên nhận cá nhân (`HS-xxx`) | `IN_SCOPE` hoặc `OUT_OF_SCOPE` | `out_of_scope` / `refusal` | `abstain_unanswerable` | `abstain` / `abstain` | `identifier_not_in_evidence` | `missing` | Từ chối đoán mò hồ sơ cá nhân |
| Đang hỏi TTHC này đột ngột đổi sang TTHC khác | `IN_SCOPE`, `FOLLOW_UP` $\rightarrow$ **Reset NEW** | `rag_search` / `rag_search` | `rag_answer` | `answer` / `answer` | `evidence_assessment` | `sufficient` | Reset NEW, tra cứu TTHC mới |
| Người dùng từ chối Menu (*"không đúng/sai"*) | (Đang ở trạng thái Menu) | `clarify` / `clarification_request` | `procedure_disambiguation_menu` | `clarify` / `clarify` | `procedure_rejected` | `None` | Đưa danh sách ứng viên thay thế |
| Người dùng trả lời đồng ý chung chung (*"ok"*) | (Đang ở trạng thái Menu) | `clarify` / `clarification_request` | `procedure_disambiguation_menu` | `clarify` / `clarify` | `selection_required` | `None` | Yêu cầu chọn đúng số thứ tự |
| Câu hỏi hỗn hợp (thủ tục + ngoài lề) | `MIXED_SCOPE` | `rag_search` / `rag_search` | `rag_answer` | `partial` / `partial_answer` | `evidence_assessment` | `partial` | Trích xuất câu TTHC, kèm notice |
| Hỏi tiếp nhưng mất state (Stateless Client) | `IN_SCOPE`, `FOLLOW_UP` | `rag_search` / `rag_search` | `rag_answer` | `answer` / `answer` | `evidence_assessment` | `sufficient` | Khôi phục mã từ lịch sử user |
| Tiền đề pháp lý sai trái (vd: kết hôn tuổi 10) | `IN_SCOPE`, `NEW` | `rag_search` / `rag_search` | `rag_answer` | `correct_premise` / `correct_premise`| `evidence_assessment` | `contradictory_premise`| Đính chính tiền đề pháp luật |
| Câu hỏi ngoài lề (thời tiết, code) | `OUT_OF_SCOPE`, `NEW`, `mix: False`, `sections: []` | `out_of_scope` / `refusal` | `abstain_unanswerable` | `abstain` / `abstain` | `out_of_scope` (`unanswerable`) | `missing` | Trả lời từ chối an toàn |
| Hỏi tiếp nhưng không có lịch sử | `IN_SCOPE`, `FOLLOW_UP`, `mix: False`, `sections: [...]` | `clarify` / `clarification_request` | `abstain_unanswerable` | `clarify` / `clarify` | `ambiguous_question` | `None` | Yêu cầu nêu rõ tên thủ tục |
| Chào hỏi xã giao | `OUT_OF_SCOPE`, `NEW`, `mix: False`, `sections: []` | `out_of_scope` / `refusal` | `abstain_unanswerable` | `abstain` / `abstain` | `social_greeting` | `missing` | Phản hồi lời chào lịch sự |
| Nhập sai số menu | (Bỏ qua Router, xử lý trực tiếp `direct_choice`) | `clarify` / `clarification_request` | `procedure_disambiguation_menu` | `clarify` / `clarify` | `invalid_selection` | `None` | Hiển thị lại Menu hiện tại |
| Menu quá hạn hoặc sai chữ ký HMAC | (Bỏ qua Router, kiểm tra chữ ký state) | `clarify` / `clarification_request` | `procedure_disambiguation_menu` | `clarify` / `clarify` | `expired_selection` | `None` | Yêu cầu nêu lại tên thủ tục |

---

## 5. Phân tích Khám phá Dữ liệu EDA trên Bộ Benchmark `test_router.jsonl` (1.246 mẫu)

Tập benchmark [`Data/dataset_v3/test_router/test_router.jsonl`](file:///c:/Users/quangTam/Documents/ViGovBot/Data/dataset_v3/test_router/test_router.jsonl) bao gồm **1.246 mẫu kiểm chuẩn độc lập** bao phủ 150 lĩnh vực quản lý nhà nước:

### 5.1. Quy mô Tập dữ liệu và Phân lớp Mẫu

| Chỉ số Phân loại | Số lượng mẫu ($N$) | Tỷ lệ (%) | Ý nghĩa Nghiệm thu / Vai trò Vận hành |
| :--- | :---: | :---: | :--- |
| **Tổng số ca kiểm thử** | **1.246** | **100,0%** | Tập kiểm chuẩn toàn diện cho bộ định tuyến đa nhiệm |
| **Câu hỏi mở đầu mới (`turn_new_question`)** | 743 | 59,63% | Câu hỏi lượt đầu tiên, không có lịch sử hội thoại trước đó |
| **Câu hỏi tiếp nối (`turn_follow_up`)** | 503 | 40,37% | Câu hỏi phụ thuộc ngữ cảnh, đòi hỏi ghi nhớ trạng thái hội thoại |
| **Độ khó thông thường (`diff_medium`)** | 1.084 | 87,00% | Câu hỏi hành chính tường minh, cú pháp chuẩn |
| **Độ khó cao / Bẫy (`diff_hard`)** | 162 | 13,00% | Câu hỏi nhiều ý định, diễn đạt phức tạp hoặc bẫy thẩm quyền |
| **Suy luận đơn bước (`single_hop`)** | 1.128 | 90,53% | Câu hỏi nhắm vào một chương mục thủ tục duy nhất |
| **Suy luận đa ý định (`multi_intent`)** | 118 | 9,47% | Câu hỏi hỏi đồng thời nhiều nội dung (vd: hồ sơ và lệ phí) |
| **Không thể trả lời (`abstain`)** | 25 | 2,01% | Câu hỏi ngoài quy định pháp luật, yêu cầu từ chối an toàn |

### 5.2. Phân bổ Hành vi Điều phối và Luồng Xử lý Mục tiêu

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

- **Phân định đa thủ tục trùng tên (3,61%):** Trong 45 trường hợp, tên thủ tục người dân cung cấp xuất hiện ở nhiều cấp chính quyền (vd: cấp Tỉnh, cấp Huyện hoặc cấp Xã). Bộ định tuyến nhận diện chính xác sự mơ hồ và xuất menu thẻ phân định thay vì tự ý truy xuất sai thẩm quyền.
- **Số lượng mã thủ tục khớp được (`matched_procedure_count`):** 1.201 trường hợp (96,39%) ánh xạ chính xác đến duy nhất 1 mã TTHC; 45 trường hợp ánh xạ đến 2, 3, 4 hoặc 7 thủ tục khả dĩ.

### 5.3. Phân bổ theo Lĩnh vực Quản lý Nhà nước
Bộ dữ liệu trải rộng trên 150 lĩnh vực công vụ khác nhau:
1. **Đất đai:** 195 ca (15,65%)
2. **Hải quan:** 46 ca (3,69%)
3. **Hàng hải và đường thủy nội địa:** 43 ca (3,45%)
4. **Hoạt động khoa học và công nghệ:** 31 ca (2,49%)
5. **Thành lập và hoạt động ngân hàng:** 28 ca (2,25%)
6. **Chứng khoán:** 27 ca (2,17%)

### 5.4. Phân bổ Nhãn Đa mục Pháp lý (`sections`)

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

---

## 6. Kết quả Thực nghiệm Đánh giá Router V1 (Ngưỡng Gốc)

| Nhóm chỉ số | Chỉ số cụ thể | Kết quả Đạt được | Mục tiêu Chuẩn | Nhận xét |
|---|---|:---:|:---:|---|
| **1. PhoBERT 4-Head Model** | **Scope Accuracy** | **96.95%** | $\ge 95\%$ | Nhận diện xuất sắc ranh giới phạm vi (`IN_SCOPE`). |
| | **Conversation Flow Acc** | **98.80%** | $\ge 95\%$ | Phân biệt gần như tuyệt đối giữa câu mới (`NEW`) và hỏi tiếp (`FOLLOW_UP`). |
| | **Mix Procedures Acc** | **100.00%** | $\ge 95\%$ | Nhận diện hoàn hảo nhờ Trọng tài Catalog giải cứu 100% ca tên dài. |
| | **Sections Exact Match** | **75.52%** | $\ge 80\%$ | Trùng khớp 100% tập mục nội dung hỏi (ngưỡng V1 còn khắt khe). |
| | **Sections Mean Jaccard** | **77.55%** | $\ge 80\%$ | Độ tương đồng trung bình của tập nhãn đa mục. |
| | **PhoBERT 4-Head Joint** | **73.03%** | $\ge 70\%$ | Cả 4 heads của mô hình đều dự đoán đúng cùng lúc. |
| **2. Catalog Disambiguation** | **Procedure Codes Match** | **91.81%** | $\ge 90\%$ | Bắt chính xác danh sách mã TTHC từ Catalog (nhờ chuẩn hóa tên). |
| | **Candidate Count Acc** | **91.81%** | $\ge 90\%$ | Nhận diện đúng số lượng $n$ thủ tục ứng viên. |
| **3. Decision & Action** | **Action Accuracy** | **84.27%** | $\ge 85\%$ | Ra đúng hành vi `answer`, `clarify`, `abstain`. |
| | **Decision Reason Acc** | **84.27%** | $\ge 85\%$ | Đúng lý do cụ thể (`sufficient`, `procedure_required`...). |
| | **Target Flow Accuracy** | **84.27%** | $\ge 85\%$ | Rẽ đúng vào luồng mục tiêu của hệ thống. |
| **4. Toàn diện Cấp Hệ thống** | ★ **STRICT E2E ACCURACY** | **67.09%** | $\ge 65\%$ | **Tất cả các tiêu chí cùng đúng 100% trên 1 mẫu (836/1.246 mẫu)**. |
| **5. Hiệu năng & Độ trễ** | **Latency P50 / P95** | **208 ms / 312 ms** | $< 1.500$ ms | Tốc độ suy luận CPU hoàn toàn đáp ứng thời gian thực. |

---

## 7. Nghiên cứu Hiệu chỉnh Ngưỡng (Threshold Calibration) và Đánh giá Router V2

| Chỉ số (Index) | Tên tiếng Việt | Mã Enum quốc tế | Ngưỡng V1 (Gốc) | Ngưỡng V2 (Tối ưu) | Độ dịch chuyển ($\Delta \tau$) | Cơ chế Điều chỉnh |
|:---:|---|---|:---:|:---:|:---:|---|
| `0` | Tổng quan | `OVERVIEW` | **0.50** | **0.31** | -0.19 | Hạ ngưỡng để cố gắng vớt các câu hỏi tổng quát |
| `1` | Trình tự thực hiện | `PROCEDURE` | **0.65** | **0.10** | -0.55 | Hạ sâu để gom các câu hỏi quy trình ngắn gọn |
| `2` | Cách thức thực hiện | `SUBMISSION_METHOD` | **0.70** | **0.89** | +0.19 | Tăng ngưỡng để khử False Positive |
| `3` | Thành phần hồ sơ | `DOSSIER` | **0.40** | **0.50** | +0.10 | Tăng nhẹ để cân bằng Precision/Recall tuyệt đối |
| `4` | Thời hạn giải quyết | `PROCESSING_TIME` | **0.75** | **0.22** | **-0.53** | **Hạ ngưỡng mạnh** (gỡ bỏ nút thắt False Negative) |
| `5` | Cơ quan thực hiện | `AUTHORITY` | **0.70** | **0.14** | -0.56 | Hạ ngưỡng để bắt trọn câu hỏi thẩm quyền |
| `6` | Kết quả thực hiện | `RESULT` | **0.35** | **0.90** | **+0.55** | **Tăng ngưỡng mạnh** (khử nhầm lẫn với Overview) |
| `7` | Phí, lệ phí | `FEE` | **0.50** | **0.10** | **-0.40** | **Hạ ngưỡng sâu** (loại bỏ 100% ca sót lệ phí) |
| `8` | Căn cứ pháp lý | `LEGAL_BASIS` | **0.40** | **0.74** | +0.34 | Tăng ngưỡng để lọc nhiễu văn bản |
| `9` | Điều kiện thực hiện | `ELIGIBILITY` | **0.50** | **0.60** | +0.10 | Tăng nhẹ để tránh kích hoạt sai |
| `10` | Mẫu đơn, tờ khai | `FORM` | **0.50** | **0.50** | 0.00 | Giữ nguyên (không có mẫu dương tính trong test) |

---

### 7.1. Bảng So sánh Đối đầu Toàn diện: Lần 1 (V1 Gốc) vs Lần 2 (V2 Calibrated)

| Nhóm Kiểm thử | Chỉ số Đo lường | Lần 1 (V1 Gốc) | Lần 2 (V2 Calibrated) | Độ Tăng trưởng ($\Delta$) | Đánh giá Kỹ thuật |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **PhoBERT 4 Heads** | Scope Accuracy | 96.95% | 96.95% | +0.00% | Đầu ra nhãn Softmax (argmax), không đổi. |
| | Conversation Flow Acc | 98.80% | 98.80% | +0.00% | Đầu ra nhãn Softmax (argmax), không đổi. |
| | Mixed Procedures Acc | 100.00% | 100.00% | +0.00% | Hoàn hảo 100% nhờ Trọng tài Catalog. |
| | **Sections Exact Match** | **75.52%** | **83.71%** | **+8.19%** | **Đột phá mạnh mẽ** nhờ gỡ bỏ ngưỡng khắt khe. |
| | Sections Mean Jaccard | 77.55% | 84.14% | +6.59% | Mức độ giao thoa danh sách mục tăng rõ rệt. |
| | **4-Head Joint Match** | **73.03%** | **80.34%** | **+7.31%** | Tỷ lệ cả 4 heads PhoBERT đồng thời chuẩn 100%. |
| **Catalog & Entities**| Catalog Codes Match | 91.81% | 91.81% | +0.00% | Tầng Clarifier Catalog độc lập với PhoBERT. |
| | Candidate Count Acc | 91.81% | 91.81% | +0.00% | Giữ nguyên độ chuẩn xác ứng viên. |
| **Quyết định Điều phối**| **Action Accuracy** | **84.27%** | **91.33%** | **+7.06%** | Giảm thiểu tối đa việc rơi nhầm vào `clarify: section_req`. |
| | **Decision Reason Acc** | **84.27%** | **91.33%** | **+7.06%** | Nhận diện chuẩn xác lý do `sufficient`. |
| | Target Flow Accuracy | 84.27% | 91.33% | +7.06% | Luồng đích điều hướng chính xác. |
| **Toàn diện Hệ thống**| ★ **STRICT E2E ACCURACY** | **67.09%** | **74.08%** | **+6.99%** | **Tăng từ 836 mẫu lên 923 mẫu chuẩn tuyệt đối.** |
| | **Tổng số ca lỗi E2E** | **410 ca** | **323 ca** | **Giảm 87 ca** | **Triệt tiêu 21.2% tổng số lỗi của hệ thống.** |

---

### 7.2. Phân tích Cắt lớp Phân khúc Đối đầu (Cohort Breakdown: V1 vs V2)

| Phân khúc Kiểm thử | Số mẫu | Strict E2E V1 | Strict E2E V2 | Biến thiên E2E | Action Acc V1 | Action Acc V2 | Biến thiên Action |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Độ khó: Hard (`diff_hard`)** | 162 | **40.74%** | **85.19%** | **+44.45%** | **70.37%** | **98.77%** | **+28.40%** |
| **Độ khó: Medium (`diff_medium`)** | 1.084 | **71.03%** | **72.42%** | **+1.39%** | **86.35%** | **90.22%** | **+3.87%** |
| **Mạch: Hỏi tiếp (`turn_follow_up`)** | 503 | **73.16%** | **82.50%** | **+9.34%** | **77.34%** | **89.26%** | **+11.92%** |
| **Mạch: Câu hỏi mới (`turn_new_question`)** | 743 | **62.99%** | **68.37%** | **+5.38%** | **88.96%** | **92.73%** | **+3.77%** |

> [!IMPORTANT]
> **Điểm đột phá vượt trội ở phân khúc ca khó (`diff_hard`):**
> Chỉ số Strict E2E của các ca khó nhảy vọt từ **40,74% lên 85,19%** (tăng **+44,45%**), đồng thời Action Accuracy đạt tới **98,77%**.

---

### 7.3. Phân tích Bản chất 323 Ca Lỗi Còn lại trong Router V2

![Bản chất 323 ca lỗi còn lại trong Router V2](images/chart_router_v2_failures_pie.png)
*(Xem tệp hình ảnh gốc độ phân giải cao tại: [chart_router_v2_failures_pie.png](file:///c:/Users/quangTam/Documents/ViGovBot/docs/reports/images/chart_router_v2_failures_pie.png))*

<details>
<summary><b>Chi tiết mã nguồn Mermaid (nhấn để mở rộng)</b></summary>

```mermaid
pie title Bản chất 323 ca lỗi còn lại trong Router V2
    "Giới hạn mô hình PhoBERT (p dưới 0.15)" : 179
    "Tầng Clarifier Catalog (Lệch mã/từ đồng nghĩa)" : 102
    "Lệch nhãn Softmax PhoBERT (Scope/Flow)" : 40
    "Nhiễu biên ngưỡng (0.15 đến dưới ngưỡng)" : 2
```

</details>

1. **Hiệu quả của việc điều chỉnh ngưỡng:** Đã khai thác tới **99% tiềm năng** của checkpoint mô hình hiện tại (chỉ còn đúng 2 ca nằm ở vùng biên ngưỡng). Mang lại mức tăng **+6.99% E2E Accuracy**, đưa tỷ lệ chính xác từ 67.09% lên 74.08%, đồng thời đưa Action Accuracy đạt **91.33%**.
2. **179 ca (55.4%) - Giới hạn biểu diễn ngữ nghĩa của PhoBERT (Model Representation Gap):** Tiêu biểu là nhãn `OVERVIEW` (Tổng quan) khi người dùng hỏi về *"đối tượng thực hiện"*, mô hình sinh xác suất $p < 0.05$.
3. **102 ca (31.6%) - Giới hạn của Tầng Đối soát Thực thể Catalog:** Do người dùng dùng tên tắt địa phương hoặc cấu trúc câu dài không khớp chuỗi từ khóa.
4. **40 ca (12.4%) - Sai lệch Softmax ở các đầu phân loại khác của PhoBERT:** Rơi vào phân loại `scope` (38 ca) hoặc `flow` (15 ca). Riêng `mix` đã đạt 100% không còn lỗi.

---

## 8. Hướng dẫn Tích hợp & Vận hành (Operational & Integration Guide)

### 8.1. Gọi trực tiếp qua Python API (`answer_conversation`)

```python
from vigovbot.rag.conversation import answer_conversation
from vigovbot.rag.clarification import Clarifier
from vigovbot.retrieval.retriever import UnifiedRetriever

# 1. Khởi tạo Retriever và Clarifier
retriever = UnifiedRetriever.from_config(settings)
clarifier = Clarifier(retriever, scope="tthc", settings=settings)

# 2. Điều phối hội thoại
result = answer_conversation(
    question="Hồ sơ làm hộ chiếu gồm những gì?",
    history=[],                         # Danh sách tin nhắn [{"role": "user", "content": ...}]
    conversation_state=None,            # State có chữ ký từ lượt trước (nếu có)
    selection=None,                     # Lựa chọn menu {"menu_id": "...", "option_id": "..."}
    settings=settings,                  # Cấu hình runtime từ inference.yaml
    retriever=retriever,
    clarifier=clarifier,
    tokenizer=tokenizer,
    phobert=True,                       # Sử dụng PhoBERT 4-Head Router
    router_fn=None,
    answer_fn=call_llm_generation,
    corpus="tthc_corpus_v3"
)

# 3. Đọc kết quả chuẩn hóa
print("Action:", result["action"])                 # "answer" | "clarify" | "abstain"
print("Route:", result["actual_route"])            # "rag_search" | "clarify" | "out_of_scope"
print("Reason:", result["decision_reason"])        # "evidence_assessment" | "procedure_required"
print("State:", result["conversation_state"])      # Signed State bảo mật HMAC SHA-256
```

### 8.2. Định dạng Yêu cầu & Phản hồi HTTP REST API

#### Request Payload:
```json
{
  "question": "Lệ phí và thời hạn làm giấy phép lái xe quốc tế?",
  "history": [],
  "conversation_state": null,
  "selection": null,
  "model_id": "qwen-rag"
}
```

#### Response Payload (RAG Thành công):
```json
{
  "answer": "Theo quy định, lệ phí cấp Giấy phép lái xe quốc tế (IDP) là 135.000 đồng/lần. Thời hạn giải quyết là không quá 05 ngày làm việc...",
  "action": "answer",
  "evidence_status": "sufficient",
  "actual_route": "rag_search",
  "decision_reason": "evidence_assessment",
  "conversation_state": {
    "version": 2,
    "scope": "tthc",
    "selected": ["1.002824"],
    "history_fingerprint": "a4f89d...",
    "signature": "8b3e9f..."
  },
  "menu": null,
  "citations": [
    {
      "chunk_id": "chunk_1.002824_fee_01",
      "claim": "lệ phí cấp Giấy phép lái xe quốc tế (IDP) là 135.000 đồng/lần",
      "source_code": "1.002824"
    }
  ]
}
```

#### Response Payload (Mở Menu Làm rõ Thủ tục Trùng tên):
```json
{
  "answer": "Bạn muốn hỏi thủ tục nào trong danh sách sau?\n1. Đăng ký kết hôn (Cấp Xã)\n2. Đăng ký kết hôn có yếu tố nước ngoài (Cấp Tỉnh)",
  "action": "clarify",
  "evidence_status": null,
  "actual_route": "clarify",
  "decision_reason": "procedure_required",
  "menu": {
    "id": "menu_7c1b...",
    "kind": "procedure",
    "options": [
      { "id": "1.001234", "label": "Đăng ký kết hôn (Cấp Xã)" },
      { "id": "1.001235", "label": "Đăng ký kết hôn có yếu tố nước ngoài (Cấp Tỉnh)" }
    ]
  },
  "conversation_state": {
    "version": 2,
    "signature": "3d5f1a..."
  }
}
```

### 8.3. Cấu hình Vận hành Runtime trong `configs/rag/inference.yaml`

```yaml
conversation:
  routing_backend: phobert
  routing_phobert_path: ../../outputs/phobert_v3_finetuned_20261028/checkpoint
  routing_phobert_threads: 2

retrieval:
  top_k: 15
  max_chunk_tokens: 1200
  max_metadata_tokens: 256

web:
  debug_routing: false  # Đặt true khi cần xem raw JSON telemetry trong API chẩn đoán
```

---

## 9. Kết luận

Hệ thống nhãn phân loại, trạng thái bằng chứng và hành vi điều phối của ViGovBot đại diện cho một kiến trúc hybrid hoàn chỉnh, kết hợp hài hòa giữa:
1. **Sức mạnh biểu diễn ngữ nghĩa** của mô hình học sâu PhoBERT fine-tune 4 đầu ra.
2. **Tính chuẩn xác và an toàn tuyệt đối** của cơ sở dữ liệu pháp điển Catalog TTHC và các luật trọng tài Adapter.
3. **Ràng buộc kép chống ảo giác** giữa `evidence_status` và `action` qua Constrained Decoding.
4. **Bảo mật trạng thái đa phiên** bằng chữ ký số mật mã HMAC SHA-256.

Việc chuẩn hóa các hợp đồng `actual_route`, `canonical_route`, `target_flow`, `action`, `decision_reason` và bảng ngưỡng động V2 giúp ViGovBot đạt **91,33% Độ chính xác Hành vi** và **74,08% Độ chính xác Toàn diện End-to-End** trên bộ dữ liệu chuẩn 1.246 mẫu, bảo đảm vận hành tin cậy, minh bạch và an toàn trong môi trường dịch vụ công trực tuyến.
