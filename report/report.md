# So sánh RAG vector và GraphRAG có quan hệ văn bản trên dữ liệu HaUI

Ngày cập nhật: 28/09/2026. Đây là bản thử nghiệm nghiên cứu trên tập nguồn đã thu thập, **không phải công cụ xác nhận quy định hiện hành**.

## Tóm tắt

Từ 11 nguồn ứng viên trên tên miền HaUI, dự án tải được 9 PDF. Bản hợp nhất quy chế đào tạo có lớp chữ; 8 PDF còn lại là ảnh quét và đã được người dùng cung cấp bản OCR dạng Markdown. Corpus hiện có **9 văn bản, 449 đoạn**, mỗi đoạn dẫn về trang PDF gốc. Đồ thị gồm 480 nút, 1.872 cạnh, trong đó 22 cạnh quan hệ văn bản được lưu kèm câu dẫn và trang chứng cứ. Các văn bản được nhắc tới nhưng không có toàn văn chỉ là nút tham chiếu, không được dùng làm chứng cứ trả lời.

Trên bộ 30 câu hỏi ban đầu (25 câu có đoạn chuẩn), Recall@5 sau mở rộng corpus là **0,70 với RAG vector** và **0,74 với GraphRAG**. Trên 8 câu kiểm tra quan hệ được viết sau khi dựng đồ thị, GraphRAG tìm đủ đoạn chuẩn ở 8/8 câu, RAG vector ở 0/8; đây là phép **kiểm tra khả năng truy xuất cạnh đã tạo**, không phải bộ đánh giá độc lập để khẳng định ưu thế chất lượng chung. Chưa chạy/chấm Gemini trên corpus mới. Kết quả 7 cặp Gemini trước đây thuộc corpus một PDF và được giữ riêng.

## Mục tiêu và phạm vi

Đề tài hỏi liệu tổ chức chứng cứ thành đồ thị văn bản, đoạn, chủ đề và quan hệ sửa đổi/thay thế có hỗ trợ truy xuất điều khoản tốt hơn RAG vector đơn thuần hay không. Hai phương pháp dùng chung 9 PDF, cùng số đoạn tối đa `top_k=5`, cùng giới hạn 6.500 ký tự chứng cứ và cùng prompt Gemini khi sinh đáp án. Phương pháp được gọi là **GraphRAG tự thiết kế**, không tái lập thuật toán cộng đồng của Microsoft GraphRAG.

Nguồn gồm quy chế hợp nhất QĐ 744/2021 và 666/2023, văn bản sửa đổi QĐ 847/2017 và 663/2019, Thông tư 08/2021, quy định đồ án/khóa luận, ngoại ngữ, học phần thay thế, đánh giá kết quả học tập. [Manifest](../data/source_manifest.csv) lưu URL trang, URL PDF, thời gian truy cập, SHA-256, số trang, số ký tự OCR và trạng thái hiệu đính. Hai URL 404 không có trong corpus.

**Hiệu lực hiện hành chưa được xác minh độc lập.** Quan hệ `REPLACES` nói rằng *văn bản nguồn ghi thay thế văn bản đích*; nó không chứng minh nguồn còn hiệu lực vào hôm nay. Một số văn bản được dẫn trong đồ thị chưa có toàn văn. Không dùng kết quả này để kết luận quyền hoặc nghĩa vụ của cá nhân.

## Xử lý dữ liệu và kiểm soát OCR

1. Bản PDF hợp nhất được PyMuPDF trích chữ, tách theo Điều/khoản và chia đoạn dài gần 1.100 ký tự; tạo 136 đoạn tính cả lời mở đầu.
2. Tám bản Markdown OCR từ ZIP của người dùng được tách bằng mốc `## Trang N`. Script kiểm tra số trang liên tục, khớp số trang PDF và SHA-256 PDF/OCR trong manifest; giữ chữ OCR, chỉ ghép khoảng trắng và chia thành đoạn tối đa 1.000 ký tự **trong cùng một trang**. Tạo 313 đoạn OCR. Mỗi đoạn có ID, văn bản, URL PDF, trang và cờ `page_matched_unreviewed`.
3. Không tự sửa hàng loạt số quyết định hoặc số liệu bị OCR nhận dạng sai. Các cạnh pháp lý chỉ được đưa vào khi câu dẫn nằm trong trang và đoạn được lập chỉ mục. Một số số hiệu ở trang đầu đã được đối chiếu trực tiếp với PDF; phần còn lại cần hiệu đính thêm, nhất là bảng học phần.

Mã xử lý: [ocr_corpus.py](../src/ocr_corpus.py), [project.py](../src/project.py) và [legal_graph.py](../src/legal_graph.py). Bản OCR nguyên vẹn ở [data/ocr](../data/ocr); PDF gốc ở [data/raw](../data/raw). [Kiểm tra dữ liệu chi tiết](../docs/data_audit.md).

## Hai pipeline truy xuất

**RAG vector:** dùng `paraphrase-multilingual-MiniLM-L12-v2` chạy cục bộ, mean pooling có attention mask, chuẩn hóa vector 384 chiều. Câu hỏi được mã hóa cùng cách, lấy 5 đoạn có cosine lớn nhất. Vector giúp chọn đoạn; Gemini nhận nguyên văn đoạn và metadata, không nhận vector.

