# Đánh giá Gemini: RAG vector và GraphRAG trên quy chế HaUI

**Lưu ý phiên bản dữ liệu:** Đây là checkpoint trước khi bổ sung 8 PDF OCR, chỉ dùng corpus 1 PDF/135 đoạn và GraphRAG chủ đề cũ. Không gộp số liệu LLM ở đây với chỉ mục 9 PDF hiện tại; bộ truy xuất mới chưa được chấm câu trả lời Gemini.

Tạo lúc 2026-09-28T16:12:33.861500+00:00 (UTC). Nguồn số liệu: `evaluation/runs/gemini_checkpoint.jsonl`; phiếu chấm tay: `evaluation/manual_scores.json`.

## Phạm vi và kết luận ngắn

Checkpoint có **7/30 cặp câu hỏi** đủ hai đáp án hợp lệ để chấm, 15 đáp án hợp lệ ở trạng thái cuối, 5 lượt đang lỗi và 40 lượt chưa chạy. Tệp thô gồm 24 lượt API, kể cả các lần thử lại. Cùng model `gemini-3.5-flash-lite`. Chỉ dùng cặp đủ hai đáp án trong bảng so sánh; đây là checkpoint, chưa phải kết quả đủ 30 câu.

Kết quả của các nhóm chưa có cặp hợp lệ chưa thể dùng để kết luận phương pháp nào tốt hơn. Lỗi dịch vụ được ghi riêng khỏi lỗi trả lời hoặc lỗi truy xuất.

## Thiết lập và cách chấm

- Corpus: 1 PDF hợp nhất QĐ 744/2021 và 666/2023 trên [SICT HaUI](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf), 22 điều, 135 đoạn; hiệu lực hiện hành `unknown`.
- Hai phương pháp dùng cùng bộ câu hỏi, model sinh, prompt tiếng Việt, `temperature=0`, `top_k=5` và giới hạn tối đa 6.500 ký tự chứng cứ. RAG dùng embedding đa ngôn ngữ/cosine; GraphRAG tự thiết kế dùng hạt giống TF-IDF ký tự rồi mở rộng chủ đề/đồ thị.
- Khi tiếp tục checkpoint, mã `src/project.py` tăng độ dài chuỗi lỗi Gemini được lưu và cấu hình SDK tối đa một request HTTP cho mỗi lượt gọi; phiên bản SDK đang cài đã có mặc định một request. Logic truy xuất, prompt, model và nhiệt độ sinh không đổi. Metadata lưu các SHA mã đã dùng.
- Chấm tay theo đáp án chuẩn đã viết trước khi gọi model: **Đúng nội dung** (0/1: ý chính thực tế đúng), **Đủ ý** (0/1: bao phủ cả điều kiện/ngoại lệ trong đáp án chuẩn), **Dẫn đúng nguồn** (0/1: ID đoạn có thật và hỗ trợ phát biểu). Câu từ chối sai trên câu trả lời được nhận 0 ở cả ba cột. Người làm dự án tự chấm, chưa có người phản biện độc lập.
- Recall theo câu: câu có ít nhất một gold ID trong top 5. Độ trễ đo từ đầu truy xuất đến khi có đáp án API, không gồm khởi động/tải model và không đại diện hiệu năng tải cao. Token lấy từ `usage_metadata` của API; không ước tính tiền.
- Từ lượt tiếp tục, script giãn tối thiểu 5 giây giữa thời điểm bắt đầu hai request (~12 lượt/phút, dưới giới hạn 15). Khoảng cách thực tế nhỏ nhất trong 7 khoảng ghi timestamp: 5.00 giây.

## Bảng tổng hợp trên cùng 7 câu

