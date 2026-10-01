# PROMPT GIAO CHO CODEX: THỰC HIỆN DỰ ÁN RAG VÀ GRAPH RAG VỚI QUY CHẾ HaUI

Bạn là Codex, chịu trách nhiệm triển khai trọn vẹn một **bản thử nghiệm nghiên cứu khoa học sinh viên** có mã nguồn, dữ liệu kiểm chứng được, thực nghiệm, ứng dụng demo và báo cáo tiếng Việt. Hãy bắt tay làm việc trong thư mục dự án hiện tại. **Không dừng ở việc lập kế hoạch, tạo khung rỗng hoặc viết báo cáo giả định**. Sau mỗi giai đoạn, kiểm tra sản phẩm rồi tiếp tục đến khi hoàn thành. Hạn nộp dự kiến: **29/09/2026, theo giờ Việt Nam**. Ưu tiên một kết quả nhỏ nhưng chạy và kiểm chứng được.

## 1. Bối cảnh và mục tiêu

- Đề tài: **So sánh RAG truyền thống và GraphRAG trong hỏi đáp có dẫn nguồn về quy chế đào tạo, kiểm tra–thi và xét tốt nghiệp của Trường Đại học Công nghiệp Hà Nội (HaUI)**.
- Người thực hiện là một sinh viên, cần **báo cáo và ứng dụng demo** cho bài tập lớn. Đây là bản thử nghiệm để sau đó mở rộng thành nghiên cứu khoa học.
- So sánh khách quan cả ưu điểm, nhược điểm: độ đúng, độ đầy đủ, dẫn nguồn, truy xuất, khả năng từ chối, độ trễ, lượng lời gọi/token API, công sức chuẩn bị chỉ mục và lỗi do dữ liệu. Không đặt trước kết luận GraphRAG tốt hơn.
- Phương án đã chọn: **RAG vector cơ sở so với GraphRAG tự thiết kế theo quan hệ văn bản/điều khoản**; không cần cài nguyên framework Microsoft GraphRAG. Gọi đúng tên phương pháp trong báo cáo: một bản GraphRAG theo thiết kế riêng, không giả nhận rằng đã tái lập thuật toán Microsoft.
- Mô hình sinh câu trả lời dự định: Gemini, mã `gemini-3.5-flash-lite`, dùng API key của người dùng trong biến môi trường. Kiểm tra tên mô hình, quyền truy cập và hạn mức thực tế trước khi chạy. Không yêu cầu người dùng gửi key trong chat, không ghi key vào repo, log hoặc báo cáo.

## 2. Quyền chủ động và quy tắc làm việc

1. Tự quyết định các lựa chọn kỹ thuật hợp lý, giải thích ngắn trong `docs/decisions.md`. Chỉ hỏi người dùng nếu thực sự thiếu thông tin không thể suy ra hoặc cần họ thiết lập API key. Nếu thiếu key, vẫn hoàn thành pipeline dữ liệu, chỉ mục, truy xuất, câu hỏi chuẩn, giao diện ở chế độ kiểm tra truy xuất và hướng dẫn chạy sau khi thêm key; tuyệt đối không tạo câu trả lời hoặc điểm số giả.
2. Trước khi viết mã, kiểm tra thư mục hiện tại để tránh ghi đè công việc có sẵn. Nếu dự án chưa tồn tại, tạo cấu trúc tối giản. Không phá hủy dữ liệu hoặc sửa nội dung nguồn đã tải.
3. Chỉ thu thập tài liệu **truy cập công khai trên tên miền chính thức của HaUI** (ví dụ các trang/tiểu miền `haui.edu.vn`). Không vượt đăng nhập, CAPTCHA, kiểm soát truy cập; không thu thập hồ sơ cá nhân. Tải với tốc độ vừa phải, tránh request hàng loạt. Mỗi tệp phải giữ URL gốc, thời điểm truy cập và hash SHA-256.
4. Văn bản cũ, văn bản sửa đổi và văn bản thay thế phải được đánh dấu. Không suy đoán hiệu lực hiện hành; nếu chưa xác minh được, ghi `unknown` và giới hạn câu hỏi về nội dung văn bản cụ thể thay vì tư vấn quy định đang có hiệu lực.
5. Không tự tạo điều khoản, URL, kết quả đánh giá, chi phí hay ảnh màn hình. Mỗi câu trả lời phải dẫn lại chứng cứ từ đoạn văn gốc. Nếu không có đủ chứng cứ, trả lời rằng chưa xác định được từ tập tài liệu.
6. Mỗi giai đoạn cần xuất tệp và một lệnh kiểm tra. Khi lỗi tải nguồn, PDF/OCR hoặc hạn mức API, ghi lý do, xử lý phần còn lại, giảm phạm vi có khai báo; không âm thầm điền dữ liệu bịa.
7. Viết mã và chú thích đủ dễ hiểu để một sinh viên có thể trình bày trước giảng viên. Viết tài liệu, báo cáo và giao diện bằng tiếng Việt.

