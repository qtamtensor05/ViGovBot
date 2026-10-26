# BỘ 20 CÂU HỎI BENCHMARK VIGOVBOT (bản đã chỉnh sửa)

## Chạy hệ thống

```bash
uv sync --extra rag

uv run --extra rag vigov web \
  --config configs/rag/inference.yaml \
  --host 127.0.0.1 \
  --port 8000
```

## 1. Tiêu chí phân chia mức độ

| Yếu tố | Dễ | Trung bình | Khó | Nâng cao |
|---|---|---|---|---|
| Độ dài câu hỏi | Ngắn, diễn đạt rõ | Có thêm ngữ cảnh | Nhiều điều kiện | Dài, nhiều điều kiện đan xen |
| Số lĩnh vực | Một lĩnh vực | Một lĩnh vực, nhiều khía cạnh | Hai lĩnh vực cần kết nối | Nhiều lĩnh vực có quan hệ phụ thuộc |
| Số thông tin cần trả lời | Một yêu cầu | 2–3 yêu cầu | Nhiều yêu cầu liên quan | Nhiều yêu cầu kèm điều kiện |
| Số nguồn cần truy xuất | Một nguồn là đủ | Có thể cần một vài phần thông tin | Cần kết hợp nhiều nguồn | Cần đối chiếu nguồn và căn cứ |
| Mức độ suy luận | Tìm thông tin trực tiếp | Tổng hợp thông tin | Đối chiếu điều kiện | Xử lý mâu thuẫn, thiếu căn cứ |
| Mức độ đầy đủ | Đủ thông tin | Có ngữ cảnh nhưng còn một điểm cần làm rõ | Thiếu thông tin ảnh hưởng đến câu trả lời | Thiếu dữ liệu quan trọng, cần hỏi lại hoặc từ chối kết luận |
| Ngôn ngữ vùng miền | Cách nói phổ thông | Cách nói đời thường, từ ngữ địa phương quen thuộc | Cách diễn đạt địa phương kết hợp nhiều yêu cầu | Cách diễn đạt địa phương, thiếu dấu hoặc mơ hồ kết hợp với nghiệp vụ phức tạp |

---

## Mức 1 — Dễ

Đặc điểm: Một lĩnh vực, một yêu cầu chính, thông tin đầu vào rõ ràng. Có thể trả lời bằng cách tìm kiếm thông tin trực tiếp trong tài liệu.

### Q01 — Hỏi giấy tờ cần chuẩn bị
- **Câu hỏi:** Tôi muốn đăng ký khai sinh cho con thì cần chuẩn bị giấy tờ gì?
- **Lĩnh vực:** Hộ tịch.
- **Số yêu cầu:** 1.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Chỉ yêu cầu một loại thông tin cụ thể.
- **Hành vi mong đợi:** Liệt kê đủ thành phần hồ sơ đúng theo tài liệu; không thêm giấy tờ không có căn cứ.

### Q02 — Hỏi nơi thực hiện thủ tục
- **Câu hỏi:** Tôi muốn đăng ký kết hôn thì phải đến đâu làm?
- **Lĩnh vực:** Hộ tịch.
- **Số yêu cầu:** 1.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Câu hỏi ngắn, mục tiêu rõ ràng, không cần kết hợp nhiều thông tin.
- **Hành vi mong đợi:** Nêu đúng cơ quan có thẩm quyền; nêu điều kiện về nơi cư trú nếu tài liệu có quy định.

### Q03 — Hỏi lệ phí
- **Câu hỏi:** Làm giấy khai sinh cho con có mất tiền không?
- **Lĩnh vực:** Hộ tịch.
- **Số yêu cầu:** 1.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Chỉ hỏi một thông tin (lệ phí). Câu trả lời phải dựa trên tài liệu và nêu rõ điều kiện áp dụng.
- **Hành vi mong đợi:** Trả lời đúng mức phí/miễn phí theo tài liệu; nêu rõ nếu phụ thuộc trường hợp (ví dụ đăng ký lần đầu so với cấp bản sao).