| Thước đo | RAG vector | GraphRAG |
|---|---:|---:|
| Đúng nội dung | 6/7 | 6/7 |
| Đủ ý | 4/7 | 4/7 |
| Dẫn đúng nguồn | 6/7 | 6/7 |
| Recall@5 (câu có gold trong top 5) | 6/7 | 6/7 |
| Độ trễ trung bình | 2095.06 ms | 1865.28 ms |
| Độ trễ trung vị | 1825.64 ms | 1835.41 ms |
| Token đầu vào | 6,313 | 9,060 |
| Token đầu ra | 607 | 703 |
| Tổng token | 6,920 | 9,763 |

Độ dài chứng cứ truy xuất có thể khác dù cùng `top_k` và mức trần ký tự. Không thể quy toàn bộ khác biệt độ trễ/token cho cấu trúc truy xuất. Chưa tính thời gian xây chỉ mục, công sức duyệt dữ liệu hoặc chi phí tiền tệ.

## Từng câu hỏi, câu trả lời và bằng chứng

### S01 — Học kỳ chính phải đăng ký tối thiểu và tối đa bao nhiêu tín chỉ?

**Đáp án chuẩn:** Tối thiểu 10, tối đa 27 tín chỉ; có ngoại lệ nêu tại khoản 5 Điều 7.

**Gold ID:** `QC2023-D07-K5-P01`

**RAG vector — 3/3** (đúng 1, đủ 1, dẫn 1)

> Dựa trên các trích đoạn, khối lượng học tập trong mỗi học kỳ chính được quy định như sau:
> - Khối lượng học tập tối thiểu: 10 tín chỉ cho mỗi học kỳ (không quy định khối lượng tối thiểu nếu sinh viên còn nợ khối lượng học tập dưới mức tối thiểu hoặc trong học kỳ không có lớp học phần để đăng ký đủ khối lượng quy định) [QC2023-D07-K5-P01].
> - Khối lượng học tập tối đa: 27 tín chỉ cho mỗi học kỳ [QC2023-D07-K5-P01].
> - Các trường hợp đặc biệt sẽ do Hiệu trưởng quyết định [QC2023-D07-K5-P01].

Nguồn dẫn: [QC2023-D07-K5-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=7).  
ID truy xuất: `QC2023-D07-K5-P01`, `QC2023-D12-K3-P01`, `QC2023-D13-K4-P01`, `QC2023-D08-K3-P02`, `QC2023-D13-K1-P01`.  
Độ trễ: 4595.75 ms; API: 1; token vào/ra/tổng: 841/169/1010.  
Nhận xét chấm tay: Đủ giới hạn 10–27 tín chỉ và các ngoại lệ; đúng Điều 7 khoản 5.

**GraphRAG cấu trúc — 3/3** (đúng 1, đủ 1, dẫn 1)

> Dựa trên các trích đoạn, khối lượng học tập (số tín chỉ) trong mỗi học kỳ chính được quy định như sau:
> 
> * **Tối thiểu:** 10 tín chỉ cho mỗi học kỳ (không quy định tối thiểu nếu sinh viên còn nợ khối lượng học tập dưới mức tối thiểu hoặc trong học kỳ không có lớp học phần để đăng ký đủ; các trường hợp đặc biệt do Hiệu trưởng quyết định) [QC2023-D07-K5-P01].
> * **Tối đa:** 27 tín chỉ cho mỗi học kỳ (các trường hợp đặc biệt do Hiệu trưởng quyết định) [QC2023-D07-K5-P01]. *(Lưu ý: Tại một thời điểm bất kỳ trong đợt đăng ký chính, sinh viên được phép đăng ký tối đa 33 tín chỉ nhưng trước khi kết thúc đợt đăng ký chính phải điều chỉnh cho phù hợp với quy định tối đa nêu trên) [QC2023-D07-K3-P01].*

Nguồn dẫn: [QC2023-D07-K5-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=7), [QC2023-D07-K3-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=7).  
ID truy xuất: `QC2023-D07-K5-P01`, `QC2023-D07-K3-P01`, `QC2023-D07-K7-P01`, `QC2023-D12-K3-P01`, `QC2023-D07-K8-P01`.  
Độ trễ: 2121.65 ms; API: 1; token vào/ra/tổng: 962/231/1193.  
Nhận xét chấm tay: Đủ 10–27 tín chỉ, ngoại lệ và giải thích thêm mốc 33 tín chỉ trong đợt đăng ký chính; các ID đều có trong chứng cứ.

