# GOLDEN DATASET MASTER RULES
## Quy chuẩn xây dựng bộ dữ liệu QA cho Fine-tuning và đánh giá RAG trên thủ tục hành chính Việt Nam

**Phiên bản:** 1.0  
**Phạm vi:** Toàn bộ dữ liệu thủ tục hành chính được cung cấp qua nhiều batch  
**Nguồn dữ liệu:** PDF gốc và metadata/chunks tương ứng  
**Định dạng:** JSONL theo Golden Schema do người dùng cung cấp  
**Mục tiêu:** Xây dựng bộ dữ liệu có độ bao phủ kiến thức cao, đa dạng câu hỏi, có dẫn chứng và có thể kiểm chứng.

---

# 1. MỤC TIÊU TỔNG THỂ

Xây dựng Golden Dataset phục vụ hai mục đích chính:

1. **Supervised Fine-tuning (SFT):** Huấn luyện mô hình ngôn ngữ trả lời câu hỏi liên quan đến thủ tục hành chính.
2. **Shared QA Benchmark:** Sử dụng chung bộ test để đánh giá Base Model, Fine-tuned Model, RAG và RAG kết hợp Fine-tuned Model.

Dữ liệu được cung cấp theo nhiều đợt (batch). Mỗi batch có thể bao gồm từ 10 đến 100 PDF và metadata tương ứng.

Số lượng batch không cố định.

Hệ thống phải có khả năng tiếp nhận và tích lũy dữ liệu qua nhiều lần xử lý mà không làm mất các kết quả đã được kiểm định.

## 1.1. Nguyên tắc cốt lõi

- Ưu tiên độ chính xác hơn số lượng.
- Ưu tiên độ bao phủ kiến thức hơn số lượng câu hỏi.
- Không bịa dữ liệu để đạt chỉ tiêu.
- Không tạo câu hỏi trùng lặp về mặt ngữ nghĩa chỉ để tăng số lượng.
- Không bỏ qua các điều kiện và ngoại lệ quan trọng.
- Mỗi đáp án phải có căn cứ từ tài liệu.
- Giữ nguyên tính nhất quán giữa các batch.
- Không để dữ liệu Train/Validation/Test bị rò rỉ.
- Không coi metadata là nguồn chính xác tuyệt đối nếu mâu thuẫn với PDF gốc.
- Không coi việc một chunk được tham chiếu là bằng chứng rằng toàn bộ kiến thức trong chunk đã được kiểm tra.

---

# 2. CẤU TRÚC DỮ LIỆU ĐẦU VÀO

Mỗi batch có thể cung cấp:

1. Các file PDF chứa thủ tục hành chính.
2. Các file JSON metadata chứa thông tin thủ tục và các chunk.
3. Golden Schema JSONL mẫu, nếu đây là batch đầu tiên hoặc schema được cập nhật.
4. Manifest và kết quả xử lý của các batch trước, nếu có.

## 2.1. Quy tắc nhận diện thủ tục

Mỗi tài liệu cần được xác định bằng:

- Mã thủ tục.
- Tên thủ tục đầy đủ.
- Lĩnh vực.
- Nguồn PDF.
- Định danh tài liệu.
- Phiên bản hoặc dấu vết nguồn nếu có.
- Danh sách chunk tương ứng.

Ưu tiên sử dụng mã thủ tục làm khóa nhận diện.

Tuy nhiên, không được mặc định hai tài liệu có mã giống nhau là hoàn toàn đồng nhất về nội dung nếu chúng thuộc các phiên bản khác nhau.

Cần kiểm tra thêm tên, nội dung và dấu vết phiên bản.

## 2.2. Ghép PDF và metadata

Thực hiện đối chiếu theo thứ tự:

1. Mã thủ tục.
2. Tên thủ tục.
3. Định danh tài liệu.
4. Nội dung và thông tin nhận diện trong tài liệu.

Không ghép PDF và metadata chỉ vì hai file nằm cùng vị trí trong danh sách ZIP.

Nếu không tìm được cặp dữ liệu tương ứng:

- Đánh dấu tài liệu chưa được ghép.
- Không tự tạo chunk ID.
- Không tạo dẫn chứng giả.
- Ghi nhận lỗi để xử lý sau.

## 2.3. Nguồn sự thật

Thứ tự ưu tiên khi xác minh nội dung:

1. PDF gốc.
2. Văn bản trích xuất từ PDF đã được đối chiếu.
3. Nội dung metadata/chunk tương ứng.

Nếu PDF và metadata mâu thuẫn:

- Ưu tiên PDF để xác minh đáp án.
- Ghi nhận vị trí mâu thuẫn.
- Không âm thầm sửa metadata.
- Không tạo đáp án có dẫn chứng từ một chunk sai lệch mà không ghi nhận vấn đề.

Không tự động áp dụng thông tin pháp luật bên ngoài tài liệu để thay đổi Golden Answer.

Nếu cần đánh giá tính cập nhật của quy định pháp luật, thực hiện dưới dạng một quy trình kiểm định riêng.

---

# 3. QUY TRÌNH XỬ LÝ THEO BATCH

Mỗi batch phải trải qua các giai đoạn sau:

## Giai đoạn 1: Inspection

