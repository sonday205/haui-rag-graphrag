# Thực nghiệm RAG và GraphRAG sau sửa lỗi — 01/10/2026

## Phạm vi và trạng thái thực nghiệm

Đây là phép thử gọn phục vụ nghiên cứu khoa học cấp trường. Không kiểm tra tải lớn; tập trung chất lượng truy xuất, đáp án, dẫn nguồn, từ chối và chi phí quan sát được.

Corpus 9 PDF, 449 đoạn; OCR chưa hiệu đính toàn bộ và hiệu lực hiện hành chưa xác minh. Cả hai pipeline dùng cùng corpus, top_k=5, trần 6.500 ký tự chứng cứ, prompt JSON có cấu trúc, temperature=0 và model `gemini-3.5-flash-lite`. Đoạn dài được embedding bằng cửa sổ 256 token, overlap 64, trung bình vector cửa sổ rồi chuẩn hóa; không đổi ID đoạn/gold.

Truy xuất chạy toàn bộ 30 câu cũ, 8 câu quan hệ và 20 câu có phạm vi văn bản rõ hơn, thêm hybrid vector/TF-IDF không graph làm đối chứng. Tổng 174 lượt truy xuất, không gọi Gemini. Bộ 20 câu chọn trước đáp án mới: 4 một điều, 4 nhiều điều, 4 phiên bản, 4 quan hệ và 4 ngoài corpus. Tám câu S/M thêm phạm vi bản hợp nhất để gold không mơ hồ; chúng không phải câu nguyên trạng trong bộ 30.

Bộ câu hỏi/gold kế thừa bộ nội bộ đã có, bộ quan hệ được viết sau đồ thị; chưa có người độc lập soạn/chấm. Vì vậy đây là thí nghiệm thăm dò có công bố thiên lệch, không phải benchmark độc lập.

Gemini: dự kiến 40 lượt/20 cặp; thực tế ghi **40 lượt**, lỗi trong log gốc **1**, lỗi sau kiểm tra lại **0**, **20/20 cặp** đủ đáp án hợp lệ. Chưa chạy: 0 lượt. Không gộp kết quả trước OCR hoặc model 3.8 Flash vào bảng này.

R03 GraphRAG ban đầu bị bộ đọc citation chặn nhóm `[ID1, ID2]` dù cả hai ID hợp lệ. Sau sửa, toàn bộ JSON đã lưu được kiểm tra lại offline, không sửa câu trả lời thô và không gọi thêm API. Log gốc giữ nguyên; `generation_revalidated.json` ghi hash log gốc, code validator, lỗi trước sửa và 0 request mới. Mọi độ trễ/token bên dưới vẫn là số đo của request gốc.

