# Trạng thái hiện tại của ViGovBot

> Cập nhật: 2026-11-08. Đây là ảnh chụp trạng thái hiện hành; các mốc thay đổi
> chi tiết nằm trong [lịch sử triển khai](implementation-history.md).

## Phạm vi dự án

ViGovBot là dự án nghiên cứu và demo mẫu thử cho hỏi đáp thủ tục hành chính
tiếng Việt. Phạm vi hiện tại ưu tiên tính đúng của dữ liệu, routing, retrieval,
prompt và đánh giá model. Dự án chưa đặt mục tiêu triển khai production, chịu tải
lớn, HA hoặc tối ưu cho máy cấu hình yếu.

## Luồng hệ thống hiện hành

1. Tài liệu thủ tục được trích xuất, chuẩn hóa và chia chunk theo cấu trúc.
2. BGE-M3 tạo embedding; FAISS và SQLite lưu vector cùng metadata.
3. PhoBERT bốn head phân loại scope, flow, mã thủ tục và section intent.
4. Runtime truy xuất trực tiếp từ FAISS theo `top_k`; không chạy cross-encoder
   reranker online.
5. Evidence được đóng gói có cấu trúc trước khi gửi tới Qwen/Ollama hoặc model
   QLoRA; output được kiểm tra schema và quan hệ action/evidence.

Các profile hiện hành dùng `top_k=15` cho host, evaluation và Docker Ollama;
profile Docker GPU dùng `top_k=5`. Giá trị thực tế phải đọc từ profile được chọn,
không suy ra từ báo cáo benchmark cũ.

## Hội thoại và state

- Routing contract hiện hành là v2 với PhoBERT bốn head.
- Signed state v3 bảo toàn menu lựa chọn, câu hỏi đang chờ, mã thủ tục và section
  intent qua nhiều lượt.
- Khi người dùng chọn một thủ tục trong menu, hệ thống khôi phục câu hỏi gốc và
  khóa retrieval theo mã thủ tục cùng section intent thay vì định tuyến lại.
- Mã thủ tục đã chọn được giữ xuyên qua cả menu chọn section; context khác mã bị
  loại trước generation, kể cả khi tiếp tục từ state v3 cũ.
- State được ký HMAC để phát hiện sửa đổi. Lưu trữ phiên dùng bộ nhớ tiến trình,
  phù hợp demo một tiến trình và chưa phải session store phân tán.
- Chuẩn hóa tiếng Việt dùng primitive chung `fold_vietnamese`; các policy bổ sung
  phải được đặt tên rõ và có kiểm thử riêng.

## Dữ liệu huấn luyện và đánh giá

- `Data/dataset_v3/finetuning_v1/`: dữ liệu SFT hội thoại cho QLoRA v1.
- `Data/dataset_v3/finetuning_v2/`: dữ liệu RAG-SFT đã lọc leakage cho QLoRA v2.
- `Data/dataset_v3/test_rag_pa1/`: tập PA1 dùng so sánh model.
- `Data/dataset_v3/test_router/`: tập đánh giá router.
- Artifact đánh giá chuẩn hóa nằm trong `result/`; báo cáo kết quả nằm tại
  `docs/reports/model-evaluation/`.

Sáu cấu hình so sánh hiện có gồm Base, RAG, QLoRA v1, QLoRA v1 + RAG,
QLoRA v2 và QLoRA v2 + RAG. Các con số trong báo cáo là snapshot của lần chạy đã
ghi nhận, không tự động chứng minh chất lượng của code hiện tại nếu chưa chạy lại.

## Giới hạn và việc còn lại

- Chưa chạy lại toàn bộ benchmark model sau các thay đổi state/section-intent.
- QLoRA v2 + RAG vẫn cần cải thiện citation, abstention và các ca hồi quy đã ghi
  trong báo cáo; model đã được judge, lần chạy lại chỉ nhằm thu hồi artifact bị
  mất và xác minh runtime mới.
- Không có reranker online. Chỉ xem xét lại khi benchmark retrieval chứng minh lợi
  ích đủ lớn so với độ trễ và độ phức tạp.
- Chưa có session store phân tán, xác thực người dùng hoặc kiểm chứng tải lớn vì
  các hạng mục này nằm ngoài phạm vi nghiên cứu/demo hiện tại.
- Các kết luận GPU, model live hoặc Docker chỉ hợp lệ khi báo cáo nêu rõ bằng chứng
  runtime; source test và kiểm tra tĩnh không thay thế kiểm chứng đó.

## Tài liệu chuẩn để tra cứu

- [Kiến trúc hệ thống](../architecture/architecture.md)
- [Routing PhoBERT bốn head](../guides/four-head-routing.md)
- [RAG nhiều lượt](../guides/rag-multi-turn.md)
- [Vận hành RAG cơ bản](../guides/trien-khai-rag-co-ban.md)
- [Đánh giá QA/RAG](../guides/qa-rag-evaluation.md)
- [Tổng hợp đánh giá model](../reports/model-evaluation/all-models.md)