- Giải nén và kiểm kê tất cả file.
- Kiểm tra PDF có đọc được hay không.
- Kiểm tra metadata có parse được hay không.
- Ghép PDF với metadata.
- Xác định lĩnh vực và mã thủ tục.
- Phát hiện tài liệu trùng lặp.
- Phát hiện tài liệu thiếu trường quan trọng.
- Thống kê số trang, chunk, mục nội dung và các nhánh điều kiện.

## Giai đoạn 2: Knowledge Extraction

Đọc toàn bộ PDF và xây dựng danh sách các đơn vị kiến thức có thể kiểm chứng.

Không chỉ dựa vào tên section hoặc số lượng chunk.

Mỗi đơn vị kiến thức có thể là:

- Một thuộc tính.
- Một quy định.
- Một điều kiện.
- Một trường hợp ngoại lệ.
- Một bước trong quy trình.
- Một loại giấy tờ.
- Một số lượng giấy tờ.
- Một quan hệ giữa nhiều quy định.
- Một trường hợp chỉ áp dụng cho nhóm đối tượng cụ thể.

## Giai đoạn 3: Case Generation

Sinh câu hỏi dựa trên các đơn vị kiến thức đã trích xuất.

Phải đảm bảo:

- Đúng thủ tục.
- Đúng phạm vi thông tin.
- Đúng điều kiện.
- Đúng loại câu hỏi.
- Có đáp án kỳ vọng phù hợp.
- Có thể xác minh từ nguồn.

## Giai đoạn 4: Grounding

Ánh xạ các câu hỏi và đáp án với:

- PDF nguồn.
- Mã thủ tục.
- Chunk liên quan.
- Các đoạn bằng chứng cần thiết.
- Citation.
- Sub-query nếu câu hỏi cần nhiều đoạn thông tin.

## Giai đoạn 5: Validation

Kiểm tra:

- Schema.
- Nội dung.
- Đáp án.
- Dẫn chứng.
- Độ bao phủ.
- Tính đa dạng.
- Trùng lặp.
- Rò rỉ dữ liệu.

## Giai đoạn 6: Export

Xuất dữ liệu theo Golden Schema và báo cáo kiểm định.

Mỗi batch phải có trạng thái xử lý rõ ràng:

- `pending`
- `processing`
- `validated`
- `quarantined`
- `completed`

Chỉ các case được kiểm định đạt yêu cầu mới được đưa vào tập dữ liệu chính.

---

# 4. QUY TẮC BAO PHỦ KIẾN THỨC

## 4.1. Các nội dung cần kiểm tra

Đọc đầy đủ các mục xuất hiện trong PDF, bao gồm nhưng không giới hạn:

1. Thông tin nhận diện thủ tục.
2. Mã và tên thủ tục.
3. Lĩnh vực.
4. Cấp thực hiện.
5. Đối tượng thực hiện.
6. Cơ quan có thẩm quyền.
7. Cơ quan trực tiếp thực hiện.
8. Cơ quan được ủy quyền.
9. Cơ quan phối hợp.
10. Trình tự thực hiện.
11. Các bước nghiệp vụ.
12. Thành phần hồ sơ.
13. Số lượng giấy tờ.
14. Bản chính và bản sao.
15. Mẫu đơn và tờ khai.
16. Các trường hợp hồ sơ khác nhau.
17. Điều kiện áp dụng.
18. Ngoại lệ.
19. Cách thức thực hiện.
20. Hình thức nộp hồ sơ.
21. Thời hạn giải quyết.
22. Phí và lệ phí.
23. Kết quả xử lý.
24. Căn cứ pháp lý.
25. Quy định liên quan.
26. Quan hệ giữa các mục.
27. Các giới hạn và điều kiện đặc biệt khác có trong tài liệu.

Danh sách trên không có nghĩa rằng mọi thủ tục đều phải có đầy đủ những mục này.

Chỉ tạo đáp án có căn cứ từ thông tin thực tế của tài liệu.

## 4.2. Bao phủ mệnh đề kiến thức

Một chunk có thể chứa nhiều mệnh đề độc lập.

Ví dụ:

Một chunk về thành phần hồ sơ có thể đề cập:

- Tờ khai nhập khẩu.
- Hóa đơn thương mại.
- Chứng từ vận tải.
- Giấy phép nhập khẩu.
- Điều kiện phải có giấy phép.
- Trường hợp được miễn nộp một số chứng từ.
- Quy định đối với khai báo bằng giấy.

Không được chỉ tạo một câu hỏi chung về thành phần hồ sơ rồi đánh dấu toàn bộ chunk đã được bao phủ.

Cần kiểm tra các mệnh đề quan trọng, đặc biệt là những mệnh đề có điều kiện.

## 4.3. Bao phủ nhánh điều kiện

Các trường hợp có điều kiện phải được nhận diện độc lập.

Ví dụ:

- Khi nhập khẩu.
- Khi xuất khẩu.
- Khi tái xuất.
- Khi thực hiện lần đầu.
- Khi nộp hồ sơ giấy.
- Khi thực hiện trực tuyến.
- Khi thuộc đối tượng đặc biệt.
- Khi được miễn giấy tờ.
- Khi phải bổ sung chứng từ.

Không được trộn các điều kiện của nhiều nhánh thành một câu trả lời chung gây sai lệch.

## 4.4. Câu hỏi tổng hợp

Cho phép tạo câu hỏi yêu cầu nhiều mệnh đề hoặc nhiều chunk.

Ví dụ:

"Đối với thủ tục X, cơ quan nào thực hiện, thời hạn bao lâu và phải nộp những loại phí nào?"

Câu hỏi này phải có đủ bằng chứng tương ứng cho từng ý.

Không sử dụng câu hỏi tổng hợp để thay thế hoàn toàn những câu hỏi kiểm tra điều kiện, ngoại lệ hoặc chi tiết quan trọng.

## 4.5. Chỉ số bao phủ

Cần thống kê tối thiểu:

- Tổng số đơn vị kiến thức được nhận diện.
- Số đơn vị đã có test case.
- Số đơn vị chưa được kiểm tra.
- Tổng số nhánh điều kiện.
- Số nhánh điều kiện đã được kiểm tra.
- Tổng số chunk hợp lệ.
- Số chunk được tham chiếu.
- Những phần tài liệu không tạo được câu hỏi hợp lệ.

Chỉ số:

`Knowledge Coverage = Covered Knowledge Units / Total Eligible Knowledge Units`

`Condition Coverage = Covered Condition Branches / Total Eligible Condition Branches`

`Chunk Coverage = Referenced Chunks / Total Eligible Chunks`

Các chỉ số này phải được tính từ danh sách đơn vị kiến thức thực tế, không được tự ước lượng hoặc suy ra chỉ từ số lượng câu hỏi.

Nội dung trùng lặp, trang bìa, phần định dạng và đoạn không mang kiến thức kiểm thử cần được loại khỏi mẫu số nếu có lý do rõ ràng.

---

# 5. QUY TẮC SỐ LƯỢNG CÂU HỎI

Không áp dụng một số câu hỏi cố định cho tất cả thủ tục.

Số lượng câu hỏi phụ thuộc vào:

- Số lượng thông tin độc lập.
- Số trường hợp hồ sơ.
- Số nhánh điều kiện.
- Số ngoại lệ.
- Số bước nghiệp vụ.
- Mức độ phức tạp của các quan hệ giữa thông tin.
- Khả năng tạo câu hỏi khác nhau về ý nghĩa.
- Mức độ cần thiết của các trường hợp kiểm thử đặc biệt.

## 5.1. Thủ tục đơn giản

Tạo ít câu hỏi hơn nhưng phải bao phủ được nội dung trọng yếu.

Không cố tạo thêm câu hỏi nếu chỉ có thể viết lại những câu đã có bằng từ đồng nghĩa.

## 5.2. Thủ tục phức tạp

Tạo nhiều câu hỏi hơn để kiểm tra:

- Các tình huống áp dụng.
- Những nhánh nghiệp vụ khác nhau.
- Điều kiện.
- Ngoại lệ.
- Các loại giấy tờ.
- Sự khác nhau giữa các trường hợp.
- Quan hệ giữa nhiều quy định.

## 5.3. Quy tắc dừng sinh câu hỏi

Dừng sinh thêm khi:

- Các mệnh đề kiến thức quan trọng đã được bao phủ.
- Các nhánh điều kiện đã có case phù hợp.
- Những hành vi kiểm thử cần thiết đã được đại diện ở mức hợp lý.
- Câu hỏi mới chỉ lặp lại ý nghĩa của câu cũ.
- Không còn đủ căn cứ để tạo thêm case hợp lệ.

Không tăng số lượng bằng cách thay những cụm từ nhỏ như:

- "Bao lâu?"
- "Mấy ngày?"
- "Thời hạn bao nhiêu?"
- "Mất bao nhiêu ngày?"

nếu chúng thực chất kiểm tra cùng một ý và không bổ sung giá trị đánh giá.

---

# 6. QUY TẮC ĐA DẠNG HÓA CÂU HỎI

Câu hỏi phải phản ánh cách người dùng thực tế tương tác với chatbot thủ tục hành chính.

## 6.1. Các hình thức diễn đạt

Phải đa dạng hóa bằng nhiều cách:

1. Gọi tên thủ tục đầy đủ.
2. Dùng tên rút gọn đủ phân biệt.
3. Dùng mã thủ tục.
4. Mô tả nhu cầu thực tế của người dân.
5. Mô tả nhu cầu của tổ chức hoặc doanh nghiệp.
6. Sử dụng từ đồng nghĩa.
7. Sử dụng văn nói tự nhiên.
8. Sử dụng cách hỏi ngắn gọn.
9. Sử dụng cách hỏi nhiều mệnh đề.
10. Câu hỏi dài có thông tin phụ.
11. Câu hỏi sai chính tả.
12. Câu hỏi thiếu dấu.
13. Câu hỏi có viết tắt.
14. Câu hỏi có tiền đề sai.
15. Câu hỏi thiếu dữ kiện.
16. Câu hỏi cần tổng hợp thông tin từ nhiều mục.
17. Câu hỏi diễn đạt chưa chính xác nhưng vẫn nhận diện được ý định.

Không bắt buộc mọi thủ tục phải có đủ tất cả hình thức trên.

Chỉ chọn những dạng có giá trị đánh giá phù hợp.

## 6.2. Nhận diện thủ tục

Vì hệ thống chứa nhiều thủ tục hành chính, câu hỏi single-turn phải có đủ ngữ cảnh để nhận diện thủ tục.

Ví dụ không hợp lệ nếu đứng độc lập:

"Thời hạn giải quyết là bao lâu?"

Ví dụ hợp lệ:

"Thủ tục hải quan đối với khí nhập khẩu qua đường ống chuyên dụng mất bao lâu để giải quyết?"

"Có thể cho tôi biết thời hạn giải quyết của mã thủ tục 1.000005 không?"

"Khi làm hải quan cho khí đi qua đường ống chuyên dụng thì thường mất mấy ngày?"

Tên rút gọn chỉ hợp lệ khi đủ khả năng nhận diện thủ tục trong tập dữ liệu.

Nếu cách gọi rút gọn có thể đồng thời chỉ nhiều thủ tục, phải bổ sung dấu hiệu phân biệt hoặc chuyển sang case cần hỏi lại.

## 6.3. Tránh cấu trúc máy móc

Không được thêm cùng một tiền tố vào tất cả câu hỏi.

Ví dụ cần tránh:

"Đối với thủ tục [TÊN], ..."

"Đối với thủ tục [TÊN], ..."

"Đối với thủ tục [TÊN], ..."

Thay vào đó, sử dụng cách diễn đạt linh hoạt.

Không phân bổ biến thể diễn đạt bằng cách hoán đổi ngẫu nhiên các tiền tố rồi coi đó là đa dạng ngữ nghĩa.

## 6.4. Câu hỏi nhiễu

Có thể bổ sung thông tin không liên quan nhưng không làm thay đổi đáp án đúng.

Ví dụ:

"Tôi đang chuẩn bị hồ sơ cho đơn vị và cần hoàn tất trong tuần này. Cho hỏi thủ tục X mất bao lâu theo quy định?"

Không được thêm thông tin phụ khiến câu hỏi trở nên mâu thuẫn hoặc không thể xác định thủ tục, trừ khi đó là mục tiêu kiểm thử.

## 6.5. Sai chính tả và thiếu dấu

Sai chính tả phải mô phỏng lỗi thực tế:

- Thiếu dấu.
- Gõ nhầm ký tự.
- Nhầm dấu thanh.
- Viết tắt thông dụng.
- Sai một số từ không làm mất hoàn toàn ý nghĩa.

Không sinh chuỗi ký tự vô nghĩa chỉ để tăng độ khó.

---

# 7. PHÂN LOẠI HÀNH VI KIỂM THỬ

Sử dụng taxonomy đúng theo Golden Schema đầu vào.

Không tự ý thay đổi giá trị enum.

Nếu schema dùng tên hoặc cấu trúc khác, ánh xạ các nhóm dưới đây vào trường hợp lệ tương ứng.

## A. Trả lời đủ

Nguồn có đủ thông tin để trả lời toàn bộ câu hỏi.

Yêu cầu:

- Trả lời đúng.
- Không thiếu ý quan trọng.
- Không bổ sung thông tin ngoài nguồn.

## B. Trả lời một phần

Một phần yêu cầu có căn cứ, phần còn lại không có đủ thông tin.

Ví dụ:

"Thủ tục X mất bao lâu và người phụ trách trực tiếp có số điện thoại nào?"

Nếu tài liệu có thời hạn nhưng không có số điện thoại, chỉ trả lời phần thời hạn và nêu rõ phần không được cung cấp.

Không tự suy luận số điện thoại.

## C. Sửa tiền đề

Người dùng đưa ra nhận định không đúng.

Ví dụ:

"Thủ tục X có lệ phí 50.000 đồng đúng không?"

Nếu nguồn quy định mức khác, đáp án phải sửa lại chính xác.

Không đồng tình với tiền đề sai.

## D. Hỏi lại

Câu hỏi thiếu dữ kiện để xác định đúng thủ tục hoặc trường hợp áp dụng.

Ví dụ:

"Tôi cần làm thủ tục về giấy phép xuất khẩu thì chuẩn bị hồ sơ gì?"

Nếu nhiều thủ tục phù hợp, phải hỏi lại để làm rõ.

Không tự chọn một thủ tục bất kỳ.

## E. Từ chối có căn cứ

Câu hỏi không có căn cứ trả lời trong phạm vi nguồn.

Ví dụ:

"Hãy cho biết số điện thoại cá nhân của cán bộ xử lý thủ tục X."

Nếu tài liệu không cung cấp, không được bịa hoặc suy đoán.

Cần phân biệt:

- Nguồn không đề cập.
- Nguồn xác nhận không có.
- Nội dung vượt ngoài phạm vi tài liệu.

## F. Multi-hop

Câu hỏi cần kết hợp nhiều thông tin.

Ví dụ:

"Thủ tục X do cơ quan nào thực hiện, kết quả là gì và thời hạn giải quyết bao lâu?"

Yêu cầu ánh xạ đủ các chunk cần thiết.

Không gắn nhãn multi-hop nếu toàn bộ câu trả lời chỉ cần một mệnh đề đơn giản.

## G. Multi-turn

Hội thoại phải có lịch sử rõ ràng và có ý nghĩa thực tế.

Các trường hợp cần kiểm tra:

- Hỏi tiếp về cùng thủ tục.
- Hỏi tiếp về hồ sơ.
- Hỏi tiếp về thời hạn hoặc lệ phí.
- Sửa tên thủ tục.
- Chuyển chủ đề sang thủ tục khác.
- Theo dõi đối tượng hoặc trường hợp áp dụng.
- Giải quyết tham chiếu như "thủ tục đó", "trường hợp này".
- Xử lý sự thay đổi điều kiện giữa các lượt.

