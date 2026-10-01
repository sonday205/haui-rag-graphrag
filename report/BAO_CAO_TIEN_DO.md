# BÁO CÁO TIẾN ĐỘ ĐỀ TÀI

**Tên đề tài:** Xây dựng hệ thống hỏi đáp quy chế đào tạo Trường Đại học Công nghiệp Hà Nội bằng RAG và GraphRAG  
**Người thực hiện:** Trần Trung Hiếu
**Mốc báo cáo:** Giai đoạn hoàn thành thu thập dữ liệu và xây dựng RAG cơ sở

## 1. Mục tiêu đề tài

Đề tài hướng tới một hệ thống cho phép người dùng đặt câu hỏi bằng tiếng Việt về quy chế, quy định đào tạo của Trường Đại học Công nghiệp Hà Nội (HaUI). Hệ thống truy xuất nội dung liên quan từ văn bản gốc, đưa nội dung đó cho mô hình ngôn ngữ lớn (LLM) tạo câu trả lời và kèm thông tin nguồn để người dùng kiểm tra. Ở giai đoạn tiếp theo, đề tài sẽ xây dựng GraphRAG và so sánh hai phương pháp trên cùng bộ dữ liệu, câu hỏi và tiêu chí đánh giá.

## 2. Công việc đã thực hiện tại mốc báo cáo

### 2.1. Tìm và thu thập dữ liệu

Đã khảo sát **11 nguồn văn bản ứng viên** từ các trang và tiểu miền của HaUI, tải được **9 tệp PDF**. Các nguồn gồm:

| Nguồn | Loại tài liệu đã khảo sát |
|---|---|
| [Trang quy chế của SICT HaUI](https://sict.haui.edu.vn/vn/html/quy-che) | Bản hợp nhất quy chế đào tạo đại học; quy định đồ án, khóa luận; chuẩn đầu ra ngoại ngữ; học phần thay thế |
| [Trang quy chế đào tạo của HaUI](https://dttc.haui.edu.vn/vn/quy-che-dao-tao) | Văn bản sửa đổi quy chế đào tạo; quy định về đồ án, khóa luận |
| [Mục văn bản pháp luật của HaUI](https://www.haui.edu.vn/vn/vbpl/detail/102) | Thông tư 08/2021/TT-BGDĐT được đăng trên trang HaUI |
| [Trang quy định của HaUI](https://tac.haui.edu.vn/vn/quy-dinh) | Quy định về đánh giá kết quả học tập |

Với mỗi nguồn, đã ghi lại tên tài liệu, đường dẫn trang giới thiệu và PDF, số hiệu văn bản (nếu có), thời điểm truy cập, tệp tải về và mã băm SHA-256. Việc lưu PDF gốc cùng bảng theo dõi nguồn giúp kiểm tra lại dữ liệu khi cần. Hai liên kết PDF khảo sát trả lỗi **404**, nên chưa đưa được các tệp đó vào tập dữ liệu.

### 2.2. Làm sạch dữ liệu và tạo tập văn bản ban đầu

Qua kiểm tra khả năng trích xuất chữ, phần lớn PDF tải được là **bản chụp/ảnh quét**. Ở mốc báo cáo này, tôi chọn trước [bản hợp nhất quy chế đào tạo trên SICT HaUI](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf), là PDF có lớp chữ có thể đọc bằng chương trình. Văn bản dài 28 trang, gồm 22 điều; nội dung được tách thành **135 đoạn** để phục vụ truy xuất.

Mỗi đoạn được gắn mã định danh và thông tin trang, liên kết về PDF gốc. Cách tổ chức này cho phép hệ thống hiển thị đoạn làm căn cứ và mở đúng trang văn bản khi người dùng muốn đối chiếu. Các PDF ảnh quét được lưu lại để xử lý ở giai đoạn sau, chưa đưa trực tiếp vào tập văn bản của RAG tại mốc này.

### 2.3. Xây dựng RAG cơ sở

Đã xây dựng luồng hỏi đáp RAG theo các bước:

1. Chuyển các đoạn văn bản đã xử lý thành vector biểu diễn ngữ nghĩa bằng mô hình embedding đa ngôn ngữ chạy cục bộ.
2. Khi nhận câu hỏi, chuyển câu hỏi thành vector và tìm các đoạn gần nghĩa nhất trong tập văn bản.
3. Đưa những đoạn tìm được cùng câu hỏi vào prompt tiếng Việt để LLM tạo câu trả lời dựa trên chứng cứ.
4. Trả về câu trả lời kèm mã đoạn và đường dẫn tới trang PDF tương ứng.

Hệ thống đã gọi được LLM và nhận câu trả lời cho các câu hỏi thử nghiệm trên văn bản đã đưa vào tập dữ liệu. Ví dụ, với câu hỏi về thời gian sinh viên được rút lớp học phần đã đăng ký, hệ thống truy xuất được nội dung tại **Điều 7, khoản 10** của bản hợp nhất và tạo câu trả lời có dẫn nguồn. Đây là kết quả thử nghiệm chức năng ban đầu; chưa dùng để khẳng định chất lượng tổng quát của hệ thống.

## 3. Khó khăn và cách xử lý

**PDF dạng ảnh quét.** Nhiều văn bản nhìn đọc được bằng mắt nhưng chương trình trích xuất gần như không lấy được chữ, nên không thể chia đoạn và tìm kiếm trực tiếp. Tôi đã kiểm tra lượng chữ trích xuất của từng PDF, giữ nguyên tệp gốc và tạm thời chỉ dùng PDF có lớp chữ cho bản RAG đầu tiên. Bước tiếp theo là chuyển ảnh thành chữ bằng OCR tiếng Việt rồi đối chiếu lại với trang gốc trước khi bổ sung vào tập dữ liệu.

**Văn bản có nhiều phiên bản và quan hệ sửa đổi.** Một quy định có thể được ban hành, sửa đổi hoặc thay thế bởi văn bản khác. Nếu chỉ ghép các PDF mà không xác định quan hệ này, hệ thống có nguy cơ đưa ra câu trả lời sai bối cảnh. Tôi đã ghi số hiệu và thông tin sửa đổi/thay thế tìm thấy trong nguồn; những trường hợp chưa đối chiếu đầy đủ được để ở trạng thái **chưa xác minh hiệu lực**. Phạm vi hỏi đáp ban đầu được giới hạn ở nội dung của bản hợp nhất đã chọn, chưa khẳng định đó là quy định đang có hiệu lực tại thời điểm người dùng hỏi.

**Chất lượng tách đoạn và dẫn nguồn.** Văn bản PDF có ngắt trang, chú thích chân trang và một số tiêu đề/điều khoản nằm sát nhau. Những đặc điểm này có thể khiến một ý bị tách qua hai đoạn hoặc lẫn chú thích. Tôi đã gắn mã đoạn và số trang để kiểm tra lại trên PDF gốc; việc rà soát, chỉnh lỗi tách đoạn sẽ tiếp tục trước khi mở rộng dữ liệu và đánh giá chất lượng trả lời.

## 4. Kết quả đạt được và giới hạn hiện tại của mốc báo cáo

- Có danh sách nguồn và các PDF gốc đã tải, kèm thông tin xuất xứ để truy vết.
- Có tập văn bản ban đầu gồm **9 văn bản, 449 đoạn** (136 PDF có chữ + 313 OCR), vector 384 chiều,.
- Có RAG cơ sở thực hiện được chuỗi **câu hỏi → truy xuất đoạn liên quan → LLM tạo câu trả lời → dẫn nguồn PDF**.
- Phạm vi dữ liệu còn hẹp vì các PDF ảnh quét chưa được kiểm tra và đưa vào tập văn bản tại mốc này. Kết quả thử nghiệm ban đầu chưa đủ để đánh giá độ chính xác trên nhiều loại câu hỏi hoặc nhiều văn bản.

## 5. Kế hoạch các tuần tiếp theo

| Giai đoạn | Công việc dự kiến | Kết quả cần có |
|---|---|---|
| Tuần tiếp theo | OCR các PDF ảnh quét, rà soát lỗi nhận dạng tiếng Việt, đối chiếu trang và số hiệu văn bản; bổ sung các văn bản đạt chất lượng vào tập dữ liệu | Tập văn bản mở rộng có thể truy xuất và kiểm tra nguồn |
| Tuần kế tiếp | Xây dựng GraphRAG: mô hình hóa văn bản, điều/khoản, chủ đề và những quan hệ được kiểm chứng; thiết kế cách truy xuất kết hợp thông tin đồ thị | Luồng GraphRAG trả về chứng cứ có thể đối chiếu với PDF |
| Tuần sau đó | Xây dựng bộ câu hỏi đánh giá; chạy RAG và GraphRAG trên cùng dữ liệu và cùng điều kiện; đối chiếu độ đúng của đoạn truy xuất, chất lượng câu trả lời, dẫn nguồn và thời gian phản hồi | Bảng so sánh có ví dụ đúng/sai, phân tích ưu nhược điểm và hướng cải thiện |

## 6. Kết luận

Tại mốc báo cáo này, đề tài đã hoàn thành phần thu thập nguồn ban đầu và xây dựng được RAG có khả năng tạo câu trả lời từ LLM dựa trên đoạn quy chế được truy xuất. Trọng tâm tiếp theo là xử lý văn bản ảnh quét, mở rộng và kiểm tra chất lượng dữ liệu, sau đó hoàn thiện GraphRAG để thực hiện phép so sánh có cùng điều kiện với RAG cơ sở.

**Tài liệu/nguồn đối chiếu trong dự án:** `data/source_manifest.csv` (danh sách nguồn), `docs/data_audit.md` (kiểm tra dữ liệu), `evaluation/runs/baseline_pre_ocr/articles.jsonl` (135 đoạn của mốc RAG ban đầu), PDF gốc tại `data/raw/`.