**GraphRAG:** tạo nút `Document`, `Article` (mỗi đoạn), `Topic`, `Audience`. Cạnh cấu trúc gồm `CONTAINS`, `NEXT`, `ABOUT`, `APPLIES_TO`; cạnh pháp lý có hướng gồm `AMENDS`, `REPLACES`, `SUPPLEMENTS`, `CONSOLIDATES`, `CITES`. Có 9 nút văn bản trong corpus và 13 nút văn bản chỉ được nhắc tên. Trong 22 cạnh pháp lý, mọi cạnh có `evidence_article_ids`, URL PDF và trang; script dừng dựng chỉ mục nếu câu dẫn không tìm thấy trong đúng đoạn. [Danh sách cạnh và chứng cứ](../data/processed/legal_relations.json).

Khi hỏi, GraphRAG lấy đoạn hạt giống bằng TF-IDF ký tự và vector, mở rộng qua chủ đề, đoạn kế cận và tối đa hai bước trên cạnh văn bản. Với câu hỏi chỉ rõ số hiệu/văn bản và loại quan hệ, hệ thống ưu tiên đoạn chứng cứ của cạnh đã kiểm tra. Sau đó xếp lại bằng `0,55 × TF-IDF + 0,45 × cosine`, cộng điểm cho chứng cứ quan hệ được hỏi, chọn tối đa 5 đoạn. Cạnh `CITES` chỉ là viện dẫn/căn cứ, không bị diễn giải thành sửa đổi hoặc thay thế. Sơ đồ, quy tắc và ví dụ nằm trong [tài liệu đồ thị](../docs/OCR_AND_LEGAL_GRAPH.md).

GraphRAG mới cũng dùng encoder vector tại lúc hỏi; vì vậy đây là so sánh **RAG vector với truy xuất lai có đồ thị**, không phải phép tách riêng tác động của đồ thị khỏi tác động của TF-IDF/vector. Chi phí truy xuất phải được đọc cùng thước đo chất lượng.

## Thiết kế đánh giá

Bộ [30 câu cũ](../evaluation/questions.jsonl) được viết trước khi thêm OCR: 12 câu một điều, 8 câu nhiều điều, 5 câu phiên bản và 5 câu ngoài corpus. Gold ID của 25 câu trả lời được đều thuộc bản hợp nhất. Khi mở rộng sang 9 PDF, một số câu không nêu rõ phiên bản trở nên mơ hồ; vì vậy bảng mới là phép kiểm tra độ ổn định truy xuất khi tăng corpus, không phải so sánh pháp lý đầy đủ giữa các văn bản.

Bộ [8 câu quan hệ](../evaluation/questions_multidoc_ocr.jsonl) dùng các cạnh vừa tạo và đáp án từ trang chứng cứ, nhằm kiểm tra việc truy xuất các quan hệ mới. Bộ này được viết **sau khi thiết kế đồ thị**, do cùng người làm dự án đặt gold, nên có thiên lệch thuận lợi cho GraphRAG. Cần bộ câu hỏi mới do người khác soạn trước khi kết luận về chất lượng tổng quát.

`Recall@5 = |gold ID ∩ 5 ID truy xuất| / |gold ID|`. `All gold found` đếm câu tìm đủ mọi đoạn chuẩn. Không tính Recall cho câu ngoài corpus. Mỗi script làm nóng cả hai đường truy xuất trước khi đo. Độ trễ là thời gian truy xuất sau khi chỉ mục/model đã nạp, không gồm OCR, tạo vector, mạng hay sinh đáp án; nó có thể dao động theo tải máy.

## Kết quả thực đo

### Bộ 30 câu ban đầu trên corpus 9 PDF

| Nhóm | Câu có gold | RAG Recall@5 | GraphRAG Recall@5 | RAG độ trễ TB (ms) | GraphRAG độ trễ TB (ms) |
|---|---:|---:|---:|---:|---:|
| Một điều | 12 | 0,8333 | 0,8333 | 14,12 | 15,28 |
| Nhiều điều | 8 | 0,5625 | 0,4375 | 17,11 | 22,65 |
| Phiên bản | 5 | 0,6000 | 1,0000 | 16,14 | 21,09 |
| Ngoài corpus | 0/5 | không tính | không tính | 17,39 | 20,92 |
| Tất cả câu có gold | 25 | **0,7000** | **0,7400** | — | — |

Kết quả chi tiết có tại [results.csv](../evaluation/results.csv), [summary.csv](../evaluation/summary.csv), [trace từng lượt](../evaluation/runs/latest.json). Trước OCR, trên corpus 1 PDF/135 đoạn, hai giá trị toàn bộ là 0,76 và 0,80; [bản chụp kết quả cũ](../evaluation/runs/baseline_pre_ocr) được giữ để đối chiếu. Cả hai giảm 0,06 sau khi thêm nhiều văn bản cạnh tranh trong top 5; không nên lấy hai lần chạy này làm bằng chứng đồ thị tự nó gây tăng/giảm chất lượng vì corpus và thuật toán GraphRAG cùng thay đổi.