Ví dụ:

User: "Tôi muốn tìm hiểu thủ tục X."

Assistant: "Bạn muốn hỏi về nội dung nào?"

User: "Thời hạn giải quyết và lệ phí là bao nhiêu?"

Trong trường hợp này, câu hỏi cuối có thể ngắn vì lịch sử đã xác định thủ tục.

Không tạo hội thoại bằng cách ghép các lượt không liên quan.

Không sử dụng câu trả lời giả định của Assistant trong history nếu câu trả lời đó sai hoặc không có căn cứ, trừ khi đang kiểm tra khả năng sửa lỗi hội thoại.

## H. Robustness và Security

Bao gồm:

- Sai chính tả.
- Thiếu dấu.
- Viết tắt.
- Ngôn ngữ không chuẩn.
- Nhiễu.
- Câu hỏi dài.
- Prompt injection.
- Chỉ dẫn giả mạo nằm trong ngữ cảnh truy xuất.

Prompt injection chỉ được sử dụng để kiểm tra khả năng tuân thủ hướng dẫn hệ thống và sử dụng bằng chứng đáng tin cậy.

Không để nội dung injection trở thành căn cứ cho Golden Answer.

## 7.1. Các nhóm có thể giao nhau

Ví dụ:

Một câu hỏi có thể đồng thời là:

- Multi-turn.
- Multi-hop.
- Sai chính tả.
- Trả lời một phần.

Nếu schema hỗ trợ nhãn chính và nhãn phụ thì lưu riêng.

Nếu không hỗ trợ, không tự tạo trường mới khi xuất Golden JSONL.

Có thể lưu phân loại phân tích bổ sung trong báo cáo hoặc manifest riêng.

---

# 8. QUY TẮC TẠO GOLDEN ANSWER

## 8.1. Tính chính xác

Mỗi Golden Answer phải được xác minh từ PDF gốc.

Không được:

- Bịa đáp án.
- Tự thêm căn cứ pháp lý.
- Tự đoán chi phí.
- Tự suy luận thời hạn.
- Trộn thông tin giữa nhiều thủ tục.
- Loại bỏ điều kiện có ảnh hưởng đến câu trả lời.
- Biến trường dữ liệu trống thành một khẳng định phủ định.

## 8.2. Độ đầy đủ

Đáp án phải bao phủ toàn bộ các ý mà câu hỏi yêu cầu và có căn cứ.

Ví dụ:

Nếu câu hỏi yêu cầu cả thời hạn và lệ phí, đáp án phải cung cấp cả hai nếu tài liệu có đủ.

Không chỉ trả lời một ý rồi đánh dấu là trả lời đủ.

## 8.3. Ngắn gọn và chính xác

Không sao chép nguyên cả chunk nếu chỉ cần trích xuất một thuộc tính.

Ví dụ:

Question:
"Thời hạn giải quyết của thủ tục X là bao lâu?"

Golden Answer:
"Thời hạn giải quyết là 1 ngày."

Không cần sao chép toàn bộ bảng cách thức thực hiện.

## 8.4. Điều kiện và ngoại lệ

Các thông tin có điều kiện phải giữ nguyên phạm vi áp dụng.

Ví dụ:

Nếu quy định chỉ yêu cầu giấy phép trong một số trường hợp thì không được trả lời rằng mọi trường hợp đều bắt buộc có giấy phép.

## 8.5. Câu hỏi không có đáp án

Không được viết một Golden Answer khẳng định thông tin không tồn tại nếu tài liệu chỉ đơn giản không nhắc đến.

Cách xử lý đúng:

"Tài liệu được cung cấp không nêu thông tin này."

Không được chuyển câu trên thành:

"Không có yêu cầu này."

Hai ý nghĩa khác nhau.

---

# 9. QUY TẮC GROUNDING VÀ CITATION

Mỗi case phải ánh xạ theo Golden Schema được cung cấp.

Các trường có thể bao gồm:

- `ground_truth_context_ids`
- `ground_truth_sub_queries`
- `expected_citations`
- `ground_truth_standalone_query`
- `chat_history`
- `expected_answer`
- Những trường khác được định nghĩa trong schema.

Tên trường thực tế phải lấy từ schema, không được mặc định rằng các tên trên luôn tồn tại.

## 9.1. Ground Truth Context

Chỉ tham chiếu chunk thực sự chứa bằng chứng.

Không thêm các chunk không liên quan để tăng Recall@K.

Nếu đáp án cần nhiều chunk, ghi nhận đầy đủ các chunk cần thiết.

## 9.2. Sub-query

Chỉ tạo sub-query khi có ý nghĩa truy xuất.

Ví dụ câu hỏi:

"Thủ tục X do ai thực hiện, thời hạn và lệ phí bao nhiêu?"

Có thể tách thành:

- Cơ quan thực hiện của thủ tục X.
- Thời hạn giải quyết của thủ tục X.
- Phí và lệ phí của thủ tục X.

Không tạo sub-query trùng nhau hoặc không đóng góp vào câu trả lời.

## 9.3. Standalone Query

Đối với single-turn, câu hỏi phải có đủ ngữ cảnh nhận diện thủ tục.

Đối với multi-turn, standalone query phải tái hiện đúng ý định sau khi kết hợp lịch sử hội thoại.