Nhịp request tối thiểu 5 giây (~12/phút). SDK một request/lượt, timeout 30 giây; dừng khi gặp quota/quyền API hoặc hai lỗi 503 liên tiếp. Mức 15 RPM là thông tin người dùng cung cấp; hạn mức thực tế còn phụ thuộc project/model/tier, không suy ra chỉ từ tên model. [Model chính thức](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [hạn mức API](https://ai.google.dev/gemini-api/docs/rate-limits).

## Chỉ số truy xuất

Recall@5 theo câu = số gold tìm được / số gold; trung bình chỉ trên câu có gold. All-gold đếm câu tìm đủ mọi gold. Câu ngoài corpus không có Recall; chất lượng từ chối phải đọc đáp án sinh. Độ trễ là thời gian pipeline sau khi model/index đã nạp, loại thời gian chờ pacing; `wall_ms` và `pacing_wait_ms` lưu riêng. Một lần đo không đủ kết luận độ ổn định hiệu năng.

| Bộ câu | Phương pháp | Câu có gold | Recall@5 | Đủ mọi gold | Độ trễ TB (ms) |
|---|---|---:|---:|---:|---:|
| original_30 | GraphRAG | 25 | 0.7800 | 16/25 | 14.13 |
| original_30 | Hybrid không graph | 25 | 0.7200 | 15/25 | 31.52 |
| original_30 | RAG vector | 25 | 0.7400 | 17/25 | 49.87 |
| relations_8 | GraphRAG | 8 | 1.0000 | 8/8 | 13.45 |
| relations_8 | Hybrid không graph | 8 | 0.6250 | 5/8 | 12.48 |
| relations_8 | RAG vector | 8 | 0.2500 | 1/8 | 10.44 |
| scoped_20 | GraphRAG | 16 | 0.7812 | 11/16 | 16.47 |
| scoped_20 | Hybrid không graph | 16 | 0.5938 | 8/16 | 20.46 |
| scoped_20 | RAG vector | 16 | 0.6250 | 8/16 | 12.77 |

Bảng chi tiết theo nhóm ở `retrieval_summary.csv`; từng câu, chứng cứ/trace ở `retrieval_results.csv` và `retrieval.json`.

Độ trễ trung vị của original_30: GraphRAG 13.48 ms; Hybrid không graph 11.89 ms; RAG vector 9.71 ms. Trung bình có outlier khi đo song song với tiến trình đánh giá Gemini; không dùng bảng này để khẳng định phương pháp nào nhanh hơn ổn định.

## Đánh giá sơ bộ nội dung đáp án

**Người/chương trình đánh giá:** Codex assistant AI; sơ bộ, chưa có người phản biện độc lập. Điểm do trợ lý đối chiếu từng đáp án với gold và chứng cứ, không dùng bộ dò từ khóa. Chưa có người phản biện độc lập; đây là nguồn ghi chép để người làm nghiên cứu kiểm tra, không trình bày như kết quả chấm bởi hội đồng.

- **correct:** 1 nếu đúng ý chính được hỏi và đúng phạm vi văn bản; trả sai trọng tâm/từ chối sai = 0.
- **complete:** 1 nếu bao phủ các ý/điều kiện trong gold đã đóng băng; không đánh giá bằng cách dò từ khóa.
- **citation_support:** 1 nếu citation hỗ trợ các khẳng định đã trả và đúng văn bản/phạm vi. Có thể 1 với đáp án thiếu/sai trọng tâm nếu các khẳng định thực tế được nguồn hỗ trợ; từ chối sai = 0.
- **appropriate_refusal:** Chỉ áp dụng 4 câu ngoài corpus; từ chối không kèm khẳng định ngoài chứng cứ = 1.

| Thước đo | RAG vector | GraphRAG |
|---|---:|---:|
| Đúng ý chính/phạm vi | 8/16 | 11/16 |
| Đủ ý theo gold | 4/16 | 8/16 |
| Nguồn hỗ trợ phát biểu | 9/16 | 12/16 |
| Từ chối đúng câu ngoài corpus | 4/4 | 4/4 |
| Độ trễ TB pipeline (ms) | 1636.32 | 1747.54 |
| Độ trễ trung vị pipeline (ms) | 1486.55 | 1709.29 |
| Token vào tổng | 29484 | 31723 |
| Token ra tổng | 1735 | 2549 |
| Token tổng | 31219 | 34272 |

Trên 16 câu trả lời được: GraphRAG đúng hơn ở 5 câu, RAG đúng hơn ở 2 câu, 9 câu bằng nhau theo thước đo đúng nội dung. Kiểm định nhị thức hai phía trên 7 cặp bất đồng (McNemar exact) cho p=0.4531; không có bằng chứng đủ mạnh ở mức 0,05 về ưu thế chung. Đây chỉ là phép kiểm tra thăm dò trên bộ chọn có thiên lệch, không loại bỏ hạn chế thiết kế mẫu.

| Nhóm | Số câu | RAG đúng / đủ / nguồn | GraphRAG đúng / đủ / nguồn |
|---|---:|---|---|
| mot_dieu | 4 | 4/4 / 2/4 / 4/4 | 3/4 / 1/4 / 3/4 |
| nhieu_dieu | 4 | 1/4 / 0/4 / 2/4 | 0/4 / 0/4 / 1/4 |
| phien_ban | 4 | 3/4 / 2/4 / 3/4 | 4/4 / 3/4 / 4/4 |
| quan_he | 4 | 0/4 / 0/4 / 0/4 | 4/4 / 4/4 / 4/4 |

Không quy token thấp hơn thành ưu thế hiệu quả nếu hệ thống từ chối nhiều câu trả lời được. Số token trên là tổng 20 lượt/phương pháp, gồm bốn từ chối đúng ngoài corpus và các từ chối sai. Không ước tính chi phí tiền.

Gold S02 yêu cầu học phí/điều kiện, gold V05 chỉ yêu cầu tuần rút; đây là sự không đồng nhất của độ đầy đủ trong bộ nội bộ. Hai phương pháp vẫn được chấm cùng gold ở từng câu, nhưng cần thống nhất rubric khi thiết kế bộ độc lập.

## Phân tích nguyên nhân và ví dụ đối chiếu

### Truy xuất

- Bộ 30 câu nguyên trạng: RAG 0,74, GraphRAG 0,78, hybrid không graph 0,72. RAG tìm đủ gold 17/25, GraphRAG 16/25. Lợi ích của GraphRAG tập trung ở phiên bản (1,00 so với RAG/hybrid 0,60); câu một điều RAG 0,9167 cao hơn GraphRAG/hybrid 0,8333. Câu nhiều điều cả RAG/GraphRAG 0,5625, hybrid 0,6250.
- Bộ 8 quan hệ: RAG 0,25, hybrid 0,625, GraphRAG 1,00. TF-IDF đã giúp đáng kể; phần tăng từ hybrid tới GraphRAG phù hợp với việc thêm cạnh/chứng cứ được ưu tiên. Đây chưa là tách riêng mọi hiệu ứng của graph vì hai thuật toán còn khác tập ứng viên và điểm thưởng cạnh.
- Bộ 20 có phạm vi rõ: GraphRAG 0,78125, RAG 0,625, hybrid 0,59375. So với bộ 30, khác cả phân bố nhóm và wording, nên không dùng chênh lệch này để chứng minh tác động nhân quả của sửa code.

### Ví dụ GraphRAG hỗ trợ tốt hơn

1. V02: tìm Điều 22 khoản 2 để trả đúng QĐ787/2018; RAG bỏ lỡ và từ chối.
2. R01: cạnh REPLACES đưa vào đoạn trang 1 QĐ721, trả cả QĐ254 và QĐ1432; RAG thiếu chứng cứ và từ chối.
3. R02: tìm đủ trang 1 và 2 của QĐ1077 để trả TT08 và QĐ239; RAG thiếu một phần. R06 tương tự với hai quyết định được TT08 thay thế.

### Ví dụ RAG tốt hơn hoặc hai phương pháp ngang nhau

1. S07: RAG tìm khoảng A=8,5–10/F<4 ở bản hợp nhất; GraphRAG dùng quy đổi A=4/F=0 của TT08. ID dẫn có thật nhưng sai trọng tâm/phạm vi. Đây là lỗi chọn/sinh nội dung, không phải lỗi ID giả.
2. M01: RAG trả GPA2,00 và thời hạn ba tháng; GraphRAG từ chối vì thiếu chứng cứ đầy đủ. RAG còn thiếu một số điều kiện so với gold.
3. S06/V04: cả hai trả đủ thông tin và dẫn nguồn đúng; GraphRAG không cải thiện nội dung. U01/U02/U03/U05: cả hai từ chối phù hợp.

### Lỗi chung và hướng nghiên cứu

- M02: hai phương pháp đều lấy Điều7 khoản3 về 33 tín chỉ trong đợt đăng ký chính, bỏ lỡ khoản5 về khối lượng học kỳ 27 và yêu cầu điều chỉnh. Câu trả lời có nguồn cho 33 nhưng chưa trả mức cuối cùng theo gold. Cần đánh giá sự đầy đủ của chuỗi điều kiện/ngoại lệ, không chỉ xem ID có thật.
- M05/M08: thiếu một phần gold dẫn tới từ chối sai trên câu trả lời được. Với top_k nhỏ, các đoạn cạnh tranh có thể chiếm chỗ của điều khoản cần thiết; trace cho phép phân biệt lỗi truy xuất với lỗi sinh.
- S02/S04/V01: đoạn cần thiết đã được tìm nhưng model lược bỏ học phí/điều kiện hoặc ngoại lệ. Đây là thiếu ý khi sinh, không sửa được chỉ bằng nâng Recall.
- Việc thêm số hiệu vào câu hỏi có thể làm đoạn mở đầu bản hợp nhất xếp cao; cần kiểm tra cơ chế phạm vi văn bản và đa dạng chứng cứ trong thí nghiệm kế tiếp, tránh hard-code theo câu hỏi.
- Token thấp hơn của RAG phần nào đi cùng nhiều từ chối sai hơn; độ trễ một lượt và token không đủ để kết luận chi phí/hiệu năng tổng quát.

## Câu hỏi và đáp án Gemini từng trường hợp

Đáp án dưới đây là dữ liệu API thật; lỗi/chưa chạy được ghi nguyên trạng. Không tự tạo đáp án thay thế và không chấm điểm nội dung khi không có đáp án hợp lệ.

### S02 — mot_dieu

Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), sinh viên được rút lớp học phần đã đăng ký vào tuần nào của học kỳ chính?

**Gold:** Từ tuần 03 đến hết tuần 08; vẫn phải đóng học phí và đáp ứng điều kiện nêu tại khoản 10 Điều 7.

**Gold ID:** QC2023-D07-K10-P01

**RAG vector**

> Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), sinh viên được phép rút khỏi lớp học phần đã đăng ký từ tuần thứ 03 đến hết tuần thứ 08 của học kỳ chính [QC2023-D07-K10-P01].