### S02 — Sinh viên được rút lớp học phần đã đăng ký vào tuần nào của học kỳ chính?

**Đáp án chuẩn:** Từ tuần 03 đến hết tuần 08; vẫn phải đóng học phí và đáp ứng điều kiện nêu tại khoản 10 Điều 7.

**Gold ID:** `QC2023-D07-K10-P01`

**RAG vector — 2/3** (đúng 1, đủ 0, dẫn 1)

> Sinh viên được rút khỏi lớp học phần đã đăng ký vào từ tuần thứ 03 đến hết tuần thứ 08 của học kỳ chính [QC2023-D07-K10-P01].

Nguồn dẫn: [QC2023-D07-K10-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8).  
ID truy xuất: `QC2023-D07-K10-P01`, `QC2023-D14-K4-P01`, `QC2023-D09-K8-P02`, `QC2023-D21-K1-P01`, `QC2023-D09-K4-P01`.  
Độ trễ: 1825.64 ms; API: 1; token vào/ra/tổng: 889/48/937.  
Nhận xét chấm tay: Đúng tuần 03–08 nhưng bỏ điều kiện vẫn phải đóng học phí trong đáp án chuẩn.

**GraphRAG cấu trúc — 2/3** (đúng 1, đủ 0, dẫn 1)

> Dựa trên phiên bản quy chế [QC2023], sinh viên được phép rút khỏi lớp học phần đã đăng ký trong học kỳ chính vào khoảng thời gian từ tuần thứ 03 đến hết tuần thứ 08 [QC2023-D07-K10-P01].

Nguồn dẫn: [QC2023-D07-K10-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8).  
ID truy xuất: `QC2023-D07-K10-P01`, `QC2023-D07-K3-P01`, `QC2023-D07-K7-P01`, `QC2023-D08-K3-P01`, `QC2023-D09-K8-P01`.  
Độ trễ: 2193.87 ms; API: 1; token vào/ra/tổng: 1337/66/1403.  
Nhận xét chấm tay: Đúng tuần 03–08 nhưng bỏ điều kiện vẫn phải đóng học phí trong đáp án chuẩn.

### S03 — Đợt đăng ký học phần chính và bổ sung diễn ra khi nào?

**Đáp án chuẩn:** Đợt chính trước học kỳ 03–04 tuần, đợt bổ sung trước học kỳ 01–02 tuần.

**Gold ID:** `QC2023-D07-K3-P01`

**RAG vector — 3/3** (đúng 1, đủ 1, dẫn 1)

> Dựa trên các tài liệu được cung cấp, thời gian diễn ra đợt đăng ký học phần chính và bổ sung được quy định như sau:
> 
> - **Đợt đăng ký chính:** Được thực hiện trước thời điểm bắt đầu học kỳ từ 03 đến 04 tuần [QC2023-D07-K3-P01].
> - **Đợt đăng ký bổ sung:** Được thực hiện trước thời điểm bắt đầu học kỳ từ 01 đến 02 tuần [QC2023-D07-K3-P01].

Nguồn dẫn: [QC2023-D07-K3-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=7).  
ID truy xuất: `QC2023-D07-Ktitle-P01`, `QC2023-D17-K1-P01`, `QC2023-D07-K3-P01`, `QC2023-D10-K3-P02`, `QC2023-D09-K8-P02`.  
Độ trễ: 1552.79 ms; API: 1; token vào/ra/tổng: 732/126/858.  
Nhận xét chấm tay: Nêu đúng cả hai mốc 03–04 và 01–02 tuần; dẫn đúng Điều 7 khoản 3.

**GraphRAG cấu trúc — 3/3** (đúng 1, đủ 1, dẫn 1)