### Q04 — Hỏi khả năng nộp hồ sơ trực tuyến
- **Câu hỏi:** Tui muốn làm giấy khai sinh cho bé qua mạng được hông?
- **Lĩnh vực:** Hộ tịch.
- **Số yêu cầu:** 1.
- **Ngôn ngữ:** Đời thường, sắc thái miền Nam.
- **Lý do phân loại:** Nghiệp vụ đơn giản, nhưng kiểm tra khả năng hiểu cách diễn đạt địa phương.
- **Hành vi mong đợi:** Hiểu "hông" = "không", "qua mạng" = trực tuyến; trả lời có/không kèm cách thực hiện ngắn gọn.

### Q05 — Hỏi thời gian giải quyết
- **Câu hỏi:** Đăng ký kết hôn thì thường chờ bao lâu mới có kết quả?
- **Lĩnh vực:** Hộ tịch.
- **Số yêu cầu:** 1.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Chỉ cần tìm thông tin thời gian giải quyết và nêu đúng điều kiện áp dụng nếu có.
- **Hành vi mong đợi:** Nêu đúng thời hạn theo tài liệu và các trường hợp kéo dài (nếu có).

---

## Mức 2 — Trung bình

Đặc điểm: Một lĩnh vực nhưng có nhiều yêu cầu liên quan, cần tổng hợp thông tin hoặc hướng dẫn theo trình tự.

### Q06 — Nhiều thông tin trong một thủ tục
- **Câu hỏi:** Tôi muốn đăng ký khai sinh cho con thì cần giấy tờ gì, nộp ở đâu và bao lâu mới nhận được kết quả?
- **Lĩnh vực:** Hộ tịch.
- **Số yêu cầu:** 3 — giấy tờ, nơi nộp, thời gian.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Phải trả lời đầy đủ ba nội dung liên quan cùng một thủ tục.
- **Hành vi mong đợi:** Trả lời đủ cả 3 ý, không bỏ sót.

### Q07 — Xử lý hồ sơ cần bổ sung (nộp trực tiếp)
- **Câu hỏi:** Tôi nộp hồ sơ đăng ký khai sinh trực tiếp rồi mà cán bộ tiếp nhận báo còn thiếu giấy tờ. Giờ tôi phải làm sao?
- **Lĩnh vực:** Hộ tịch, thực hiện thủ tục hành chính.
- **Số yêu cầu:** 1 yêu cầu chính, gồm nhiều bước xử lý.
- **Ngôn ngữ:** Đời thường.
- **Lý do phân loại:** Cần hướng dẫn cách xử lý tình huống thay vì chỉ cung cấp một thông tin. Nêu rõ thủ tục và hình thức nộp để không trùng với Q12 (nộp trực tuyến).
- **Hành vi mong đợi:** Hướng dẫn các bước bổ sung hồ sơ, thời hạn bổ sung nếu tài liệu có quy định.

### Q08 — So sánh cách nộp hồ sơ
- **Câu hỏi:** Tui muốn làm giấy khai sinh cho con, không biết nộp trên mạng hay đi trực tiếp thì tiện hơn. Hai cách khác nhau chỗ nào?
- **Lĩnh vực:** Hộ tịch và dịch vụ công trực tuyến.
- **Số yêu cầu:** 2 — so sánh phương thức và giải thích khác biệt.
- **Ngôn ngữ:** Đời thường, sắc thái miền Nam.
- **Lý do phân loại:** Cần tổng hợp thông tin về hai phương thức. Không nên khẳng định một phương thức tốt hơn nếu chưa biết nhu cầu của người dân.
- **Hành vi mong đợi:** Nêu điểm giống/khác của hai cách; không kết luận "cách nào tốt hơn" khi chưa đủ căn cứ.

### Q09 — Trường hợp thiếu bản chính
- **Câu hỏi:** Tôi cần nộp hồ sơ đăng ký kết hôn nhưng chỉ còn bản photo giấy tờ tùy thân, không tìm thấy bản chính. Tôi có dùng bản photo được không, hay phải làm gì khác?
- **Lĩnh vực:** Hộ tịch, thủ tục hành chính.
- **Số yêu cầu:** 2 — khả năng dùng bản photo và hướng xử lý thay thế.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Cần tìm điều kiện tiếp nhận hồ sơ và hướng dẫn phù hợp với tình huống. Đã nêu rõ thủ tục để câu hỏi không bị mơ hồ.
- **Hành vi mong đợi:** Nêu quy định về bản chính/bản sao/xuất trình bản chính; hướng dẫn cách xin cấp lại hoặc thay thế.

