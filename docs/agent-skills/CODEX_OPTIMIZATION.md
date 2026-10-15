# Tối ưu Codex có kiểm chứng

Luồng mặc định: `context-navigation` khi chưa rõ phạm vi → planning nếu nhiều
bước → minimal diff → verification → handoff khi chuyển phiên. Kiểm soát token
nằm trong context-navigation khi context lớn hoặc được yêu cầu và không được làm
giảm correctness.

AGENTS giữ quy tắc chung và routing; workflow chi tiết nằm trong từng skill để
không nạp toàn bộ catalog. Giới hạn log tại nguồn, báo summary và chỉ mở rộng
đoạn lỗi cần thiết. Mọi tuyên bố tiết kiệm token cần telemetry thực.
