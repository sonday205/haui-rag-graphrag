# Bàn giao phiên làm việc: OCR và GraphRAG HaUI

## Cập nhật mới nhất — 01/10/2026

Đọc [báo cáo sửa lỗi](docs/FIX_REPORT_2026-10-01.md) và [thực nghiệm mới](evaluation/runs/research_20261001/BAO_CAO_THUC_NGHIEM.md) trước các ghi chép lịch sử bên dưới. Model hiện tại trong `.env` là `gemini-3.5-flash-lite`; 40 request/20 cặp đã chạy thành công về dịch vụ, nhịp thực tế tối thiểu 5,000067 giây. Một lỗi parser citation nhóm được sửa và revalidate JSON đã lưu offline; không sửa log gốc hoặc gọi thêm API.

- Đã sửa sáu vấn đề review, thêm parser citation nhóm; 15 test hồi quy và build frontend qua.
- Chỉ mục 9 PDF/449 đoạn lưu theo phiên bản atomic, có hash artifact/cấu hình encoder. Vector cửa sổ 256 token, overlap 64; 160 đoạn dài được giữ cả phần cuối. ID/text/gold giữ nguyên; corpus thêm metadata ngày cho bản hợp nhất.
- Checkpoint khóa model hiệu dụng/runtime/script; không dùng lại run cũ sau đổi model/corpus/code. `evaluate` và evaluator multidoc tạo run mới, không ghi đè số liệu cũ.
- Phép đo mới: trên 25 câu có gold của bộ 30, Recall RAG 0,74, hybrid 0,72, GraphRAG 0,78; tìm đủ mọi gold 17/25, 15/25, 16/25. Bộ 8 quan hệ: 0,25/0,625/1,00.
- Bộ LLM 20 câu gồm 16 có đáp án và 4 ngoài corpus. Đối chiếu sơ bộ bằng trợ lý AI: đúng RAG 8/16, GraphRAG 11/16; đủ 4/16 và 8/16; nguồn 9/16 và 12/16; từ chối đúng ngoài corpus 4/4 cả hai. Chưa có chấm độc lập, không tuyên bố ưu thế tổng quát.
- Điểm yếu cần nghiên cứu tiếp: S07 GraphRAG chọn sai trọng tâm/phiên bản; M02 cả hai thiếu phân biệt 33 tín chỉ tạm với 27 khối lượng học kỳ; M05/M08 thiếu một phần chứng cứ; model thường lược bỏ ngoại lệ. Không hard-code các câu này.
- Nguồn thô/phiếu chấm/CSV/trace có trong `evaluation/runs/research_20261001/`; snapshot trước sửa ở `evaluation/runs/pre_fix_20261001/` và `data/processed/versions/legacy_pre_atomic/`.

Các số liệu/ngữ cảnh dưới đây là lịch sử ngày 28/09, không phải trạng thái hiện tại.

Cập nhật ngày 28/09/2026. Đọc file này trước khi tiếp tục mở rộng dự án OCR/GraphRAG HaUI. Phần tích hợp OCR, đồ thị có chứng cứ, tài liệu và kiểm tra truy xuất đã hoàn tất trong phạm vi nêu dưới đây; các việc đánh giá LLM và hiệu đính toàn bộ còn phụ thuộc dịch vụ/đối chiếu nguồn.

## Trạng thái đã kiểm tra