Lỗi: Không. Độ trễ: 4017.67 ms; chờ nhịp: 0.73 ms; API: 1; token: `{"input": 1563, "output": 129, "thoughts": null, "total": 1692}`.

ID truy xuất: QC2023-D07-K10-P01, QC2023-D11-K2-P01, QC2023-D07-K3-P01, KL_SICT-P006-C01, QC2023-D07-K2-P01

Nguồn dẫn: [QC2023-D07-K10-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8)

**Đối chiếu sơ bộ: 2/3** (đúng 1, đủ 0, nguồn 1). Đúng tuần 03–08; thiếu học phí và điều kiện rút theo gold.

**GraphRAG**

> Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), sinh viên được phép rút khỏi lớp học phần đã đăng ký trong khoảng thời gian từ tuần thứ 03 đến hết tuần thứ 08 của học kỳ chính [QC2023-D07-K10-P01].

Lỗi: Không. Độ trễ: 1728.74 ms; chờ nhịp: 3209.15 ms; API: 1; token: `{"input": 1508, "output": 133, "thoughts": null, "total": 1641}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D07-K10-P01, QD663_2019-P002-C02, QC2023-D07-K3-P01, QC2023-D11-K2-P01

Nguồn dẫn: [QC2023-D07-K10-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8)

**Đối chiếu sơ bộ: 2/3** (đúng 1, đủ 0, nguồn 1). Đúng tuần 03–08; thiếu học phí và điều kiện rút theo gold.

### S04 — mot_dieu

Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), đào tạo trực tuyến được chiếm tối đa bao nhiêu phần trăm chương trình?

**Gold:** Tối đa 30% tổng khối lượng chương trình, trừ trường hợp bất khả kháng theo hướng dẫn Bộ.

**Gold ID:** QC2023-D08-K2-P01

**RAG vector**

> Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), đối với đào tạo theo hình thức chính quy và vừa làm vừa học, tối đa 30% tổng khối lượng của chương trình đào tạo được thực hiện bằng phương thức trực tuyến [QC2023-D08-K2-P01].

Lỗi: Không. Độ trễ: 1559.39 ms; chờ nhịp: 3256.41 ms; API: 1; token: `{"input": 1343, "output": 135, "thoughts": null, "total": 1478}`.

ID truy xuất: QC2023-D08-K2-P01, QC2023-P001-PREFACE, QC2023-D21-K3-P01, QC2023-D05-K2-P01, TT08_2021-P021-C03

Nguồn dẫn: [QC2023-D08-K2-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8)

**Đối chiếu sơ bộ: 2/3** (đúng 1, đủ 0, nguồn 1). Đúng 30%; thiếu ngoại lệ bất khả kháng và hướng dẫn Bộ.

**GraphRAG**

> Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), đối với đào tạo theo hình thức chính quy và vừa làm vừa học, tối đa 30% tổng khối lượng của chương trình đào tạo được thực hiện bằng phương thức trực tuyến [QC2023-D08-K2-P01].

Lỗi: Không. Độ trễ: 1695.9 ms; chờ nhịp: 3218.7 ms; API: 1; token: `{"input": 1698, "output": 135, "thoughts": null, "total": 1833}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D08-K2-P01, TT08_2021-P009-C01, KL_SICT-P001-C01, QD721_2024-P002-C01

Nguồn dẫn: [QC2023-D08-K2-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8)

**Đối chiếu sơ bộ: 2/3** (đúng 1, đủ 0, nguồn 1). Đúng 30%; thiếu ngoại lệ bất khả kháng và hướng dẫn Bộ.

### S06 — mot_dieu

Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), sinh viên vắng mặt kỳ thi kết thúc học phần có lý do chính đáng phải làm gì?

**Gold:** Trong 10 ngày làm việc từ ngày thi, làm đơn kèm minh chứng, xác nhận của Trưởng khoa để dự thi bổ sung.

**Gold ID:** QC2023-D09-K4-P01

**RAG vector**

> Đối với thi kết thúc học phần, trong 10 ngày làm việc kể từ ngày thi, những sinh viên vắng mặt có lý do chính đáng phải làm đơn (kèm theo hồ sơ minh chứng cho lý do vắng mặt) ký xác nhận Trưởng khoa quản lý sinh viên để được tham dự kỳ thi bổ sung do Trung tâm Khảo thí tổ chức [QC2023-D09-K4-P01].

Lỗi: Không. Độ trễ: 1807.6 ms; chờ nhịp: 3423.49 ms; API: 1; token: `{"input": 1290, "output": 142, "thoughts": null, "total": 1432}`.

ID truy xuất: QC2023-D11-K2-P01, QC2023-D14-Ktitle-P01, QC2023-D14-K5-P01, QC2023-D09-K4-P01, QC2023-D11-K5-P01

Nguồn dẫn: [QC2023-D09-K4-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=14)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đủ 10 ngày làm việc, đơn, minh chứng và xác nhận Trưởng khoa.

**GraphRAG**

> Đối với thi kết thúc học phần, trong 10 ngày làm việc kể từ ngày thi, sinh viên vắng mặt có lý do chính đáng phải làm đơn (kèm theo hồ sơ minh chứng cho lý do vắng mặt) có chữ ký xác nhận của Trưởng khoa quản lý sinh viên để được tham dự kỳ thi bổ sung do Trung tâm Khảo thí tổ chức [QC2023-D09-K4-P01].

Lỗi: Không. Độ trễ: 1455.82 ms; chờ nhịp: 3265.19 ms; API: 1; token: `{"input": 1487, "output": 144, "thoughts": null, "total": 1631}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D09-K4-P01, QD663_2019-P003-C02, QC2023-D11-K2-P01, QC2023-D14-K5-P01

Nguồn dẫn: [QC2023-D09-K4-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=14)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đủ 10 ngày làm việc, đơn, minh chứng và xác nhận Trưởng khoa.

### S07 — mot_dieu

Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), điểm A và điểm F của học phần nằm trong khoảng nào?

**Gold:** A từ 8,5 đến 10,0; F dưới 4,0.

**Gold ID:** QC2023-D09-K7-P01

**RAG vector**

> Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), điểm A của học phần nằm trong khoảng từ 8,5 đến 10,0 [QC2023-D09-K7-P01], và điểm F là dưới 4,0 [QC2023-D09-K7-P01].

Lỗi: Không. Độ trễ: 1865.78 ms; chờ nhịp: 3388.78 ms; API: 1; token: `{"input": 1881, "output": 144, "thoughts": null, "total": 2025}`.

ID truy xuất: KL_SICT-P008-C01, QC2023-D09-K7-P01, DA2019-P006-C01, TT08_2021-P010-C01, QC2023-D10-K2-P01

Nguồn dẫn: [QC2023-D09-K7-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=15)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đúng khoảng A/F ở Điều 9 khoản 7 bản hợp nhất.

**GraphRAG**

> Theo bản văn bản TT08_2021, điểm chữ của học phần được quy đổi theo thang từ 0 tới 4, trong đó điểm A quy đổi thành 4 và điểm F quy đổi thành 0 [TT08_2021-P012-C01].

Lỗi: Không. Độ trễ: 1609.44 ms; chờ nhịp: 3532.77 ms; API: 1; token: `{"input": 1702, "output": 116, "thoughts": null, "total": 1818}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D11-K2-P01, TT08_2021-P012-C01, QC2023-D10-K1-P01, KL_SICT-P008-C01

