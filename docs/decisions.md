# Quyết định kỹ thuật

1. Chỉ thu thập PDF từ HaUI và các tiểu miền. Manifest giữ URL, ngày truy cập, hash, lỗi tải, số trang và lý do chọn. Hai URL 404 không vào corpus. Hiệu lực hiện hành của các văn bản đặt `unknown`.
2. Tám PDF ảnh quét dùng bản OCR Markdown do người dùng cung cấp. `src/ocr_corpus.py` kiểm tra hash/trang rồi chia đoạn trong cùng trang. Văn bản OCR được đánh dấu chưa hiệu đính toàn bộ; không tự chuẩn hóa số hiệu mơ hồ. Bản hợp nhất lấy lớp chữ PDF và thêm đoạn mở đầu làm chứng cứ quan hệ.
3. Hai phương pháp dùng chung 449 đoạn, `top_k=5`, trần 6.500 ký tự chứng cứ và cùng prompt/model Gemini khi sinh. RAG vector dùng `paraphrase-multilingual-MiniLM-L12-v2`, cosine. GraphRAG tự thiết kế dùng hạt giống TF-IDF ký tự và vector, mở rộng cạnh cấu trúc/chủ đề/văn bản, rồi xếp hạng kết hợp. Đây không phải bản triển khai Microsoft GraphRAG.
4. Cạnh pháp lý chỉ được đưa vào từ `data/relations_reviewed.json` khi câu dẫn khớp đúng trang OCR và đoạn chỉ mục. Có 22 cạnh thuộc `AMENDS`, `REPLACES`, `SUPPLEMENTS`, `CONSOLIDATES`, `CITES`; các cạnh chủ đề dựa từ khóa chỉ phục vụ truy xuất. Nút văn bản chưa có toàn văn không làm chứng cứ trả lời. Quan hệ nguồn ghi “thay thế” không tự xác nhận hiệu lực hiện hành.
5. Kết quả retrieval cũ và mới được giữ riêng. Bộ 8 câu hỏi quan hệ soạn sau khi dựng đồ thị là kiểm thử chức năng có thiên lệch; không dùng nó để khẳng định chất lượng tổng quát. Kết quả 7 cặp Gemini trước OCR chỉ thuộc corpus 1 PDF/135 đoạn. Run Gemini mới cần `--run-id` riêng; script giãn 5 giây giữa các lượt, dưới 15 lượt/phút.
6. Giao diện React/Vite + FastAPI, không dùng Streamlit. Key Gemini chỉ ở backend; giao diện hiển thị URL trang PDF, đoạn nguồn, trace và thời gian. Khi không gọi Gemini, chế độ chỉ truy xuất vẫn cho xem chứng cứ.

Chi tiết: [OCR và GraphRAG](OCR_AND_LEGAL_GRAPH.md), [kiểm tra dữ liệu](data_audit.md), [báo cáo](../report/report.md).

## Cập nhật sau review 01/10/2026

- Giữ nguyên ID/text của 449 đoạn để gold và chứng cứ cạnh còn đối chiếu được. Đọc toàn bộ đoạn dài bằng cửa sổ 256 token/overlap 64, trung bình các vector cửa sổ rồi chuẩn hóa. Đây là thiết kế riêng, không giả nhận giống nguyên thuật toán sentence-transformers cho đoạn dài.
- Dựng cả phiên bản chỉ mục rồi đổi `current` atomic trên Linux; giữ snapshot cũ. Hash và encoder config được kiểm tra trước phục vụ. Không đưa thêm database/hạ tầng vào nghiên cứu quy mô gọn.
- Model hiện tại `gemini-3.5-flash-lite`; đầu ra JSON trả lời/từ chối được kiểm tra riêng. Cùng schema/prompt/temperature/context budget cho cả hai phương pháp.
- Thực nghiệm nhỏ có thêm hybrid không graph để phân biệt một phần lợi ích từ TF-IDF với graph. Không tạo suy luận pháp lý tự động hoặc chỉnh cạnh/gold theo đáp án sinh.
- Kết quả40 request và174 lượt truy xuất ở [báo cáo mới](../evaluation/runs/research_20261001/BAO_CAO_THUC_NGHIEM.md). Đánh giá nội dung sơ bộ do trợ lý AI; bộ câu hỏi nội bộ và mẫu nhỏ chưa đủ cho kết luận tổng quát.
