# Tóm tắt refactor ViGovBot

## Chiến lược

Refactor dùng phương án tăng dần: giữ nguyên package `training/` đã được kiểm
chứng bằng GPU và các artifact trong `outputs/`, đồng thời dựng CLI/cấu hình sạch
trong namespace `vigovbot`. Chỉ di chuyển implementation sau khi có test tương
thích; không đổi tên, sao chép hoặc xóa checkpoint, adapter và dataset hiện có.

## Cấu trúc cuối

```text
ViGovBot/
├── pyproject.toml
├── src/vigovbot/
│   ├── cli/                 # CLI thống nhất, lazy import
│   ├── training/            # QLoRA, lifecycle, evaluation và reporting canonical
│   ├── server/              # web và /api/chat
│   ├── rag/                 # điều phối RAG
│   ├── evaluation/          # đánh giá RAG
│   └── ...
├── src/training/            # alias được đóng gói cho import cũ ngoài repository
├── training/                # alias tương thích cho lệnh/import cũ trong checkout
├── configs/
│   ├── ingestion/           # pipeline, OCR/parser và chunking
│   ├── rag/                 # inference web và các profile đánh giá
│   └── training/
│       ├── base.yaml
│       ├── environments/    # local, GPU, phần cứng
│       └── experiments/     # smoke, qlora_7b
├── scripts/                 # worker/lifecycle compatibility
├── tests/
├── docs/
├── Data/                    # ignored, không di chuyển
└── outputs/                 # ignored, không di chuyển
```

## Ánh xạ migration

| Đường dẫn/lệnh cũ | Đường dẫn/lệnh chuẩn | Trạng thái |
|---|---|---|
| `src/vigovbot/cli.py` | `src/vigovbot/cli/main.py` | Đã chuyển; import `vigovbot.cli:main` vẫn hoạt động |
| console script `vigovbot` | console script `vigov` | Đã thêm; alias cũ được giữ |
| `config.yaml`, `configs/pipeline.yaml` | `configs/ingestion/pipeline.yaml` | Đã hợp nhất cấu hình nguồn trùng vai trò |
| `configs/ingestion.yaml`, `configs/chunking.yaml` | `configs/ingestion/settings.yaml`, `configs/ingestion/chunking.yaml` | Đã nhóm theo pipeline ingestion |
| `rag_config.yaml`, `configs/inference.yaml` | `configs/rag/inference.yaml` | Đã hợp nhất entry point suy luận |
| `configs/rag*.yaml` | `configs/rag/evaluation*.yaml` | Đã nhóm các profile đánh giá RAG |
| `configs/base.yaml` | `configs/training/base.yaml` | Đã chuyển cấu hình QLoRA nền |
| `configs/local.yaml`, `configs/gpu*.yaml` | `configs/training/environments/` | Đã nhóm profile môi trường/phần cứng |
| `configs/smoke*.yaml` | `configs/training/experiments/` | Đã nhóm profile thí nghiệm |
| `training/*.py` | `src/vigovbot/training/` | Đã chuyển implementation; file cũ chỉ alias cùng module object |
| `scripts/start_qlora.ps1` | `vigov train start` | CLI dùng lifecycle Python; script cũ còn tương thích |
| `scripts/status_qlora.ps1` | `vigov train status` | CLI dùng lifecycle Python đa nền tảng |
| `scripts/stop_qlora.ps1` | `vigov train stop` | CLI xác minh PID, create-time và command trước khi dừng |
| không có | `vigov train logs` | CLI đọc log persisted và hỗ trợ `--follow` |

Business logic trùng lặp trong `training/*.py` đã được loại bỏ: implementation
chỉ còn tại `src/vigovbot/training/`; hai namespace cũ là alias cùng module object.
Các YAML nguồn cũ đã được hợp nhất theo miền; chuỗi `extends` trong training giữ
giá trị dùng chung mà không nhân đôi. Snapshot `config.yaml` trong run lịch sử
không bị di chuyển. Script PowerShell cũ chưa xóa vì còn là compatibility entry point.

## CLI và cấu hình

`vigov` có các nhóm `data`, `gpu`, `train`, `eval`, `report`, cùng `doctor` và
`dashboard`. Handler chỉ điều phối service/module hiện có và không import Torch,
Transformers hoặc model khi chỉ xem help/status.

Thứ tự cấu hình QLoRA là: giá trị base qua chuỗi `extends` → environment →
experiment → biến môi trường `VIGOVBOT_QLORA__...` → `--set` CLI. Giá trị CLI
luôn thắng biến môi trường. Cấu hình resolved tiếp tục được snapshot vào run bởi
`training.artifacts.snapshot_config`; các invariant NF4, double quant, LoRA,
batch/cadence, optimizer và Early Stopping được `training.config` kiểm tra.

## Baseline và kiểm chứng

- Baseline trước refactor: 145 test; 143 pass, 1 skip, 1 fail. Failure ở readiness
  vì profile RTX 5060 Ti tham chiếu layout `data/fintuning` không có trên checkout
  hiện tại; không phải regression mã nguồn.
- Sau toàn bộ refactor: full suite 156 test pass,
  1 optional skip; Ruff, compileall, `pip check`, `git diff --check` và AST của
  sáu script PowerShell lifecycle đều pass.
- `vigov --help`, help matrix, `vigov doctor`, `vigov data stats` và smoke
  `train start --dry-run` đã chạy bằng interpreter `env`, kể cả từ cwd ngoài repo.
  Editable install và alias import cũ-mới đều được kiểm chứng. Không chạy full
  training và không tải model.

## Tương thích và giới hạn

- `/api/chat`, Base/RAG/QLoRA provider, masking, Early Stopping, checkpoint/resume,
  metric và artifact cũ chưa bị thay đổi.
- Background lifecycle và TensorBoard dùng Python/psutil trên Windows và Linux;
  worker độc lập ghi PID/create-time/command, stdout/stderr và exit code. Các script
  PowerShell cũ vẫn được giữ cho quy trình lịch sử.
- Profile canonical RTX 5060 Ti đã trỏ đến layout SFT phẳng hiện có. Snapshot cấu
  hình trong các run lịch sử vẫn giữ nguyên provenance cũ.
- Dry-run thật đã xác nhận RTX 4050, CUDA 13.0, ba dataset hash và đúng 4 smoke
  step mà không tạo run/artifact. Chưa chạy GPU smoke/training trong refactor này.
- Lifecycle Linux có implementation và CI Ubuntu nhưng chưa được chạy trên máy
  Linux GPU thật trong phiên này; không xem test mock/CI source là GPU evidence.

## Lệnh GPU tiếp theo

Chỉ sau khi xác nhận đúng interpreter, dataset và GPU:

```powershell
vigov doctor
vigov data check --config configs/training/experiments/smoke.yaml
vigov gpu check
vigov train start --config configs/training/experiments/smoke.yaml --dry-run
vigov train smoke --config configs/training/experiments/smoke.yaml --approve
```

Không chạy `vigov train start` cho full profile cho đến khi smoke mới có artifact
PASS và profile dữ liệu đã được sửa bằng override rõ ràng.
