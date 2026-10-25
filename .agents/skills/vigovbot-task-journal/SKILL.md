---
name: vigovbot-task-journal
description: Cập nhật hồ sơ tiếng Việt khi chỉnh sửa quan trọng làm thay đổi hệ thống hoặc vận hành ViGovBot; không dùng cho báo cáo, dọn dẹp, kiểm tra hay chỉnh sửa nhỏ.
---

# Nhật ký thay đổi quan trọng ViGovBot

Chỉ áp dụng khi thay đổi ít nhất một nội dung sau:

- kiến trúc, package, CLI hoặc hợp đồng công khai;
- luồng runtime, triển khai, Docker, GPU hoặc cache dùng chung;
- cấu hình nguồn ảnh hưởng nhiều luồng;
- dữ liệu nguồn, huấn luyện hoặc đánh giá làm đổi khả năng hệ thống;
- cơ chế retrieval, generation, API hoặc bảo mật ảnh hưởng kết quả vận hành.

Không áp dụng chỉ vì công việc nhiều bước hoặc mất nhiều thời gian. Không ghi hồ
sơ cho báo cáo/phân tích thuần túy, dọn dẹp, đo dung lượng, chạy kiểm tra, sửa tài
liệu nhỏ, typo, định dạng hoặc lỗi công cụ không ảnh hưởng hệ thống.

## Hồ sơ

- `docs/project/requests.md`: mục tiêu thay đổi quan trọng đang thực hiện.
- `docs/project/current-stage.md`: trạng thái hệ thống hiện tại, không chứa lịch sử.
- `docs/project/implementation-history.md`: các mốc hệ thống đã hoàn tất.
- `docs/project/failure-journal.md`: chỉ giữ sự cố vận hành hoặc lỗi thiết kế có
  ảnh hưởng và bài học phòng ngừa còn giá trị.

## Cách cập nhật

Mỗi mục chỉ gồm `Mục tiêu`, `Thực hiện`, `Kết quả`. Gộp các chỉnh sửa cùng một
outcome thành một mốc; không tạo ID cho từng yêu cầu nhỏ. Ghi đường dẫn hoặc lệnh
kiểm chứng khi cần, không chép diff, log dài hay diễn giải quá trình.

Cập nhật hồ sơ khi bắt đầu và khi kết thúc một chỉnh sửa quan trọng. Chỉ ghi kết
quả đã kiểm chứng; nêu rõ phần chưa kiểm chứng. Không lưu bí mật, dữ liệu cá nhân,
giá trị `.env`, checkpoint hoặc artifact lớn trong `docs/`.