## 3. Phạm vi và tiêu chí khả thi

Nhắm đến **8–15 văn bản phù hợp** và **30–50 câu hỏi đánh giá**. Đây là mục tiêu, không phải con số được phép khai khống. Nếu văn bản chuẩn hóa không đủ, dùng tập nhỏ hơn, báo rõ số lượng thực tế và hạn chế thực nghiệm. Ưu tiên quy chế đào tạo đại học, đánh giá học phần, thi, xét tốt nghiệp và các văn bản hướng dẫn/sửa đổi liên quan. Không mở rộng sang tuyển sinh hoặc sau đại học chỉ để đủ số lượng.

Gợi ý kiểm tra ban đầu, không mặc định các nguồn này đều đang hiệu lực:

- https://dttc.haui.edu.vn/vn/quy-che-dao-tao
- https://qldt.haui.edu.vn/tintuc/quyche
- https://www.haui.edu.vn/vn/vbpl/detail/102

Với từng nguồn, kiểm tra trang gốc, tệp đính kèm, số hiệu, ngày ban hành, đối tượng áp dụng, quan hệ sửa đổi và chất lượng trích xuất. Nếu nguồn chỉ là trang tin dẫn đến PDF, lưu cả URL trang và URL PDF. Chỉ dùng tài liệu đọc được trong chỉ mục.

## 4. Kiến trúc và nguyên tắc so sánh

**Phần dùng chung:** dữ liệu chuẩn hóa, câu hỏi, mô hình sinh Gemini, chỉ dẫn trả lời dựa trên chứng cứ, chế độ sinh, cài đặt thử nghiệm và cách tính độ trễ. Hai phương pháp chỉ khác cách truy xuất/tổ chức chứng cứ. Ghi các tham số khác biệt trong báo cáo. Không dùng Google Search grounding khi sinh đáp án vì sẽ làm sai lệch phép so sánh trên cùng tập văn bản.

**RAG cơ sở:** chia đoạn theo điều/khoản, dùng mô hình embedding đa ngôn ngữ có hỗ trợ tiếng Việt chạy cục bộ nếu khả thi; tạo chỉ mục vector và truy xuất top-k. Với mỗi đoạn giữ metadata `document_id`, `article_id`, URL, trang, vị trí. Nếu có thể, bổ sung tìm kiếm từ khóa như một thí nghiệm phụ, không thay thế mốc vector đã định.

**GraphRAG:** dựng đồ thị có ít nhất các kiểu nút `Document`, `Article`, `Topic`, `Audience`; các cạnh như `CONTAINS`, `ABOUT`, `APPLIES_TO`, `AMENDS` chỉ thêm khi có bằng chứng kiểm tra được. Đối với cạnh do mô hình gợi ý, lưu `evidence_article_ids` và trạng thái cần kiểm tra; không coi quan hệ được LLM suy ra là sự thật pháp lý. Truy xuất bắt đầu từ nút/điều khoản phù hợp với câu hỏi, mở rộng một số cạnh có giới hạn, rồi lấy **nội dung điều khoản nguyên văn** để tạo đáp án. Không trả lời chỉ từ nhãn nút hay tóm tắt đồ thị. Nếu không đủ thời gian hoặc hạn mức, ưu tiên đồ thị xác định bằng cấu trúc văn bản và từ điển chủ đề nhỏ, có mô tả hạn chế.

Gợi ý công cụ: Python, PyMuPDF/BeautifulSoup cho tài liệu, một vector store nhẹ hoặc NumPy, NetworkX cho đồ thị, Streamlit cho demo, Gemini SDK chính thức cho lời gọi mô hình. Chọn phụ thuộc thực sự cài và chạy được trên máy hiện tại; không cần Neo4j hoặc hạ tầng server riêng. Tạo file cấu hình tham số và `.env.example`. `GEMINI_API_KEY` là biến môi trường; không lưu trong `.env.example` giá trị thật.

## 5. Các giai đoạn bắt buộc

### Giai đoạn A — Khảo sát nguồn và chuẩn hóa dữ liệu

