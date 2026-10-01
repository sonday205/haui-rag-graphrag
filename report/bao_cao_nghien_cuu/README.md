# Báo cáo nghiên cứu RAG và GraphRAG HaUI

Bản ngày 01/10/2026, tác giả Trần Trung Hiếu, dự án cá nhân. PDF 22 trang A4 tính cả bìa, mục lục, tóm tắt, tài liệu tham khảo và phụ lục. Nội dung tập trung thiết kế so sánh, kết quả và phân tích nguyên nhân.

## Chỉnh sửa

- `main.tex`: bìa, tên tác giả, thông tin để trống và định dạng.
- `sections/`: nội dung theo từng phần; tên file tương ứng thứ tự trong mục lục.
- `figures/`: hình vector PDF, dùng được khi biên dịch mà không chạy Python.
- `question_table.tex`: bảng điểm từng câu, được tạo từ artifact nội bộ.
- `artifact_hashes.json`: hash đầu vào tạo hình/bảng.

Thông tin khoa, mã sinh viên, lớp, người hướng dẫn, bộ môn và tháng/năm trên bìa được để trống. Không có tên giảng viên, mã đề tài hay thông tin phê duyệt tự đặt.

## Quy cách

Tham khảo `../latex.tex`: A4, lề trên/dưới 2 cm, trái 2,5 cm, phải 2 cm; giãn dòng 1,4; bìa có khung và tiêu đề căn giữa. Tùy chọn `13pt` trong mẫu `article` không được LaTeX hỗ trợ. Nguồn mới đặt **cỡ chữ thân bài 13 pt thực sự**, không để trình biên dịch bỏ qua.

Máy hiện tại không có Times New Roman, nên PDF dùng **Liberation Serif**, phông tương thích kiểu Times, có đầy đủ tiếng Việt. Nếu máy biên dịch có Times New Roman, `main.tex` tự dùng phông đó. Việc đổi phông có thể làm đổi ngắt dòng/số trang. Công thức dùng Latin Modern Math; bảng và chú thích dùng chữ nhỏ hơn thân bài.

## Biên dịch

Từ thư mục này:

```bash
bash build.sh
```

Script ưu tiên XeLaTeX trong PATH, sau đó dùng bản TinyTeX đã cài tại `.local-tools/tex/.TinyTeX/` của dự án. Chạy ba lượt để cập nhật mục lục và citation, xuất `../BAO_CAO_NGHIEN_CUU_RAG_GRAPHRAG.pdf`. Nhật ký trong `build/`.

Trên máy khác, cài TeX Live/TinyTeX có XeLaTeX và các gói: fontspec, extsizes, geometry, setspace, amsmath, amssymb, graphicx, booktabs, tools, float, unicode-math, lm-math, etoolbox, pgf, enumitem, caption, fancyhdr, titlesec, microtype, hyperref. Nguồn UTF-8; không dùng pdfLaTeX.

Để tạo lại hình/bảng từ dữ liệu gốc trong checkout này (không gọi Gemini):

```bash
python3 generate_figures.py
bash build.sh
```

Python cần matplotlib/numpy và các artifact ở `evaluation/runs/research_20261001/`. Gói nguồn ZIP chứa sẵn hình/bảng nên không cần chạy script Python để sửa nội dung rồi tạo PDF.

## Phạm vi số liệu

- 9 PDF/449 đoạn/480 nút/1.872 cạnh, 22 quan hệ pháp lý có chứng cứ.
- 174 lượt truy xuất trên ba bộ có chồng lấp; không phải 174 câu độc lập.
- 40 request Gemini/20 cặp, model `gemini-3.5-flash-lite`; một lượt HTTP smoke riêng không tính vào nghiên cứu.
- R03/GraphRAG được kiểm tra lại offline sau sửa parser citation nhóm. JSON thô, thời gian và token gốc giữ nguyên; không có request mới để thay đáp án.
- Điểm nội dung do trợ lý AI đối chiếu sơ bộ; chưa có chấm độc lập bởi người. OCR chưa hiệu đính toàn bộ; hiệu lực hiện hành chưa xác minh.

Hồ sơ đầy đủ: `../../evaluation/runs/research_20261001/BAO_CAO_THUC_NGHIEM.md`, log API gốc, CSV và JSON trong cùng run. Bảng chính không gộp số liệu trước OCR hoặc trước sửa lỗi. Các ablation, tập độc lập và chấm mù là hướng tiếp theo, chưa có kết quả thực hiện.

## Kiểm tra bàn giao

Đã biên dịch XeLaTeX ba lượt, kiểm tra tiếng Việt/phông được nhúng, mục lục/citation, số trang A4, liên kết PDF, bảng/hình và bản render toàn bộ trang. `build/verification.json` ghi kiểm tra kỹ thuật; đây không phải xác nhận học thuật độc lập. File mẫu `../latex.tex` và `../cv.pdf` giữ nguyên.
