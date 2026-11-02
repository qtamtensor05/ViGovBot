# Ngôn ngữ: Tiếng Việt

Dùng fragment này khi người dùng yêu cầu đầu ra bằng tiếng Việt hoặc cung cấp
ghi chú chủ yếu bằng tiếng Việt mà không yêu cầu ngôn ngữ khác.

## Văn phong

- Viết rõ ràng, trang trọng và trực tiếp; ưu tiên câu chủ động khi xác định được
  chủ thể thực hiện.
- Mỗi đoạn tập trung vào một luận điểm. Câu đầu nêu ý chính, các câu sau lần
  lượt cung cấp bằng chứng, điều kiện, so sánh hoặc giới hạn.
- Tránh lối diễn đạt quảng bá như “đột phá”, “toàn diện”, “vượt trội” nếu không
  có số liệu và đối chứng trực tiếp hỗ trợ.
- Hiệu chỉnh mức độ khẳng định theo bằng chứng: phân biệt “cho thấy”, “gợi ý”,
  “có thể” và “chưa được xác minh”.

## Thuật ngữ kỹ thuật

- Giữ nguyên tên model, metric, API, lệnh, đường dẫn, định danh mã nguồn và cấu
  hình. Không dịch nội dung bên trong dấu backtick.
- Với thuật ngữ chuyên môn ít quen thuộc, dùng tên tiếng Việt trước và tên
  tiếng Anh trong ngoặc ở lần xuất hiện đầu tiên; sau đó dùng nhất quán một tên.
- Định nghĩa chữ viết tắt ở lần đầu xuất hiện, trừ các tên đã là định danh chính
  thức của dự án.
- Giữ nguyên giá trị số, đơn vị và độ chính xác từ nguồn. Không tự đổi dấu thập
  phân hoặc quy đổi đơn vị nếu việc đó làm khó đối chiếu artifact gốc.

## Ranh giới bằng chứng trong báo cáo dự án

- Phân biệt rõ: có trong mã nguồn, đã kiểm thử tự động, đã chạy cục bộ, đã xác
  minh trên trình duyệt hoặc phần cứng, và đã triển khai. Không suy diễn trạng
  thái mạnh hơn từ trạng thái yếu hơn.
- Chỉ ghi “hoàn thành” khi artifact, kết quả kiểm thử hoặc trạng thái runtime
  tương ứng đã được xác minh. Nếu hồ sơ còn ghi “đang chạy”, phải đối chiếu đầu
  ra cuối trước khi kết luận.
- Nêu nguồn của số liệu bằng đường dẫn artifact, báo cáo hoặc lần chạy khi nguồn
  đã được cung cấp. Không tạo số liệu, mốc thời gian hay kết quả còn thiếu.
- Khi thiếu bằng chứng, chèn một placeholder rõ ràng và liệt kê dưới mục
  `Giả định hoặc dữ liệu còn thiếu` thay vì điền nội dung suy đoán.

## Cấu trúc trình bày

- Giữ cấu trúc do người dùng hoặc cơ sở đào tạo yêu cầu. Nếu chưa có mẫu, chọn
  cấu trúc phù hợp với báo cáo kỹ thuật: bối cảnh và mục tiêu, kiến trúc/phương
  pháp, triển khai, thực nghiệm, kết quả, giới hạn và hướng phát triển.
- Với nhật ký hoặc mốc triển khai, ưu tiên ba phần `Mục tiêu`, `Thực hiện`,
  `Kết quả`; không ép cấu trúc này lên toàn bộ báo cáo nếu không phù hợp.