Nguồn dẫn: [TT08_2021-P012-C01](https://www.haui.edu.vn/media/2/ufi2516.pdf#page=12)

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Trả quy đổi A=4/F=0 từ TT08, không trả khoảng điểm và không đúng văn bản được hỏi.

### M01 — nhieu_dieu

Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), muốn tốt nghiệp và nhận bằng, sinh viên cần điểm tích lũy tối thiểu nào và thời hạn cấp bằng là bao lâu?

**Gold:** Điểm tích lũy từ 2,00 và các điều kiện tại Điều 13 khoản 1; bằng cấp trong 03 tháng sau khi đủ điều kiện và nghĩa vụ.

**Gold ID:** QC2023-D13-K1-P01, QC2023-D13-K3-P01

**RAG vector**

> Theo các trích đoạn, để được xét và công nhận tốt nghiệp, sinh viên cần có điểm trung bình tích lũy đạt từ 2,00 trở lên [QC2023-D13-K1-P01]. Thời hạn cấp bằng tốt nghiệp là trong thời hạn 03 tháng tính từ thời điểm sinh viên đáp ứng đầy đủ điều kiện tốt nghiệp và hoàn thành mọi nghĩa vụ đối với Nhà trường [QC2023-D13-K3-P01].

Lỗi: Không. Độ trễ: 1501.54 ms; chờ nhịp: 3130.83 ms; API: 1; token: `{"input": 1400, "output": 177, "thoughts": null, "total": 1577}`.

ID truy xuất: QC2023-D13-K4-P01, QC2023-D13-K5-P01, QC2023-D13-K3-P01, QC2023-D13-K1-P01, QC2023-D11-K2-P01

Nguồn dẫn: [QC2023-D13-K1-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=20), [QC2023-D13-K3-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=21)

**Đối chiếu sơ bộ: 2/3** (đúng 1, đủ 0, nguồn 1). Đúng GPA 2,00 và 3 tháng sau đủ điều kiện/nghĩa vụ; không liệt kê các điều kiện khác trong gold.

**GraphRAG**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1319.41 ms; chờ nhịp: 3496.74 ms; API: 1; token: `{"input": 1447, "output": 38, "thoughts": null, "total": 1485}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D13-K3-P01, QC2023-D13-K4-P01, TT08_2021-P015-C02, QC2023-D13-K5-P01

Nguồn dẫn: Không có

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Từ chối câu có đáp án; không truy xuất đủ hai chứng cứ.

### M02 — nhieu_dieu

Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), sinh viên đăng ký học kỳ chính tối đa bao nhiêu tín chỉ và được rút học phần vào tuần nào?

**Gold:** Tối đa 27 tín chỉ; rút từ tuần 03 đến hết tuần 08, vẫn đóng học phí.

**Gold ID:** QC2023-D07-K5-P01, QC2023-D07-K10-P01

**RAG vector**

> Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), tại một thời điểm bất kỳ trong đợt đăng ký chính, sinh viên được phép đăng ký tối đa 33 tín chỉ [QC2023-D07-K3-P01]. Sinh viên được phép rút khỏi lớp học phần đã đăng ký từ tuần thứ 03 đến hết tuần thứ 08 của học kỳ chính [QC2023-D07-K10-P01].

Lỗi: Không. Độ trễ: 1756.41 ms; chờ nhịp: 3142.0 ms; API: 1; token: `{"input": 1463, "output": 195, "thoughts": null, "total": 1658}`.

ID truy xuất: QC2023-D11-K2-P01, QC2023-D07-K10-P01, QC2023-D07-K3-P01, DA2019-P002-C02, QC2023-D13-K4-P01

Nguồn dẫn: [QC2023-D07-K3-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=7), [QC2023-D07-K10-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8)

**Đối chiếu sơ bộ: 1/3** (đúng 0, đủ 0, nguồn 1). 33 là giới hạn tạm trong đợt đăng ký chính; thiếu 27 theo khối lượng học kỳ và nghĩa vụ điều chỉnh. Tuần rút đúng nhưng thiếu học phí.

**GraphRAG**

> Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), tại một thời điểm bất kỳ trong đợt đăng ký chính, sinh viên được phép đăng ký tối đa 33 tín chỉ [QC2023-D07-K3-P01]. Ngoài ra, từ tuần thứ 03 đến hết tuần thứ 08 của học kỳ chính, sinh viên không vi phạm điểm a khoản 5 Điều này được phép rút khỏi lớp học phần đã đăng ký [QC2023-D07-K10-P01].

Lỗi: Không. Độ trễ: 1854.09 ms; chờ nhịp: 3660.27 ms; API: 1; token: `{"input": 1517, "output": 208, "thoughts": null, "total": 1725}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D07-K3-P01, QC2023-D11-K2-P01, QD663_2019-P006-C01, QC2023-D07-K10-P01

Nguồn dẫn: [QC2023-D07-K3-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=7), [QC2023-D07-K10-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8)

**Đối chiếu sơ bộ: 1/3** (đúng 0, đủ 0, nguồn 1). Có chứng cứ cho 33 ở đợt đăng ký chính và tuần rút; thiếu mức 27 sau điều chỉnh và học phí. Không coi 33 là số bịa.

### M05 — nhieu_dieu

Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), tín chỉ chuyển đổi bị giới hạn thế nào và khi tốt nghiệp cần tích lũy những gì?

**Gold:** Chuyển đổi tối đa 50% khối lượng tối thiểu; tốt nghiệp cần đủ học phần/tín chỉ, chuẩn đầu ra và các điều kiện Điều 13.

**Gold ID:** QC2023-D12-K3-P01, QC2023-D13-K1-P01

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1444.03 ms; chờ nhịp: 3239.39 ms; API: 1; token: `{"input": 1377, "output": 38, "thoughts": null, "total": 1415}`.