> Dựa trên các trích đoạn, thời gian diễn ra hai đợt đăng ký học phần được quy định như sau (phiên bản [QC2023]):
> 
> - **Đợt đăng ký chính:** Được thực hiện trước thời điểm bắt đầu học kỳ từ 03 đến 04 tuần cho tất cả sinh viên muốn đăng ký hoặc hủy đăng ký vào các lớp học phần được tổ chức trong học kỳ ([QC2023-D07-K3-P01]).
> - **Đợt đăng ký bổ sung:** Được thực hiện trước thời điểm bắt đầu học kỳ từ 01 đến 02 tuần cho những sinh viên muốn đăng ký bổ sung vào các lớp học phần đã được Nhà trường thông báo mở ([QC2023-D07-K3-P01]).

Nguồn dẫn: [QC2023-D07-K3-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=7).  
ID truy xuất: `QC2023-D07-K3-P01`, `QC2023-D07-K1-P01`, `QC2023-D07-K7-P01`, `QC2023-D09-K8-P01`, `QC2023-D09-K4-P01`.  
Độ trễ: 1978.99 ms; API: 1; token vào/ra/tổng: 1221/175/1396.  
Nhận xét chấm tay: Nêu đúng cả hai đợt và phạm vi người đăng ký; dẫn đúng Điều 7 khoản 3.

### S04 — Đào tạo trực tuyến được chiếm tối đa bao nhiêu phần trăm chương trình?

**Đáp án chuẩn:** Tối đa 30% tổng khối lượng chương trình, trừ trường hợp bất khả kháng theo hướng dẫn Bộ.

**Gold ID:** `QC2023-D08-K2-P01`

**RAG vector — 2/3** (đúng 1, đủ 0, dẫn 1)

> Dựa trên các trích đoạn, đối với đào tạo theo hình thức chính quy và vừa làm vừa học, đào tạo trực tuyến được chiếm tối đa 30% tổng khối lượng của chương trình đào tạo [QC2023-D08-K2-P01].

Nguồn dẫn: [QC2023-D08-K2-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8).  
ID truy xuất: `QC2023-D08-K2-P01`, `QC2023-D16-K3-P01`, `QC2023-D02-K2-P01`, `QC2023-D12-K3-P01`, `QC2023-D02-Ktitle-P01`.  
Độ trễ: 1422.26 ms; API: 1; token vào/ra/tổng: 620/61/681.  
Nhận xét chấm tay: Đúng ngưỡng 30% nhưng chưa nêu ngoại lệ thiên tai, dịch bệnh, bất khả kháng theo hướng dẫn Bộ.

**GraphRAG cấu trúc — 2/3** (đúng 1, đủ 0, dẫn 1)

> Đào tạo trực tuyến được chiếm tối đa 30% tổng khối lượng của chương trình đào tạo đối với hình thức chính quy và vừa làm vừa học ([QC2023-D08-K2-P01]).

Nguồn dẫn: [QC2023-D08-K2-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8).  
ID truy xuất: `QC2023-D08-K2-P01`, `QC2023-D09-K3-P01`, `QC2023-D17-K4-P01`.  
Độ trễ: 1572.86 ms; API: 1; token vào/ra/tổng: 619/50/669.  
Nhận xét chấm tay: Đúng ngưỡng 30% nhưng chưa nêu ngoại lệ thiên tai, dịch bệnh, bất khả kháng theo hướng dẫn Bộ.

### S05 — Một học phần thường phải có tối thiểu bao nhiêu điểm thành phần?

**Đáp án chuẩn:** Tối thiểu hai; học phần dưới 02 tín chỉ có thể chỉ một điểm.

**Gold ID:** `QC2023-D09-K1-P01`

**RAG vector — 0/3** (đúng 0, đủ 0, dẫn 0)

> Chưa xác định được từ tập tài liệu.

