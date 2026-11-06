# Báo cáo Xác minh Hậu-Đánh giá ViGovBot

> **Snapshot lịch sử:** Báo cáo phản ánh mã nguồn tại thời điểm xác minh. Một số
> phát hiện đã được xử lý sau đó; hãy đối chiếu source hiện tại và
> [`docs/project/current-stage.md`](../../project/current-stage.md) trước khi xem
> một mục là lỗi còn tồn tại.

> [!IMPORTANT]
> Mọi kết luận dưới đây được tra trực tiếp từ mã nguồn hiện tại — không dùng lại kết quả từ lần đánh giá trước. Mỗi mục ghi rõ file và dòng code là bằng chứng.

---

## Tóm tắt nhanh

| Trạng thái | Số lượng |
|---|---|
| ✅ Đã sửa hoàn toàn | 6 |
| 🔄 Đã sửa một phần / cải thiện đáng kể | 3 |
| ❌ Vẫn còn tồn đọng | 7 |
| 🆕 Vấn đề mới phát sinh sau chỉnh sửa | 2 |

---

## Phần 1 — Các lỗi đã được sửa hoàn toàn ✅

---

### ✅ FIX 1: `source_fingerprint()` — đã cache, đã loại trừ `__pycache__`

**Báo cáo gốc:** Hàm đọc toàn bộ file `.py` mỗi lần gọi, không cache, không loại trừ `__pycache__`.

**Trạng thái hiện tại:** Đã sửa triệt để.

**Bằng chứng** (`pipeline.py` L25–43):
```python
@lru_cache(maxsize=2)
def _fingerprint_source_files(root_value, signature):
    root = Path(root_value)
    return json_hash({name: (root / name).read_text(...) for name, _, _ in signature})

def source_fingerprint():
    root = Path(__file__).resolve().parents[1]
    paths = sorted(
        path for path in root.rglob("*.py")
        if "__pycache__" not in path.relative_to(root).parts   # ← loại trừ __pycache__
    )
    signature = tuple(
        (path.relative_to(root).as_posix(), path.stat().st_mtime_ns, path.stat().st_size)
        for path in paths
    )
    return _fingerprint_source_files(str(root), signature)     # ← cache qua lru_cache
```

**Phân tích chất lượng fix:** Tốt. `signature` chỉ dùng `mtime_ns` + `st_size` (không đọc nội dung file), `_fingerprint_source_files` được cache với key là `(root_value, signature)`. Chỉ đọc nội dung file thực khi signature thay đổi. Loại trừ `__pycache__` đúng bằng kiểm tra `.parts`.

---

### ✅ FIX 2: `_fold()` phân tán — đã hợp nhất về `utils/text.py`

**Báo cáo gốc:** ≥4 biến thể `_fold` khác hành vi nhỏ, phân tán khắp các module.

**Trạng thái hiện tại:** Đã tạo `utils/text.py` làm nguồn duy nhất với 3 hàm rõ vai trò.

**Bằng chứng** (`utils/text.py`):
```python
def fold_vietnamese(text: str) -> str:
    """Casefold và bỏ dấu, không thay đổi khoảng trắng."""
    normalized = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")

def ascii_word_tokens(text: str) -> list[str]:
    """ASCII alphanumeric tokens từ dạng không dấu."""
    return re.findall(r"[a-z0-9]+", fold_vietnamese(text))
```

**Các module đã import đúng:**
- `retriever.py` L9: `from vigovbot.utils.text import fold_vietnamese` → dùng `fold_retrieval_text` wrap thêm alias "dang ki"
- `procedure_discovery.py` L9: `from vigovbot.utils.text import fold_vietnamese` → `fold()` chỉ thêm `split().join()`
- `response.py` L11: `from vigovbot.utils.text import ascii_word_tokens` → thay thế `_fold_words` cũ
- `prompt_templates.py` L8: `from vigovbot.utils.text import fold_vietnamese`
- `conversation.py` L23: `from vigovbot.retrieval.retriever import fold_retrieval_text as _fold`
- `clarification.py` L17: `from vigovbot.retrieval.retriever import fold_retrieval_text as _fold`

**Phân tích chất lượng fix:** Tốt về cơ bản — một nền chung `fold_vietnamese` cho tất cả. Vẫn còn 2 wrapper khác nhau nhỏ (`fold_retrieval_text` thêm alias "dang ki", `fold` trong discovery thêm whitespace collapse) nhưng cả hai đều tường minh và có docstring.