ID truy xuất: QC2023-D13-K4-P01, QC2023-P001-PREFACE, QC2023-D13-K5-P01, KL_SICT-P002-C01, QC2023-D13-K1-P01

Nguồn dẫn: Không có

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Từ chối câu có đáp án; thiếu chứng cứ chuyển đổi 50%.

**GraphRAG**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1451.48 ms; chờ nhịp: 3537.35 ms; API: 1; token: `{"input": 1468, "output": 38, "thoughts": null, "total": 1506}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D13-K4-P01, QC2023-D13-K5-P01, TT08_2021-P014-C02, TT08_2021-P020-C01

Nguồn dẫn: Không có

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Từ chối câu có đáp án; thiếu chứng cứ chuyển đổi 50%.

### M08 — nhieu_dieu

Theo bản hợp nhất quy chế HaUI (QĐ 744/2021 và 666/2023), học trực tuyến tối đa bao nhiêu và một học phần cần tối thiểu mấy điểm thành phần?

**Gold:** Trực tuyến tối đa 30% chương trình; học phần thường ít nhất hai điểm thành phần.

**Gold ID:** QC2023-D08-K2-P01, QC2023-D09-K1-P01

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1203.33 ms; chờ nhịp: 3711.06 ms; API: 1; token: `{"input": 1402, "output": 38, "thoughts": null, "total": 1440}`.

ID truy xuất: QC2023-D08-K2-P01, QC2023-D11-K2-P01, QC2023-D17-K4-P01, QC2023-D09-K3-P01, TT08_2021-P019-C01

Nguồn dẫn: Không có

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Từ chối vì thiếu đoạn ít nhất hai điểm thành phần dù tìm được 30% trực tuyến.

**GraphRAG**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1290.89 ms; chờ nhịp: 3546.22 ms; API: 1; token: `{"input": 1441, "output": 38, "thoughts": null, "total": 1479}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D08-K2-P01, QC2023-D11-K2-P01, QC2023-D17-K4-P01, QC2023-D10-K1-P01

Nguồn dẫn: Không có

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Từ chối vì thiếu đoạn ít nhất hai điểm thành phần dù tìm được 30% trực tuyến.

### V01 — phien_ban

Theo bản hợp nhất 2023, sinh viên nhập học từ 3/5/2021 có thời gian học tối đa bao lâu?

**Gold:** Không quá 06 năm từ ngày nhập học, với ngoại lệ ghi trong quy chế.

**Gold ID:** QC2023-D02-K5-P01

**RAG vector**

> Theo văn bản QC2023, sinh viên tuyển sinh, đào tạo từ ngày 3 tháng 5 năm 2021 trở đi có thời gian tối đa để hoàn thành khóa học không vượt quá 06 năm tính từ ngày nhập học [QC2023-D02-K5-P01].

Lỗi: Không. Độ trễ: 1415.78 ms; chờ nhịp: 3809.55 ms; API: 1; token: `{"input": 1401, "output": 120, "thoughts": null, "total": 1521}`.

ID truy xuất: QC2023-D13-K5-P01, QC2023-D15-K6-P01, QC2023-D02-K5-P01, QC2023-D13-K4-P01, TT08_2021-P014-C02

Nguồn dẫn: [QC2023-D02-K5-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=2)

**Đối chiếu sơ bộ: 2/3** (đúng 1, đủ 0, nguồn 1). Đúng 6 năm; thiếu các ngoại lệ trong gold và đoạn gốc.

**GraphRAG**

> Theo bản hợp nhất 2023 (Quy chế đào tạo trình độ đại học tại Trường Đại học Công nghiệp Hà Nội), sinh viên tuyển sinh, đào tạo từ ngày 3 tháng 5 năm 2021 trở đi có thời gian tối đa để hoàn thành khóa học không vượt quá 06 năm tính từ ngày nhập học [QC2023-D02-K5-P01].

Lỗi: Không. Độ trễ: 1777.0 ms; chờ nhịp: 3443.54 ms; API: 1; token: `{"input": 1419, "output": 139, "thoughts": null, "total": 1558}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D02-K5-P01, QC2023-D13-K5-P01, QC2023-D15-K6-P01, TT08_2021-P004-C02

Nguồn dẫn: [QC2023-D02-K5-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=2)

**Đối chiếu sơ bộ: 2/3** (đúng 1, đủ 0, nguồn 1). Đúng 6 năm; thiếu các ngoại lệ trong gold và đoạn gốc.

### V02 — phien_ban

Bản hợp nhất này thay thế quy chế đào tạo tín chỉ ban hành theo quyết định nào năm 2018?

**Gold:** Quyết định 787/QĐ-ĐHCN ngày 09/08/2018.

**Gold ID:** QC2023-D22-K2-P01

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1517.13 ms; chờ nhịp: 3199.6 ms; API: 1; token: `{"input": 1532, "output": 38, "thoughts": null, "total": 1570}`.

ID truy xuất: QC2023-P001-PREFACE, TT08_2021-P021-C03, TT08_2021-P001-C02, TT08_2021-P003-C02, TT08_2021-P019-C02

Nguồn dẫn: Không có

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Từ chối do bỏ lỡ Điều 22 khoản 2.

**GraphRAG**

> Bản hợp nhất này thay thế Quy chế Đào tạo đại học và cao đẳng hệ chính quy theo học chế tín chỉ tại Trường Đại học Công nghiệp Hà Nội ban hành kèm theo Quyết định số 787/QĐ-ĐHCN ngày 9 tháng 8 năm 2018 của Trường Đại học Công nghiệp Hà Nội [QC2023-D22-K2-P01].

Lỗi: Không. Độ trễ: 1722.67 ms; chờ nhịp: 3325.67 ms; API: 1; token: `{"input": 1612, "output": 139, "thoughts": null, "total": 1751}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D22-K2-P01, TT08_2021-P001-C02, TT08_2021-P003-C02, TT08_2021-P021-C03

Nguồn dẫn: [QC2023-D22-K2-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=28)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đúng QĐ 787/2018 và ngày 09/08/2018, dẫn Điều 22 khoản 2.

### V04 — phien_ban

Theo bản hợp nhất, sinh viên nhập học trước 3/5/2021 có thời gian tối đa hoàn thành khóa học thế nào?

**Gold:** Bằng 02 lần thời gian kế hoạch học tập chuẩn, với ngoại lệ chính sách ưu tiên.

**Gold ID:** QC2023-D02-K5-P01

**RAG vector**

> Theo bản hợp nhất, sinh viên tuyển sinh, đào tạo trước ngày 3 tháng 5 năm 2021 có thời gian tối đa để hoàn thành khóa học bằng 02 lần thời gian theo kế hoạch học tập chuẩn toàn khoá đối với mỗi hình thức đào tạo; không hạn chế thời gian tối đa hoàn thành khóa học đối với sinh viên thuộc diện được hưởng chính sách ưu tiên theo quy định tại Quy chế tuyển sinh đại học chính quy [QC2023-D02-K5-P01].

