# Hệ thống tài liệu ViGovBot

Thư mục này chứa tài liệu kỹ thuật và tài liệu quản trị dự án. Tài liệu được phân
loại theo mục đích để tránh lặp lại hướng dẫn vận hành trong các tài liệu kiến trúc.

## Phân loại tài liệu

| Nhóm | Tài liệu | Phạm vi |
|---|---|---|
| Tổng quan | [README dự án](../README.md) | Trạng thái, yêu cầu, cài đặt và giao diện CLI |
| Vận hành | [Triển khai RAG](trien-khai-rag-co-ban.md) | Tạo corpus, thực hiện truy vấn và chạy đánh giá |
| Kiến trúc | [Kiến trúc hệ thống](architecture.md) | Thành phần, luồng dữ liệu, phụ thuộc và hợp đồng artifact |
| Dữ liệu | [Embedding và corpus](../EMBEDDING.md) | Định dạng pack, revision mô hình, hợp nhất và giới hạn tài nguyên |
| Môi trường | [Môi trường và khả năng tái lập](environments.md) | Dependency, lock file, nền tảng hỗ trợ và kiểm chứng |
| Tương thích | [Hướng dẫn migration](migration.md) | Namespace cũ, cấu hình cũ và corpus không có manifest |
| Quản trị | [Trạng thái và lộ trình](roadmap.md) | Năng lực hiện tại, mốc phát triển và tiêu chí nghiệm thu |
| Kiểm chứng | [Báo cáo kiểm chứng](verification.md) | Phạm vi, môi trường và kết quả kiểm tra đã ghi nhận |
| Phát triển | [Quy trình đóng góp](../CONTRIBUTING.md) | Yêu cầu đối với issue, commit và pull request |

## Quy ước duy trì

- `README.md` ở thư mục gốc là điểm vào duy nhất cho cài đặt và vận hành cơ bản.
- Tài liệu kiến trúc mô tả ranh giới và hợp đồng, không sao chép hướng dẫn cài đặt.
- Tài liệu vận hành cung cấp lệnh thực thi hoàn chỉnh và điều kiện tiên quyết.
- Báo cáo kiểm chứng ghi nhận kết quả tại một thời điểm, không đại diện cho trạng thái hiện thời.
- README trong module chỉ mô tả trách nhiệm của module và dẫn chiếu về tài liệu trung tâm.