---

### ✅ FIX 3: `_presentation_instruction()` — đã dùng word boundary regex thay substring match

**Báo cáo gốc:** `any(term in folded for term in ...)` — substring match thuần, "phi" match trong "khoa phi".

**Trạng thái hiện tại:** Đã sửa thành `re.search` với word boundary.

**Bằng chứng** (`prompt_templates.py` L33–37):
```python
def asks_for(terms):
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", folded)
        for term in terms
    )
```

**Phân tích:** Fix đúng và đủ. Dùng negative lookbehind/lookahead `[a-z0-9]` phù hợp với text đã fold (không còn dấu, không còn ký tự đặc biệt tiếng Việt).

---

### ✅ FIX 4: `MAX_BODY_BYTES` — đã được enforce thực sự

**Báo cáo gốc:** Constant được định nghĩa nhưng không rõ có được áp dụng không.

**Trạng thái hiện tại:** Đã kiểm tra và enforce tại nhiều điểm trong request handler.

**Bằng chứng** (`server/app.py` L560, L562, L579, L581):
```
L560: if len(body) > MAX_BODY_BYTES:
L562: if not body or len(body) > MAX_BODY_BYTES:
L579: if len(body) > MAX_BODY_BYTES:
L581: if not body or len(body) > MAX_BODY_BYTES:
```

**Phân tích:** Kiểm tra ở cả trường hợp body rỗng và body quá lớn, trên nhiều endpoint.

---

### ✅ FIX 5: `procedure_discovery.py` — đã import `fold_vietnamese` thay tự implement

**Báo cáo gốc:** Module tự implement hàm `fold()` trùng logic với các nơi khác.

**Trạng thái hiện tại:** Import `fold_vietnamese` từ `utils/text.py`, hàm `fold()` local chỉ thêm whitespace collapse.

**Bằng chứng** (`procedure_discovery.py` L9, L17–19):
```python
from vigovbot.utils.text import fold_vietnamese

def fold(text):
    """Collapse whitespace for discovery after shared Unicode folding."""
    return " ".join(fold_vietnamese(text).split())
```

**Phân tích:** Đúng — `fold()` local không còn tự implement logic bỏ dấu mà delegate sang `fold_vietnamese`.

---

### ✅ FIX 6: `_fold_words` trong `response.py` — đã thay bằng `ascii_word_tokens`

**Báo cáo gốc:** `_fold_words` là biến thể thứ 4 của _fold, defined local trong `response.py`.

**Trạng thái hiện tại:** Không còn `def _fold_words` trong `response.py`. Module import `ascii_word_tokens` từ `utils/text.py`.

**Bằng chứng** (`response.py` L11, L16, L28, L43, L49, L51): tất cả đều dùng `ascii_word_tokens(...)`.

---

## Phần 2 — Đã cải thiện một phần 🔄

---

### 🔄 PARTIAL 1: `_ensure_source_code_index()` — vẫn mở write connection nhưng có cơ chế phòng vệ

**Báo cáo gốc:** Mở connection ghi (không read-only), không nhất quán với Retriever.

**Trạng thái hiện tại:** Vẫn mở write connection (`sqlite3.connect(db_path)` không có URI mode=ro).

**Bằng chứng** (`vector_store.py` L18):
```python
def _ensure_source_code_index(db_path):
    connection = sqlite3.connect(db_path)   # ← không có mode=ro
```

**Nhưng:** Hàm này chỉ được gọi từ `_prepare_corpus()` bên trong `output_lock()` (L74) — đảm bảo không có writer nào khác chạy đồng thời. Rủi ro race condition thực tế thấp hơn báo cáo gốc đánh giá.

**Vẫn còn:** Connection ghi mở trên corpus đã được "seal" — về nguyên tắc, có thể gây lỗi nếu hệ thống file mount read-only. Chưa sửa.

---

### 🔄 PARTIAL 2: `answer_question()` — đã thêm nhánh v2 trả về sớm nhưng v1 vẫn 290 dòng

**Báo cáo gốc:** 382 dòng, 14 tham số, hai contract song song.

**Trạng thái hiện tại:** File tăng thêm 14 dòng (từ 382 → 396). Nhánh v2 trả về sớm ở L112–119 khi `routing_contract == "v2"`. V1 fallback vẫn còn toàn bộ logic (L120–396 = 276 dòng logic).

