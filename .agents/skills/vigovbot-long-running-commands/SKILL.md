---
name: vigovbot-long-running-commands
description: Run long ViGovBot installs, model downloads, embedding jobs and benchmarks with completion-oriented waiting and minimal log reads. Use when a command is expected to take significant time or returns a running session.
---

# Chờ lệnh dài mà không đọc log liên tục

Trước khi chạy, xác định kết quả cần có, thời gian dự kiến nếu biết và timeout
hợp lý cho công việc. Với task lớn, ghi lệnh, thời điểm bắt đầu, nơi lưu artifact
và stage trong `docs/project/current-stage.md`. Sau khi công cụ trả session ID,
ghi ID để phiên hiện tại có thể tiếp tục chờ; ID có thể hết hiệu lực ở phiên mới.

## Cách chờ

- Chạy lệnh một lần. Ưu tiên công cụ có thông báo hoàn tất tự động.
- Nếu công cụ trả session đang chạy và không có thông báo hoàn tất, dùng thao
  tác chờ của chính session với khoảng chờ dài nhất phù hợp giới hạn công cụ
  và yêu cầu phản hồi người dùng (thường tối đa 60 giây mỗi lần).
- Trong lúc chờ, không gọi Get-Content/tail, tìm log, đọc artifact dở dang hoặc
  gọi kiểm tra mỗi vài giây. Chỉ chờ trạng thái hoàn tất; giới hạn output trả về.
  Nếu chờ trả trạng thái running, tiếp tục chờ, không phân tích log tiến độ.
- Nếu functions.exec trả `Script running with cell ID`, dùng functions.wait
  cho cell đó; nếu exec_command trả session_id, dùng write_stdin với chars rỗng.
  Không gọi wait khi không có cell đang chạy. Không chạy lại lệnh vì chưa có output.
- Có thể gửi cập nhật ngắn rằng vẫn đang chờ mà không đọc log; tiếp nhận yêu cầu
  mới và hủy khi người dùng yêu cầu. Không chặn một thao tác chờ quá 60 giây.

## Hoàn tất hoặc lỗi

Sau khi hoàn tất, đọc exit code và tóm tắt output một lần, kiểm tra artifact cần
thiết. Nếu thất bại, đọc trích đoạn lỗi liên quan rồi lưu nhật ký lỗi và sửa
nguyên nhân trước khi thử lại. Không tự động retry vô hạn.

Chỉ kiểm tra sớm khi công cụ báo lỗi, đến timeout đã chọn, cần tương tác nhập
liệu hoặc người dùng yêu cầu chẩn đoán tiến độ. Không kết luận treo vì log im lặng.
Không giết process hoặc khởi động job trùng chỉ vì chờ lâu.
Server web là dịch vụ chạy liên tục: kiểm tra readiness một lần rồi giữ session,
không chờ server tự kết thúc và không theo dõi log liên tục.

Quy trình này giảm lượt đọc log; skill không tự cung cấp cơ chế đánh thức agent
khi process hoàn tất. Nếu công cụ thiếu thông báo hoàn tất, vẫn cần lượt chờ
trạng thái thưa để biết process đã kết thúc.