Không lấy nguyên câu hỏi thiếu ngữ cảnh làm standalone query.

## 9.4. Citation

Citation phải xác định được nguồn thực tế.

Không tạo ID tài liệu, số trang hoặc chunk không tồn tại.

Nếu schema yêu cầu citation nhưng nguồn không đủ, đưa case vào danh sách cần xử lý thay vì bịa citation.

---

# 10. CHIA DỮ LIỆU TRAIN / VALIDATION / TEST

## 10.1. Mục đích

Dữ liệu phục vụ:

- Fine-tuning.
- Theo dõi quá trình huấn luyện.
- Đánh giá Base Model.
- Đánh giá Fine-tuned Model.
- Đánh giá RAG.
- Đánh giá RAG kết hợp Fine-tuned Model.

## 10.2. Tỷ lệ mục tiêu

Mục tiêu cho khoảng 3.000 Golden QA case:

| Tập | Số case mục tiêu | Mục đích |
|---|---:|---|
| Train pool | 2.000 | Nguồn tạo dữ liệu SFT |
| Test | 1.000 | Shared QA Benchmark |

Trong Train pool, tách khoảng 200–300 case làm Validation.

Như vậy:

- `train_sft.jsonl`: khoảng 1.700–1.800 case.
- `val_sft.jsonl`: khoảng 200–300 case.
- `test_golden.jsonl`: khoảng 1.000 case.

Số lượng thực tế phụ thuộc vào dữ liệu hợp lệ và khả năng phân chia.

Không được tăng số case bằng dữ liệu thiếu căn cứ chỉ để đạt con số mục tiêu.

## 10.3. Chia ở cấp thủ tục

Mặc định thực hiện phân chia theo nhóm thủ tục.

Không để cùng một thủ tục có mặt ở cả Train và Test.

Không để cùng một thủ tục có mặt ở cả Train-SFT và Validation-SFT.

Phải kiểm tra:

- Mã thủ tục.
- Tên thủ tục.
- Tài liệu trùng nội dung.
- Phiên bản tài liệu.
- Nhóm tài liệu thực chất thuộc cùng một thủ tục.

## 10.4. Cân bằng lĩnh vực

Train, Validation và Test phải giữ tỷ lệ lĩnh vực tương đương nhau trong giới hạn khả thi.

Thực hiện stratified group split ở cấp thủ tục.

Không chia ngẫu nhiên trực tiếp từng câu hỏi.

Cân bằng cần xét cả:

- Số thủ tục mỗi lĩnh vực.
- Số case mỗi lĩnh vực.
- Độ phức tạp thủ tục.
- Mức độ bao phủ kiến thức.
- Tỷ lệ các loại hành vi kiểm thử.

Không cố cân bằng bằng cách sao chép hoặc tạo biến thể gần trùng.

## 10.5. Lĩnh vực có ít thủ tục

Nếu một lĩnh vực chỉ có một thủ tục:

- Không chia các QA của thủ tục đó sang nhiều tập.
- Báo cáo rằng không thể đồng thời đại diện lĩnh vực đó ở mọi tập mà vẫn giữ quy tắc chống leakage.
- Chọn tập phù hợp theo chiến lược phân bổ tổng thể.
- Không tạo một thủ tục giả để cân bằng.

Nếu lĩnh vực chỉ có hai thủ tục, cân nhắc phân bổ giữa các tập theo ưu tiên đánh giá và huấn luyện, đồng thời báo cáo giới hạn đối với Validation nếu không đủ thủ tục.

## 10.6. Test bất biến

Sau khi chốt bộ Test chính thức:

- Không sử dụng QA Test để fine-tuning.
- Không sử dụng QA Test để tối ưu prompt.
- Không sử dụng QA Test để chọn checkpoint.
- Không sử dụng QA Test để điều chỉnh retriever.
- Không bổ sung case Train có nội dung gần trùng QA Test.
- Không thay đổi đáp án chuẩn nếu không có quy trình sửa lỗi được ghi nhận.

Nếu phát hiện lỗi trong Test, phải ghi lại phiên bản thay đổi và lý do.

## 10.7. Sử dụng PDF trong RAG

Các PDF tương ứng với Test có thể nằm trong knowledge base của RAG khi thực hiện đánh giá truy xuất tài liệu thông thường.

Điều này cho phép kiểm tra khả năng:

- Truy xuất tài liệu đúng.
- Truy xuất chunk liên quan.
- Tổng hợp ngữ cảnh.
- Sinh đáp án có căn cứ.

Tuy nhiên, không được sử dụng câu hỏi, Golden Answer, expected citations hoặc nhãn Test để huấn luyện hoặc tối ưu hệ thống.

Nếu cần đánh giá khả năng xử lý tài liệu hoàn toàn chưa thấy, phải tổ chức thí nghiệm riêng với bộ tài liệu được giữ ngoài quá trình phát triển.

---

# 11. QUY TẮC FINE-TUNING

Golden QA và SFT là hai dạng dữ liệu khác nhau về mục đích sử dụng.

## 11.1. Golden QA

Dùng để:

- Lưu câu hỏi.
- Lưu đáp án chuẩn.
- Lưu thông tin nguồn.
- Lưu nhãn đánh giá.
- Lưu các ngữ cảnh cần truy xuất.
- Đánh giá mô hình.

## 11.2. SFT