**Bằng chứng** (`pipeline.py` L107–119):
```python
def answer_question(question, retriever, tokenizer, settings, history=None, *, structured=False, answer_fn=None,
                    retrieval_context=None, clarification_context=None, clarification_scope="",
                    router_fn=None, conversation_state=None, selection=None):
    ...
    if settings.get("routing_contract") == "v2" and settings.get("routing_enabled", True):
        ...
        return answer_conversation(...)   # ← delegate toàn bộ, không xử lý gì thêm
    # V1 fallback: 276 dòng còn lại
```

**Nhận định:** Hai contract song song vẫn tồn tại nhưng v2 không bị "nhiễm" logic v1 vì return sớm. Vấn đề chính vẫn là **14 tham số** và **hàm 276 dòng logic v1** chưa được tách nhỏ hơn. Chưa sửa đủ.

---

### 🔄 PARTIAL 3: Training — `_precision()` logic float32 vẫn redundant nhưng tác hại bị chặn bởi CUDA guard

**Báo cáo gốc:** `_precision()` trả về `torch.float32, False, False` khi không có CUDA, nhưng ngay sau đó `train()` raise RuntimeError vì CUDA không có.

**Trạng thái hiện tại:** Vẫn còn pattern này.

**Bằng chứng** (`train.py` L36–50):
```python
def _precision(torch, config):
    if requested == "bfloat16" and torch.cuda.is_bf16_supported(): return torch.bfloat16, True, False
    if torch.cuda.is_available(): return torch.float16, False, True
    return torch.float32, False, False   # ← nhánh không bao giờ được dùng thực tế

def train(...):
    ...
    if not environment["cuda_available"]:
        raise RuntimeError("CUDA is unavailable...")   # ← chặn trước khi gọi _precision
    ...
    dtype, bf16, fp16 = _precision(torch, config)     # ← chỉ gọi sau khi CUDA confirmed
```

**Nhận định:** Vô hại trong runtime nhưng code gây nhầm lẫn vẫn chưa được xóa. Không phải lỗi, là code smell chưa được dọn.

---

## Phần 3 — Vẫn còn tồn đọng ❌

---

### ❌ PENDING 1: `_STATES` OrderedDict 256 session in-memory, không persist

**Báo cáo gốc:** Session in-memory, giới hạn 256, mất khi restart, không shared giữa workers.

**Bằng chứng hiện tại** (`conversation.py` L38–39, L193–196):
```python
_STATES = OrderedDict()
_STATE_LOCK = Lock()
...
_STATES[key] = result["conversation_state"]
_STATES.move_to_end(key)
while len(_STATES) > 256:
    _STATES.popitem(last=False)
```

**Trạng thái:** Không thay đổi. Vẫn là in-memory LRU 256 slot. Chưa có Redis, database, hay bất kỳ persistence nào.

---

### ❌ PENDING 2: Không có retry/circuit breaker cho Ollama

**Báo cáo gốc:** `llm_client.py` không có retry, không có circuit breaker, không phân biệt 4xx/5xx.

**Bằng chứng hiện tại** (`llm_client.py` L30–48): Toàn bộ file 78 dòng — không có import `tenacity`, `requests.adapters.Retry`, hay bất kỳ retry mechanism nào. Vẫn là một lần `requests.post()` với `raise_for_status()`.

**Trạng thái:** Không thay đổi.

---

### ❌ PENDING 3: Vector normalization dư thừa trong `retriever.py`

**Báo cáo gốc:** `vector /= np.max(np.abs(vector))` trước `faiss.normalize_L2(vector)` — max-abs scaling không thay đổi hướng vector.

**Bằng chứng hiện tại** (`retriever.py` L129–130):
```python
vector /= np.max(np.abs(vector))   # ← dư thừa
faiss.normalize_L2(vector)         # ← L2 normalization đã đủ
```

**Trạng thái:** Không thay đổi. Code vẫn chạy đúng (không gây lỗi) nhưng bước max-abs là thừa.

---

### ❌ PENDING 4: `torch.set_num_threads()` global setting trong `PhoBERTRouter.__init__`

**Báo cáo gốc:** `torch.set_num_threads(threads)` ảnh hưởng global PyTorch, không riêng PhoBERT.

**Bằng chứng hiện tại** (`phobert_router.py` L107):
```python
torch.set_num_threads(threads)   # ← global, không scoped
```

**Trạng thái:** Không thay đổi.

---

### ❌ PENDING 5: `heads.pt` dùng `torch.save()` thay vì safetensors