Nguồn dẫn: Không có.  
ID truy xuất: `QC2023-D09-K1-P02`, `QC2023-D09-K2-P02`, `QC2023-D09-K7-P01`, `QC2023-D12-K3-P01`, `QC2023-D09-K7-P02`.  
Độ trễ: 1379.07 ms; API: 1; token vào/ra/tổng: 1161/10/1171.  
Nhận xét chấm tay: Từ chối sai trên câu có đáp án; top 5 không chứa đoạn chuẩn Điều 9 khoản 1 phần 1.

**GraphRAG cấu trúc — 3/3** (đúng 1, đủ 1, dẫn 1)

> Dựa trên các trích đoạn, đối với mỗi học phần, sinh viên được đánh giá tối thiểu qua hai điểm thành phần, đối với các học phần có khối lượng nhỏ hơn 02 tín chỉ có thể chỉ có một điểm đánh giá ([QC2023-D09-K1-P01]).

Nguồn dẫn: [QC2023-D09-K1-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=12).  
ID truy xuất: `QC2023-D09-K1-P01`, `QC2023-D09-K2-P02`, `QC2023-D09-K2-P01`, `QC2023-D08-K3-P01`, `QC2023-D03-K1-P01`.  
Độ trễ: 1835.41 ms; API: 1; token vào/ra/tổng: 1580/68/1648.  
Nhận xét chấm tay: Đủ quy tắc hai điểm thành phần và ngoại lệ học phần dưới 02 tín chỉ; dẫn đúng đoạn.

### S06 — Sinh viên vắng mặt kỳ thi kết thúc học phần có lý do chính đáng phải làm gì?

**Đáp án chuẩn:** Trong 10 ngày làm việc từ ngày thi, làm đơn kèm minh chứng, xác nhận của Trưởng khoa để dự thi bổ sung.

**Gold ID:** `QC2023-D09-K4-P01`

**RAG vector — 3/3** (đúng 1, đủ 1, dẫn 1)

> Theo phiên bản [QC2023-D09-K4-P01], sinh viên vắng mặt có lý do chính đáng ở kỳ thi kết thúc học phần phải làm đơn (kèm theo hồ sơ minh chứng cho lý do vắng mặt) ký xác nhận của Trưởng khoa quản lý sinh viên trong 10 ngày làm việc kể từ ngày thi để được tham dự kỳ thi bổ sung [QC2023-D09-K4-P01].

Nguồn dẫn: [QC2023-D09-K4-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=14).  
ID truy xuất: `QC2023-D14-K5-P01`, `QC2023-D09-K4-P01`, `QC2023-D13-K6-P01`, `QC2023-D07-K9-P01`, `QC2023-D13-K1-P01`.  
Độ trễ: 1851.81 ms; API: 1; token vào/ra/tổng: 825/104/929.  
Nhận xét chấm tay: Đủ hạn 10 ngày, đơn, minh chứng và xác nhận Trưởng khoa.

**GraphRAG cấu trúc — 3/3** (đúng 1, đủ 1, dẫn 1)

> Dựa trên phiên bản [QC2023], trong vòng 10 ngày làm việc kể từ ngày thi kết thúc học phần, sinh viên vắng mặt có lý do chính đáng phải làm đơn (kèm theo hồ sơ minh chứng cho lý do vắng mặt) có ký xác nhận của Trưởng khoa quản lý sinh viên để được tham dự kỳ thi bổ sung do Trung tâm Khảo thí tổ chức [QC2023-D09-K4-P01].

Nguồn dẫn: [QC2023-D09-K4-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=14).  
ID truy xuất: `QC2023-D09-K4-P01`, `QC2023-D08-K6-P01`, `QC2023-D09-K1-P01`, `QC2023-D08-K6-P02`, `QC2023-D09-K2-P02`.  
Độ trễ: 1558.86 ms; API: 1; token vào/ra/tổng: 1660/103/1763.  
Nhận xét chấm tay: Đủ hạn 10 ngày, hồ sơ minh chứng, xác nhận Trưởng khoa và kỳ thi bổ sung.

### S07 — Điểm A và điểm F của học phần nằm trong khoảng nào?