- ZIP đầu vào: `data/pdf_to_markdown_md_files.zip`; 9 Markdown đã giải nén trong `data/ocr/`. Tám PDF ảnh quét dùng Markdown OCR; bản hợp nhất 2023 tiếp tục lấy chữ trực tiếp từ PDF.
- `src/ocr_corpus.py` kiểm tra SHA-256, thứ tự/số trang OCR khớp PDF và chia đoạn trong từng trang. `src/sources.py` cập nhật manifest, gồm ký tự/hash OCR, lý do chọn nguồn; không tự sửa đại trà lỗi nhận dạng chữ/số.
- `src/legal_graph.py` dựng đồ thị và kiểm tra câu chứng cứ trong đúng trang/đoạn. `data/relations_reviewed.json` chứa 22 quan hệ có hướng: `REPLACES`, `AMENDS`, `SUPPLEMENTS`, `CONSOLIDATES`, `CITES`. `data/processed/legal_relations.json` là kết quả đã gắn ID đoạn và URL PDF. Các nút văn bản chưa có toàn văn chỉ là tham chiếu; tình trạng hiệu lực vẫn `unknown`.
- `src/project.py` đã ghép corpus OCR, tạo đoạn mở đầu của bản hợp nhất và dùng cạnh quan hệ trong GraphRAG. `server.py` và `frontend/src/App.tsx` đã được cập nhật sơ bộ để hiện corpus/trace mới.
- Lần chạy `python3 -m src.project prepare` thành công: **9 văn bản, 449 đoạn** (136 PDF có chữ + 313 OCR), vector 384 chiều, **480 nút, 1.872 cạnh**. `data/processed/build_meta.json` ghi tổng thời gian khoảng 21,96 giây.
- Lần chạy `python3 -m src.project evaluate --retrieve-only`: trên 25/30 câu có gold, Recall@5 trung bình RAG **0,70**, GraphRAG **0,74**. Bộ 8 câu kiểm tra quan hệ tại `evaluation/questions_multidoc_ocr.jsonl`: RAG **0,1875** và tìm đủ gold **0/8**; GraphRAG **1,0** và **8/8**. Bộ 8 câu được viết sau khi dựng đồ thị, cùng người thiết kế, nên chỉ là kiểm thử chức năng thiên về GraphRAG, không phải đánh giá độc lập. Kết quả ở `evaluation/runs/multidoc_ocr_retrieval.json`.
- Đã chụp bộ dữ liệu/kết quả trước OCR vào `evaluation/runs/baseline_pre_ocr/`. Báo cáo cũ ở `report/report_pre_ocr.md`; `report/report.md` đã được viết lại cho corpus mới. **Chưa chạy Gemini trên corpus mới**, không trộn 7 cặp Gemini cũ với dữ liệu mới.
- `evaluation/run_gemini.py` đã có `--run-id`, fingerprint corpus/vector/graph/code và nhịp tối thiểu 4,5 giây (mặc định 5 giây). Checkpoint cũ bị chặn khi dùng corpus mới. Không in hoặc đưa `.env`/API key vào báo cáo.

## Tiến độ sau bản bàn giao đầu

- Đã tạo `docs/OCR_AND_LEGAL_GRAPH.md`, cập nhật README, `docs/data_audit.md`, `docs/decisions.md`, `docs/demo_script.md`, `.gitignore`, báo cáo `report/report.md` và nhãn trước OCR của `evaluation/BAO_CAO_DANH_GIA_GEMINI.md`.
- Đã sửa kiểm tra ID nguồn Gemini để nhận cả đoạn PDF có chữ và đoạn OCR. Nhãn cạnh là `ocr_page_and_chunk_verified`, diễn đạt đúng mức kiểm tra; dựng lại chỉ mục thành công: 9 PDF, 449 đoạn, 480 nút, 1.872 cạnh, 22 cạnh pháp lý. Lần dựng cuối `data/processed/build_meta.json`: 24,03 giây.
- `python3 -m compileall -q src evaluation server.py` và `npm run build --prefix frontend` đã qua. API health trả 9/449/8; `POST /api/chat` chế độ `graph_rag` + `retrieve_only` với câu QĐ 721 trả chứng cứ trang 1 và trace cạnh.
- Hai bộ truy xuất đã chạy lại sau lần dựng cuối: 25 câu có gold trong bộ cũ RAG 0,70/GraphRAG 0,74; 8 câu quan hệ RAG 0,1875/GraphRAG 1,0. `evaluation/evaluate_multidoc.py` đã ghi fingerprint. Độ trễ đo lại trong `evaluation/summary.csv` và JSON; xem `report/report.md`.
- Đã gọi thử Gemini sau OCR trên R01 bằng run `post_ocr_relations`: RAG và GraphRAG đều nhận HTTP 503, bắt đầu cách nhau 5 giây; script dừng sau hai lỗi. `evaluation/BAO_CAO_GEMINI_SAU_OCR.md` ghi chi tiết. Run này dùng dấu vân tay trước lần đổi nhãn cạnh, nên **không tiếp tục trên chỉ mục hiện tại**; khi dịch vụ ổn định dùng run ID mới, ví dụ `post_ocr_relations_v2`.
- Kiểm tra ứng dụng với key mới: frontend HTML/JS/CSS, health, suggestions đều trả 200; `POST /api/chat` chế độ `rag` và `gemini-3.8-flash` trả một câu trả lời S02 có dẫn Điều 7 khoản 10, `error=null`. `.env` đã đặt model này, không lộ key. Model 3.5 Flash-Lite trả 503, model 2.5 Flash-Lite trả 404 với key mới. Trình duyệt tích hợp không khả dụng, nên chưa xác nhận giao diện bằng mắt.
- Người dùng sau đó gửi ảnh chế độ so sánh gặp hai lỗi 503 dù server đang dùng `gemini-3.8-flash`. Đã sửa `server.py` giãn 5 giây giữa lượt gọi và không gọi Gemini thứ hai sau 503/429; `src/project.py` tạo thông báo lỗi ngắn; `frontend/src/App.tsx` hiện trạng thái quá tải và chuyển lỗi cũ sang lời dễ hiểu. Build và mô phỏng API lỗi 503 đã qua; máy chủ đã khởi động lại trên `127.0.0.1:8000`. Chưa gọi Gemini sau sửa.