**Báo cáo gốc:** File weights `heads.pt` nên dùng safetensors cho consistency với encoder.

**Bằng chứng hiện tại** (`phobert_router.py` L100–101, L112):
```python
required = ("meta.json", "heads.pt", "vocab.txt", ...)
...
weights = torch.load(root / "heads.pt", map_location="cpu", weights_only=True)
```

**Trạng thái:** Không thay đổi. `weights_only=True` vẫn an toàn, nhưng định dạng vẫn là `.pt`.

---

### ❌ PENDING 6: Giới hạn cứng 2/4/6 turns trong SFT validation

**Báo cáo gốc:** `if len(conversation) not in (2, 4, 6)` — không có tham số cấu hình.

**Bằng chứng hiện tại** (`training/data.py` L45):
```python
if len(conversation) not in (2, 4, 6):
    raise ValueError(...)
```

**Trạng thái:** Không thay đổi.

---

### ❌ PENDING 7: `max_seq_length=2048` (train) ≠ `num_ctx=16384` (inference)

**Báo cáo gốc:** Training context window nhỏ hơn 8x so với inference — potential degradation với long context.

**Bằng chứng hiện tại:**
- `configs/training/base.yaml` L4: `max_seq_length: 2048`
- `configs/rag/inference.yaml` L12: `num_ctx: 16384`

**Trạng thái:** Không thay đổi. Khoảng cách 8x vẫn còn.

---

## Phần 4 — Vấn đề mới phát sinh sau chỉnh sửa 🆕

---

### 🆕 NEW ISSUE 1: `procedure_discovery.py` hàm `fold()` local vẫn tồn tại song song với `fold_retrieval_text` — nguy cơ divergence

**Phát hiện mới từ code hiện tại:**

Sau khi hợp nhất `_fold` về `utils/text.py`, hiện có 2 wrapper khác nhau với tên khác nhau cùng được import vào `conversation.py`:

```python
# conversation.py L23:
from vigovbot.retrieval.retriever import fold_retrieval_text as _fold

# conversation.py L325 (lazy import bên trong hàm):
from vigovbot.retrieval.procedure_discovery import NEGATIVE_QUALIFIERS, fold
```

**Vấn đề:** Trong cùng một file `conversation.py`, có 2 hàm fold với hành vi khác nhau:
- `_fold` (alias `fold_retrieval_text`): `fold_vietnamese(text)` + sửa "dang ki→dang ky"
- `fold` (từ `procedure_discovery`): `" ".join(fold_vietnamese(text).split())` — thêm whitespace collapse, **không** sửa "dang ki"

Nếu dev dùng lẫn `_fold` và `fold` trong cùng logic, kết quả matching sẽ khác nhau với query có "dang ki". Hiện tại chúng được dùng ở các branch khác nhau (phát hiện thủ tục mờ vs routing), nhưng là potential confusion point.

**Mức độ:** 🟡 Trung bình — không gây bug hiện tại nhưng là technical debt sau refactor.

---

### 🆕 NEW ISSUE 2: `_fingerprint_source_files` được cache với `maxsize=2` nhưng key tính toán phức tạp có thể cache miss không cần thiết

**Phát hiện mới từ code hiện tại:**

**Bằng chứng** (`pipeline.py` L25–43):
```python
@lru_cache(maxsize=2)
def _fingerprint_source_files(root_value, signature):
    ...
```

`signature` là `tuple((name, mtime_ns, size) for ...)` — đây là tuple có thể có vài trăm phần tử (một tuple per `.py` file). Mỗi lần `source_fingerprint()` gọi, nó tạo tuple này và dùng làm key của `lru_cache`.

**Vấn đề:** `lru_cache` cache theo equality của arguments. `tuple` so sánh element-by-element — O(N) với N là số file. Với ~100 file Python, mỗi cache lookup là O(100). Điều này tốt hơn nhiều so với đọc tất cả file (fix gốc tốt), nhưng mỗi lần `source_fingerprint()` gọi vẫn phải:
1. Duyệt tất cả `.py` file để lấy `mtime_ns` + `st_size` → O(N) stat syscalls
2. So sánh tuple N phần tử với cached key → O(N)

Nếu `evaluation_complete=True` được gọi nhiều lần liên tiếp (không thay đổi code), stat syscalls vẫn xảy ra mỗi lần. `lru_cache` chỉ tránh được việc đọc nội dung file (bước tốn kém nhất), nhưng **không** tránh được N stat calls.

