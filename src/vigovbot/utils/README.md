# Module `vigovbot.utils`

## Trách nhiệm

Module chứa tiện ích hạ tầng không thuộc domain RAG: hàm băm dữ liệu/file, nhận
diện trạng thái file và hỗ trợ runtime Colab. Logic quản lý lượt chạy nằm tại
`vigovbot.experiments`; một số tên được re-export để tương thích.

## Thành phần

| File | Đầu vào | Đầu ra |
|---|---|---|
| `helpers.py` | Giá trị JSON hoặc đường dẫn file | SHA-256 và định danh trạng thái file |
| `colab_runtime.py` | Tên model, URL Ollama | Kiểm tra executable/service và trạng thái model |
| `build_colab_notebooks.py` | Template notebook trong mã nguồn | Notebook được sinh tại `ipynb/` |

## Ràng buộc

Các helper phải giữ tính xác định và không chứa logic nghiệp vụ. Runtime Colab
phân biệt Ollama cục bộ với endpoint từ xa; endpoint từ xa không kích hoạt cài đặt
hoặc khởi chạy tiến trình trên máy. Notebook là artifact sinh tự động và không
được chứa output hoặc thông tin xác thực.

[Kiến trúc hệ thống](../../../docs/architecture.md) · [Quy trình phát triển](../../../CONTRIBUTING.md)
