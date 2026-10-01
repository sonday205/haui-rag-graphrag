# Kịch bản demo 3–5 phút

1. Mở manifest và `report/report.md` (40 giây): 11 ứng viên, 9 PDF trong corpus, 449 đoạn; 8 PDF dùng OCR chưa hiệu đính toàn bộ. Chỉ vào URL trang PDF và cờ hiệu lực `unknown`.
2. Hỏi một điều của bản hợp nhất (1 phút): “Sinh viên được rút lớp học phần vào tuần nào?” Xem top 5, mở PDF ở Điều 7 khoản 10 và so sánh trace hai cách truy xuất.
3. Hỏi quan hệ văn bản (1 phút): “QĐ 721/2024 thay thế những quyết định nào?” Chọn GraphRAG, xem cạnh `REPLACES`, đoạn chứng cứ trang 1 và mở PDF gốc. Giải thích chiều cạnh và số hiệu; không kết luận văn bản đang áp dụng hiện nay.
4. Hỏi nhiều văn bản (45 giây): câu QĐ 1077/2023 viện dẫn TT 08/2021 và thay QĐ 239/2022. Đối chiếu hai trang chứng cứ; `CITES` và `REPLACES` có nghĩa khác nhau.
5. Kết luận (45 giây): mở bảng 30 câu cũ và bộ 8 câu quan hệ trong `report/report.md`. Nêu rõ bộ 8 câu là kiểm thử chức năng do người làm dự án soạn; kết quả 7 cặp Gemini trong `evaluation/BAO_CAO_DANH_GIA_GEMINI.md` thuộc corpus trước OCR.

Lệnh demo: `npm run build --prefix frontend` rồi `python -m uvicorn server:app --host 127.0.0.1 --port 8000`; mở `http://127.0.0.1:8000`.