**Giải pháp đúng hơn:** Cache `signature` một lần lúc khởi động server, invalidate chỉ khi nhận signal `SIGHUP` hoặc theo TTL.

**Mức độ:** 🟢 Thấp — tốt hơn nhiều so với trước (không còn đọc file content mỗi request), nhưng N stat calls vẫn xảy ra mỗi lần `source_fingerprint()` được invoke.

---

## Phần 5 — Kiểm tra chéo tính nhất quán sau refactor

### Điểm cần lưu ý

| Module | Dùng fold nào | Alias "dang ki"? | Whitespace collapse? |
|---|---|---|---|
| `retriever.py` | `fold_retrieval_text` | ✅ Có | ❌ Không |
| `clarification.py` | `fold_retrieval_text` as `_fold` | ✅ Có | ❌ Không |
| `conversation.py` | `fold_retrieval_text` as `_fold` | ✅ Có | ❌ Không |
| `pipeline.py` | `fold_retrieval_text` as `_fold` | ✅ Có | ❌ Không |
| `procedure_discovery.py` | `fold()` wrap `fold_vietnamese` | ❌ Không | ✅ Có |
| `prompt_templates.py` | `fold_vietnamese` trực tiếp | ❌ Không | ❌ Không |
| `response.py` | `ascii_word_tokens` | ❌ Không (strip hết) | N/A |

> [!WARNING]
> `procedure_discovery.py` và `prompt_templates.py` **không** sửa alias "dang ki→dang ky". Nếu user gõ "đăng kí" (thay vì "đăng ký"), `fold_vietnamese("đăng kí") = "dang ki"` — sẽ không match với corpus được index theo "dang ky". Vấn đề này chỉ ảnh hưởng discovery và presentation check, không ảnh hưởng retrieval chính (dùng `fold_retrieval_text`).

---

## Phần 6 — Vấn đề chưa thay đổi trạng thái (không phải lỗi mới, không phải fix mới)

| Vấn đề | Trạng thái |
|---|---|
| `records.py` 1022 dòng (file lớn nhất) | Không thay đổi |
| `_tokens()` duplicate giữa `scoring.py` và `records.py` | Không thay đổi — cả hai vẫn define riêng |
| `_lcs_length()` tự implement thay vì dùng `difflib` | Không thay đổi |
| Không có auth/rate limiting trên API | Không thay đổi (phù hợp với scope research) |
| `if __package__ in (None, ""):` trong `markdown.py` | Không thay đổi |
| `heads.pt` không phải safetensors | Không thay đổi |
| `sha256_file` alias public trong `training/data.py` | Không thay đổi (giữ compatibility) |

---

## Kết luận

### Chất lượng các fix đã thực hiện

| Fix | Chất lượng | Nhận xét |
|---|---|---|
| `source_fingerprint` caching | ⭐⭐⭐⭐ Tốt | Giải quyết đúng vấn đề, loại trừ __pycache__ |
| Hợp nhất `_fold` về `utils/text.py` | ⭐⭐⭐ Khá | Cải thiện đáng kể, còn 2 wrapper nhỏ có hành vi khác |
| `_presentation_instruction` word boundary | ⭐⭐⭐⭐ Tốt | Sửa đúng, dùng regex lookbehind/lookahead |
| `MAX_BODY_BYTES` enforce thực sự | ⭐⭐⭐⭐ Tốt | Kiểm tra ở nhiều điểm |

### Rủi ro tồn đọng quan trọng nhất

1. **Session in-memory** (`❌ PENDING 1`) — rủi ro cao nhất với multi-worker deployment
2. **Không có Ollama retry** (`❌ PENDING 2`) — rủi ro cao khi Ollama overloaded
3. **`fold` divergence sau refactor** (`🆕 NEW ISSUE 1`) — technical debt tiềm tàng

### Khuyến nghị ưu tiên tiếp theo

```
1. [Cao] llm_client.py: thêm retry với exponential backoff (tenacity hoặc tự implement)
2. [Cao] conversation.py: document rõ 2 "fold" khác nhau và khi nào dùng cái nào
3. [Trung bình] pipeline.py: tách answer_question v1 thành các helper nhỏ hơn
4. [Thấp] retriever.py L129: xóa dòng max-abs normalization dư thừa
5. [Thấp] training/data.py: đổi hard-coded (2,4,6) thành config param
```