### Q10 — Hướng dẫn theo trình tự
- **Câu hỏi:** Tui muốn đăng ký kết hôn thì phải chuẩn bị những gì, đi đâu nộp hồ sơ, rồi làm tiếp những bước nào nữa?
- **Lĩnh vực:** Hộ tịch.
- **Số yêu cầu:** 3 — chuẩn bị hồ sơ, nơi nộp, các bước tiếp theo.
- **Ngôn ngữ:** Đời thường, sắc thái miền Nam.
- **Lý do phân loại:** Cần tổng hợp thông tin thành quy trình dễ hiểu, thay vì trả lời từng ý rời rạc.
- **Hành vi mong đợi:** Trình bày theo thứ tự các bước từ chuẩn bị đến nhận kết quả.

---

## Mức 3 — Khó

Đặc điểm: Cần kết hợp nhiều nguồn hoặc nhiều lĩnh vực, đối chiếu thông tin, xác định điều kiện áp dụng hoặc xử lý các yêu cầu có liên quan với nhau.

### Q11 — Tổng hợp đầy đủ thông tin
- **Câu hỏi:** Tôi muốn đăng ký khai sinh cho con. Hãy cho biết giấy tờ cần chuẩn bị, nơi nộp, cách nộp trực tuyến nếu có, thời gian giải quyết và các khoản phí phải trả.
- **Lĩnh vực:** Hộ tịch và dịch vụ công trực tuyến.
- **Số yêu cầu:** 5 — giấy tờ, nơi nộp, phương thức, thời gian, phí.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Cần tổng hợp nhiều khía cạnh, bảo đảm câu trả lời không bỏ sót yêu cầu.
- **Hành vi mong đợi:** Trả lời đủ 5 ý, mỗi ý có căn cứ từ tài liệu.

### Q12 — Xử lý hồ sơ trực tuyến cần bổ sung
- **Câu hỏi:** Tui nộp hồ sơ qua mạng rồi, giờ hệ thống báo cần bổ sung giấy tờ. Tui phải vô đâu để xem thiếu gì, bổ sung như thế nào rồi kiểm tra kết quả ở đâu?
- **Lĩnh vực:** Dịch vụ công trực tuyến và xử lý hồ sơ.
- **Số yêu cầu:** 3 — kiểm tra yêu cầu bổ sung, nộp bổ sung, theo dõi kết quả.
- **Ngôn ngữ:** Đời thường, sắc thái miền Nam.
- **Lý do phân loại:** Cần kết hợp hướng dẫn ở nhiều bước và diễn đạt lại thành quy trình dễ thực hiện.
- **Hành vi mong đợi:** Hướng dẫn theo 3 bước; hỏi lại hoặc nêu rõ nếu tài liệu không nêu chi tiết thao tác trên cổng cụ thể.

### Q13 — Đối chiếu hai hướng dẫn (đã nêu rõ thủ tục)
- **Câu hỏi:** Tôi đang tìm hiểu thủ tục đăng ký kết hôn. Một hướng dẫn ghi thời gian giải quyết là 3 ngày làm việc, một hướng dẫn khác ghi 5 ngày. Bạn hãy đối chiếu căn cứ của hai thông tin này và giải thích trường hợp nào áp dụng.
- **Lĩnh vực:** Thủ tục hành chính và tra cứu văn bản.
- **Số yêu cầu:** 3 — kiểm tra nguồn, đối chiếu thời gian, xác định phạm vi áp dụng.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Cần đối chiếu nguồn và điều kiện áp dụng, không thể chỉ chọn một con số. Đã nêu rõ thủ tục để chatbot có thể truy xuất; chưa đủ thông tin sẽ được kiểm tra ở Q20.
- **Chuẩn bị trước:** Có sẵn trong kho tri thức hai tài liệu có thời hạn khác nhau (hoặc một tài liệu có quy định thời hạn chính và thời hạn kéo dài khi cần xác minh).
- **Hành vi mong đợi:** Giải thích được vì sao có hai con số và khi nào áp dụng từng con số, kèm căn cứ.