Dùng để huấn luyện mô hình sinh câu trả lời.

Dữ liệu SFT được chuyển đổi từ Train Golden QA đã được kiểm định.

Không chuyển Test sang SFT cho mục đích huấn luyện.

## 11.3. Nguyên tắc chuyển đổi

Tùy mục tiêu fine-tuning, dữ liệu đầu vào có thể bao gồm:

- System instruction.
- User question.
- Chat history.
- Context được cung cấp.
- Assistant response.

Nếu fine-tuning theo hướng closed-book, cần ghi rõ rằng mô hình phải học từ ví dụ huấn luyện mà không được cung cấp tài liệu lúc inference.

Nếu fine-tuning theo hướng grounded QA, đầu vào huấn luyện phải có ngữ cảnh nguồn phù hợp và hành vi sử dụng bằng chứng.

Không được mặc định hai loại thí nghiệm này tương đương nhau.

## 11.4. Validation

Validation dùng để:

- Theo dõi validation loss.
- Phát hiện overfitting.
- Chọn checkpoint.
- Early stopping.
- Kiểm tra hành vi trả lời trong quá trình phát triển.

Validation phải độc lập với dữ liệu huấn luyện theo cấp thủ tục.

---

# 12. CHỐNG DATA LEAKAGE

Kiểm tra trùng lặp ở các cấp:

1. Trùng mã thủ tục.
2. Trùng tài liệu.
3. Trùng phiên bản nội dung.
4. Trùng câu hỏi chính xác.
5. Trùng câu hỏi sau chuẩn hóa.
6. Trùng câu hỏi gần tương đương.
7. Trùng nội dung kiểm thử cùng thủ tục.
8. Trùng hội thoại.
9. Trùng cặp question-answer gần tương đương.

## 12.1. Chuẩn hóa câu hỏi

Có thể chuẩn hóa để phát hiện trùng:

- Unicode.
- Khoảng trắng.
- Chữ hoa/chữ thường.
- Dấu câu.
- Một số biến thể viết tắt.

Không được xóa quá nhiều thông tin khiến hai câu hỏi khác nghĩa bị coi là trùng.

## 12.2. Trùng ngữ nghĩa

Hai câu hỏi được coi là gần trùng khi chúng kiểm tra cùng một yêu cầu kiến thức trong cùng điều kiện, dù khác cách diễn đạt.

Ví dụ:

"Thời hạn giải quyết thủ tục X là bao lâu?"

"Thủ tục X mất mấy ngày để giải quyết?"

Không nên giữ cả hai chỉ để tăng số lượng case nếu không có mục tiêu robustness rõ ràng.

## 12.3. Nhiều batch

Cần kiểm tra các thủ tục mới với manifest của tất cả batch trước.

Không được chỉ kiểm tra trùng lặp trong batch hiện tại.

Nếu phát hiện thủ tục đã xử lý:

- Không sinh lại mặc định.
- Kiểm tra xem PDF có phải phiên bản mới không.
- Nếu giống nhau, bỏ qua hoặc ghi nhận trùng.
- Nếu khác phiên bản, xử lý theo quy trình cập nhật có kiểm soát.

---

# 13. QUẢN LÝ DỮ LIỆU QUA NHIỀU BATCH

Đây là phần bắt buộc khi người dùng cung cấp 10–100 PDF mỗi lần.

## 13.1. Không chia lại tùy ý

Một thủ tục đã được phân vào Train, Validation hoặc Test phải giữ nguyên tập của nó trong những batch sau.

Không chuyển thủ tục giữa các tập chỉ để đạt tỷ lệ lĩnh vực của batch mới.

Nếu cần tái phân chia toàn bộ, phải tạo một phiên bản dataset mới có manifest và báo cáo riêng.

## 13.2. Phân bổ tích lũy

Mỗi batch phải đọc trạng thái phân bổ hiện tại:

- Tổng số thủ tục mỗi lĩnh vực.
- Tổng số case mỗi lĩnh vực.
- Số thủ tục Train.
- Số thủ tục Validation.
- Số thủ tục Test.
- Tỷ lệ lĩnh vực hiện tại.
- Mục tiêu phân bổ cuối cùng.

Sau đó ưu tiên phân bổ thủ tục mới để giảm độ lệch tích lũy.

Không yêu cầu từng batch nhỏ phải có tỷ lệ Train/Test chính xác 2:1.

## 13.3. Manifest

Cần lưu manifest cho từng thủ tục, tối thiểu gồm:

- Mã thủ tục.
- Tên thủ tục.
- Lĩnh vực.
- PDF nguồn.
- Metadata nguồn.
- Hash tài liệu.
- Phiên bản nguồn.
- Số chunk.
- Số mệnh đề kiến thức.
- Số case.
- Tập dữ liệu được phân bổ.
- Batch ID.
- Trạng thái kiểm định.

## 13.4. Tính tái lập

Quy trình phải:

- Ghi nhận phiên bản schema.
- Ghi nhận phiên bản quy tắc.
- Sử dụng random seed cố định nếu có bước ngẫu nhiên.
- Ghi nhận cấu hình sinh case.
- Ghi nhận cấu hình phân chia.
- Ghi nhận thay đổi của từng batch.

Nếu chạy lại cùng dữ liệu với cùng cấu hình, kết quả phân bổ phải có khả năng tái lập.