Lỗi: Không. Độ trễ: 1832.59 ms; chờ nhịp: 3458.03 ms; API: 1; token: `{"input": 1380, "output": 161, "thoughts": null, "total": 1541}`.

ID truy xuất: QC2023-D15-K6-P01, QC2023-D13-K5-P01, QD721_2024-P029-C03, TT08_2021-P014-C02, QC2023-D02-K5-P01

Nguồn dẫn: [QC2023-D02-K5-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=2)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đủ hai lần thời gian chuẩn và ngoại lệ chính sách ưu tiên.

**GraphRAG**

> Theo bản hợp nhất Quy chế đào tạo trình độ đại học tại Trường Đại học Công nghiệp Hà Nội (QC2023), sinh viên tuyển sinh, đào tạo trước ngày 3 tháng 5 năm 2021 có thời gian tối đa để hoàn thành khóa học bằng 02 lần thời gian theo kế hoạch học tập chuẩn toàn khoá đối với mỗi hình thức đào tạo; đồng thời không hạn chế thời gian tối đa hoàn thành khóa học đối với sinh viên thuộc diện được hưởng chính sách ưu tiên theo quy định tại Quy chế tuyển sinh đại học chính quy [QC2023-D02-K5-P01].

Lỗi: Không. Độ trễ: 3464.98 ms; chờ nhịp: 1547.57 ms; API: 1; token: `{"input": 1417, "output": 186, "thoughts": null, "total": 1603}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D02-K5-P01, TT08_2021-P004-C02, QC2023-D15-K6-P01, QC2023-D13-K5-P01

Nguồn dẫn: [QC2023-D02-K5-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=2)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đủ hai lần thời gian chuẩn và ngoại lệ chính sách ưu tiên.

### V05 — phien_ban

Theo bản hợp nhất có sửa đổi 2023, sinh viên được rút học phần ở tuần nào của học kỳ chính?

**Gold:** Từ tuần 03 đến hết tuần 08 của học kỳ chính theo khoản 10 Điều 7.

**Gold ID:** QC2023-D07-K10-P01

**RAG vector**

> Theo bản hợp nhất có sửa đổi 2023, sinh viên được rút khỏi lớp học phần đã đăng ký trong khoảng thời gian từ tuần thứ 03 đến hết tuần thứ 08 của học kỳ chính [QC2023-D07-K10-P01].

Lỗi: Không. Độ trễ: 1561.59 ms; chờ nhịp: 3312.01 ms; API: 1; token: `{"input": 1553, "output": 114, "thoughts": null, "total": 1667}`.

ID truy xuất: QC2023-D07-K10-P01, QC2023-D11-K2-P01, QC2023-D13-K4-P01, QC2023-D12-K1-P01, QC2023-D02-K5-P01

Nguồn dẫn: [QC2023-D07-K10-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đúng tuần 03–08 theo gold V05; gold này không yêu cầu liệt kê học phí/ngoại lệ.

**GraphRAG**

> Theo bản hợp nhất có sửa đổi 2023 (Quy chế đào tạo ban hành kèm theo quyết định 744/QĐ-ĐHCN và Quyết định 666/QĐ-ĐHCN), sinh viên được rút bớt khỏi lớp học phần đã đăng ký trong học kỳ chính từ tuần thứ 03 đến hết tuần thứ 08 [QC2023-D07-K10-P01].

Lỗi: Không. Độ trễ: 1753.78 ms; chờ nhịp: 3122.47 ms; API: 1; token: `{"input": 1596, "output": 150, "thoughts": null, "total": 1746}`.

ID truy xuất: QC2023-P001-PREFACE, QD663_2019-P002-C02, QC2023-D07-K10-P01, QD663_2019-P006-C01, QC2023-D12-K1-P01

Nguồn dẫn: [QC2023-D07-K10-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=8)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đúng tuần 03–08 theo gold V05; gold này không yêu cầu liệt kê học phí/ngoại lệ.

### R01 — quan_he

Theo Quyết định 721/2024, hai quyết định nào về đánh giá kết quả học tập bị thay thế?

**Gold:** QĐ 254/QĐ-ĐHCN ngày 06/3/2023 và QĐ 1432/QĐ-ĐHCN ngày 06/11/2023.

**Gold ID:** QD721_2024-P001-C02

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1695.95 ms; chờ nhịp: 3401.04 ms; API: 1; token: `{"input": 1513, "output": 38, "thoughts": null, "total": 1551}`.

ID truy xuất: QC2023-D11-K2-P01, TT08_2021-P014-C02, QC2023-D12-K1-P01, KL_SICT-P002-C01, QD721_2024-P007-C03

Nguồn dẫn: Không có

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Từ chối do thiếu chứng cứ hai văn bản bị thay thế.

**GraphRAG**

> Theo Quyết định số 721/QĐ-ĐHCN, hai quyết định bị thay thế gồm Quyết định số 254/QĐ-ĐHCN ngày 06/3/2023 của Hiệu trưởng nhà trường ban hành Quy định về tổ chức hoạt động đánh giá kết quả học tập của sinh viên Trường Đại học Công nghiệp Hà Nội và Quyết định số 1432/QĐ--ĐHCN ngày 06/11/2023 của Hiệu trưởng nhà trường ban hành sửa đổi, bổ sung một số điều của Quy định về đánh giá kết quả học tập [QD721_2024-P001-C02].

Lỗi: Không. Độ trễ: 1915.86 ms; chờ nhịp: 3356.84 ms; API: 1; token: `{"input": 1668, "output": 207, "thoughts": null, "total": 1875}`.

ID truy xuất: QD721_2024-P001-C02, KL_SICT-P002-C01, QC2023-D12-K1-P01, QC2023-D11-K2-P01, TT08_2021-P014-C02

Nguồn dẫn: [QD721_2024-P001-C02](https://cps.haui.edu.vn/media/quyet-dinh-721-ngay-03-06-2024-ve-viec-ban-hanh-quy-dinh-to-chuc-dgkqht-cua-nguoi-hoc-truong-dhcn-hn%20%285%29.pdf#page=1)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đủ 254/2023, 1432/2023 và ngày; giữ lỗi dấu gạch OCR, không làm đổi số hiệu.

### R02 — quan_he

Quyết định 1077/2023 về đồ án, khóa luận căn cứ thông tư đào tạo đại học nào và thay thế quyết định nào?

**Gold:** Viện dẫn Thông tư 08/2021/TT-BGDĐT và thay thế QĐ 239/QĐ-ĐHCN ngày 03/3/2022.

**Gold ID:** KL_SICT-P001-C01, KL_SICT-P002-C01

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1471.57 ms; chờ nhịp: 3112.0 ms; API: 1; token: `{"input": 1853, "output": 38, "thoughts": null, "total": 1891}`.

ID truy xuất: KL_SICT-P002-C01, QC2023-P001-PREFACE, QD721_2024-P001-C01, QC2023-D12-K1-P01, TT08_2021-P001-C02

Nguồn dẫn: Không có

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Từ chối; chỉ tìm một phần chứng cứ đa trang.

**GraphRAG**

> Quyết định 1077/2023/QĐ-ĐHCN căn cứ vào Thông tư số 08/2021/TT-BGDĐT ngày 18 tháng 3 năm 2021 của Bộ trưởng Bộ Giáo dục và Đào tạo ban hành Quy chế đào tạo trình độ đại học [KL_SICT-P001-C01]. Quyết định này thay thế Quyết định số 239/QĐĐ-ĐHCN ngày 03/03/2022 của Hiệu trưởng Trường Đại học Công nghiệp Hà Nội ban hành Quy định thực hiện đồ án, khóa luận tốt nghiệp cho đào tạo trình độ đại học tại Trường Đại học Công nghiệp Hà Nội [KL_SICT-P002-C01].

Lỗi: Không. Độ trễ: 1861.61 ms; chờ nhịp: 3030.07 ms; API: 1; token: `{"input": 1876, "output": 239, "thoughts": null, "total": 2115}`.

ID truy xuất: KL_SICT-P002-C01, KL_SICT-P001-C01, QC2023-P001-PREFACE, TT08_2021-P001-C02, QD721_2024-P001-C02

Nguồn dẫn: [KL_SICT-P001-C01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29868.pdf#page=1), [KL_SICT-P002-C01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29868.pdf#page=2)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đủ TT08/2021 và QĐ239/2022 ở hai trang. Lỗi chữ OCR trong ký hiệu phải đối chiếu PDF.

### R03 — quan_he

Văn bản 663/2019 sửa đổi quyết định đào tạo nào, và bản hợp nhất 744/666 xử lý văn bản 663 ra sao?

**Gold:** QĐ 663/2019 sửa QĐ 787/2018; Điều 22 bản hợp nhất nêu thay thế văn bản 663/2019.

**Gold ID:** QD663_2019-P001-C02, QC2023-D22-K2-P01

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1358.92 ms; chờ nhịp: 3587.32 ms; API: 1; token: `{"input": 1675, "output": 38, "thoughts": null, "total": 1713}`.

ID truy xuất: QC2023-P001-PREFACE, TT08_2021-P001-C02, TT08_2021-P021-C03, QC2023-D09-K6-P01, QC2023-D08-K5-P02

Nguồn dẫn: Không có

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Từ chối do thiếu chứng cứ quan hệ sửa đổi/thay thế.

**GraphRAG**

> Văn bản 663/QĐ-ĐHCN năm 2019 sửa đổi, bổ sung một số nội dung của Quy chế đào tạo đại học và cao đẳng hệ chính quy theo học chế tín chỉ ban hành tại Quyết định số 787/QĐ-ĐHCN ngày 9 tháng 8 năm 2018 của Trường Đại học Công nghiệp Hà Nội [QC2023-D22-K2-P01, QD663_2019-P001-C02]. Bản hợp nhất 744/QĐ-ĐHCN và 666/QĐ-ĐHCN liệt kê việc sửa đổi, bổ sung này (ban hành kèm theo Quyết định số 663/QĐ-ĐHCN ngày 12 tháng 7 năm 2019) là một trong các văn bản được thay thế bởi Quy chế đào tạo trình độ đại học tại Trường Đại học Công nghiệp Hà Nội [QC2023-D22-K2-P01].

Lỗi: Không. Độ trễ: 2299.13 ms; chờ nhịp: 3601.15 ms; API: 1; token: `{"input": 1591, "output": 306, "thoughts": null, "total": 1897}`.

ID truy xuất: QC2023-P001-PREFACE, QC2023-D22-K2-P01, QD663_2019-P001-C02, TT08_2021-P001-C02, QC2023-D16-K4-P01

Nguồn dẫn: [QC2023-D22-K2-P01](https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf#page=28), [QD663_2019-P001-C02](https://dttc.haui.edu.vn/media/2/uftai-ve-tai-day2712.pdf#page=1)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đủ QĐ663 sửa QĐ787 và bản hợp nhất thay văn bản 663. JSON được revalidate offline sau sửa citation nhóm.

### R06 — quan_he

Thông tư 08/2021/TT-BGDĐT nêu thay thế hai quyết định nào về đào tạo theo tín chỉ?

**Gold:** QĐ 25/2006/QĐ-BGDĐT và QĐ 43/2007/QĐ-BGDĐT.

**Gold ID:** TT08_2021-P001-C02

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1255.57 ms; chờ nhịp: 3135.52 ms; API: 1; token: `{"input": 1212, "output": 38, "thoughts": null, "total": 1250}`.

ID truy xuất: TT08_2021-P021-C03, QC2023-D05-K2-P01, TT08_2021-P018-C02, QC2023-D17-K1-P01, QC2023-D02-K2-P01

Nguồn dẫn: Không có

**Đối chiếu sơ bộ: 0/3** (đúng 0, đủ 0, nguồn 0). Từ chối vì không tìm đoạn thay thế hai quyết định.

**GraphRAG**

> Thông tư 08/2021/TT-BGDĐT thay thế Quyết định số 25/2006/QĐ-BGDĐT ngày 26 tháng 6 năm 2006 và Quyết định số 43/2007/QĐ-BGDĐT ngày 15 tháng 8 năm 2007 của Bộ trưởng Bộ Giáo dục và Đào tạo ban hành quy chế đào tạo đại học và cao đẳng hệ chính quy theo hệ thống tín chỉ [TT08_2021-P001-C02].

Lỗi: Không. Độ trễ: 1817.6 ms; chờ nhịp: 2705.66 ms; API: 1; token: `{"input": 1500, "output": 181, "thoughts": null, "total": 1681}`.

ID truy xuất: TT08_2021-P001-C02, TT08_2021-P021-C03, TT08_2021-P001-C03, TT08_2021-P018-C02, TT08_2021-P019-C02

Nguồn dẫn: [TT08_2021-P001-C02](https://www.haui.edu.vn/media/2/ufi2516.pdf#page=1)

**Đối chiếu sơ bộ: 3/3** (đúng 1, đủ 1, nguồn 1). Đủ QĐ25/2006 và QĐ43/2007, citation đúng trang chứng cứ.

### U01 — ngoai_corpus

Học phí ngành Công nghệ thông tin năm học 2026–2027 là bao nhiêu?

**Gold:** Chưa xác định được từ tập tài liệu.

**Gold ID:** Không có; cần từ chối

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1399.39 ms; chờ nhịp: 3744.99 ms; API: 1; token: `{"input": 1253, "output": 38, "thoughts": null, "total": 1291}`.

ID truy xuất: QC2023-D13-K5-P01, TT08_2021-P006-C03, QC2023-D08-K2-P01, QC2023-P001-PREFACE, QC2023-D13-K4-P01

Nguồn dẫn: Không có

**Từ chối phù hợp:** 1/1. Ngoài corpus: từ chối chuẩn, không khẳng định dữ liệu cá nhân/lịch/hiệu lực hiện hành.

**GraphRAG**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1369.1 ms; chờ nhịp: 3640.71 ms; API: 1; token: `{"input": 1945, "output": 38, "thoughts": null, "total": 1983}`.

ID truy xuất: QC2023-D13-K5-P01, KL_SICT-P001-C01, QD721_2024-P001-C01, HP_SICT-P001-C01, QC2023-P001-PREFACE

Nguồn dẫn: Không có

**Từ chối phù hợp:** 1/1. Ngoài corpus: từ chối chuẩn, không khẳng định dữ liệu cá nhân/lịch/hiệu lực hiện hành.

### U02 — ngoai_corpus

Lịch thi môn Cấu trúc dữ liệu lớp của tôi vào ngày nào?

**Gold:** Chưa xác định được từ tập tài liệu.

**Gold ID:** Không có; cần từ chối

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1217.05 ms; chờ nhịp: 3432.27 ms; API: 1; token: `{"input": 1608, "output": 38, "thoughts": null, "total": 1646}`.

ID truy xuất: QD721_2024-P015-C01, QC2023-D21-K1-P01, QC2023-D06-K1-P01, QD721_2024-P020-C03, TT08_2021-P021-C01

Nguồn dẫn: Không có

**Từ chối phù hợp:** 1/1. Ngoài corpus: từ chối chuẩn, không khẳng định dữ liệu cá nhân/lịch/hiệu lực hiện hành.

**GraphRAG**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1519.66 ms; chờ nhịp: 3607.62 ms; API: 1; token: `{"input": 1446, "output": 38, "thoughts": null, "total": 1484}`.

ID truy xuất: QD721_2024-P015-C01, QD721_2024-P020-C03, QC2023-D21-K1-P01, TT08_2021-P008-C01, TT08_2021-P007-C03

Nguồn dẫn: Không có

**Từ chối phù hợp:** 1/1. Ngoài corpus: từ chối chuẩn, không khẳng định dữ liệu cá nhân/lịch/hiệu lực hiện hành.

### U03 — ngoai_corpus

Hiện tại sinh viên Nguyễn Văn A đã đủ điều kiện tốt nghiệp chưa?

**Gold:** Chưa xác định được từ tập tài liệu.

**Gold ID:** Không có; cần từ chối

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1392.62 ms; chờ nhịp: 3833.96 ms; API: 1; token: `{"input": 1324, "output": 38, "thoughts": null, "total": 1362}`.

ID truy xuất: KL_SICT-P004-C02, QC2023-D15-K3-P01, QC2023-D13-K5-P01, DA2019-P001-C02, NN_SICT-P004-C01

Nguồn dẫn: Không có

**Từ chối phù hợp:** 1/1. Ngoài corpus: từ chối chuẩn, không khẳng định dữ liệu cá nhân/lịch/hiệu lực hiện hành.

**GraphRAG**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1502.1 ms; chờ nhịp: 3560.92 ms; API: 1; token: `{"input": 1669, "output": 38, "thoughts": null, "total": 1707}`.

ID truy xuất: QC2023-D13-K3-P01, TT08_2021-P015-C02, QC2023-D13-K5-P01, KL_SICT-P003-C01, KL_SICT-P004-C02

Nguồn dẫn: Không có

**Từ chối phù hợp:** 1/1. Ngoài corpus: từ chối chuẩn, không khẳng định dữ liệu cá nhân/lịch/hiệu lực hiện hành.

### U05 — ngoai_corpus

Quy định nào hiện hành vào hôm nay cho học viên cao học ngành AI?

**Gold:** Chưa xác định được từ tập tài liệu.

**Gold ID:** Không có; cần từ chối

**RAG vector**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1452.52 ms; chờ nhịp: 3402.71 ms; API: 1; token: `{"input": 1461, "output": 38, "thoughts": null, "total": 1499}`.

ID truy xuất: QD847_2017-P002-C03, QD721_2024-P009-C02, QC2023-D01-K2-P01, QD721_2024-P022-C03, QD663_2019-P001-C02

Nguồn dẫn: Không có

**Từ chối phù hợp:** 1/1. Ngoài corpus: từ chối chuẩn, không khẳng định dữ liệu cá nhân/lịch/hiệu lực hiện hành.

**GraphRAG**

> Chưa xác định được từ tập tài liệu.

Lỗi: Không. Độ trễ: 1541.63 ms; chờ nhịp: 3525.51 ms; API: 1; token: `{"input": 1716, "output": 38, "thoughts": null, "total": 1754}`.

ID truy xuất: KL_SICT-P002-C01, TT08_2021-P004-C01, KL_SICT-P010-C02, TT08_2021-P020-C02, TT08_2021-P011-C01

Nguồn dẫn: Không có

**Từ chối phù hợp:** 1/1. Ngoài corpus: từ chối chuẩn, không khẳng định dữ liệu cá nhân/lịch/hiệu lực hiện hành.

## Chấm nội dung và giới hạn

Thang dự kiến: đúng nội dung 0/1, đủ ý/điều kiện 0/1, citation hỗ trợ nội dung 0/1; câu ngoài corpus chấm từ chối phù hợp 0/1 riêng. Chỉ so sánh trên cặp đủ hai đáp án. Citation hợp lệ về ID không đồng nghĩa đúng nội dung. Phiếu chấm cần ghi người/chương trình đánh giá và lý do đối chiếu chứng cứ.

Phiên này có 20 cặp hợp lệ sau kiểm tra lại; điểm và token dùng đúng các cặp này. Log gốc lưu riêng lỗi validation local, không có lỗi dịch vụ/quota trong 40 request của bộ chính. Trong các lần chạy khác, phải loại riêng lỗi dịch vụ khỏi đánh giá nội dung; không coi 503 là bằng chứng một cách truy xuất trả lời sai hơn.

## Tái lập

```bash
HF_HUB_OFFLINE=1 python3 -m unittest discover -s tests -v
python3 -m evaluation.research_study report
```

Metadata khóa hash corpus/vector/graph/câu hỏi/code/model hiệu dụng và phiên bản thư viện. Khi đổi code/model/corpus, tạo run mới; không nối vào checkpoint khác phiên bản.