**Đáp án chuẩn:** A từ 8,5 đến 10,0; F dưới 4,0.

**Gold ID:** `QC2023-D09-K7-P01`

**RAG vector — 3/3** (đúng 1, đủ 1, dẫn 1)

> Dựa trên các trích đoạn, điểm A và điểm F của học phần nằm trong các khoảng sau:
> 
> * **Điểm A:** Từ 8,5 đến 10,0 [QC2023-D09-K7-P01].
> * **Điểm F:** Dưới 4,0 [QC2023-D09-K7-P01].

Nguồn dẫn: [QC2023-D09-K7-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=15).  
ID truy xuất: `QC2023-D10-K2-P01`, `QC2023-D09-K7-P01`, `QC2023-D09-K2-P02`, `QC2023-D09-K7-P02`, `QC2023-D09-K1-P02`.  
Độ trễ: 2038.10 ms; API: 1; token vào/ra/tổng: 1245/89/1334.  
Nhận xét chấm tay: Đúng cả khoảng A 8,5–10,0 và F dưới 4,0; dẫn đúng Điều 9 khoản 7.

**GraphRAG cấu trúc — 0/3** (đúng 0, đủ 0, dẫn 0)

> Chưa xác định được từ tập tài liệu.

Nguồn dẫn: Không có.  
ID truy xuất: `QC2023-D09-K2-P02`, `QC2023-D09-K2-P01`, `QC2023-D10-K1-P01`, `QC2023-D10-K3-P01`, `QC2023-D09-K1-P01`.  
Độ trễ: 1795.35 ms; API: 1; token vào/ra/tổng: 1681/10/1691.  
Nhận xét chấm tay: Từ chối sai trên câu có đáp án; top 5 thiếu đoạn chuẩn Điều 9 khoản 7 phần 1.

## Lượt không ghép cặp và lỗi dịch vụ

Trên 24 lượt API đã ghi: 15 lượt có đáp án, 1 lượt `429`, 8 lượt `503`. Các lần thử lỗi vẫn được giữ trong checkpoint; bảng dưới hiển thị trạng thái mới nhất của mỗi cặp câu hỏi và phương pháp.

### S08 — Điểm trung bình tích lũy tối thiểu để được xét tốt nghiệp là bao nhiêu?

Đáp án chuẩn: Từ 2,00 trở lên, cùng các điều kiện khác ở khoản 1 Điều 13.

- RAG vector: có đáp án nhưng không đưa vào bảng so sánh vì thiếu cặp tương ứng; 1497.63 ms; lỗi: `không`.

> Chưa xác định được từ tập tài liệu

- GraphRAG cấu trúc: lỗi API, không có đáp án hợp lệ; 2237.64 ms; lỗi: `Lỗi Gemini: ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}`.

### S09 — Sinh viên được công nhận, chuyển đổi tối đa bao nhiêu tín chỉ?

Đáp án chuẩn: Không vượt quá 50% khối lượng học tập tối thiểu của chương trình.

- RAG vector: lỗi API, không có đáp án hợp lệ; 3063.86 ms; lỗi: `Lỗi Gemini: ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}`.
- GraphRAG cấu trúc: lỗi API, không có đáp án hợp lệ; 856.72 ms; lỗi: `Lỗi Gemini: ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}`.

### S10 — Lần đầu thi hộ hoặc nhờ thi hộ bị xử lý thế nào?

Đáp án chuẩn: Đình chỉ học tập 01 năm; lần thứ hai buộc thôi học.

- RAG vector: lỗi API, không có đáp án hợp lệ; 1143.45 ms; lỗi: `Lỗi Gemini: ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}`.
- GraphRAG cấu trúc: lỗi API, không có đáp án hợp lệ; 969.48 ms; lỗi: `Lỗi Gemini: ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}`.

### S11 — Khi nào sớm nhất sinh viên được đăng ký chương trình thứ hai?