1. Tạo `data/source_manifest.csv` gồm tối thiểu: ID, tiêu đề, URL trang, URL tệp, tên miền, loại tệp, số hiệu, ngày ban hành, ngày truy cập, phạm vi áp dụng, quan hệ sửa đổi/thay thế (nếu tìm thấy), tình trạng hiệu lực (`verified/unknown/...` kèm căn cứ), lý do chọn/loại, lỗi tải và hash tệp.
2. Tải các tệp nguồn được chọn vào `data/raw/`, không sửa bản gốc. Trích xuất HTML/PDF thành bản đọc được và phân đoạn theo chương, điều, khoản; nếu văn bản không có cấu trúc đó, ghi quy tắc chia tương ứng.
3. Xuất `data/processed/articles.jsonl` với ID ổn định, nội dung, tên văn bản, số hiệu, điều/khoản, trang nếu xác định được, URL nguồn và tọa độ/đoạn gốc đủ để đối chiếu.
4. Kiểm tra thủ công mẫu ở đầu, giữa và cuối các tài liệu quan trọng. Lưu `docs/data_audit.md` với tổng số tài liệu, số điều khoản, lỗi OCR/định dạng, tài liệu bị loại và các cặp văn bản có khả năng sửa đổi nhau. Không che giấu lỗi.

**Điều kiện qua giai đoạn:** có thể tra một ID điều khoản để đọc nội dung và mở đúng nguồn HaUI.

### Giai đoạn B — Hai pipeline hỏi đáp

1. Xây CLI hoặc module riêng `rag` và `graph_rag`, dùng chung bộ sinh câu trả lời. Mỗi câu trả lời có `answer`, `citations`, `retrieved_article_ids`, `retrieval_trace`, `latency_ms`, số lượt gọi và thông tin token nếu API cung cấp.
2. Trích dẫn là **tên/số hiệu văn bản + điều/khoản + link gốc**. Kiểm tra rằng mọi citation đều là ID đã được truy xuất trong corpus; nếu không, chặn hoặc gắn lỗi.
3. Chỉ dẫn mô hình: trả lời tiếng Việt, không suy đoán ngoài chứng cứ, phân biệt quy định theo phiên bản, nêu rõ khi chưa đủ tài liệu. Cùng một prompt sinh câu trả lời cho hai pipeline, chỉ phần chứng cứ đầu vào khác nhau.
4. Đặt giới hạn số đoạn và token ngữ cảnh tương đương giữa hai phương pháp; ghi lại trường hợp GraphRAG dùng thêm nhiều bước/lời gọi để so sánh chi phí công bằng.
5. Tạo chế độ `--dry-run` hoặc `--retrieve-only` để xem truy xuất ngay cả khi chưa có API key. Thử ít nhất một câu một điều khoản và một câu nhiều điều khoản; kiểm tra link và điều khoản có thật.

**Điều kiện qua giai đoạn:** cả hai phương pháp trả về cấu trúc thống nhất và có trace truy xuất; không phải giao diện với câu trả lời hard-code.

### Giai đoạn C — Bộ câu hỏi và thực nghiệm

1. Tạo `evaluation/questions.jsonl` với **30–50 câu nếu dữ liệu cho phép**, phân loại: một điều khoản; nhiều điều khoản; nhiều văn bản; sửa đổi/phiên bản khi có chứng cứ; không có thông tin trong corpus. Cần tối thiểu 5 câu ở mỗi nhóm được đưa vào đánh giá, trừ nhóm phiên bản nếu nguồn không hỗ trợ; ghi rõ ngoại lệ.
2. Mỗi mục có `question_id`, câu hỏi, loại, đáp án chuẩn ngắn, `gold_article_ids`, ghi chú điều kiện thời điểm/đối tượng, và `answerable`. Viết đáp án từ văn bản nguồn **trước khi xem câu trả lời của hai hệ thống**. Nếu không có người phản biện độc lập, ghi giới hạn này trong báo cáo.
3. Định nghĩa thang chấm rõ ràng: đúng nội dung (0/1), đủ ý (0/1 hoặc tỷ lệ ý), dẫn đúng điều/khoản (0/1), từ chối phù hợp với câu không trả lời được (0/1); `Recall@k` trên gold IDs khi so sánh truy xuất. Với trường hợp nhiều điều khoản, có thể báo cả recall theo từng điều khoản. Không dùng một điểm tự động để thay thế hoàn toàn việc kiểm tra đáp án và nguồn.
4. Chạy cố định cùng tập câu hỏi qua hai hệ thống. Lưu đầu ra nguyên bản `evaluation/runs/`, bảng kết quả từng câu `evaluation/results.csv`, tóm tắt theo nhóm `evaluation/summary.csv`, thông tin cấu hình, phiên bản code, thời điểm chạy và lỗi API. Không thay câu hỏi/đáp án chuẩn giữa hai lượt chạy.
5. Báo rõ số câu đã chấm tay, số câu bị lỗi, số câu chưa chạy do quota. Nếu bị giới hạn API, giảm số lượng cả **hai** pipeline theo cùng danh sách ID; không so sánh các tập lệch nhau. Với mỗi thước đo có mẫu số và cách tính; chi phí tiền tệ chỉ ước tính nếu có bảng giá tại thời điểm chạy, phân biệt với token và độ trễ đo được.
6. Chọn ít nhất 3 ví dụ GraphRAG cải thiện và 3 ví dụ RAG tốt hơn/ngang nhau **nếu thực tế có**; nếu không có, nói đúng kết quả. Phân tích nguyên nhân như chất lượng tách đoạn, cạnh đồ thị sai, truy xuất thiếu, nhầm phiên bản hoặc sinh sai dù chứng cứ đúng.

