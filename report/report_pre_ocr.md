# So sánh RAG vector và GraphRAG cấu trúc trên quy chế đào tạo HaUI: bản thử nghiệm nhỏ

Ngày ghi nhận: 28/09/2026. Trạng thái: **đã đo truy xuất đủ 30 câu và đã chạy Gemini trên 7 cặp câu hỏi; thử tiếp với giãn 5 giây/lượt nhưng dịch vụ trả 503**.

## Tóm tắt

Khảo sát 11 nguồn ứng viên từ trang HaUI, tải được 9 PDF; 8 PDF là ảnh quét chưa OCR nên corpus hiện gồm 1 bản hợp nhất quy chế đào tạo có 22 điều và 135 đoạn. Hai pipeline dùng chung corpus và top 5 đoạn. Trên 25 câu trả lời được bằng corpus, Recall@5 trung bình là 0,76 (RAG vector) và 0,80 (GraphRAG cấu trúc). Với Gemini, quota chỉ cho phép hoàn thành 7 cặp câu hỏi: mỗi bên đúng nội dung 6/7 và đủ ý 4/7 theo phiếu chấm tay. [Báo cáo Gemini theo từng câu](../evaluation/BAO_CAO_DANH_GIA_GEMINI.md) giữ câu trả lời, nguồn, thời gian, token và giới hạn phép đo. Năm câu ngoài corpus không tính Recall vì không có gold ID.

## Lý do, câu hỏi và giả thuyết nghiên cứu

Quy chế đào tạo có cấu trúc Điều/khoản, các mốc áp dụng và quan hệ thay thế. Người học cần câu trả lời kiểm tra được trên PDF gốc. Câu hỏi nghiên cứu là: đồ thị cấu trúc văn bản/chủ đề có tăng khả năng tìm đúng đoạn, nhất là câu hỏi nhiều điều, so với chỉ mục vector trên cùng dữ liệu không? Giả thuyết mở: mỗi cách có thể thắng ở loại câu hỏi khác nhau; chi phí chuẩn bị chỉ mục và lỗi tách đoạn có thể lấn át lợi ích.

## Tổng quan phương pháp

