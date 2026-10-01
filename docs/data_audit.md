# Kiểm tra dữ liệu ngày 28/09/2026

## Nguồn và phạm vi

- `data/source_manifest.csv` ghi 11 nguồn ứng viên trên tên miền HaUI: 9 PDF tải được, 2 URL trả 404. Tình trạng hiệu lực của từng văn bản để `unknown` vì chưa rà toàn bộ văn bản mới và ngày hiệu lực.
- Corpus hiện gồm 9 PDF/449 đoạn: bản hợp nhất QĐ 744/2021 và 666/2023 được trích chữ trực tiếp (136 đoạn kể cả lời mở đầu); 8 PDF ảnh quét dùng Markdown OCR do người dùng cung cấp (313 đoạn). Không đưa hai URL lỗi vào chỉ mục.
- Bản OCR nằm trong `data/ocr/`, bản ZIP ở `data/pdf_to_markdown_md_files.zip`, PDF gốc ở `data/raw/`. Chỉ mục có thể tái tạo bằng `python3 -m src.sources` rồi `python3 -m src.project prepare` khi các file OCR đã có sẵn.

## Các kiểm tra đã làm

1. Với từng PDF OCR: SHA-256 PDF và OCR khớp manifest; mốc `## Trang N` tăng liên tục từ 1; số mốc bằng số trang PDF. Mỗi đoạn có ID, trang, URL PDF, hash nguồn và cờ `page_matched_unreviewed`.
2. Với bản hợp nhất: đoạn mở đầu ở trang 1 và các Điều/khoản giữ URL, trang gốc. Có thể đối chiếu mẫu `QC2023-D10-K1-P01` ở trang 16 và `QC2023-D22-K2-P01` ở trang 28.
3. `src/legal_graph.py` chỉ nhận 22 quan hệ có câu dẫn trùng trong đúng trang OCR và đúng đoạn đã lập chỉ mục. File `data/processed/legal_relations.json` lưu ID đoạn và URL PDF cho từng cạnh.
4. Số hiệu QĐ 1077/2023 (khóa luận), 427/2022 (học phần thay thế), 242/2022 (ngoại ngữ) đã đối chiếu trang đầu PDF. Số hiệu PDF quy định đồ án 2019 chưa đọc chắc nên để trống, không đoán.

## Lỗi dữ liệu còn lại

- Khớp trang và hash không chứng minh chữ OCR đúng. Lỗi dấu tiếng Việt, dấu gạch, số hiệu và bảng còn tồn tại; riêng câu dẫn QĐ 1432/2023 có dấu gạch OCR dư, được ghi chú trên cạnh.
- PDF hợp nhất có chú thích chân trang chen vào câu tại chỗ ngắt trang; một số tiêu đề Điều và khoản 1 nằm cùng đoạn. Đoạn dài có thể tách câu khi chia mốc độ dài.
- Các nút văn bản được dẫn nhưng chưa có toàn văn chỉ dùng làm đích quan hệ. Không dùng chúng để suy luận nội dung điều khoản hay hiệu lực hiện hành.
- Bộ 30 câu cũ chỉ gắn gold ID của bản hợp nhất. Sau khi thêm 8 PDF, câu hỏi chung chung có thể khớp một văn bản khác, ảnh hưởng Recall@5.

Xem [mô hình OCR và đồ thị](OCR_AND_LEGAL_GRAPH.md), [báo cáo kết quả](../report/report.md) và mở `source_url#page=N` trong `data/processed/articles.jsonl` để kiểm tra từng nhận định.
