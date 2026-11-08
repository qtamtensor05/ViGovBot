# Phục hồi QLoRA v2 trên máy mới

Luồng này tái tạo model triển khai từ adapter PEFT rút gọn thay vì chuyển file
GGUF 8,1 GB. Entry point trực tiếp là
`recovery/qlora_v2/restore.py`; lệnh CLI tương đương là
`vigov train restore`. Manifest, checksum và adapter đều nằm trong cùng bundle
`recovery/qlora_v2/`.

## Artifact cần mang sang máy mới

Bundle adapter mặc định là `recovery/qlora_v2/adapter/`, dung lượng
177.420.652 byte. Bundle chỉ chứa:

- `adapter_model.safetensors`, `adapter_config.json`, `model_metadata.json`;
- tokenizer, vocabulary, merge rules, special tokens và chat template;
- Modelfile dùng để import bản GGUF phục hồi vào Ollama.

Bundle không chứa optimizer, scheduler, RNG state, trainer state, checkpoint
trung gian hoặc model GGUF. Các file bị loại chỉ phục vụ resume training hoặc là
đầu ra có thể tái tạo.

Mọi file trong bundle được kiểm tra SHA-256 trước khi tải model nền hoặc merge.
Sai hoặc thiếu một file làm luồng dừng ngay.

## Yêu cầu máy phục hồi

- Python tương thích và môi trường `.[training,gpu]`;
- đủ RAM để nạp Qwen2.5-7B ở BF16 trên CPU và tối thiểu 50 GiB trống trong thư
  mục làm việc;
- Git checkout của `llama.cpp` đã build, có `convert_hf_to_gguf.py` và
  `llama-quantize`;
- Ollama nếu cần bước import cuối;
- Internet hoặc Hugging Face cache có đúng snapshot model nền.

Không cần GPU để merge vì công cụ cố định `device_map="cpu"`. GPU không thay thế
yêu cầu RAM/ổ đĩa cho model BF16.

## Khóa revision trước khi phục hồi

Run lịch sử chỉ ghi `model_revision: main`, không ghi Hugging Face commit SHA.
Vì vậy manifest mặc định cố ý bị chặn. Khi xác định được snapshot gốc, thay:

```yaml
base_model:
  repo_id: Qwen/Qwen2.5-7B-Instruct
  revision: <hugging-face-commit-sha>
```

Nếu chấp nhận tải trạng thái `main` hiện tại và rủi ro không tái tạo bit-for-bit,
phải truyền tường minh `--allow-unpinned-revision`.

## Chuẩn bị adapter

Có hai cách:

1. Chép nguyên bundle vào `recovery/qlora_v2/`, gồm script, manifest và `adapter/`.
2. Đăng bundle lên một Hugging Face model repository rồi dùng
   `--adapter-repo ORG/REPO --adapter-revision COMMIT_SHA`.

Sau khi đăng bundle, có thể điền `adapter.repo_id` và `adapter.revision` vào
manifest để máy mới không cần truyền hai option này.

## Chạy phục hồi đầy đủ

Luồng đầy đủ trên máy mới, thực hiện từ thư mục gốc repository sau khi đã chép
toàn bộ `recovery/`:

```powershell
python -m pip install -e ".[training,gpu]"

python recovery/qlora_v2/restore.py `
  --dry-run `
  --allow-unpinned-revision

python recovery/qlora_v2/restore.py `
  --llama-cpp-dir C:\tools\llama.cpp `
  --allow-unpinned-revision
```

Nếu đã thay `revision` trong manifest bằng commit SHA chính xác của model nền,
có thể bỏ `--allow-unpinned-revision`:

```powershell
python recovery/qlora_v2/restore.py `
  --llama-cpp-dir C:\tools\llama.cpp
```

Luồng thực hiện tuần tự:

1. tải adapter nếu local chưa có và đã cấu hình repository;
2. kiểm tra SHA-256, base-model identity và metadata;
3. tải đúng snapshot `Qwen/Qwen2.5-7B-Instruct`;
4. nạp base BF16 trên CPU, nạp PEFT adapter và `merge_and_unload()`;
5. lưu model Hugging Face đã merge;
6. chuyển sang GGUF F16 rồi lượng tử hóa Q8_0;
7. sinh Modelfile và chạy `ollama create qwen-qlora-rag-sft:latest`.

Model Hugging Face đã merge và GGUF F16 trung gian nằm trong
`model/qlora_v2/build/`. GGUF Q8_0 cùng Modelfile triển khai cuối nằm trong
`model/qlora_v2/runtime/`. Công cụ từ chối ghi đè bất kỳ đầu ra nào đã tồn tại.

Chỉ cần model Hugging Face đã merge:

```powershell
python recovery/qlora_v2/restore.py --skip-gguf --skip-ollama
```

Chỉ xem kế hoạch, không tải hoặc merge:

```powershell
python recovery/qlora_v2/restore.py --dry-run --allow-unpinned-revision
```

## Có nên commit adapter vào Git?

Không commit `adapter_model.safetensors` bằng Git thường. File khoảng 154 MiB,
vượt giới hạn 100 MiB thường gặp của Git hosting và làm repository phình lâu dài.
Repository này giữ runtime trong `model/` và hai thư mục trọng số
`recovery/phobert/checkpoint/`, `recovery/qlora_v2/adapter/` trong `.gitignore`.

Nên commit bình thường:

- `recovery/qlora_v2/restore.py`, chứa logic và entry point recovery;
- lệnh CLI điều phối tới script;
- manifest, danh sách file và SHA-256;
- tài liệu phục hồi.

Nên lưu trọng số bằng một trong các cách:

1. Hugging Face model repository riêng tư/công khai, có commit SHA — khuyến nghị;
2. GitHub Release hoặc object storage có version và checksum;
3. Git LFS nếu tổ chức đã có quota, retention và backup phù hợp.

Không đưa access token hoặc URL có credential vào manifest hay Git.

## Giới hạn kiểm chứng hiện tại

Luồng đã được triển khai nhưng chưa chạy download, merge, chuyển GGUF hoặc import
Ollama trên máy hiện tại. Chỉ nên công bố model phục hồi thành công sau khi máy
đích hoàn tất toàn bộ lệnh và kiểm tra inference đối chiếu.
