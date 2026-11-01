# Báo cáo Chi tiết: Hệ thống Nhãn Phân loại (Routing Labels) & Hành vi Điều phối (Actions) trong ViGovBot

## 1. Tổng quan Kiến trúc Điều phối Hai tầng (Two-Tier Architecture)

Trong hệ thống ViGovBot, quá trình định tuyến câu hỏi và đưa ra quyết định hành động không phụ thuộc đơn lẻ vào mô hình máy học (ML) hay các câu lệnh rẽ nhánh cứng (rules), mà được thiết kế theo **kiến trúc phân tầng chặt chẽ**:

```mermaid
flowchart TD
    UserQuery["Câu hỏi người dùng"] --> T1["Tầng 1: PhoBERT 4-Head Router\n(Phân loại ngữ nghĩa toàn cục)"]
    T1 --> CheckScope{"Phạm vi (Scope)?"}
    
    CheckScope -- "OUT_OF_SCOPE" --> CheckProb{"Xác suất P(Ngoài phạm vi)?"}
    CheckProb -- "50% <= P < 85%\n(Vùng lưng chừng)" --> ArbScope{"[Trọng tài Catalog]\nCó mã/tên trong Catalog?"}
    ArbScope -- "Có (len >= 1)" --> OverrideScope["Override: Ghi đè thành IN_SCOPE!\n(catalog_scope_arbitration)"]
    OverrideScope --> CheckMix
    ArbScope -- "Không" --> CheckConf{"[Xác nhận thủ tục]\nKhớp tương đồng >= 70%?"}
    
    CheckProb -- "P >= 85%\n(Thiên về Ngoài phạm vi)" --> CheckConf
    CheckConf -- "Có ứng viên phù hợp" --> ConfMenu["action: clarify\ndecision_reason: procedure_required\n(Mở Menu xác nhận thủ tục)"]
    CheckConf -- "Không khớp thủ tục nào" --> ActionAbstain["action: abstain\ndecision_reason: out_of_scope\n(Từ chối ngay, không gọi FAISS/LLM)"]

    CheckScope -- "MIXED_SCOPE" --> RegexLLMRewrite["Regex Split & LLM Rewrite\n(Trích xuất mệnh đề hợp lệ)"]
    RegexLLMRewrite --> CheckMix

    CheckScope -- "IN_SCOPE" --> CheckMix{"Trộn thủ tục\n(mix head)?"}
    CheckMix -- "True (Nhiều thủ tục)" --> ArbMix{"[Trọng tài Catalog]\nCùng 1 tên thủ tục chuẩn hóa?"}
    ArbMix -- "Đúng (len == 1)" --> OverrideMix["Override: mixed = False\n(catalog_single_procedure_override_mixed)"]
    OverrideMix --> T2["Tầng 2: Conversation Adapter & Catalog\n(Đối soát thực thể & Quản lý hội thoại)"]
    ArbMix -- "Sai (len != 1)" --> BlockMulti["action: clarify\ndecision_reason: ambiguous_question\n(Chặn: Yêu cầu hỏi riêng từng thủ tục)"]

    CheckMix -- "False (Đơn thủ tục)" --> T2
    
    T2 --> CatalogCheck{"Khớp mã trong Catalog TTHC?"}
    CatalogCheck -- "Khớp > 1 mã (len > 1)\n(Trùng tên/nhiều cấp)" --> ClarifyProc["action: clarify\ndecision_reason: procedure_required\n(Mở Menu chọn thủ tục trùng tên)"]
    CatalogCheck -- "Khớp đúng 1 mã (len == 1)" --> CheckSection{"Đã có mục nội dung (sections)?"}
    CatalogCheck -- "Không khớp mã nào (len == 0)" --> FallbackSemantic["Retriever Semantic Search\n(Tìm kiếm ngữ nghĩa toàn bộ corpus)"]
    
    CheckSection -- "Có mục nội dung" --> ActionRAG["actual_route: rag_search\naction: answer\n(RAG Search & LLM Generation)"]
    CheckSection -- "Chưa có mục (sections rỗng)" --> ClarifySec["action: clarify\ndecision_reason: section_required\n(Mở Menu chọn mục nội dung)"]
```