### Q14 — Điều kiện được miễn phí
- **Câu hỏi:** Tôi muốn xin bản sao giấy khai sinh cho con. Có trường hợp nào được miễn phí không, và tôi cần đáp ứng điều kiện gì?
- **Lĩnh vực:** Hộ tịch và lệ phí.
- **Số yêu cầu:** 2 — xác định trường hợp miễn phí và điều kiện.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Cần kết hợp thông tin về thủ tục với quy định phí, lệ phí và điều kiện áp dụng. Nếu kho tri thức không có căn cứ phù hợp, chatbot phải nêu rõ giới hạn.
- **Hành vi mong đợi:** Nêu đúng các trường hợp miễn phí theo tài liệu; không bịa nếu thiếu căn cứ.

### Q15 — Kiểm tra thông tin truyền miệng
- **Câu hỏi:** Người quen nói với tui là đăng ký kết hôn chỉ cần chờ một ngày là xong. Có đúng vậy không? Tui muốn biết thời gian giải quyết theo hướng dẫn chính thức và những trường hợp nào có thể khác.
- **Lĩnh vực:** Hộ tịch (đối chiếu thông tin truyền miệng với hướng dẫn chính thức).
- **Số yêu cầu:** 2 — kiểm tra thông tin và xác định trường hợp áp dụng.
- **Ngôn ngữ:** Đời thường, sắc thái miền Nam.
- **Lý do phân loại:** Cần xác minh thông tin và giải thích điều kiện, tránh xác nhận lời truyền miệng khi chưa có căn cứ. Mức khó đến từ yêu cầu đối chiếu, không phải từ số lĩnh vực.
- **Hành vi mong đợi:** Không xác nhận "một ngày" nếu không có căn cứ; nêu thời hạn chính thức và các trường hợp khác biệt.

---

## Mức 4 — Nâng cao

Đặc điểm: Cần xử lý thiếu thông tin, mâu thuẫn giữa các nguồn, giới hạn dữ liệu hoặc yêu cầu ngoài phạm vi. Mục tiêu không chỉ là trả lời đúng mà còn phải biết khi nào chưa đủ căn cứ để trả lời.

### Q16 — Yêu cầu tổng hợp có điều kiện
- **Câu hỏi:** Tôi muốn xin bản sao giấy khai sinh cho con nhưng chưa rõ trường hợp của mình cần những giấy tờ gì, nộp ở đâu, bao lâu có kết quả và có phải trả phí không. Hãy hướng dẫn đầy đủ, đồng thời chỉ rõ thông tin nào còn phụ thuộc vào trường hợp cụ thể.
- **Lĩnh vực:** Hộ tịch, nơi tiếp nhận hồ sơ và lệ phí.
- **Số yêu cầu:** 4 — giấy tờ, nơi nộp, thời gian, phí.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Cần tổng hợp nhiều khía cạnh và phân biệt thông tin chung với thông tin phụ thuộc điều kiện.
- **Hành vi mong đợi:** Trả lời đủ 4 ý; tách rõ phần chung và phần phụ thuộc trường hợp (ví dụ nơi lưu sổ gốc, có/không cần cấp lại); có thể hỏi thêm thông tin cần thiết.

### Q17 — Chưa xác định rõ nhu cầu
- **Câu hỏi:** Tui muốn làm giấy tờ cho con mà chưa biết bắt đầu từ đâu. Bạn hỏi tui vài câu trước để xác định cần làm thủ tục gì rồi hãy hướng dẫn nha.
- **Lĩnh vực:** Chưa xác định.
- **Số yêu cầu:** 1 yêu cầu chính — làm rõ nhu cầu trước khi tư vấn.
- **Ngôn ngữ:** Đời thường, sắc thái miền Nam.
- **Lý do phân loại:** Chatbot cần nhận ra thiếu thông tin và đặt câu hỏi làm rõ, thay vì tự đoán loại thủ tục.
- **Hành vi mong đợi:** Đặt câu hỏi làm rõ (ví dụ: loại giấy tờ, độ tuổi của con, tình trạng đã đăng ký hay chưa); không tự chọn thủ tục.

