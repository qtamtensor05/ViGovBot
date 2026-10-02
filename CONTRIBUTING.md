# Quy trình phát triển

Tài liệu này quy định yêu cầu tối thiểu đối với issue, commit, pull request và
artifact thí nghiệm được đưa vào repository.

## Phạm vi thay đổi

Mỗi issue mô tả vấn đề, phạm vi và tiêu chí hoàn thành có thể kiểm chứng.
Chia PR theo một mục tiêu; tránh gộp đổi schema, đổi thuật toán và benchmark
khác cấu hình vào cùng một PR. Dùng tiền tố commit `feat:`, `fix:`, `refactor:`,
`test:` hoặc `docs:` cùng mô tả hành vi cụ thể.

## Điều kiện trước khi merge

1. Chạy test offline, Ruff và `pip check` theo [hướng dẫn môi trường](docs/environments.md).
2. Nếu sửa generator, sinh lại notebook và bảo đảm không lưu output/thông tin đăng nhập.
3. Nếu sửa schema/artifact, tăng version phù hợp, kiểm thử dữ liệu lỗi và cập nhật migration.
4. Nếu sửa retrieval/prompt/model, lưu benchmark cùng corpus/model revision và cấu hình.
5. Mô tả kết quả kiểm chứng, phạm vi chưa kiểm chứng và cách quay lại phiên bản cũ trong PR.

## Dữ liệu, bí mật và giấy phép

Không commit dữ liệu riêng, trọng số, `.env` hoặc kết quả lớn. Fixture nhỏ có
chủ đích đặt trong `examples/` hoặc `tests/`. Không chỉnh manifest để hợp thức
hóa artifact chưa biết nguồn gốc. Chưa cấp giấy phép sử dụng lại mã nguồn;
xem [LICENSE](LICENSE) trước khi chia sẻ bên ngoài.