[RAG của Lewis và cộng sự](https://arxiv.org/abs/2005.11401) kết hợp truy xuất tài liệu với mô hình sinh. Trong thí nghiệm này, RAG cơ sở dùng embedding đa ngôn ngữ cục bộ và cosine top 5. [GraphRAG của Edge và cộng sự](https://arxiv.org/abs/2404.16130) là một hướng nghiên cứu về biểu diễn/khai thác đồ thị cho câu hỏi trên corpus. Pipeline ở đây là **GraphRAG tự thiết kế**: đồ thị Document–Article–Topic–Audience, tìm hạt giống bằng TF-IDF ký tự, mở rộng cạnh chủ đề rồi trả về đoạn nguyên văn. Không tái lập quy trình cộng đồng và tóm tắt của Microsoft.

## Dữ liệu và xuất xứ

Nguồn được chỉ mục là [PDF bản hợp nhất trên SICT HaUI](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf), trang đăng [quy chế](https://sict.haui.edu.vn/vn/html/quy-che). Trang đầu PDF ghi bản hợp nhất QĐ 744/QĐ-ĐHCN ngày 19/08/2021 và QĐ 666/QĐ-ĐHCN ngày 01/06/2023. Điều 22 nêu văn bản bị thay thế. Điều này chỉ xác nhận nội dung của PDF; **hiệu lực hiện hành chưa được xác minh độc lập**. Manifest có URL, ngày truy cập UTC, SHA-256, số trang, lý do chọn/loại. Tám PDF ảnh quét và hai URL 404 ghi trong [data_audit.md](../docs/data_audit.md). Corpus chỉ áp dụng cho hỏi nội dung bản hợp nhất cụ thể, không tư vấn quy định hôm nay.

## Kiến trúc và thiết kế so sánh

1. PyMuPDF tách văn bản theo tiêu đề Điều và khoản, đoạn dài chia gần 1.100 ký tự; mỗi đoạn giữ ID, URL PDF, trang, SHA nguồn.
2. RAG vector dùng `paraphrase-multilingual-MiniLM-L12-v2` (384 chiều), chuẩn hóa vector và cosine top 5.
3. GraphRAG tạo 145 nút và 442 cạnh từ cấu trúc/chuỗi từ khóa; không có cạnh AMENDS chưa kiểm chứng. Câu hỏi tìm các hạt giống TF-IDF ký tự, mở rộng tối đa tới nút chủ đề liên quan rồi xếp hạng đoạn.
4. Cả hai giới hạn top 5, 6.500 ký tự ngữ cảnh, dùng cùng một prompt tiếng Việt và `gemini-3.5-flash-lite`. Không bật Search grounding. Lượt đo truy xuất dưới đây dùng `--retrieve-only`; lượt Gemini được báo riêng và có token API thật.
5. Thời gian `latency_ms` là thời gian truy xuất/câu hỏi sau khi tải model và chỉ mục vào bộ nhớ; chưa gồm thời gian khởi động, tải model, tạo chỉ mục hay mạng/API.

## Câu hỏi chuẩn và thước đo

`evaluation/questions.jsonl` được viết từ PDF trước khi chạy hai pipeline, gồm 12 câu một điều, 8 câu nhiều điều, 5 câu phiên bản/mốc áp dụng, 5 câu ngoài corpus. Không có nhóm nhiều văn bản vì chỉ có một PDF đọc được; đây là thiếu hụt lớn so với mục tiêu ban đầu. Chưa có người phản biện độc lập đối chiếu câu hỏi và đáp án chuẩn.

Với câu có tập đoạn chuẩn `G`, `Recall@5 = |G ∩ R5| / |G|`, trong đó `R5` là tối đa năm ID được truy xuất. Trung bình nhóm là trung bình theo câu có `G` không rỗng. Nhóm ngoài corpus có mẫu số 0, nên không báo Recall. Phiếu chấm tay Gemini: đúng nội dung 0/1, đủ ý 0/1, dẫn đúng điều/khoản 0/1; từ chối phù hợp chỉ tính được khi có câu ngoài corpus. Hiện đã chấm **14 câu trả lời thuộc 7 cặp**; chưa có người phản biện độc lập.

## Kết quả đo thật

Lượt đo `retrieve_only`, 30 câu × 2 pipeline = 60 hàng. Bảng dưới đọc trực tiếp từ `evaluation/summary.csv`; độ trễ tính bằng ms và có tính lần chạy đầu trong phiên.

| Nhóm | Số câu có gold | RAG Recall@5 | GraphRAG Recall@5 | RAG độ trễ TB | GraphRAG độ trễ TB |
|---|---:|---:|---:|---:|---:|
| Một điều | 12 | 0,8333 | 0,8333 | 17,43 | 1,14 |
| Nhiều điều | 8 | 0,6250 | 0,6250 | 8,46 | 1,19 |
| Phiên bản | 5 | 0,8000 | 1,0000 | 9,60 | 1,28 |
| Ngoài corpus | 0/5 | không tính | không tính | 8,30 | 1,06 |
| Tất cả câu có gold | 25 | 0,7600 | 0,8000 | — | — |

Độ trễ GraphRAG thấp trong lần chạy truy xuất vì dùng TF-IDF ký tự/đồ thị đã nạp, còn RAG phải mã hóa vector câu hỏi bằng Transformer. Lượt `prepare` cuối ghi trong `data/processed/build_meta.json`: tách PDF 509,00 ms, nạp mô hình và tạo vector 10.805,11 ms, dựng đồ thị cấu trúc 3,70 ms (chưa gồm khởi tạo TF-IDF khi mở ứng dụng); tổng 11.317,81 ms. Đây là thời gian máy của một lượt chạy, không đo công sức đối chiếu/OCR thủ công. Không có dữ liệu giá tiền API để ước tính chi phí.

### Checkpoint sinh đáp án Gemini

Trên cùng **7 cặp** S01–S07, hai phương pháp cùng đạt 6/7 đúng nội dung, 4/7 đủ ý, 6/7 dẫn đúng nguồn. Độ trễ trung bình gồm truy xuất và API là 2.095,06 ms (RAG) và 1.865,28 ms (GraphRAG). Tổng token API tương ứng 6.920 và 9.763; độ dài chứng cứ thực tế khác nhau dù cùng mức trần, nên không coi đây là so sánh chi phí đã kiểm soát hoàn toàn. Checkpoint có 24 lượt API: S08 GraphRAG từng gặp `429 RESOURCE_EXHAUSTED` khi script chưa có bộ điều tiết nhịp; không đủ dữ liệu để biết đã chạm RPM, TPM hay hạn mức ngày. Các lần thử sau gặp `503 UNAVAILABLE` dù đã giãn tối thiểu 5 giây giữa hai lượt (~12 lượt/phút). Một lượt xác minh sau khi khóa SDK ở một request HTTP vẫn gặp 503. S08–S10 không được tính vào thống kê cặp. Chưa có kết quả Gemini cho câu nhiều điều, phiên bản hay ngoài corpus. Xem [file đánh giá chi tiết](../evaluation/BAO_CAO_DANH_GIA_GEMINI.md) trước khi đưa số liệu vào báo cáo nộp.

## Phân tích trường hợp

- GraphRAG truy xuất tốt hơn ở S05 (1 so với 0): đoạn Điều 9 khoản 1 là hạt giống TF-IDF nhưng vector chọn phần tiếp theo của khoản. M02 (1 so với 0,5): đồ thị tìm được cả Điều 7 khoản 5 và khoản 10. M03 (1 so với 0,5): tìm được cả Điều 9 khoản 4 và Điều 8 khoản 6. Đây là cải thiện **truy xuất**, chưa phải cải thiện câu trả lời.
- RAG tốt hơn ở S07 (1 so với 0): vector có Điều 9 khoản 7 chứa ngưỡng A/F, còn đồ thị ưu tiên các đoạn khác về điểm. M01 (1 so với 0,5): vector lấy cả điều kiện và thời hạn tốt nghiệp, đồ thị thiếu khoản 1. M05 (0,5 so với 0): đồ thị không tìm được hai đoạn chuẩn về chuyển đổi tín chỉ và tốt nghiệp. Điều này cho thấy mở rộng theo chủ đề vẫn có thể lấn chỗ đoạn cần tìm trong top 5.
- Hai cách đều chưa tốt ở câu nhiều điều: 0,625 trung bình. Một số đoạn bị chia đôi và chú thích chân trang lẫn vào câu; khả năng truy xuất phụ thuộc mạnh vào câu chữ của bộ câu hỏi và gold ID do một người đặt.

## Hạn chế, hướng mở rộng và kết luận

Phạm vi chỉ một PDF, thiếu OCR cho tám nguồn, không có câu nhiều văn bản, không xác minh hiệu lực hiện hành; Gemini mới có 7 cặp một điều, các lần thử thêm gặp lỗi dịch vụ. Năm câu ngoài corpus vẫn có thể nhận đoạn gần nghĩa từ bộ truy xuất; chưa thể chấm khả năng từ chối của hệ thống sinh. Bước có tác động lớn nhất là OCR tiếng Việt và đối chiếu thủ công văn bản đánh giá học phần/đồ án cùng quan hệ sửa đổi; sau đó khóa lại bộ câu hỏi nhiều văn bản, chạy cùng ID qua Gemini với quota có kiểm soát và chấm tay độc lập.

Với phép đo truy xuất, GraphRAG tự thiết kế hơn 0,04 Recall@5 trung bình trên 25 câu có gold, nhưng ngang RAG vector ở nhóm nhiều điều. Với 7 cặp Gemini đã chấm, hai bên ngang nhau ở ba thước đo chấm tay. Chưa có bằng chứng về ưu thế chất lượng câu trả lời.

## Tài liệu tham khảo

1. [PDF quy chế hợp nhất HaUI](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf), truy cập 28/09/2026.
2. [Lewis và cộng sự, RAG (2020)](https://arxiv.org/abs/2005.11401).
3. [Edge và cộng sự, GraphRAG (2024)](https://arxiv.org/abs/2404.16130).
4. [Google, Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), mã model đã được thử với key trong `.env`.

Tái tính: `python3 -m src.project evaluate --retrieve-only`. Hàng chi tiết: `evaluation/results.csv`; trace và đoạn gốc theo câu: `evaluation/runs/latest.json`; đáp án chuẩn: `evaluation/questions.jsonl`.