Đáp án chuẩn: Khi được xếp trình độ năm thứ hai của chương trình thứ nhất và đáp ứng một trong hai điều kiện về học lực, tuyển sinh.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### S12 — Thời hạn cấp bằng cho sinh viên đủ điều kiện tốt nghiệp là bao lâu?

Đáp án chuẩn: Trong 03 tháng từ khi đáp ứng đầy đủ điều kiện và nghĩa vụ với Nhà trường.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### M01 — Muốn tốt nghiệp và nhận bằng, sinh viên cần điểm tích lũy tối thiểu nào và thời hạn cấp bằng là bao lâu?

Đáp án chuẩn: Điểm tích lũy từ 2,00 và các điều kiện tại Điều 13 khoản 1; bằng cấp trong 03 tháng sau khi đủ điều kiện và nghĩa vụ.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### M02 — Sinh viên đăng ký học kỳ chính tối đa bao nhiêu tín chỉ và được rút học phần vào tuần nào?

Đáp án chuẩn: Tối đa 27 tín chỉ; rút từ tuần 03 đến hết tuần 08, vẫn đóng học phí.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### M03 — Nếu vắng thi có lý do chính đáng và muốn phúc tra kết quả thì các mốc thời gian là gì?

Đáp án chuẩn: Đơn dự thi bổ sung trong 10 ngày làm việc từ ngày thi; phúc tra trong 05 ngày làm việc từ ngày công bố kết quả.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### M04 — Điều kiện học chương trình thứ hai và điều kiện tốt nghiệp chương trình thứ hai là gì?

Đáp án chuẩn: Được xếp năm thứ hai và đạt điều kiện học lực/tuyển sinh; muốn xét tốt nghiệp chương trình hai phải đủ điều kiện chương trình một và đăng ký muộn nhất 02 năm trước xét.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### M05 — Tín chỉ chuyển đổi bị giới hạn thế nào và khi tốt nghiệp cần tích lũy những gì?

Đáp án chuẩn: Chuyển đổi tối đa 50% khối lượng tối thiểu; tốt nghiệp cần đủ học phần/tín chỉ, chuẩn đầu ra và các điều kiện Điều 13.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### M06 — Quy chế quy định thời gian học tối đa cho người nhập học từ 3/5/2021 và xếp loại học lực giỏi theo GPA nào?

Đáp án chuẩn: Thời gian tối đa không quá 06 năm, một số ngoại lệ; học lực giỏi GPA từ 3,20 đến 3,59.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### M07 — Điểm F dưới mức nào và học lực trung bình trên thang 4 ở mức nào?

Đáp án chuẩn: F dưới 4,0 ở học phần; học lực trung bình GPA 2,00–2,49.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### M08 — Học trực tuyến tối đa bao nhiêu và một học phần cần tối thiểu mấy điểm thành phần?

Đáp án chuẩn: Trực tuyến tối đa 30% chương trình; học phần thường ít nhất hai điểm thành phần.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### V01 — Theo bản hợp nhất 2023, sinh viên nhập học từ 3/5/2021 có thời gian học tối đa bao lâu?

Đáp án chuẩn: Không quá 06 năm từ ngày nhập học, với ngoại lệ ghi trong quy chế.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### V02 — Bản hợp nhất này thay thế quy chế đào tạo tín chỉ ban hành theo quyết định nào năm 2018?

Đáp án chuẩn: Quyết định 787/QĐ-ĐHCN ngày 09/08/2018.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### V03 — Bản hợp nhất này có nhắc thay thế quyết định sửa đổi nào năm 2019?

Đáp án chuẩn: Quyết định 663/QĐ-ĐHCN ngày 12/07/2019.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### V04 — Theo bản hợp nhất, sinh viên nhập học trước 3/5/2021 có thời gian tối đa hoàn thành khóa học thế nào?

Đáp án chuẩn: Bằng 02 lần thời gian kế hoạch học tập chuẩn, với ngoại lệ chính sách ưu tiên.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### V05 — Theo bản hợp nhất có sửa đổi 2023, sinh viên được rút học phần ở tuần nào của học kỳ chính?