### Tám câu kiểm tra quan hệ pháp lý

| Thước đo | RAG vector | GraphRAG |
|---|---:|---:|
| Recall@5 trung bình | 0,1875 | 1,0000 |
| Tìm đủ mọi gold ID | 0/8 | 8/8 |
| Độ trễ trung vị | 12,61 ms | 16,62 ms |

Ví dụ, câu về QĐ 1077/2023 cần chứng cứ ở trang 1 (căn cứ Thông tư 08/2021) và trang 2 (thay QĐ 239/2022); GraphRAG tìm cả hai, RAG chỉ tìm trang 2. Câu hỏi QĐ 721/2024 thay văn bản nào lấy đúng trang 1 nhờ cạnh `REPLACES`. Kết quả từng câu, gold, top 5 và trace nằm trong [multidoc_ocr_retrieval.json](../evaluation/runs/multidoc_ocr_retrieval.json). Đây chỉ là phép thử truy xuất chứng cứ cạnh, **chưa đo độ đúng câu trả lời Gemini**.

### Chi phí tạo chỉ mục và kết quả Gemini trước OCR

Lượt dựng chỉ mục mới ghi nhận 0,52 giây tách/ghép văn bản, 23,48 giây tạo vector, 0,02 giây dựng đồ thị, tổng 24,03 giây trên máy thử nghiệm. Không tính thời gian người dùng OCR, thời gian rà PDF hoặc tải mô hình lần đầu. Số liệu nằm ở [build_meta.json](../data/processed/build_meta.json).

[Báo cáo Gemini trước OCR](../evaluation/BAO_CAO_DANH_GIA_GEMINI.md) ghi 7 cặp S01–S07 trên 1 PDF/135 đoạn: mỗi phương pháp đúng nội dung 6/7, đủ ý 4/7, dẫn đúng nguồn 6/7. Các lượt tiếp theo gặp 429/503. **Không chuyển điểm LLM này sang corpus mới.** [Lượt thử Gemini sau OCR](../evaluation/BAO_CAO_GEMINI_SAU_OCR.md) ghi hai request R01 với model 3.5 Flash-Lite đều trả 503; một lượt kiểm tra ứng dụng S02 với key mới và model 3.8 Flash đã trả lời, dẫn nguồn hợp lệ. Chưa có cặp RAG/GraphRAG thành công trên corpus mới để chấm. Run đánh giá mới cần ID riêng và khóa dấu vân tay chỉ mục.

## Hạn chế và hướng tiếp theo

- OCR có lỗi ở dấu, số hiệu, bảng và nội dung vắt qua trang. Khớp số trang/SHA chỉ xác minh xuất xứ, không chứng minh toàn bộ câu chữ chính xác. Cần người đọc soát từng trang liên quan đến câu trả lời trước khi công bố kết luận pháp lý.
- Đồ thị có 22 quan hệ đã kiểm tra trong phạm vi nguồn; các quan hệ khác của toàn hệ thống văn bản HaUI có thể chưa thu thập. Nút văn bản chưa có toàn văn không được dùng để trả lời nội dung của văn bản đó.
- Hiệu lực hiện hành và quan hệ với văn bản mới sau 2024 chưa được xác minh đầy đủ. Câu hỏi “hiện nay áp dụng quy định nào?” cần quy trình đối chiếu nguồn chính thức và ngày hiệu lực riêng.
- Bộ 8 câu quan hệ do người xây hệ thống đặt sau khi tạo đồ thị, chỉ nên xem là kiểm thử chức năng. Cần bộ đánh giá độc lập, chấm tay câu trả lời hai pipeline và ghi rõ sai số OCR.
- Khi Gemini hoạt động ổn định, tạo run mới trên chỉ mục cuối cùng và cùng bộ câu hỏi, giãn tối thiểu 5 giây/lượt. Run lỗi `post_ocr_relations` được giữ nguyên dấu vân tay của đồ thị trước lần cập nhật nhãn kiểm chứng; không nối tiếp run đó với chỉ mục hiện tại. Không trộn với 7 cặp trước OCR.

## Tái lập và tài liệu

```bash
python3 -m src.sources
python3 -m src.project prepare
python3 -m src.project evaluate --retrieve-only
python3 -m evaluation.evaluate_multidoc
```

Nguồn nghiên cứu: [Lewis và cộng sự, RAG](https://arxiv.org/abs/2005.11401); [Edge và cộng sự, GraphRAG](https://arxiv.org/abs/2404.16130). Quan hệ thay thế 254/2023 và 1432/2023 được đối chiếu thêm trên [PDF QĐ 721/2024 của HaUI](https://cps.haui.edu.vn/media/quyet-dinh-721-ngay-03-06-2024-ve-viec-ban-hanh-quy-dinh-to-chuc-dgkqht-cua-nguoi-hoc-truong-dhcn-hn%20%285%29.pdf); quan hệ QĐ 663/2019 sửa QĐ 787/2018 trên [PDF HaUI](https://dttc.haui.edu.vn/media/2/uftai-ve-tai-day2712.pdf).
