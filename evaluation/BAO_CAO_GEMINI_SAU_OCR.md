# Kiểm tra Gemini sau khi bổ sung OCR và quan hệ văn bản

**Cập nhật kiểm tra ứng dụng 28/09/2026:** Với key mới, `gemini-3.5-flash-lite` vẫn trả HTTP 503 cho một câu hỏi giao diện; `gemini-2.5-flash-lite` trả HTTP 404 vì key này không có quyền dùng model cũ. Chuyển model trong `.env` sang `gemini-3.8-flash` và hỏi một lượt qua `POST /api/chat` ở chế độ `rag`: HTTP 200, `error=null`, một lời gọi Gemini, câu trả lời nêu tuần 03–08 và dẫn [Điều 7 khoản 10, trang 8](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8). Độ trễ API 6.728,93 ms. Đây là **kiểm tra hoạt động một câu**, không phải điểm đánh giá chất lượng. Trang `/`, hai tài nguyên JS/CSS, `/api/health` và `/api/suggestions` đều trả HTTP 200; không mở được trình duyệt tích hợp để xác nhận giao diện bằng mắt.

**Sự cố giao diện sau đó:** Người dùng gửi ảnh một lượt so sánh trên frontend: cả hai kết quả hiện `503 UNAVAILABLE`. Log backend xác nhận có `POST /api/chat` mới và health lúc đó báo model `gemini-3.8-flash`; một lượt thành công trước đó không đảm bảo dịch vụ luôn sẵn sàng. Frontend và backend đã được sửa để giãn lời gọi tối thiểu 5 giây trong một tiến trình, hiển thị lỗi 503 ngắn gọn, báo trạng thái quá tải thay vì chỉ hiện “đã cấu hình”, và bỏ lời gọi Gemini thứ hai của một lượt so sánh khi lời gọi đầu đã trả 503/429. Kiểm tra cú pháp, build frontend và phép thử API giả lập lỗi 503 đã qua; **chưa gọi Gemini thêm sau bản sửa**.

Ngày thử: 28/09/2026 (UTC). Dữ liệu thô: `evaluation/runs/gemini_post_ocr_relations.jsonl`; metadata và dấu vân tay: `evaluation/runs/gemini_post_ocr_relations_meta.json`.

## Thiết lập

- Corpus: 9 PDF, 449 đoạn; 8 PDF ảnh quét dùng OCR Markdown chưa hiệu đính toàn bộ. GraphRAG có 22 cạnh pháp lý đã gắn trang/ID chứng cứ.
- Model cấu hình: `gemini-3.5-flash-lite`. Bộ câu hỏi: `evaluation/questions_multidoc_ocr.jsonl`; lượt thử chọn `R01 R02 R03`, tối đa 6 lời gọi (mỗi câu × 2 phương pháp). Script giữ khoảng cách tối thiểu 5 giây giữa lúc bắt đầu hai request; mỗi `answer()` cấu hình SDK tối đa một HTTP request.
- Lệnh: `python3 -m evaluation.run_gemini --run-id post_ocr_relations --questions-file questions_multidoc_ocr.jsonl --ids R01 R02 R03 --max-new-calls 6`.

## Kết quả thực tế

| Câu | Phương pháp | Chứng cứ đúng có trong top 5? | Thời gian cả truy xuất/API | Kết quả model |
|---|---|---|---:|---|
| R01: QĐ 721/2024 thay QĐ nào? | RAG vector | Không; thiếu `QD721_2024-P001-C02` | 4.901,54 ms | HTTP 503 `UNAVAILABLE` |
| R01 | GraphRAG | Có; `QD721_2024-P001-C02` đứng đầu | 1.228,75 ms | HTTP 503 `UNAVAILABLE` |

Hai request bắt đầu lúc **16:15:37.169693** và **16:15:42.172413 UTC**, cách nhau khoảng **5,00 giây**. Sau hai lỗi 503 liên tiếp, script dừng; R02 và R03 **chưa gọi API**. Run quan hệ này không có đáp án Gemini hợp lệ; không tính điểm đúng/đủ ý/dẫn nguồn hay so sánh chất lượng LLM từ run. Hai thời gian trên chủ yếu phản ánh thời gian thất bại của dịch vụ, không đại diện độ trễ trả lời thành công. Lượt kiểm tra hoạt động S02 với model khác được ghi riêng ở đầu file.

Kết quả truy xuất trên toàn bộ 8 câu quan hệ vẫn ở `evaluation/runs/multidoc_ocr_retrieval.json`: Recall@5 trung bình RAG 0,1875, GraphRAG 1,0. Bộ 8 câu do cùng người xây đồ thị soạn sau khi tạo cạnh, nên chỉ kiểm tra chức năng truy xuất quan hệ. Báo cáo Gemini [trước OCR](BAO_CAO_DANH_GIA_GEMINI.md) thuộc corpus cũ và không được gộp vào phép đo này.

Sau lượt lỗi này, nhãn kiểm chứng cạnh pháp lý trong đồ thị đã được đổi cho chính xác hơn và chỉ mục được dựng lại. Vì SHA mã/đồ thị đã đổi, **không tiếp tục checkpoint `post_ocr_relations` trên chỉ mục hiện tại**. Khi dịch vụ ổn định, tạo `--run-id post_ocr_relations_v2` với cùng `--questions-file` và `--ids`; metadata ngăn trộn các phiên bản. Chỉ chấm một câu khi cả RAG và GraphRAG có đáp án hợp lệ, rồi đối chiếu câu trả lời với trang PDF gốc vì OCR có thể sai số hiệu.