**Điều kiện qua giai đoạn:** từ một hàng trong bảng kết quả truy được câu hỏi, đáp án chuẩn, câu trả lời của hai hệ thống và văn bản làm bằng chứng; mọi điểm số tổng hợp tính lại được từ dữ liệu hàng.

### Giai đoạn D — Demo và báo cáo

1. Tạo ứng dụng Streamlit gồm ô nhập câu hỏi và hai cột RAG/GraphRAG. Hiện trạng thái đang chạy, câu trả lời, trích dẫn có link, đoạn văn được dùng, trace nút/cạnh đối với GraphRAG, độ trễ và lỗi API dễ hiểu. Có ít nhất vài câu hỏi gợi ý lấy từ tập đánh giá, không hard-code đáp án.
2. Viết `report/report.md` tiếng Việt đủ các mục: tóm tắt; lý do chọn đề tài; câu hỏi/giả thuyết nghiên cứu; tổng quan RAG và GraphRAG có nguồn; phạm vi và xuất xứ dữ liệu HaUI; kiến trúc; thiết kế phép so sánh; xây dựng bộ câu hỏi; thước đo; bảng kết quả đo thật; phân tích theo nhóm; ví dụ thắng/thua; hạn chế; hướng mở rộng; kết luận; tài liệu tham khảo có link. Nếu cần PDF để nộp, xuất từ nội dung đã kiểm tra và xác nhận bảng/tiếng Việt hiển thị đúng.
3. Viết `README.md` có yêu cầu môi trường, lệnh cài đặt, lệnh tạo chỉ mục, chạy từng phương pháp, thực nghiệm, demo, cấu trúc dự án, vị trí file kết quả, cách đặt API key và giới hạn đã gặp.
4. Chụp ảnh demo hoặc tạo kịch bản trình bày 3–5 phút trong `docs/demo_script.md`: một câu hỏi một điều khoản, một câu nhiều văn bản, một câu thiếu chứng cứ; không tạo screenshot giả.

**Điều kiện hoàn tất:** một người khác theo README có thể tái tạo chỉ mục, hỏi cả hai pipeline và hiểu bảng so sánh; báo cáo phản ánh đúng dữ liệu đo được.

## 6. Kiểm tra cuối và bàn giao

- Chạy kiểm tra cú pháp/import, kiểm tra ID trùng hoặc citation trỏ ra ngoài corpus, kiểm tra một mẫu đối chiếu văn bản gốc; chạy lệnh thực tế theo README. Không viết hàng loạt test hình thức chỉ để tăng số lượng.
- In cây thư mục ngắn và đường dẫn các sản phẩm chính. Trong thông báo cuối, nêu **thực tế đã làm được gì**, số văn bản/câu hỏi/câu đã chạy, kết quả nổi bật có số liệu thật, cách chạy demo, điều gì bị chặn (nếu có), và bước tiếp theo có tác động lớn nhất.
- Khi deadline sát, ưu tiên theo thứ tự: **nguồn có thể kiểm chứng → hai pipeline thật → kết quả thực nghiệm → báo cáo đúng kết quả → giao diện tối giản**. Không hy sinh tính trung thực để đạt số trang, số file hay số lượng câu hỏi dự kiến.
- Nếu không thể truy cập mạng, không có API key hoặc hạn mức không đủ, hoàn thiện tối đa phần độc lập; lưu log lỗi, chỉ dẫn cách chạy lại; tuyệt đối không báo là đã thực nghiệm nếu chưa chạy.

**Bắt đầu ngay bằng cách kiểm tra thư mục dự án, khảo sát nguồn HaUI và tạo manifest. Tiếp tục thực hiện các giai đoạn, không dừng lại để trình bày lại kế hoạch.**