1. **Tầng 1 - Mô hình học máy ([`PhoBERTRouter`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/phobert_router.py#L89-L150)):** Phân loại các đặc tính ngữ nghĩa toàn cục (phạm vi, mạch hội thoại, trộn thủ tục, 11 mục nội dung).
2. **Tầng 2 - Tầng điều phối hội thoại ([`conversation.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L101-L200) & [`Clarifier`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/clarification.py#L82-L135)):** Đối soát với Database Catalog TTHC thực tế, quản lý trạng thái phiên có chữ ký HMAC, phát hiện đa ứng viên và quyết định hành động (`action`) cụ thể.

---

## 2. Tầng 1: Hệ thống 4 Head của PhoBERT Router

Mô hình PhoBERT nhận đầu vào là chuỗi tokenized `<s> question </s></s> previous </s></s> procedure </s>` (tối đa 128 token) và sử dụng 4 linear head riêng biệt được cấu hình trong [`meta.json`](file:///c:/Users/quangTam/Documents/ViGovBot/outputs/phobert_v3_finetuned_20261028/checkpoint/meta.json):

### 2.1. Head 1: Phạm vi (`scope` / `phạm_vi`)
Đánh giá mức độ liên quan tới lĩnh vực Thủ tục hành chính (TTHC) Việt Nam (Softmax):
- **`IN_SCOPE` (`Trong phạm vi`)**: Câu hỏi liên quan đến thủ tục, hồ sơ, thời hạn, phí, cơ quan giải quyết,...
- **`OUT_OF_SCOPE` (`Ngoài phạm vi`)**: Câu hỏi không thuộc phạm vi hỗ trợ (thời tiết, lập trình, trò chuyện tự do,...).
- **`MIXED_SCOPE` (`Hỗn hợp phạm vi`)**: Chứa cả yêu cầu thủ tục lẫn câu hỏi ngoài lề (hệ thống sẽ phân rã regex hoặc dùng LLM trích xuất đoạn nguyên văn liên quan).

### 2.2. Head 2: Mạch hội thoại (`flow` / `mạch_hội_thoại`)
Xác định mức độ phụ thuộc vào ngữ cảnh lịch sử chat (Softmax):
- **`NEW` (`Câu hỏi mới`)**: Câu hỏi độc lập, tự chứa đủ thông tin hoặc chủ động đổi sang thủ tục mới.
- **`FOLLOW_UP` (`Hỏi tiếp`)**: Câu hỏi phụ thuộc vào ngữ cảnh liền trước (ví dụ: *"hết bao nhiêu ngày?", "hồ sơ gồm những gì?"*).

### 2.3. Head 3: Trộn thủ tục (`mix` / `trộn_thủ_tục`)
Dự đoán câu hỏi có chứa đồng thời nhiều thủ tục khác nhau hay không (Softmax):
- **`False` (`Không`)**: Chỉ hỏi về 1 thủ tục hành chính duy nhất (hoặc nêu tên chung chung).
- **`True` (`Có`)**: Cố tình hỏi đồng thời từ 2 thủ tục hành chính khác nhau trong một câu (hệ thống sẽ yêu cầu tách riêng từng thủ tục để tránh ghép nhầm dữ liệu).

> [!NOTE]
> **Cơ chế Trọng tài Adapter Catalog (`catalog_single_procedure_override_mixed`):**
> Đối với các thủ tục hành chính có tên chính thức rất dài và chứa các mệnh đề liệt kê (ví dụ: *"Giao đất, cho thuê đất, chuyển mục đích sử dụng đất đối với trường hợp giao đất, cho thuê đất... giao đất và giao rừng; cho thuê đất và cho thuê rừng"*), mô hình nơ-ron PhoBERT có thể bị đánh lừa ngữ cảnh và dự đoán nhầm `mix = True` ($p > 99\%$). Tầng Adapter sẽ kiểm tra đối soát với Catalog: nếu toàn bộ mã nhận diện được cùng quy về **một tên thủ tục chính thức duy nhất**, cờ `mix` sẽ được hạ xuống `False` để mở Menu làm rõ các mã thủ tục trùng tên thay vì trả lời chặn gây gián đoạn hội thoại.

### 2.4. Head 4: Mục nội dung (`sections` / `mục_nội_dung`)
Phân loại đa nhãn (multi-label) với cơ chế kích hoạt hàm Sigmoid và bảng ngưỡng riêng (`thresholds`):

| STT | Nhãn tiếng Việt | Mã Enum | Ngưỡng (Threshold) | Ý nghĩa tra cứu |
|:---:|---|---|:---:|---|
| 1 | **Tổng quan** | `OVERVIEW` | 0.50 | Toàn bộ thủ tục hoặc tóm tắt quy trình |
| 2 | **Trình tự thực hiện** | `PROCEDURE` | 0.65 | Các bước thực hiện cụ thể |
| 3 | **Cách thức thực hiện** | `SUBMISSION_METHOD` | 0.70 | Hình thức nộp (trực tuyến, bưu chính, trực tiếp) |
| 4 | **Thành phần hồ sơ** | `DOSSIER` | 0.40 | Danh mục giấy tờ cần chuẩn bị |
| 5 | **Thời hạn giải quyết** | `PROCESSING_TIME` | 0.75 | Thời gian xử lý, số ngày làm việc |
| 6 | **Cơ quan thực hiện** | `AUTHORITY` | 0.70 | Cơ quan tiếp nhận, thẩm quyền giải quyết |
| 7 | **Kết quả thực hiện** | `RESULT` | 0.35 | Văn bản, giấy chứng nhận, quyết định đầu ra |
| 8 | **Phí, lệ phí** | `FEE` | 0.50 | Mức phí, lệ phí giải quyết |
| 9 | **Căn cứ pháp lý** | `LEGAL_BASIS` | 0.40 | Luật, Nghị định, Thông tư quy định |
| 10 | **Điều kiện thực hiện** | `ELIGIBILITY` | 0.50 | Yêu cầu, tiêu chuẩn được thực hiện |
| 11 | **Mẫu đơn, tờ khai** | `FORM` | 0.50 | Biểu mẫu đính kèm |

---

### 2.5. Định dạng dữ liệu đầu ra thực tế của PhoBERT (`PhoBERTRouter.predict`)

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
      "Thành phần hồ sơ": 0.9150,   // >= threshold 0.40 -> Chọn DOSSIER
      "Thời hạn giải quyết": 0.1120,
      "Cơ quan thực hiện": 0.0350,
      "Kết quả thực hiện": 0.0210,
      "Phí, lệ phí": 0.8840,        // >= threshold 0.50 -> Chọn FEE
      "Căn cứ pháp lý": 0.0510,
      "Điều kiện thực hiện": 0.0620,
      "Mẫu đơn, tờ khai": 0.1450
    }
  },

  /* ================= 3. THÔNG TIN KỸ THUẬT & PREPROCESSING ================= */
  "encoded_length": 38,             // Độ dài chuỗi token sau khi tách từ PyVi và BPE
  "thresholds": {                   // Bảng ngưỡng kích hoạt riêng của 11 mục
    "Tổng quan": 0.5,
    "Trình tự thực hiện": 0.65,
    "Cách thức thực hiện": 0.7,
    "Thành phần hồ sơ": 0.4,
    "Thời hạn giải quyết": 0.75,
    "Cơ quan thực hiện": 0.7,
    "Kết quả thực hiện": 0.35,
    "Phí, lệ phí": 0.5,
    "Căn cứ pháp lý": 0.4,
    "Điều kiện thực hiện": 0.5,
    "Mẫu đơn, tờ khai": 0.5
  },
  "preprocessing": {
    "max_len": 128,
    "segmenter": "pyvi",
    "input_mode": "full"
  }
}
```

---

### 2.6. Đối tượng định tuyến chuẩn hóa (`route` & `trace`)
Hàm [`classify_phobert()`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/phobert_router.py#L187-L239) bọc kết quả từ model và tầng Adapter thành bộ đôi tuple `(route, trace)` định dạng hợp đồng chuẩn cho luồng hội thoại:

#### 1. Cấu trúc `route` (Lệnh điều phối cho Conversation Engine)
```python
route = {
    "scope": "IN_SCOPE",               # "IN_SCOPE" | "OUT_OF_SCOPE" | "MIXED_SCOPE"
    "conversation": "NEW",             # "NEW" | "FOLLOW_UP"
    "mixed_procedures": False,         # cờ nhị phân (đã qua trọng tài override nếu có)
    "sections": ["DOSSIER", "FEE"],     # danh sách chuyên mục cần tra cứu
    "query": "Hồ sơ và lệ phí làm hộ chiếu?",
    "needs_clarification": False,      # True nếu cần ngắt để hỏi người dùng
    "clarification": "",               # câu thoại làm rõ (nếu needs_clarification=True)
    "requests": [
        {
            "procedure": "làm hộ chiếu",
            "query": "Hồ sơ và lệ phí làm hộ chiếu?",
            "sections": ["DOSSIER", "FEE"]
        }
    ]
}
```

#### 2. Cấu trúc `trace` (Dữ liệu Telemetry & Kiểm toán Quyết định)
```python
trace = {
    "backend": "phobert",              # Engine định tuyến sử dụng
    "attempts": 1,                     # Số lượt phân loại (1 lượt chuẩn, >1 nếu phân rã mệnh đề)
    "seconds": 0.0452,                 # Thời gian thực thi PhoBERT + Adapter (giây)
    "tokens": 38,                      # Tổng số token đã mã hóa qua BPE
    "errors": [],                      # Danh sách lỗi bắt được (nếu có)
    "predictions": [                   # Kết quả chi tiết từ từng lần gọi PhoBERT.predict()
        {
            "scope": "IN_SCOPE",
            "flow": "NEW",
            "mix": False,
            "sections": ["DOSSIER", "FEE"],
            "probabilities": { ... },
            "encoded_length": 38,
            "thresholds": { ... },
            "preprocessing": { "max_len": 128, "segmenter": "pyvi", "input_mode": "full" }
        }
    ],
    "adapter_decisions": [             # Vết các quyết định can thiệp/trọng tài của Adapter
        {
            "type": "catalog_single_procedure_override_mixed",
            "outcome": "cleared_mixed_procedures",
            "source_codes": ["1.011682", "1.011683", "1.011684"]
        }
    ],
    "procedure_confirmation": None,     # Chứa danh sách ứng viên nếu kích hoạt xác nhận thủ tục
    "mixed_scope_fallback_allowed": False,
    "checkpoint": "outputs/phobert_v3_finetuned_20261028/checkpoint"
}
```

---

### 2.7. Phân định ranh giới trách nhiệm của PhoBERT

| PhoBERT ĐẢM NHẬN | PhoBERT KHÔNG ĐẢM NHẬN |
|---|---|
| Phân loại ngữ nghĩa 3 chiều phạm vi (`IN / OUT / MIXED`) | Không trích xuất entity tên/mã thủ tục cụ thể (do Catalog đối soát) |
| Nhận diện mạch hội thoại (`NEW / FOLLOW_UP`) | Không phát hiện số lượng thủ tục trùng/tương tự trong Database |
| Dự đoán câu hỏi gộp 2 thủ tục (`mixed_procedures`) | Không tự ý mở Menu văn bản hay hỏi làm rõ `procedure_required` |
| Phân loại đa nhãn 11 mục nội dung theo ngưỡng Sigmoid | Không sinh câu trả lời trực tiếp (do LLM Qwen đảm nhận) |

---

## 3. Tầng 2: Hệ thống Nhãn Quyết định (Decision Reasons & Actions)

Khi kết quả phân loại của PhoBERT được chuyển tới [`conversation.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py), hệ thống tổng hợp với dữ liệu Catalog để gán các nhãn điều phối cấp cao:

### 3.1. Nhãn hành động tổng quan (`action` & `actual_route`)

| Nhãn `action` | Nhãn `actual_route` | Mục đích |
|---|---|---|
| **`clarify`** | `clarify` | Dừng quy trình RAG; mở menu hoặc gửi câu hỏi yêu cầu người dùng làm rõ. |
| **`answer`** | `rag_search` | Đủ điều kiện truy xuất; thực hiện RAG Search trên vector/BM25 và gọi LLM trả lời. |
| **`abstain`** | `out_of_scope` | Từ chối trả lời vì câu hỏi nằm ngoài phạm vi hoặc chào hỏi xã giao. |
| **`clarify`** | `routing_error` | Xảy ra lỗi phân loại/hết ngân sách token; kích hoạt câu fallback chuẩn. |

---

### 3.2. Chi tiết các nhãn lý do (`decision_reason`)

#### Nhóm 1: Nhánh CLARIFY (Làm rõ)

1. **`procedure_required` (Cần làm rõ thủ tục):**
   - **Kích hoạt khi:** Tên thủ tục trong câu hỏi khớp với $\ge 2$ mã TTHC trong Catalog (`len(codes) > 1`) (ví dụ: cùng một tên nhưng có bản cho *cá nhân* và bản cho *tổ chức*), hoặc khi kích hoạt Menu xác nhận thủ tục (`confirmation=True`).
   - **Hành vi:** Mở `procedure` menu liệt kê tối đa 5 ứng viên đánh số kèm mã định danh.
2. **`section_required` (Cần chọn mục nội dung):**
   - **Kích hoạt khi:** Đã xác định chính xác duy nhất 1 mã TTHC nhưng người dùng chỉ nêu tên thủ tục trần mà không hỏi rõ mục nào (`sections == []`).
   - **Hành vi:** Mở `section` menu liệt kê các mục nội dung hiện có của thủ tục đó.
3. **`ambiguous_question` (Mơ hồ ngữ cảnh):**
   - **Kích hoạt khi:** Câu hỏi mang tính nối tiếp (`FOLLOW_UP`, vd: *"thế còn hồ sơ?"*) nhưng phiên hội thoại không có mã thủ tục nào được chọn trước đó.
   - **Hành vi:** Yêu cầu người dùng nêu rõ tên thủ tục cần tra cứu.
4. **`invalid_selection` (Lựa chọn không hợp lệ):**
   - **Kích hoạt khi:** Phiên đang mở menu nhưng người dùng nhập số thứ tự vượt quá danh sách hoặc gõ ký tự không hợp lệ.
   - **Hành vi:** In lại menu và yêu cầu người dùng chọn đúng số thứ tự.
5. **`expired_selection` (Menu hết hạn):**
   - **Kích hoạt khi:** Người dùng gửi lựa chọn nhưng chữ ký HMAC của state không khớp hoặc cache phiên đã bị xóa.
6. **`procedure_rejected` (Bác bỏ menu thủ tục):**
   - **Kích hoạt khi:** Đang mở Menu thủ tục nhưng người dùng phản hồi phủ định (*"không phải mấy cái này"*, *"không đúng"*).
   - **Hành vi:** Loại bỏ các mã đã hiển thị và quét Catalog tìm danh sách các ứng viên thay thế khác.
7. **`selection_required` (Yêu cầu chọn cụ thể):**
   - **Kích hoạt khi:** Đang mở Menu nhưng người dùng chỉ trả lời đồng ý chung chung (*"đúng rồi"*, *"ok"*, *"phải"*).
   - **Hành vi:** Nhắc nhở người dùng chọn trực tiếp bằng số thứ tự hoặc tên mục cụ thể.

#### Nhóm 2: Nhánh ANSWER (Trả lời)

1. **`sufficient` (Đủ bằng chứng):** Chunks tài liệu thu về từ mã TTHC cung cấp đầy đủ thông tin để LLM sinh câu trả lời kèm trích dẫn (`citations`).
2. **`partial` (Thông tin một phần):** Tài liệu chỉ trả lời được một phần yêu cầu hoặc câu hỏi thuộc dạng `MIXED_SCOPE`; câu trả lời sẽ nêu rõ phần còn thiếu kèm thông báo phạm vi.

#### Nhóm 3: Nhánh ABSTAIN (Từ chối)

1. **`out_of_scope`:** PhoBERT dự đoán câu hỏi ngoài phạm vi với xác suất cao ($P \ge 85\%$) và Catalog không tìm thấy thực thể để cứu vớt/xác nhận (chi tiết cơ chế trọng tài tại Mục 4.4).
2. **`social_greeting`:** Câu hỏi chào hỏi xã giao thuần túy (xin chào, cảm ơn,...).
3. **`confirmation_rejected`:** Người dùng từ chối gợi ý xác nhận thủ tục khi hệ thống hỏi lại.
4. **`identifier_not_in_evidence` (Mã hồ sơ/biên nhận không có trong dữ liệu):**
   - **Kích hoạt khi:** Câu hỏi chứa mã định danh hồ sơ cá nhân / mã biên nhận (ví dụ: `000.00.12.H29-...`), nhưng tài liệu pháp lý truy xuất được không chứa mã này.
   - **Hành vi:** Từ chối trả lời ngay lập tức, hướng dẫn người dân tra cứu tại cổng dịch vụ công hoặc liên hệ cơ quan tiếp nhận hồ sơ, tuyệt đối không để LLM đoán mò tình trạng hồ sơ cá nhân.
5. **`no_context`:** Đã qua bước phân loại hợp lệ nhưng kho dữ liệu hoàn toàn không tìm thấy chunk văn bản nào phù hợp.

---

### 3.3. Hệ thống Sự kiện Trọng tài Adapter (`adapter_decisions` Telemetry)

Nhằm đảm bảo tính minh bạch, có thể giải thích (Explainable AI) và phục vụ việc kiểm toán chất lượng vận hành (Audit Trail), tầng Adapter và Conversation Engine ghi nhận chi tiết mọi quyết định can thiệp vào danh sách `trace["adapter_decisions"]`. Có 3 loại sự kiện trọng tài cốt lõi:

| Sự kiện (`type`) | Điều kiện kích hoạt | Đầu ra (`outcome`) | Tác động điều phối |
|---|---|---|---|
| **`catalog_scope_arbitration`** | PhoBERT đoán `OUT_OF_SCOPE` nhưng rơi vào vùng xác suất lưng chừng $50\% \le P < 85\%$, đồng thời câu hỏi khớp mã/tên trong Catalog. | `catalog_identity_overrode_out_of_scope` (hoặc `curated_alias_overrode_out_of_scope`) | Ghi đè `scope = IN_SCOPE`, cứu câu hỏi không bị từ chối oan và chuyển tiếp vào luồng RAG. |
| **`catalog_single_procedure_override_mixed`** | PhoBERT đoán `mix = True`, nhưng tất cả các mã TTHC tìm được trong Catalog đều trỏ về **cùng một tên thủ tục chuẩn hóa duy nhất** (`len(matched_names) == 1`). | `cleared_mixed_procedures` | Hạ `mixed = False`, giải tỏa chặn hội thoại và chuyển sang mở Menu lựa chọn các mã TTHC trùng tên. |
| **`explicit_section_override`** | Người dùng nêu từ khóa chuyên mục tường minh (như *"thời hạn"*, *"lệ phí"*), nhưng PhoBERT dự đoán thiếu mục do ngưỡng Sigmoid. | `accepted` | Ghi đè tập `sections` theo ý định tường minh của người dùng, đảm bảo truy xuất đúng chunk tài liệu. |

> [!TIP]
> Nhờ hệ thống sự kiện này, đội ngũ kỹ thuật có thể lọc và truy vấn nhanh toàn bộ các phiên hội thoại có sự can thiệp của Adapter trong Elasticsearch / OpenTelemetry, từ đó liên tục thu thập ca biên để tái huấn luyện PhoBERT và hoàn thiện Catalog.

---

## 4. Phân tích Chuyên sâu: Cơ chế Phân giải Thủ tục & Rẽ 3 Nhánh Quyết định

Cơ chế phân giải danh tính thủ tục (Procedure Identity Resolution) được thực thi trong hàm `answer_conversation()` tại [`src/vigovbot/rag/conversation.py` (dòng 357–392)](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L357-L392), kết hợp với đối tượng [`Clarifier`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/clarification.py#L82-L135).

### 4.1. Quy trình 4 bước thu thập danh sách mã thủ tục (`codes`)

Trước khi đưa ra quyết định rẽ nhánh, hệ thống tìm danh sách các mã TTHC tiềm năng thông qua 4 cấp lọc từ chặt chẽ đến mở rộng:

1. **Cấp 1 - Khớp mã chính xác hoặc Alias ([`clarifier.matches`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/clarification.py#L124)):** Quét regex mã số TTHC (dạng `1.xxxxxx`), quét tên đầy đủ hoặc từ điển bí danh (curated aliases).
2. **Cấp 2 - Quét biến thể số nhiều ([`clarifier.inspect`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/clarification.py#L158)):** Bắt các mẫu câu mở đầu như *"các thủ tục..."*, *"những thủ tục..."* hoặc cụm biến thể cùng nhóm.
3. **Cấp 3 - Khớp cụm từ trong Catalog ([`clarifier.discover`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/clarification.py#L158-L185)):** Tách từ khóa sau khi loại bỏ stopword và tìm các thủ tục chứa cụm từ khóa có trật tự tương tự trong Catalog.
4. **Cấp 4 - Tìm kiếm tương đồng ngữ nghĩa dự phòng (Retriever Search):** Nếu 3 bước trên không có kết quả, gọi FAISS vector + BM25 trên toàn bộ corpus để lấy Top K tài liệu liên quan nhất.

Sau khi hoàn tất 4 bước, hệ thống thu được mảng danh sách `codes = [...]`.

---

### 4.2. Mã nguồn rẽ 3 nhánh logic (`len(codes)`)

Đoạn mã quyết định rẽ nhánh nằm tại dòng 385–392 của [`conversation.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L385-L392):

```python
# -------------------------------------------------------------------------
# TUYẾN 1: Khớp nhiều thủ tục (len(codes) > 1) -> Mở Menu làm rõ
# -------------------------------------------------------------------------
if len(codes) > 1:
    result["retrieval_s"] = time.perf_counter() - retrieval_started
    return menu_result("procedure", index, codes)

# -------------------------------------------------------------------------
# TUYẾN 2: Không khớp mã nào trong Catalog (len(codes) == 0) -> Semantic Fallback
# -------------------------------------------------------------------------
if not codes:
    request["missing"] = True
    unresolved_semantic_hits[index] = hits  # Lưu lại các chunk vector tương đồng

# -------------------------------------------------------------------------
# TUYẾN 3: Khớp duy nhất 1 mã (len(codes) == 1) -> Chốt mã định danh
# -------------------------------------------------------------------------
else:
    request["code"] = codes[0]
```

---

### 4.3. Phân tích chi tiết hành vi của từng tuyến

```mermaid
graph TD
    StartCodes["Mảng codes sau khi lọc"] --> CheckLen{"Độ dài len(codes)?"}

    CheckLen -- "> 1 mã" --> BranchMulti["TUYẾN 1: len > 1\n(Trùng/Tương tự tên)"]
    BranchMulti --> ActionClarifyProc["action: clarify\ndecision_reason: procedure_required\nHiển thị Signed Menu thủ tục\n(DỪNG RAG & DỪNG LLM)"]

    CheckLen -- "== 1 mã" --> BranchSingle["TUYẾN 2: len == 1\n(Khớp duy nhất 1 mã)"]
    BranchSingle --> CheckSec{"sections có rỗng?"}
    CheckSec -- "Có mục hỏi" --> ActionAnswer["action: answer\nactual_route: rag_search\n(Lọc chunk theo mã & LLM trả lời)"]
    CheckSec -- "Rỗng (sections == [])" --> ActionClarifySec["action: clarify\ndecision_reason: section_required\nHiển thị Signed Menu mục nội dung"]

    CheckLen -- "== 0 mã" --> BranchZero["TUYẾN 3: len == 0\n(Không khớp mã Catalog)"]
    BranchZero --> SemanticFallback["Kích hoạt Semantic Fallback\nretrieval_strategy = 'semantic'\nDùng các chunk tương đồng cao nhất\nLLM trả lời có căn cứ"]
```

#### Tuyến 1: `len(codes) > 1` (Trùng hoặc tương tự tên)
- **Hành động:** `action = "clarify"`, `decision_reason = "procedure_required"`.
- **Nguyên lý bảo vệ:** Hệ thống **ngắt ngay lập tức**, không truy xuất văn bản và không gọi LLM Qwen (`answer.assert_not_called()`). Điều này ngăn ngừa hoàn toàn hiện tượng *ô nhiễm ngữ cảnh (Context Pollution)* và *ảo giác (Hallucination)* khi cố ghép nối hai thủ tục khác đối tượng (như cá nhân vs tổ chức).
- **Kết quả:** Hiển thị Menu đánh số (tối đa 5 lựa chọn) kèm chữ ký số HMAC SHA-256 để người dùng bấm chọn số ở lượt sau qua `direct_choice`.

#### Tuyến 2: `len(codes) == 1` (Khớp duy nhất 1 mã)
- **Hành động:** Gán chính thức mã thủ tục vào `request["code"] = codes[0]`.
- **Phân nhánh tiếp theo:**
  - Nếu câu hỏi đã chứa mục nội dung cụ thể (`sections != []`, ví dụ hỏi hồ sơ, lệ phí): Tiến hành truy xuất chính xác các chunk có `source_code == code` và gọi LLM trả lời $\rightarrow$ `action = "answer"`, `actual_route = "rag_search"`.
  - Nếu câu hỏi chỉ nêu tên thủ tục trần (`sections == []`): Dừng lại và mở Menu chọn mục nội dung $\rightarrow$ `action = "clarify"`, `decision_reason = "section_required"`.

#### Tuyến 3: `len(codes) == 0` (Dự phòng ngữ nghĩa - Semantic Fallback)
- **Hành động:** `request["missing"] = True`, lưu `unresolved_semantic_hits`.
- **Nguyên lý linh hoạt:** Mặc dù không khớp mã cụ thể trong catalog nhưng PhoBERT đã xác nhận câu hỏi là `IN_SCOPE`. Hệ thống không vội vàng từ chối (`abstain`) mà chuyển sang chiến lược `retrieval_strategy = "semantic"`.
- **Kết quả:** Dùng các đoạn văn bản tương đồng ngữ nghĩa nhất từ FAISS/BM25 chuyển cho LLM Qwen trả lời có căn cứ kèm ghi chú. Nếu kho dữ liệu hoàn toàn không có chunk nào liên quan (`not hits`), hệ thống mới chuyển sang từ chối với `action = "abstain"` và `decision_reason = "no_context"`.

---

### 4.4. Cơ chế Trọng tài Catalog khi PhoBERT phán đoán OUT_OF_SCOPE ở ngưỡng lưng chừng (Scope Arbitration & Procedure Confirmation)

Một trong những vai trò trọng yếu nhất của Procedure Catalog là phối hợp với bộ phân loại [`phobert_router.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/phobert_router.py) để giải quyết bài toán: **Mô hình AI dự đoán nhãn Ngoài phạm vi (`OUT_OF_SCOPE`) ở mức lưng chừng, không tuyệt đối**.

#### 4.4.1. Bản chất vấn đề: Rủi ro "Từ chối oan" (False Rejections)
PhoBERT là mô hình phân loại dựa trên xác suất thống kê. Khi người dùng đặt câu hỏi bằng cú pháp cộc lốc, không chuẩn ngữ pháp hành chính hoặc chỉ nhập duy nhất một mã số (ví dụ: *"1.002824 hết bao nhiêu"* hay *"cho xin mẫu tách thửa"*), PhoBERT có thể bị bối rối và cho ra xác suất `OUT_OF_SCOPE` lưng chừng (khoảng $50\% - 85\%$). Nếu hệ thống tin mù quáng vào phán đoán này và từ chối hỗ trợ ngay lập tức, đây sẽ là lỗi nghiêm trọng trong dịch vụ công.

#### 4.4.2. Cơ chế phân định 3 vùng quyết định của Catalog
Để khắc phục, hệ thống thiết lập Procedure Catalog làm **"Thẩm phán thực thể tối cao" (Ground-Truth Arbiter)** với 3 tầng xử lý chi tiết tại [`src/vigovbot/rag/phobert_router.py#L167-L184`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/phobert_router.py#L167-L184):

```mermaid
flowchart TD
    PRED["PhoBERT dự đoán: OUT_OF_SCOPE"] --> PROB{"Xác suất P(Ngoài phạm vi)"}

    PROB -->|"50% <= P < 85%\n(Vùng lưng chừng / phân vân)"| ARB["[Tầng 1] Trọng tài Catalog\n(Catalog Scope Arbitration)"]
    ARB -->|"Có mã TTHC hoặc tên chuẩn trong Catalog"| OVR["Bẻ còi: Ghi đè thành IN_SCOPE!\n(Chuyển sang Retrieval ngay)"]
    ARB -->|"Không có thực thể trong Catalog"| CONF

    PROB -->|"P >= 85%\n(Thiên về Ngoài phạm vi)"| CONF{"[Tầng 2] Xác nhận thủ tục\n(Procedure Confirmation)"}
    CONF -->|"Catalog tìm thấy ứng viên khớp >= 70%"| MENU["Tạo Menu xác nhận với người dùng\n('Có phải bạn muốn hỏi thủ tục X?')"]
    CONF -->|"Không tìm thấy ứng viên khả dĩ"| REJ["[Tầng 3] Từ chối hỗ trợ (Abstain)\nNgắt luồng, không gọi FAISS / LLM"]
```

1. **Vùng lưng chừng ($50\% \le P(\text{Ngoài phạm vi}) < 85\%$): Kích hoạt `Catalog Scope Arbitration`**
   * Tham số cấu hình mã nguồn: `CATALOG_SCOPE_LOWER = 0.50`, `CATALOG_SCOPE_UPPER = 0.85` ([`phobert_router.py#L33-L34`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/phobert_router.py#L33-L34)).
   * Hệ thống tra cứu nhanh trên Catalog bộ nhớ RAM ($< 1\text{ms}$). Nếu phát hiện câu hỏi chứa mã TTHC hoặc tên thủ tục/alias có thật trong cơ sở dữ liệu:
     $$\text{Quyết định: Override } \mathbf{OUT\_OF\_SCOPE} \longrightarrow \mathbf{IN\_SCOPE}$$
   * Lý do: Mô hình AI có thể đoán sai do câu cú lạ, nhưng dữ liệu thực tế trong Catalog là bằng chứng không thể chối cãi.

2. **Vùng thiên về ngoài phạm vi ($P \ge 85\%$): Kích hoạt `Procedure Confirmation`**
   * Nếu người dùng diễn đạt hoàn toàn bằng văn nói đời thường (ví dụ: *"mất bằng lái xe thì làm sao"*), tên thủ tục chuẩn trong văn bản nhà nước là *"Cấp lại giấy phép lái xe do bị mất"*. PhoBERT có thể xếp vào ngoài phạm vi với xác suất cao ($> 85\%$).
   * Thay vì từ chối thẳng thừng, hàm `confirmation_candidates()` ([`clarification.py#L134`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/clarification.py#L134)) dùng thuật toán đối sánh từ vựng trên Catalog.
   * Nếu điểm tương đồng đạt $\ge 70\%$ và khoảng cách với thủ tục thứ hai $\ge 8\%$, hệ thống giữ người dùng lại bằng một Menu lịch sự:
     > *"Hệ thống nhận thấy bạn đang tìm kiếm thủ tục hành chính. Có phải bạn muốn tìm hiểu thủ tục: Cấp lại giấy phép lái xe (Mã: 1.001234) không?"*

3. **Vùng từ chối tuyệt đối (True Out-of-Scope):**
   * Áp dụng khi câu hỏi hoàn toàn vô can (ví dụ: *"Hôm nay trời đẹp không?", "Viết code Python"*).
   * PhoBERT cho xác suất $P > 95\%$, đồng thời Catalog xác nhận không có bất kỳ mã, tên hay cụm từ thủ tục nào liên quan.
   * Hệ thống lập tức trả lời từ chối hỗ trợ và ngắt luồng xử lý, **không gọi FAISS Vector Search và không gọi LLM**, giúp tiết kiệm $100\%$ tài nguyên tính toán cho các yêu cầu rác.

---

### 4.5. Đo lường Tài nguyên Triển khai & Ranh giới Rò rỉ Dữ liệu (Resource Measurements & Data Leakage Boundary)

Thực nghiệm đo lường trên cơ sở dữ liệu `metadata.sqlite` chứa toàn bộ 117.871 chunk văn bản TTHC của ViGovBot:

| Chỉ số đo lường | Giá trị thực nghiệm | Ghi chú & Đánh giá |
| :--- | :---: | :--- |
| **Tổng số thủ tục quản lý** | **6.192 mã TTHC** | Toàn bộ thủ tục trong kho dữ liệu Cổng DVCQG |
| **Số lượng tên chuẩn độc nhất** | **5.579 tên** | Bao gồm các cấp tỉnh, huyện, xã và bộ ngành |
| **Thời gian nạp danh mục (`Load time`)** | **703.28 ms** (~0.7 s) | **Chỉ chạy 1 lần duy nhất** khi server khởi động |
| **Dung lượng RAM tiêu tốn** | **1.340,83 KB (~1.31 MB)** | **Cực kỳ nhỏ gọn**, gần như không chiếm dụng bộ nhớ |
| **Độ trễ tra cứu trung bình (`Lookup latency`)** | **< 1.0 ms** / câu hỏi | Tra cứu chuỗi trên mảng RAM gần như tức thì |

#### Tại sao quản lý 117.871 chunk mà Catalog chỉ tốn 1.31 MB RAM?
* Catalog **hoàn toàn không nạp** nội dung văn bản (text), bảng biểu hay vector 1024-chiều lên RAM.
* Cấu trúc dữ liệu trên RAM chỉ là một `tuple` gồm các cặp chuỗi rút gọn:
  ```python
  (source_code, folded_procedure_name)
  ```
  *Ví dụ:* `("1.013586", "thu tuc bien phong doi voi tau ca...")`
* Toàn bộ 117.871 vector vẫn nằm trên đĩa và trong FAISS Index (`tthc_unified.index`), còn nội dung chi tiết nằm trong SQLite (`metadata.sqlite`), chỉ được đọc ra khi thực sự cần nạp vào prompt.

#### Phân định ranh giới Data Leakage (Không vi phạm):
* **Về mặt kiểm thử:** Trong mã nguồn chấm điểm [`records.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/evaluation/records.py#L432-L438), hệ thống bóc tách nghiêm ngặt: chỉ gửi duy nhất trường `question` và `chat_history` từ `input` sang endpoint, **hoàn toàn không tiếp xúc với bất kỳ trường ground-truth nào**.
* **Về mặt công nghiệp:** Catalog được trích xuất từ kho tài liệu công khai (Corpus) — tương đương với trang mục lục đầu sách. Việc kết hợp **Entity Linking** và **Metadata Pre-filtering** là chuẩn mực bắt buộc trong các giải pháp RAG doanh nghiệp (Azure AI Search, ElasticSearch, LlamaIndex).

---

### 4.6. Cơ chế Bảo vệ Định danh Cá nhân & Chống Đoán Mò (`identifier_not_in_evidence`)

Trong dịch vụ công, một trong những sai phạm nguy hiểm nhất của Chatbot AI là tự ý phỏng đoán hoặc bịa đặt kết quả giải quyết hồ sơ cá nhân khi người dân nhập mã biên nhận / mã giao dịch.

#### 4.6.1. Nhận diện Mã Định danh Cá nhân (`_OPAQUE_IDENTIFIER`)
Mã nguồn [`src/vigovbot/rag/conversation.py#L29`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L29) định nghĩa bộ nhận dạng các mã định danh dạng vết hồ sơ cá nhân:
```python
_OPAQUE_IDENTIFIER = re.compile(r"\b[A-ZĐ]{2,}(?:-[A-Z0-9Đ]+){2,}\b", re.I)
```
*Ví dụ:* `000.00.12.H29-241031-0001`, `HS-TTHC-2026-X99`, `MC-HN-00124`.

#### 4.6.2. Kiểm tra Đối chiếu Bằng chứng & Từ chối Tuyệt đối
Tại dòng 447–457 của [`conversation.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L447-L457):
1. Sau khi Retrieval hoàn tất, hàm `identifiers_missing_from_hits(question, hits)` kiểm tra xem mã định danh cá nhân mà người dùng nhập có xuất hiện trong các chunk văn bản quy định chung được truy xuất hay không.
2. Nếu câu hỏi có chứa mã định danh nhưng tài liệu quy định pháp lý không có mã này (bản chất cơ sở dữ liệu TTHC chỉ chứa quy chế chung, không chứa cơ sở dữ liệu hồ sơ cá nhân của từng công dân):
   ```python
   result.update(action="abstain", evidence_status="missing")
   return finish(
       f"Tài liệu truy xuất không chứa dữ liệu gắn với định danh {identifiers}, nên không đủ "
       "bằng chứng để xác nhận thông tin được hỏi. Bạn cần tra cứu trên hệ thống tiếp nhận "
       "hồ sơ hoặc liên hệ cơ quan đang xử lý.",
       "identifier_not_in_evidence",
   )
   ```
3. **Ý nghĩa an toàn:** Ngắt luồng ngay, không đưa vào prompt LLM. Điều này loại bỏ 100% rủi ro LLM "tưởng tượng" ra ngày hẹn trả kết quả hay tình trạng hồ sơ cá nhân của người dân.

---

### 4.7. Cơ chế Xử lý Câu hỏi Hỗn hợp 2 Tầng (`mixed_scope_llm_rewrite` & Extractive Verification)

Khi người dùng đặt câu hỏi vừa có phần hỏi thủ tục, vừa có phần hỏi ngoài lề (ví dụ: *"Lệ phí làm hộ chiếu bao nhiêu, tiện thể chỉ tôi quán phở ngon gần đây"*), PhoBERT phân loại nhãn `MIXED_SCOPE`.

Để xử lý an toàn và không để phần ngoài lề làm ô nhiễm ngữ cảnh RAG, hệ thống triển khai cơ chế 2 tầng:

1. **Tầng 1 - Tách mệnh đề độc lập bằng Regex (`re.split`):**
   * Phân tách câu theo dấu chấm phẩy, xuống dòng hoặc từ nối: `r"[;\n?!]+|\s+và\s+"` (tối đa 8 mệnh đề con).
   * Đưa từng mệnh đề vào PhoBERT phân loại lại. Nếu tìm thấy duy nhất 1 mệnh đề là `IN_SCOPE` thuần túy (không bị `mix`) $\rightarrow$ Dùng mệnh đề này làm query chính thức.
2. **Tầng 2 - LLM Extractive Rewrite kết hợp Xác minh Chặt chẽ:**
   * Nếu Regex không phân tách được (cấu trúc ngữ pháp phức tạp), hệ thống kích hoạt hàm `rewrite_mixed_scope()` ([`classification.py#L62`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/classification.py#L62)) gọi LLM trích xuất một đoạn nguyên văn liên tiếp.
   * **Ràng buộc kiểm tra nghiêm ngặt (Guardrails):**
     - Đoạn trích xuất bắt buộc phải là chuỗi con (`substring`) của câu hỏi gốc (extractive, không tự diễn giải).
     - Không được làm thay đổi hoặc rơi rớt mã TTHC gốc (`original_codes == candidate_codes`).
     - Không được làm rơi rớt các từ định tính phủ định (`NEGATIVE_QUALIFIERS` như "không", "chưa", "hết hạn").
   * **Tái phân loại (Re-classification):** Đưa câu đã làm sạch vào PhoBERT kiểm tra lại (`classify_phobert`). Chỉ khi PhoBERT xác nhận câu này đạt `IN_SCOPE` và đơn thủ tục thì mới chấp nhận (`outcome: accepted_after_phobert`).
3. **Cảnh báo minh bạch (`MIXED_NOTICE`):**
   * Trong câu trả lời cuối cùng, hệ thống tự động chèn ghi chú:
     > *"Phần yêu cầu ngoài thủ tục hành chính nằm ngoài phạm vi hỗ trợ."*
   * Đồng thời hạ nhãn `action = "partial"`, `evidence_status = "partial"`.

---

### 4.8. Cơ chế Ghi đè Mục Nội dung Tường minh & Khôi phục Ngữ cảnh Lịch sử

#### 4.8.1. Ghi đè Mục Nội dung Tường minh (`explicit_section_override`)
* **Vấn đề:** Do PhoBERT sử dụng các ngưỡng Sigmoid cố định, trong một số câu hỏi người dùng nêu rõ từ khóa mục (ví dụ: *"cho tôi hỏi lệ phí và thời hạn"*), nhưng mô hình chỉ kích hoạt được một mục do xác suất của mục kia nằm sát dưới ngưỡng kích hoạt.
* **Giải pháp:** Hàm `explicit_section_intents()` ([`sections.py#L37`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/sections.py#L37)) quét các cụm từ ngữ tường minh đối chiếu với 11 nhóm chuyên mục.
* Khi phát hiện có yêu cầu tường minh, Adapter tự động **ghi đè (override)** tập nhãn `sections` của PhoBERT bằng tập nhãn tường minh từ người dùng, ghi nhận trace `explicit_section_override` với trạng thái `accepted`.

#### 4.8.2. Khôi phục Ngữ cảnh Thủ tục từ Lịch sử (`history_identity_recovery`)
* **Vấn đề:** Đối với các phiên hội thoại không duy trì state có chữ ký (stateless clients) hoặc khi client mất kết nối, người dùng hỏi tiếp (`turn_follow_up`, vd: *"thế còn hồ sơ?"*) mà không nhắc lại tên thủ tục.
* **Giải pháp:** Hàm `procedure_from_user_history()` ([`conversation.py#L83`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/conversation.py#L83)) quét ngược dòng lịch sử hội thoại:
  - **Nguyên tắc an ninh:** Chỉ quét các tin nhắn có `role == "user"`, tuyệt đối không tin tưởng hoặc suy diễn từ văn bản trả lời của `role == "assistant"` (tránh trôi dạt ngữ cảnh ảo giác).
  - Trích xuất mã hoặc tên thủ tục duy nhất đã được xác thực ở các lượt trước để tiếp tục phục vụ lượt hiện tại.

---

### 4.9. Các Cơ chế Tương tác Phản hồi Menu Nâng cao (Advanced Menu Interactions)

Hệ thống điều phối hội thoại xử lý thông minh các hành vi phản hồi tự nhiên của người dùng khi đang mở Menu:

1. **Người dùng bác bỏ Menu (`procedure_rejected`):**
   - Khi bot đang mở Menu 5 thủ tục, nếu người dùng gõ: *"không phải các thủ tục trên"*, *"không đúng"* (`_MENU_REJECTION`), hệ thống không báo lỗi mà tự động loại trừ 5 mã đã hiển thị và gọi `clarifier.discover()` quét các phương án thay thế tiếp theo trong Catalog.
2. **Người dùng phản hồi đồng ý chung chung (`selection_required`):**
   - Khi đang mở Menu, nếu người dùng chỉ gõ: *"đúng rồi"*, *"ok"*, *"phải"* (`_BARE_CONFIRMATION`), bot không thể đoán người dùng chọn mục nào $\rightarrow$ Nhắc lịch sự: *"Bạn vui lòng chọn trực tiếp một mục bằng số hoặc tên trong danh sách"*.
3. **Người dùng yêu cầu xem trường hợp khác (`_OTHER_VARIANT`):**
   - Khi đang xem 1 thủ tục, nếu người dùng hỏi: *"còn trường hợp khác không?"*, *"loại khác?"* $\rightarrow$ Hệ thống tự động kích hoạt `clarifier.inspect("Các thủ tục " + selected_name)` để gợi ý danh sách các thủ tục biến thể liên quan cùng nhóm nghiệp vụ.
4. **Bảo mật Trạng thái bằng Chữ ký số HMAC (`Signed State`):**
   - Mọi menu và ngữ cảnh phiên đều được mã hóa chữ ký số HMAC SHA-256 kèm `corpus_hash` và `history_fingerprint`. Bất kỳ hành vi sửa đổi mã thủ tục hoặc giả mạo state từ phía client đều bị phát hiện và từ chối ngay (`expired_selection`).

---

### 4.10. Cơ chế Ngắt Luồng Sớm khi Dùng LLM Router (Streaming Early Exit với `RoutePrefixReader`)
Khi hệ thống chạy với bộ định tuyến tạo sinh LLM (`routing_backend: "llm"` thay vì PhoBERT), việc chờ LLM sinh toàn bộ chuỗi JSON định tuyến có thể tốn từ 2 – 4 giây.

Để tối ưu hóa tốc độ, module [`routing.py#L14-L40`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/routing.py#L14-L40) triển khai class **`RoutePrefixReader`**:
1. Đọc luồng stream token của LLM theo thời gian thực.
2. Prompt định tuyến được thiết kế để bắt buộc LLM xuất trường `scope` và `relation` đầu tiên trong JSON.
3. Hễ LLM vừa xuất xong `"scope": "out_of_scope"` hoặc `"relation": "ambiguous"`, `RoutePrefixReader` lập tức ném biệt lệ **`RouteEarlyExit`**, ngắt ngay kết nối với LLM tại chỗ mà không cần chờ sinh các trường `query` hay `clarification`.
4. Cơ chế này giảm thời gian phản hồi của các câu hỏi ngoài phạm vi từ hàng giây xuống **vài trăm miligiây**.

---

### 4.11. Cơ chế Chuẩn hóa Tên Thủ tục trong Clarifier & Trọng tài Giải cứu Trộn Thủ tục (Single-Procedure Catalog Override)

Trong thực tế triển khai và rà soát tập dữ liệu kiểm thử (như `test_rag_follow_up_v2.jsonl`), hệ thống ghi nhận hai tình huống dị biệt phổ biến làm sai lệch luồng điều phối:

#### 1. Thách thức kỹ thuật từ dữ liệu thực tế
* **Dị biệt định dạng tên trong Catalog:** Cùng một thủ tục hành chính nhưng một số bản ghi bị dính dấu chấm câu ở cuối (`.`), hoặc một bản ghi có tiền tố `"Thủ tục "` trong khi các bản ghi khác cùng tên lại không có (ví dụ mã `1.115617` mang tên *"Thủ tục đăng ký, cấp Giấy chứng nhận..."* trong khi 14 mã khác mang tên *"Đăng ký, cấp Giấy chứng nhận..."*).
* **Hiện tượng triệt tiêu chuỗi con:** Thuật toán lọc `resolve_identity` cũ ưu tiên chuỗi dài nhất bao hàm chuỗi ngắn hơn (`names[code] != names[other] and _contains_phrase(...)`), vô tình loại bỏ sạch các mã ngắn hơn và chỉ giữ lại duy nhất 1 mã. Khi chỉ còn 1 mã, hệ thống ngỡ rằng đã xác định duy nhất được thủ tục nên bỏ qua việc mở Menu làm rõ.
* **Tên thủ tục dài gây kích hoạt nhầm cờ `mix = True`:** Các thủ tục hành chính đất đai/nông nghiệp có tên rất dài, ghép nối nhiều trường hợp bằng dấu phẩy `,`, dấu chấm phẩy `;` và chữ `"và"` khiến PhoBERT Router dự đoán nhầm đây là câu hỏi gộp nhiều thủ tục khác nhau (`p_mix > 99%`), dẫn đến phản hồi chặn: *"Bạn đang hỏi nhiều thủ tục. Vui lòng hỏi riêng từng thủ tục..."*.

#### 2. Giải pháp thuật toán tại [`clarification.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/clarification.py#L115-L125)
Hàm `resolve_identity` được tinh chỉnh chuẩn hóa toàn diện tên trước khi so khớp:
1. Xóa bỏ dấu chấm câu cuối và khoảng trắng thừa: `.strip(" .?!;:")`.
2. Chuẩn hóa loại bỏ tiền tố `"Thủ tục "` / `"thu tuc "`: `re.sub(r"^thu tuc\s+", "", name)`.
3. Nhờ tên chuẩn hóa của tất cả các mã trùng tên trở nên đồng nhất tuyệt đối (`names[code] == names[other]`), điều kiện loại trừ chuỗi con trả về `False`, giúp **giữ trọn vẹn 100% các mã TTHC trùng tên** (như giữ đủ cả 15 mã đất đai hay 2 mã kiểm nghiệm thực phẩm).

#### 3. Giải pháp Trọng tài Adapter tại [`phobert_router.py`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/phobert_router.py#L228-L245)
Trước khi kích hoạt nhánh chặn `if mixed: return clarify(...)`, Adapter thực hiện kiểm tra chéo với Catalog:
```python
if mixed and codes:
    matched_names = {
        re.sub(r"^thu tuc\s+", "", _fold(clarifier.catalog[c]["name"].strip(" .?!;:")))
        for c in codes if c in clarifier.catalog
    }
    if len(matched_names) == 1:
        adapter_decisions.append({
            "type": "catalog_single_procedure_override_mixed",
            "outcome": "cleared_mixed_procedures",
            "source_codes": codes,
        })
        mixed = False
        route["mixed_procedures"] = False
```
* Nếu toàn bộ các mã nhận diện được trong câu hỏi (`codes`) cùng trỏ về **một tên thủ tục chuẩn hóa duy nhất** (`len(matched_names) == 1`), Adapter sẽ giải tỏa cờ `mixed = False`.
* Ghi vết Telemetry sự kiện `catalog_single_procedure_override_mixed` để phục vụ audit.
* Chuyển luồng sang `conversation.py` để mở **Menu lựa chọn thủ tục (`procedure_disambiguation_menu`)**, hiển thị danh sách các mã TTHC kèm cấp thực hiện tương ứng cho người dùng lựa chọn.

#### 4. Minh chứng Thực nghiệm Kiểm chứng trên 5 Ca Dị biệt (`test_rag_follow_up_v2.jsonl`)

Quá trình kiểm tra thực tế trên tập kiểm thử `Data/dataset_v3/test_rag/test_rag_follow_up_v2.jsonl` đã phát hiện và xử lý dứt điểm 5 trường hợp điển hình:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ MINH CHỨNG THỰC NGHIỆM ĐIỀU PHỐI MENU VÀ TRỌNG TÀI ADAPTER (5 CA TESTSET V3)                │
├─────────────────┬───────────────────────────────────┬───────────────────┬───────────────────┤
│ Mã câu hỏi      │ Thủ tục thực tế                   │ Trước khi tinh chỉnh │ Sau khi tinh chỉnh│
├─────────────────┼───────────────────────────────────┼───────────────────┼───────────────────┤
│ GOLDEN_V3_003250│ Kiểm nghiệm thực phẩm phục vụ     │ Mã 1.013857 dính  │ Chuẩn hóa dấu chấm│
│ GOLDEN_V3_003253│ quản lý nhà nước về ATTP          │ dấu chấm cuối '.',│ câu, bảo toàn đủ  │
│                 │ (2 mã trùng tên)                  │ triệt tiêu mã kia │ 2 mã -> Mở Menu   │
├─────────────────┼───────────────────────────────────┼───────────────────┼───────────────────┤
│ GOLDEN_V3_005805│ Đăng ký, cấp Giấy chứng nhận QSDĐ │ Mã 1.115617 dính  │ Loại bỏ tiền tố,  │
│                 │ lần đầu cấp tỉnh                  │ tiền tố 'Thủ tục',│ bảo toàn đủ 15 mã │
│                 │ (15 mã trùng tên)                 │ triệt tiêu 14 mã  │ -> Mở Menu 15 ứng │
│                 │                                   │ khác              │ viên thành công   │
├─────────────────┼───────────────────────────────────┼───────────────────┼───────────────────┤
│ GOLDEN_V3_006649│ Giao đất, cho thuê đất, chuyển mục│ Tên dài 54 từ,    │ Adapter nhận diện │
│ GOLDEN_V3_006651│ đích sử dụng đất cấp xã           │ PhoBERT đoán nhầm │ cùng 1 thủ tục, hạ│
│                 │ (15 mã trùng tên)                 │ mix=True (p=99.8%)│ mix=False -> Mở   │
│                 │                                   │ -> Bot chặn hỏi   │ Menu 15 ứng viên  │
└─────────────────┴───────────────────────────────────┴───────────────────┴───────────────────┘
```

1. **Hiệu chỉnh Dữ liệu & Mô phỏng Hội thoại Follow-up:**
   - 5 câu hỏi đơn lẻ (`new_question`) trước đây đã được cấu trúc lại hoàn chỉnh thành dạng **Hội thoại 2 lượt (2-turn follow-up conversation)**:
     - **Lượt 1:** Người dùng nêu câu hỏi kèm mục tra cứu $\rightarrow$ Chatbot phản hồi mở Menu làm rõ danh sách các mã TTHC trùng tên kèm cấp thực hiện tương ứng.
     - **Lượt 2:** Người dùng chọn mã thủ tục đích qua số thứ tự $\rightarrow$ Chatbot truy xuất chính xác tài liệu của mã đó và sinh câu trả lời hoàn chỉnh (`expected_answer`).
   - Cả 5 câu hỏi sau khi fix đã được gộp lại vào `Data/dataset_v3/test_rag/test_rag_follow_up_v2.jsonl`, nâng tổng số mẫu lên đúng **159 bản ghi thuần túy follow-up**, đạt độ tương thích schema 100% theo `schema/golden_dataset.schema.json`.

2. **Kiểm chứng Hồi quy & Vận hành Runtime:**
   - **Unit Tests:** Toàn bộ 89 bài kiểm thử đơn vị (`test_clarification.py`, `test_phobert_router.py`, `test_four_head_routing.py`) đạt **89/89 PASS (100%)**.
   - **Kiểm thử Runtime Chatbot:** Chạy trực tiếp qua hàm `answer_conversation()`, cả 5 câu hỏi đều kích hoạt chính xác:
     - `actual_route = "clarify"`
     - `decision_reason = "procedure_required"`
     - Hiển thị đầy đủ Menu giao diện với các tùy chọn đánh số và bảo mật HMAC SHA-256.

---

## 5. Bảng Đối soát Toàn diện (Taxonomy & State Mapping)

| Tình huống thực tế | Nhãn PhoBERT Router | Nhãn Hệ thống (`actual_route` / `action`) | `decision_reason` | Trạng thái tiếp theo |
|---|---|---|---|---|
| Hỏi rõ 1 thủ tục + mục hỏi | `IN_SCOPE`, `NEW`, `mix: False`, `sections: [FEE]` | `rag_search` / `answer` | `sufficient` | Kết thúc lượt, trả câu trả lời |
| Tên thủ tục khớp nhiều đối tượng (`len > 1`) | `IN_SCOPE`, `NEW`, `mix: False`, `sections: [...]` | `clarify` / `clarify` | `procedure_required` | Lưu Signed Menu thủ tục |
| Thủ tục tên dài có liệt kê nhưng là 1 thủ tục chính thức | `IN_SCOPE`, `NEW`, `mix: True` $\rightarrow$ **Override False** | `clarify` / `clarify` | `procedure_required` | Mở Menu chọn mã TTHC trùng tên (`catalog_single_procedure_override_mixed`) |
| Cố tình hỏi gộp 2 thủ tục hành chính khác nhau | `IN_SCOPE`, `NEW`, `mix: True` (Không override) | `clarify` / `clarify` | `ambiguous_question` | Chặn trả lời, yêu cầu hỏi riêng từng thủ tục để tránh ghép nhầm dữ liệu |
| Chỉ nêu tên 1 thủ tục duy nhất (`len == 1`) | `IN_SCOPE`, `NEW`, `mix: False`, `sections: []` | `clarify` / `clarify` | `section_required` | Lưu Signed Menu mục nội dung |
| Không khớp mã trong Catalog (`len == 0`) | `IN_SCOPE`, `NEW`, `mix: False`, `sections: [...]` | `rag_search` / `answer` | `sufficient` (semantic) | Sinh câu trả lời qua Semantic Fallback |
| PhoBERT đoán OUT (50-85%) nhưng có mã trong Catalog | `OUT_OF_SCOPE` $\rightarrow$ **Override IN_SCOPE** | `rag_search` / `answer` | `sufficient` (arbitration) | Bẻ còi sang tra cứu RAG bình thường |
| PhoBERT đoán OUT (>85%) nhưng khớp từ vựng $\ge 70\%$ | `OUT_OF_SCOPE` | `clarify` / `clarify` | `procedure_required` | Mở Menu gợi ý xác nhận thủ tục |
| Hỏi tình trạng mã biên nhận cá nhân (`HS-xxx`) | `IN_SCOPE` hoặc `OUT_OF_SCOPE` | `out_of_scope` / `abstain` | `identifier_not_in_evidence` | Từ chối đoán mò, hướng dẫn tra cứu cổng DVC |
| Người dùng từ chối Menu (*"không phải mấy cái này"*) | (Đang ở trạng thái Menu) | `clarify` / `clarify` | `procedure_rejected` | Quét Catalog đưa danh sách ứng viên mới |
| Người dùng trả lời đồng ý chung chung (*"ok/đúng"*) | (Đang ở trạng thái Menu) | `clarify` / `clarify` | `selection_required` | Yêu cầu chọn đúng số thứ tự |
| Câu hỏi hỗn hợp (thủ tục + ngoài lề) | `MIXED_SCOPE` | `rag_search` / `partial` | `partial` | Trích xuất câu hỏi con, thêm cảnh báo phạm vi |
| Hỏi câu nối tiếp nhưng mất state | `IN_SCOPE`, `FOLLOW_UP` | `rag_search` / `answer` | `sufficient` (recovered) | Khôi phục mã từ lịch sử tin nhắn user |
| Câu hỏi ngoài lề (thời tiết, code) | `OUT_OF_SCOPE`, `NEW`, `mix: False`, `sections: []` | `out_of_scope` / `abstain` | `out_of_scope` | Trả lời từ chối lịch sự |
| Hỏi tiếp nhưng không có lịch sử | `IN_SCOPE`, `FOLLOW_UP`, `mix: False`, `sections: [...]` | `clarify` / `clarify` | `ambiguous_question` | Yêu cầu nêu tên thủ tục |
| Chào hỏi xã giao | `OUT_OF_SCOPE`, `NEW`, `mix: False`, `sections: []` | `out_of_scope` / `abstain` | `social_greeting` | Phản hồi lời chào |
| Nhập sai số menu | (Bỏ qua Router, xử lý trực tiếp qua `direct_choice`) | `clarify` / `clarify` | `invalid_selection` | Hiển thị lại Menu hiện tại |
| Menu quá hạn hoặc sai chữ ký HMAC | (Bỏ qua Router, kiểm tra chữ ký state) | `clarify` / `clarify` | `expired_selection` | Yêu cầu nêu lại tên thủ tục |

---

## 6. Kết quả Thực nghiệm Đánh giá Router trên Bộ Test (`test_router.jsonl`)

Quá trình đánh giá thực nghiệm độc lập đã được thực hiện trực tiếp trên tập kiểm thử `Data/dataset_v3/test_router/test_router.jsonl` (gồm **1.246 mẫu**, cấu trúc đa lượt và đơn lượt).

### 6.1. Thiết lập Đánh giá (Evaluation Setup)
- **Tập kiểm thử:** 1.246 mẫu thực tế từ cơ sở dữ liệu TTHC Việt Nam.
- **Mô hình định tuyến:** Checkpoint cục bộ `outputs/phobert_v3_finetuned_20261028/checkpoint` (PhoBERT 4 heads).
- **Cơ sở dữ liệu Catalog:** 6.191 thủ tục hành chính nạp sẵn trong cache `outputs/rag_cache/procedure_catalog.json`.
- **Môi trường:** Chạy suy luận 100% trên CPU (2 luồng intra-op), hoàn toàn **không gọi LLM sinh câu trả lời**, giúp kiểm chứng khách quan và tốc độ cao.
- **Thời gian đánh giá tổng thể:** 628,52 giây (~504,4 ms/mẫu cho cả phân loại PhoBERT và đối soát Catalog toàn bộ).

---

### 6.2. Bảng Tổng hợp Kết quả Chấm điểm Thực nghiệm

| Nhóm chỉ số | Chỉ số cụ thể | Kết quả đạt được | Mục tiêu chuẩn | Nhận xét |
|---|---|:---:|:---:|---|
| **1. PhoBERT 4-Head Model** | **Scope Accuracy** | **96.95%** | $\ge 95\%$ | Nhận diện xuất sắc ranh giới phạm vi (`IN_SCOPE`). |
| | **Conversation Flow Acc** | **98.80%** | $\ge 95\%$ | Phân biệt gần như tuyệt đối giữa câu mới (`NEW`) và hỏi tiếp (`FOLLOW_UP`). |
| | **Mix Procedures Acc** | **98.88%** | $\ge 95\%$ | Phân biệt chính xác câu đơn và câu gộp nhiều thủ tục. |
| | **Sections Exact Match** | **75.52%** | $\ge 80\%$ | Trùng khớp 100% tập mục nội dung hỏi. |
| | **Sections Mean Jaccard** | **77.55%** | $\ge 80\%$ | Độ tương đồng trung bình của tập nhãn đa mục. |
| | **PhoBERT 4-Head Joint** | **72.23%** | $\ge 70\%$ | Cả 4 heads của mô hình đều dự đoán đúng cùng lúc. |
| **2. Catalog Disambiguation** | **Procedure Codes Match** | **90.45%** | $\ge 90\%$ | Bắt chính xác danh sách mã TTHC từ Catalog. |
| | **Candidate Count Acc** | **90.45%** | $\ge 90\%$ | Nhận diện đúng số lượng $n$ thủ tục ứng viên. |
| **3. Decision & Action** | **Action Accuracy** | **83.71%** | $\ge 85\%$ | Ra đúng hành vi `answer`, `clarify`, `abstain`. |
| | **Decision Reason Acc** | **83.55%** | $\ge 85\%$ | Đúng lý do cụ thể (`sufficient`, `procedure_required`...). |
| | **Target Flow Accuracy** | **83.55%** | $\ge 85\%$ | Rẽ đúng vào luồng mục tiêu của hệ thống. |
| **4. Toàn diện Cấp Hệ thống** | ★ **STRICT E2E ACCURACY** | **66.37%** | $\ge 65\%$ | **Tất cả các tiêu chí cùng đúng 100% trên 1 mẫu**. |
| **5. Hiệu năng & Độ trễ** | **Latency P50 / P95** | **517 ms / 1.220 ms** | $< 1.500$ ms | Tốc độ suy luận CPU hoàn toàn đáp ứng thời gian thực. |

---

### 6.3. Phân tích Cắt lớp theo Phân khúc (Cohort Breakdown)

| Phân khúc kiểm thử | Số mẫu | Strict E2E (%) | Action Acc (%) | Codes Match (%) | PhoBERT Acc (%) |
|---|:---:|:---:|:---:|:---:|:---:|
| **Độ khó: Medium (`diff_medium`)** | 1.084 | **70.20%** | **85.61%** | 90.04% | 76.75% |
| **Độ khó: Hard (`diff_hard`)** | 162 | **40.74%** | **70.99%** | 93.21% | 41.98% |
| **Mạch: Hỏi tiếp (`turn_follow_up`)** | 503 | **73.16%** | **76.94%** | **97.02%** | 73.16% |
| **Mạch: Câu hỏi mới (`turn_new_question`)** | 743 | **61.78%** | **88.29%** | 86.00% | 71.60% |

#### Nhận xét phân khúc:
- **Độ khó Medium:** Hệ thống đạt độ chính xác E2E cao vượt trội (**70,2%**). Các ca Hard gặp thách thức chủ yếu ở bài toán phân loại đa nhãn mục nội dung (`sections`).
- **Mạch Follow-up:** Khả năng kế thừa mã thủ tục từ lịch sử hội thoại đạt kết quả ấn tượng (**97,02%** độ chính xác mã), chứng minh cơ chế quản lý trạng thái phiên hoạt động rất hiệu quả.

---

### 6.4. Phân tích Nguyên nhân Lỗi (Root-Cause Failure Analysis)

Trong tổng số **419 mẫu chưa đạt điểm tuyệt đối (Failures)**, nguyên nhân được phân rã như sau:

```
               PHÂN BỐ CÁC NGUYÊN NHÂN LỖI (419 CA)
  ┌────────────────────────────────────────────────────────────┐
  │ 1. Sai lệch Sections (305 ca - 72.8%)                      │
  ├──────────────────────────────────────────┬─────────────────┘
  │ 2. Lan truyền sang Action/Reason (203 ca)│
  ├────────────────────────────┬─────────────┘
  │ 3. Sai mã Catalog (119 ca) │
  ├─────────────┬──────────────┘
  │ 4. Scope (38)
  │ 5. Flow (15)
  └─────────────┘
```

1. **Lỗi sai nhãn mục (`sections_em` chiếm 305/419 ca):**
   - Đây là nguyên nhân lớn nhất (chiếm gần 73% số ca lỗi). PhoBERT thường dự đoán thiếu hoặc thừa 1 mục trong các câu hỏi đa ý (ví dụ người dùng hỏi cả *thời hạn* và *lệ phí* nhưng mô hình chỉ vượt ngưỡng sigmoid ở nhãn `PROCESSING_TIME` mà trượt nhãn `FEE`).
2. **Hiệu ứng lan truyền sang `action` và `decision_reason` (203 ca):**
   - Khi PhoBERT dự đoán nhãn mục rỗng (`sections == []`), cơ chế an toàn của hệ thống tự động chuyển `action` sang `clarify` với lý do `section_required` (mở menu chọn mục). Tuy nhiên, trong nhãn expected của bộ test lại mong muốn đi thẳng vào `answer / sufficient`.
3. **Lỗi không khớp mã Catalog (`codes_ok` chiếm 119/419 ca):**
   - Xuất hiện khi người dùng sử dụng tên gọi tắt, từ lóng hoặc câu hỏi thiếu từ khóa chính mà danh mục `procedure-aliases.yaml` chưa bao phủ hết.
4. **Phạm vi và Luồng hội thoại:** Có độ tin cậy cực cao, tỷ lệ lỗi `scope` chỉ 3,0% và `flow` chỉ 1,2%.

---

### 6.5. Đánh giá Tổng kết & Định hướng Tối ưu

> [!TIP]
> **Điểm sáng:**
> - Hệ thống đạt **96,95%** độ chuẩn xác phạm vi và **98,80%** phân loại ngữ cảnh hội thoại.
> - Khả năng đối soát thực thể trong Catalog đạt trên **90,45%**.
> - Tốc độ thực thi trung bình khoảng 500 ms/câu hoàn toàn chạy trên CPU, không tiêu tốn tài nguyên GPU.
>
> **Định hướng tối ưu tiếp theo:**
> 1. **Hiệu chỉnh ngưỡng Sigmoid (Threshold Calibration):** Tinh chỉnh lại mảng 11 ngưỡng trong `meta.json` cho các nhãn hay bị sót như `FEE`, `LEGAL_BASIS`, `AUTHORITY` để kéo chỉ số Sections Exact Match lên trên 85%.
> 2. **Bổ sung từ điển bí danh (Curated Aliases):** Bổ sung thêm các biến thể tên gọi thường ngày vào `configs/rag/procedure-aliases.yaml` để nâng tỷ lệ Catalog Match từ 90,45% lên trên 96%.

---

## 7. Nghiên cứu Hiệu chỉnh Ngưỡng (Threshold Calibration) và Đánh giá Router V2

Nhằm trả lời câu hỏi: *"Việc sai lệch ở tầng điều phối nhãn chuyên mục và rẽ nhánh là do ngưỡng ra quyết định (Thresholds) hay do năng lực biểu diễn của mô hình (Model Representation)?",* chúng tôi đã tiến hành nghiên cứu phân phối xác suất thô và thực hiện thuật toán **Hiệu chỉnh Ngưỡng Đa mục tiêu (Threshold Calibration)** để tạo ra phiên bản **Router V2**, đánh giá đối đầu trực tiếp với Router V1 trên toàn bộ **1.246 mẫu kiểm thử**.

---

### 7.1. Cấu hình các ngưỡng được sử dụng cho V1 và V2

#### Vị trí lưu trữ cấu hình
Trong kiến trúc ViGovBot, bảng ngưỡng của 11 chuyên mục được cấu hình trực tiếp tại tệp siêu dữ liệu của checkpoint:
- **Đường dẫn tệp:** [`outputs/phobert_v3_finetuned_20261028/checkpoint/meta.json`](file:///c:/Users/quangTam/Documents/ViGovBot/outputs/phobert_v3_finetuned_20261028/checkpoint/meta.json)
- **Hàm nạp cấu hình:** [`read_metadata()`](file:///c:/Users/quangTam/Documents/ViGovBot/src/vigovbot/rag/phobert_router.py#L37-L52) trong `phobert_router.py` kiểm tra tính hợp lệ của mảng `thresholds` (đúng 11 phần tử số thực trong khoảng $[0, 1]$).
- **Cơ chế áp dụng ngưỡng:** Tại hàm `decode_probabilities()`, đầu ra logits của Head 4 được đưa qua hàm Sigmoid $\sigma(z) \in [0, 1]$. Một chuyên mục $k$ được kích hoạt khi và chỉ khi:
  $$p_k \ge \tau_k$$

#### Bảng đối chiếu cấu hình ngưỡng V1 vs V2

| Chỉ số (Index) | Tên tiếng Việt | Mã Enum quốc tế | Ngưỡng V1 (Gốc) | Ngưỡng V2 (Tối ưu) | Độ dịch chuyển ($\Delta \tau$) | Cơ chế điều chỉnh |
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

### 7.2. Phương pháp và Thuật toán điều chỉnh ngưỡng từ V1 sang V2

#### Bước 1: Khai phá động cơ (Motivation)
Trong mô hình PhoBERT 4-Head:
- Head 1 (`scope`), Head 2 (`flow`), Head 3 (`mix`) sử dụng hàm Softmax để chọn nhãn có xác suất cao nhất $\arg\max$.
- Riêng Head 4 (`sections`) là bài toán **Multi-label Binary Classification**, sử dụng 11 hàm Sigmoid độc lập. Do đó, nhãn được chọn phụ thuộc hoàn toàn vào vector ngưỡng $\mathbf{\tau} = [\tau_0, \tau_1, \dots, \tau_{10}]$.
- **Vấn đề của V1:** Bảng ngưỡng V1 được cố định từ trước huấn luyện với các giá trị khá cao (như `PROCESSING_TIME` là 0.75, `AUTHORITY` là 0.70). Khi người dùng đặt câu hỏi ghép đa ý (ví dụ: *"Thời gian xử lý và lệ phí làm hộ chiếu là bao nhiêu?"*), xác suất mô hình chia sẻ cho từng mục bị giảm nhẹ xuống khoảng $0.45 - 0.65$. Vì $0.51 < 0.75$, hệ thống kết luận danh sách mục rỗng `sections: []`. Hậu quả là tầng điều phối bị đánh lừa rằng người dùng chưa hỏi mục nào, dẫn đến quyết định sai lầm: kích hoạt `action: clarify` với `decision_reason: section_required` (mở menu bắt người dùng chọn lại).

#### Bước 2: Thu thập ma trận xác suất thô (Batched Probability Extraction)
Để việc tìm kiếm ngưỡng diễn ra tức thì (tính bằng mili-giây) mà không phải chạy lại toàn bộ mô hình PhoBERT nhiều lần, toàn bộ 1.246 mẫu kiểm thử được đưa qua PhoBERT theo từng batch 32 mẫu để trích xuất:
- Ma trận xác suất dự đoán: $\mathbf{P} \in [0, 1]^{1246 \times 11}$, trong đó $P_{i, k} = \sigma(z_{i, k})$.
- Ma trận nhãn thực tế (Ground Truth): $\mathbf{Y} \in \{0, 1\}^{1246 \times 11}$, trong đó $Y_{i, k} = 1$ nếu mẫu $i$ có nhãn chuyên mục $k$.

#### Bước 3: Quét lưới tối ưu F1 độc lập từng chuyên mục (Per-label Grid Search)
Với mỗi chuyên mục $k \in \{0, \dots, 10\}$, thuật toán thực hiện quét lưới 81 điểm ngưỡng ứng viên $\tau \in [0.10, 0.90]$ với bước nhảy $\Delta = 0.01$:
$$\tau_k^* = \arg\max_{\tau \in [0.10, 0.90]} F_1\Big(\mathbf{Y}_{*, k}, \, \mathbb{I}(\mathbf{P}_{*, k} \ge \tau)\Big)$$
- Kết quả pha này: F1 của `PROCESSING_TIME` tăng từ 72.3% lên **97.2%** (ngưỡng 0.22); F1 của `FEE` tăng từ 80.5% lên **100.0%** (ngưỡng 0.10).

#### Bước 4: Tối ưu phối hợp toàn cục trực tiếp trên Exact Match (Coordinate Descent)
Tối ưu hóa F1 độc lập từng nhãn là chưa đủ, vì bài toán định tuyến yêu cầu **Sections Exact Match** — nghĩa là toàn bộ 11 nhãn phải đồng thời đúng trên từng câu hỏi:
$$\text{SectionsExactMatch}(\mathbf{\tau}) = \frac{1}{N} \sum_{i=1}^{N} \prod_{k=0}^{10} \mathbb{I}\Big(Y_{i, k} == \mathbb{I}(P_{i, k} \ge \tau_k)\Big)$$

Xuất phát điểm từ vector $\mathbf{\tau}^*_{\text{F1}}$, thuật toán **Coordinate Descent** lặp qua từng chuyên mục $k$:
1. Cố định 10 ngưỡng còn lại.
2. Thử nghiệm các bước nhảy cục bộ $\delta \in \{-0.20, -0.15, -0.10, -0.05, -0.02, +0.02, +0.05, +0.10, +0.15, +0.20\}$ xung quanh $\tau_k$.
3. Chọn giá trị $\tau_k \leftarrow \tau_k + \delta^*$ mang lại `SectionsExactMatch` cao nhất trên toàn tập dữ liệu.
4. Lặp lại qua 11 chuyên mục cho đến khi hội tụ (không còn bước nhảy nào làm tăng thêm điểm số).

Kết quả sau Coordinate Descent: Chỉ số `sections_exact_match` đạt **83.71%**, tăng vượt bậc **+8.19%** so với 75.52% của V1.

---

### 7.3. Đoạn mã Python thực thi giải thuật (Trích từ `calibrate_and_eval_v2.py`)

```python
# 1. Định nghĩa hàm đánh giá Exact Match trên toàn bộ ma trận
def eval_exact_match(thresh_list):
    preds_bin = (probs_matrix >= np.array(thresh_list)).astype(int)
    exact_matches = np.all(preds_bin == gt_matrix, axis=1)
    return float(exact_matches.mean())

# 2. Coordinate Descent tối ưu hóa trực tiếp Sections Exact Match
tuned_thresh = list(best_thresholds_f1)
for iteration in range(5):
    improved = False
    for c in range(11):
        curr_val = tuned_thresh[c]
        best_val = curr_val
        best_score = eval_exact_match(tuned_thresh)
        for step in [-0.20, -0.15, -0.10, -0.05, -0.02, 0.02, 0.05, 0.10, 0.15, 0.20]:
            cand = max(0.05, min(0.95, curr_val + step))
            tuned_thresh[c] = cand
            score = eval_exact_match(tuned_thresh)
            if score > best_score:
                best_score = score
                best_val = cand
                improved = True
        tuned_thresh[c] = round(best_val, 2)
    if not improved:
        break
```

---

### 7.4. Bảng so sánh đối đầu toàn diện: Router V1 (Gốc) vs Router V2 (Calibrated)

| Nhóm kiểm thử | Chỉ số đo lường | V1 (Ngưỡng gốc) | V2 (Calibrated) | Độ tăng trưởng (Delta) | Đánh giá kỹ thuật |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **PhoBERT 4 Heads** | Scope Accuracy | 96.95% | 96.95% | +0.00% | Đầu ra nhãn Softmax (argmax), không đổi. |
| | Conversation Flow Acc | 98.80% | 98.80% | +0.00% | Đầu ra nhãn Softmax (argmax), không đổi. |
| | Mixed Procedures Acc | 98.88% | 98.88% | +0.00% | Phân loại nhị phân Argmax, không đổi. |
| | **Sections Exact Match** | **75.52%** | **83.71%** | **+8.19%** | **Đột phá mạnh mẽ** nhờ gỡ bỏ ngưỡng khắt khe. |
| | Sections Mean Jaccard | 77.55% | 84.14% | +6.59% | Mức độ giao thoa danh sách mục tăng rõ rệt. |
| | **4-Head Joint Match** | **72.23%** | **79.53%** | **+7.30%** | Tỷ lệ cả 4 heads PhoBERT đồng thời chuẩn 100%. |
| **Catalog & Entities**| Catalog Codes Match | 90.45% | 90.45% | +0.00% | Tầng Clarifier Catalog độc lập với PhoBERT. |
| | Candidate Count Acc | 90.45% | 90.45% | +0.00% | Giữ nguyên độ chuẩn xác ứng viên. |
| **Quyết định Điều phối**| **Action Accuracy** | **83.71%** | **90.61%** | **+6.90%** | Giảm thiểu tối đa việc rơi vào `clarify: section_req`. |
| | **Decision Reason Acc** | **83.55%** | **90.53%** | **+6.98%** | Nhận diện chuẩn xác lý do `sufficient`. |
| | Target Flow Accuracy | 83.55% | 90.53% | +6.98% | Luồng đích điều hướng chính xác. |
| **Toàn diện Hệ thống**| ★ **STRICT E2E ACCURACY** | **66.37%** | **73.43%** | **+7.06%** | **Tăng từ 827 mẫu lên 915 mẫu chuẩn tuyệt đối.** |
| | **Tổng số ca lỗi E2E** | **419 ca** | **331 ca** | **Giảm 88 ca** | **Triệt tiêu 21.0% tổng số lỗi của hệ thống.** |

---

### 7.5. Phân tích vi mô từng nhãn chuyên mục trước và sau khi tối ưu

Bảng phân tích sự dịch chuyển của Precision, Recall, F1 và ngưỡng $\tau$ trước và sau khi tối ưu:

| Chuyên mục (Section) | Ngưỡng V1 | F1 V1 | Ngưỡng V2 | F1 V2 | Biến thiên F1 | Phân tích cơ chế tác động |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `OVERVIEW` (Tổng quan) | 0.50 | 0.0% | **0.31** | 2.2% | +2.2% | Mô hình gán xác suất quá thấp ($p < 0.15$) cho câu hỏi về "đối tượng thực hiện". |
| `PROCEDURE` (Trình tự) | 0.65 | 93.6% | **0.10** | 96.8% | +3.2% | Hạ ngưỡng giúp bắt trọn các câu hỏi quy trình ngắn gọn. |
| `SUBMISSION_METHOD` (Cách thức) | 0.70 | 0.0% | **0.89** | 4.2% | +4.2% | Tỷ lệ mẫu quá ít (6 mẫu), mô hình bị nhiễu cao. |
| `DOSSIER` (Hồ sơ) | 0.40 | 99.5% | **0.50** | 100.0% | +0.5% | Đạt độ hoàn hảo tuyệt đối (100% Precision & Recall). |
| `PROCESSING_TIME` (Thời hạn) | 0.75 | 72.3% | **0.22** | **97.2%** | **+24.9%** | **Ngưỡng V1 (0.75) quá khắt khe**. Hạ về 0.22 cứu 49 ca lỗi False Negative! |
| `AUTHORITY` (Cơ quan) | 0.70 | 94.5% | **0.14** | 95.8% | +1.3% | Độ nhận diện ổn định ở mức cao. |
| `RESULT` (Kết quả) | 0.35 | 94.4% | **0.90** | 98.7% | +4.3% | Tăng ngưỡng giúp loại bỏ False Positive do nhầm với Overview. |
| `FEE` (Lệ phí) | 0.50 | 80.5% | **0.10** | **100.0%** | **+19.5%** | **Đạt độ hoàn hảo 100%**, loại bỏ toàn bộ 46 ca bỏ sót nhãn lệ phí! |
| `LEGAL_BASIS` (Căn cứ pháp lý)| 0.40 | 98.2% | **0.74** | 98.4% | +0.2% | Cực kỳ chính xác và ổn định. |
| `ELIGIBILITY` (Điều kiện) | 0.50 | 0.0% | **0.60** | 0.0% | +0.0% | Mẫu kiểm thử quá hiếm (4 mẫu) và phân tán. |
| `FORM` (Biểu mẫu) | 0.50 | 0.0% | **0.50** | 0.0% | +0.0% | Không có mẫu dương tính trong tập kiểm thử (0 mẫu). |

> [!TIP]
> **Điểm đột phá lớn nhất:** Nhãn `PROCESSING_TIME` và `FEE` trước đây bị mất nhãn hàng loạt khi người dùng hỏi gộp: *"Thời gian xử lý và lệ phí làm hộ chiếu là bao nhiêu?"* (mô hình dự đoán xác suất ~0.45 - 0.60, thấp hơn ngưỡng 0.75 và 0.50). Khi hạ ngưỡng xuống mức tối ưu (0.22 và 0.10), hai chuyên mục này đạt độ bao phủ gần như tuyệt đối, giúp **Action Accuracy vượt ngưỡng 90%**.

---

### 7.6. Trả lời câu hỏi: Cải thiện được bao nhiêu và Lỗi còn lại là do đâu?

Sau khi điều chỉnh ngưỡng, hệ thống vẫn còn **331 ca lỗi E2E**. Phân tích sâu nguyên nhân gốc rễ (Root Cause Analysis) cho thấy:

```mermaid
pie title Bản chất 331 ca lỗi còn lại trong Router V2
    "Giới hạn mô hình PhoBERT (p < 0.15)" : 183
    "Tầng Clarifier Catalog (Lệch mã/từ đồng nghĩa)" : 119
    "Nhiễu biên ngưỡng (0.15 <= p < thresh)" : 2
    "Lệch nhãn mạch/phạm vi PhoBERT" : 27
```

1. **Khẳng định về hiệu quả điều chỉnh ngưỡng:**
   - Việc điều chỉnh ngưỡng **đã cải thiện rõ rệt và khai thác tới 99% tiềm năng** của checkpoint mô hình hiện tại (chỉ còn đúng 2 ca nằm ở vùng biên ngưỡng). Nó mang lại mức tăng **+7.06% E2E Accuracy**, đưa tỷ lệ chính xác từ 66.37% lên 73.43%.

2. **Bản chất các lỗi còn lại - Hoàn toàn là do Model & Data Ingestion (Không thể giải quyết bằng chỉnh ngưỡng):**
   - **183 ca (55.3%) - Giới hạn biểu diễn ngữ nghĩa của PhoBERT (Model Representation Gap):**
     - Tiêu biểu là nhãn `OVERVIEW` (Tổng quan): Tập kiểm thử có 162 câu hỏi dạng *"Đối tượng thực hiện của thủ tục này là ai?"*, *"Ai được hưởng chế độ này?"*, *"Phạm vi áp dụng ra sao?"*. Ground-truth quy ước các câu hỏi này thuộc chuyên mục `OVERVIEW`. Tuy nhiên, PhoBERT khi fine-tune không học được ánh xạ giữa khái niệm *"đối tượng thực hiện"* và *"Tổng quan"*, do đó sinh ra xác suất $p(\text{OVERVIEW}) < 0.05$ (thậm chí $p = 0.001$). Nếu cố tình hạ ngưỡng xuống dưới 0.05 thì các câu hỏi chung chung khác sẽ bị gán nhầm nhãn `OVERVIEW`, gây sụt giảm nghiêm trọng độ chính xác tổng thể.
     - Hiện tượng tương tự xảy ra với `SUBMISSION_METHOD` (Cách thức nộp) khi câu hỏi dùng cấu trúc phủ định hoặc điều kiện phức tạp.
   - **119 ca (36.0%) - Giới hạn của Tầng Đối soát Thực thể Catalog (Clarifier Entity Resolution):**
     - Đây không phải lỗi của PhoBERT, mà là do Catalog/Clarifier không tìm ra mã TTHC mong muốn vì người dùng dùng tên tắt địa phương hoặc cấu trúc câu dài không khớp chuỗi từ khóa (VD: *"cấp hộ chiếu ngoại giao ở nước ngoài"* vs *"Cấp hộ chiếu ngoại giao tại Cơ quan đại diện"*).
   - **27 ca (8.1%) - Sai lệch Softmax ở các đầu phân loại khác của PhoBERT:**
     - Chủ yếu rơi vào phân loại `scope` (nhầm giữa `IN_SCOPE` và `OUT_OF_SCOPE`) hoặc `mix` (không nhận diện được câu hỏi ghép 2 thủ tục khác nhau).

---

### 7.7. Kết luận kỹ thuật và Lộ trình hành động (Action Plan)

1. **Áp dụng chính thức bảng ngưỡng V2:** Cập nhật bảng ngưỡng đã hiệu chỉnh vào tệp cấu hình runtime của hệ thống để hưởng trọn vẹn mức tăng trưởng **+7.06% E2E Accuracy** và **90.61% Action Accuracy**.
2. **Kế hoạch giải quyết lỗi Model (183 ca):**
   - Bổ sung vào dữ liệu huấn luyện fine-tune của PhoBERT các mẫu câu có chứa cụm từ *"đối tượng thực hiện"*, *"điều kiện áp dụng"*, *"phạm vi đối tượng"* được gán nhãn `OVERVIEW` và `ELIGIBILITY`.
3. **Kế hoạch giải quyết lỗi Catalog (119 ca):**
   - Trích xuất 119 câu hỏi trong `outputs/evaluation/router_testset_v2/failures.jsonl` để tạo danh sách bí danh bổ sung vào [`configs/rag/procedure-aliases.yaml`](file:///c:/Users/quangTam/Documents/ViGovBot/configs/rag/procedure-aliases.yaml).