## Việc còn lại nếu tiếp tục mở rộng

1. Hiệu đính các trang OCR chứa số hiệu/bảng được dùng để trả lời, đối chiếu trực tiếp PDF ảnh. Giữ bản OCR gốc và ghi nhật ký hiệu đính; sau đó cập nhật manifest hash, dựng lại chỉ mục và đo lại. Hiện kiểm tra chỉ xác nhận hash và vị trí trang.
2. Rà thêm tham chiếu văn bản còn chưa có cạnh, ví dụ 945/QĐ-TTg, 4811/QĐ-BCT, 862/QĐ-ĐHCN, 366/QĐ-ĐHCN, 1224/QĐ-ĐHCN, 1202/QĐ-ĐHCN. Chỉ thêm cạnh khi đã xác định đúng số hiệu, vai trò `CITES`/khác và trang chứng cứ. 22 cạnh hiện tại **không phải mọi quan hệ** trong 9 PDF.
3. Khi Gemini hết lỗi 503, chạy run mới `python3 -m evaluation.run_gemini --run-id post_ocr_relations_v2 --questions-file questions_multidoc_ocr.jsonl --ids R01 R02 R03 --max-new-calls 2`; script giãn ít nhất 5 giây. Chỉ chấm cặp đủ hai kết quả và ghi vào báo cáo sau OCR. Không trộn với checkpoint 1 PDF trước OCR.
4. Nhờ người khác soạn và chấm bộ câu hỏi nhiều văn bản độc lập trước khi kết luận chất lượng chung của GraphRAG. Kiểm tra thêm văn bản mới và ngày hiệu lực trước mọi kết luận về quy định hiện hành.

## Lưu ý khi báo cáo cho người dùng

- Giải thích bằng tiếng Việt, nêu cụ thể file, thay đổi, lệnh chạy và kết quả đã **thực sự** test.
- OCR có lỗi tiếng Việt, đặc biệt số, dấu và bảng; khớp trang/SHA chỉ xác nhận xuất xứ. `REPLACES` là điều văn bản nguồn ghi, không chứng minh nguồn còn hiệu lực hôm nay.
- Bộ 30 câu cũ có gold thuộc bản hợp nhất, nên giảm Recall khi mở rộng corpus không trực tiếp đo chất lượng pháp lý. Bộ 8 câu quan hệ là thử chức năng, không phải benchmark độc lập.
- Nguồn chính thức đã đối chiếu: QĐ 721/2024 trên `https://cps.haui.edu.vn/media/quyet-dinh-721-ngay-03-06-2024-ve-viec-ban-hanh-quy-dinh-to-chuc-dgkqht-cua-nguoi-hoc-truong-dhcn-hn%20%285%29.pdf`; QĐ 663/2019 trên `https://dttc.haui.edu.vn/media/2/uftai-ve-tai-day2712.pdf`; QĐ 847/2017 trên `https://dttc.haui.edu.vn/media/2/uftai-ve-tai-day2542.pdf`.