Đáp án chuẩn: Từ tuần 03 đến hết tuần 08 của học kỳ chính theo khoản 10 Điều 7.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### U01 — Học phí ngành Công nghệ thông tin năm học 2026–2027 là bao nhiêu?

Đáp án chuẩn: Chưa xác định được từ tập tài liệu.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### U02 — Lịch thi môn Cấu trúc dữ liệu lớp của tôi vào ngày nào?

Đáp án chuẩn: Chưa xác định được từ tập tài liệu.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### U03 — Hiện tại sinh viên Nguyễn Văn A đã đủ điều kiện tốt nghiệp chưa?

Đáp án chuẩn: Chưa xác định được từ tập tài liệu.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### U04 — Số điện thoại cá nhân của trưởng khoa Công nghệ thông tin là gì?

Đáp án chuẩn: Chưa xác định được từ tập tài liệu.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

### U05 — Quy định nào hiện hành vào hôm nay cho học viên cao học ngành AI?

Đáp án chuẩn: Chưa xác định được từ tập tài liệu.

- RAG vector: chưa chạy.
- GraphRAG cấu trúc: chưa chạy.

## Nhận xét và giới hạn cho báo cáo học phần

- Lần chạy đầu chỉ nghỉ 0,7 giây sau mỗi lượt và không kiểm soát số lần bắt đầu trong một phút. Đây là thiếu sót ở code có thể góp phần gây `429`, nhưng bản ghi cũ không có timestamp và nội dung lỗi bị cắt nên không xác định được 429 do RPM, TPM hay hạn mức ngày. Script hiện giãn tối thiểu 5 giây/lượt và cấu hình SDK một HTTP request/lượt.
- S05: GraphRAG tìm đúng Điều 9 khoản 1 và trả lời; RAG bỏ lỡ đoạn này nên từ chối sai. S07: tình huống ngược lại với khoảng điểm A/F ở Điều 9 khoản 7. Hai ví dụ cho thấy lỗi truy xuất chuyển thẳng thành lỗi trả lời dù cùng model sinh.
- S02 và S04: cả hai trả đúng ý chính nhưng lược bỏ điều kiện trong đáp án chuẩn (học phí khi rút học phần; ngoại lệ bất khả kháng của giới hạn học trực tuyến). Vì vậy điểm **đủ ý** thấp hơn điểm **đúng nội dung**.
- Tập chấm hiện có 7 cặp; người viết và chấm gold là cùng một người, có nguy cơ thiên lệch. Cần người phản biện độc lập trước khi dùng làm kết luận mạnh.
- Lần thử ban đầu gặp `429 RESOURCE_EXHAUSTED` ở S08 GraphRAG. Khi tiếp tục với giãn 5 giây, Gemini trả `503 UNAVAILABLE` liên tiếp. Một lượt kiểm chứng sau khi cấu hình SDK chỉ gửi một request HTTP vẫn trả 503. Đây là lỗi dịch vụ/model quá tải theo nội dung phản hồi, không có bằng chứng do code hoặc vượt giới hạn 15 lượt/phút. Giữ nguyên từng lần thử trong checkpoint.
- Khi dịch vụ ổn định, tiếp tục bằng `python -m evaluation.run_gemini --retry-errors` với cùng corpus/config; sau khi có các cặp mới, chấm tay vào `manual_scores.json` rồi chạy `python -m evaluation.write_gemini_report`. Không cộng điểm của câu chưa chấm.

## Tài liệu kiểm chứng

- [PDF quy chế hợp nhất HaUI](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf).
- `evaluation/questions.jsonl`: câu hỏi, đáp án chuẩn, gold ID.
- `evaluation/runs/gemini_checkpoint.jsonl`: đầu ra nguyên bản, đoạn truy xuất, trace, lỗi và token theo lượt.
- `evaluation/manual_scores.json`: điểm và lý do chấm từng đáp án.