### Q18 — Yêu cầu thông tin chưa thể xác định
- **Câu hỏi:** Tôi dự định nộp hồ sơ vào tháng tới. Bạn cho tôi biết chính xác ngày nào sẽ có kết quả nhé.
- **Lĩnh vực:** Thời gian giải quyết thủ tục hành chính.
- **Số yêu cầu:** 1 yêu cầu chính.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Chưa có loại thủ tục, ngày nộp cụ thể và thông tin cần thiết để tính ngày trả kết quả. Chatbot phải giải thích giới hạn và hỏi thêm thông tin, không tự đưa ra ngày chính xác.
- **Hành vi mong đợi:** Không đưa ra ngày cụ thể; hỏi loại thủ tục và ngày nộp; giải thích cách tính thời hạn.

### Q19 — Câu hỏi ngoài phạm vi
- **Câu hỏi:** Theo bạn, tháng tới tôi nên mua cổ phiếu công nghệ nào để có lời?
- **Lĩnh vực:** Đầu tư tài chính, ngoài phạm vi hỗ trợ thủ tục hành chính.
- **Số yêu cầu:** 1.
- **Ngôn ngữ:** Phổ thông.
- **Lý do phân loại:** Kiểm tra khả năng nhận diện câu hỏi ngoài phạm vi và điều hướng phù hợp. Câu này dùng để đánh giá độ tin cậy, không đại diện cho độ khó nghiệp vụ hành chính.
- **Hành vi mong đợi:** Từ chối lịch sự, nêu rõ phạm vi hỗ trợ (thủ tục hành chính công), không đưa khuyến nghị đầu tư.

### Q20 — Nguồn mâu thuẫn, thiếu thông tin, viết không dấu
- **Câu hỏi:** Tui doc duoc hai huong dan ve cung mot thu tuc: mot cho noi mat 3 ngay, cho khac noi 5 ngay. Ban kiem tra giup tui ngay ban hanh, noi dung ap dung va can cu cua tung huong dan. Neu chua du thong tin de ket luan thi noi ro can kiem tra them gi, dung doan nha.
- **Lĩnh vực:** Thủ tục hành chính và tra cứu văn bản.
- **Số yêu cầu:** 4 — kiểm tra ngày ban hành, phạm vi áp dụng, căn cứ và xác định thông tin còn thiếu.
- **Ngôn ngữ:** Đời thường, sắc thái miền Nam, viết không dấu.
- **Lý do phân loại:** Kết hợp cách diễn đạt địa phương, thiếu dấu với yêu cầu đối chiếu nguồn và xử lý bất định. Khác Q13 ở chỗ không nêu rõ thủ tục và không có đủ thông tin để kết luận.
- **Hành vi mong đợi:** Hiểu được câu không dấu; hỏi lại tên thủ tục và nguồn của hai hướng dẫn; không đoán kết luận.

---

## Nguyên tắc sử dụng bộ câu hỏi

1. Mỗi câu hỏi có một mức độ nghiệp vụ chính để thuận tiện phân tích kết quả.
2. Đặc trưng ngôn ngữ vùng miền được ghi nhận riêng, không tự động làm tăng mức độ nghiệp vụ.
3. Số nguồn cần truy xuất phải được xác định dựa trên kho tri thức và tài liệu tham chiếu thực tế, không suy đoán chỉ từ câu hỏi.
4. Với Q13 và Q20, cần chuẩn bị trước các tài liệu có thông tin khác nhau để đánh giá khả năng đối chiếu nguồn.
5. Với Q19, chấm khả năng nhận diện ngoài phạm vi; không chấm theo tiêu chí trả lời thủ tục hành chính.
6. Với Q17 và Q18, chấm khả năng hỏi lại/làm rõ; không chấm theo việc có đưa ra đáp án cuối cùng hay không.
7. Trước khi đánh giá chính thức, cần xây dựng đáp án chuẩn (đối chiếu văn bản hiện hành, kiểm tra lại các thời hạn và mức phí) và tiêu chí chấm chi tiết cho từng câu hỏi. Mục "Hành vi mong đợi" ở trên chỉ là khung, chưa phải đáp án.