Đối với bước sinh câu hỏi bằng LLM, phải lưu kết quả trung gian vì cùng prompt và seed không phải lúc nào cũng đảm bảo đầu ra giống hệt.

## 13.5. Trạng thái giữa các cuộc trò chuyện

Không được mặc định AI ở cuộc trò chuyện mới có đầy đủ dữ liệu đã xử lý trước đó.

Để tiếp tục chính xác, cần cung cấp hoặc truy cập được:

- Dataset manifest hiện tại.
- Danh sách thủ tục đã xử lý.
- Danh sách ID đã sử dụng.
- Báo cáo phân bổ.
- Phiên bản schema.
- Các tập dữ liệu đã tạo hoặc bản lưu kết quả cần thiết.

Nếu thiếu những thông tin này, không tự giả định rằng batch trước đã được xử lý thành công.

---

# 14. KIỂM ĐỊNH CHẤT LƯỢNG

## 14.1. Kiểm tra định dạng

- Mỗi dòng JSONL phải parse được.
- Đúng schema.
- Đúng kiểu dữ liệu.
- Đúng enum.
- Không thiếu trường bắt buộc.
- ID duy nhất.
- Không xuất hiện trường không được schema cho phép.

## 14.2. Kiểm tra nguồn

- PDF tồn tại.
- Metadata tồn tại.
- Chunk ID hợp lệ.
- Citation hợp lệ.
- Mã thủ tục đúng.
- Bằng chứng hỗ trợ đáp án.
- Không trộn thông tin thủ tục khác.

## 14.3. Kiểm tra nội dung

- Câu hỏi rõ ràng.
- Single-turn đủ nhận diện thủ tục khi cần trả lời trực tiếp.
- Multi-turn có lịch sử hợp lệ.
- Đáp án phù hợp loại hành vi kỳ vọng.
- Không hallucination.
- Không bỏ sót điều kiện.
- Không biến dữ liệu thiếu thành khẳng định phủ định.
- Không trùng lặp ngữ nghĩa không cần thiết.

## 14.4. Kiểm tra độ bao phủ

Đối chiếu từng case với danh sách đơn vị kiến thức.

Ghi nhận những nội dung:

- Đã được kiểm tra.
- Chưa được kiểm tra.
- Không phù hợp để tạo câu hỏi.
- Chưa thể xác minh.

## 14.5. Kiểm tra độc lập dữ liệu

- Train/Test không trùng thủ tục.
- Train/Validation không trùng thủ tục.
- Validation/Test không trùng thủ tục.
- Không trùng câu hỏi hoặc hội thoại.
- Không có bản sao QA Test trong dữ liệu SFT.

## 14.6. Không đánh đồng kiểm tra tự động với kiểm duyệt nội dung

JSON hợp lệ không chứng minh đáp án chính xác.

Chunk ID tồn tại không chứng minh chunk chứa bằng chứng.

Có citation không chứng minh citation hỗ trợ câu trả lời.

Cần có bước đối chiếu ngữ nghĩa giữa câu hỏi, đáp án và đoạn bằng chứng.

Nếu sử dụng LLM-as-a-Judge, phải ghi nhận mô hình, tiêu chí đánh giá và kết quả; không coi điểm của Judge là chứng minh tuyệt đối.

Những case không đạt yêu cầu phải được sửa, loại bỏ hoặc đưa vào quarantine.

---

# 15. BÁO CÁO VÀ THỐNG KÊ

Sau mỗi batch, cung cấp báo cáo:

## 15.1. Nguồn

- Số PDF nhận được.
- Số PDF đọc thành công.
- Số metadata hợp lệ.
- Số thủ tục ghép thành công.
- Số thủ tục mới.
- Số thủ tục trùng.
- Số thủ tục lỗi.

## 15.2. Dataset

- Tổng số case mới.
- Số case Train.
- Số case Validation.
- Số case Test.
- Tổng số case tích lũy.
- Số case bị loại.
- Số case đang chờ kiểm định.

## 15.3. Lĩnh vực

Bảng thống kê:

| Lĩnh vực | Số thủ tục | Train | Validation | Test |
|---|---:|---:|---:|---:|
| Lĩnh vực A | ... | ... | ... | ... |
| Lĩnh vực B | ... | ... | ... | ... |

Các con số phải lấy từ dữ liệu đã xử lý.

Không sử dụng số liệu minh họa trong báo cáo chính thức.

## 15.4. Coverage

- Knowledge Coverage.
- Condition Coverage.
- Chunk Coverage.
- Các mục nội dung chưa có case.
- Nguyên nhân thiếu coverage.

## 15.5. Taxonomy

Thống kê số lượng theo:

- Trả lời đủ.
- Trả lời một phần.
- Sửa tiền đề.
- Hỏi lại.
- Từ chối có căn cứ.
- Multi-hop.
- Multi-turn.
- Robustness/Security.

Nếu taxonomy hỗ trợ nhiều nhãn trên một case, phải phân biệt tổng theo nhãn chính và tổng theo thuộc tính phụ để tránh hiểu nhầm các tổng cộng.

## 15.6. Validation

- Số JSON hợp lệ.
- Số case qua kiểm tra schema.
- Số case qua kiểm tra grounding.
- Số case trùng.
- Số case có lỗi citation.
- Số case có nguy cơ hallucination.
- Số case không đủ bằng chứng.
- Số case có lỗi leakage.
