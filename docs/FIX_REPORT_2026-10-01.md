# Báo cáo sửa lỗi và kiểm chứng ngày 01/10/2026

## Kết quả

Đã sửa sáu vấn đề từ `REVIEW_2026-10-01.md` và một lỗi parser citation phát hiện trong thực nghiệm thật. Đã chuyển model trong `.env` sang `gemini-3.5-flash-lite`, giữ nguyên key; quyền file `.env` vẫn 600. Không thêm thư viện, không sửa PDF/OCR/quan hệ pháp lý đã rà, không ghi đè số liệu thực nghiệm cũ.

Phạm vi phù hợp nghiên cứu khoa học cấp trường: kiểm tra hồi quy có ý nghĩa, phép đo truy xuất nhỏ và 20 câu/40 request để phân tích hai pipeline. Không kiểm tra tải lớn hay mở rộng hạ tầng ngoài mục tiêu.

## Từng lỗi và cách sửa

| Vấn đề trước sửa | Thay đổi | Bằng chứng kiểm chứng |
|---|---|---|
| Checkpoint vẫn tiếp tục khi đổi model trong `.env` | Fingerprint ghi cấu hình hiệu dụng, model embedding/revision/cửa sổ, runtime, SHA script và thứ tự chạy; lưu snapshot câu hỏi | Test tạo checkpoint model-A rồi chuyển model-B: bị chặn |
| OCR/embedding lỗi để lại corpus/vector/graph khác phiên bản | Các hàm tách không ghi chỉ mục; tạo phiên bản staging đầy đủ, kiểm tra rồi atomically đổi `current` | Giả lập lỗi OCR, lỗi embedding và vector sai số hàng: bản đang dùng giữ nguyên |
| Có câu từ chối là được miễn citation, dù còn khẳng định khác | Gemini trả JSON với `status`, `answer`, `cited_ids`; nhánh từ chối chỉ chấp nhận câu chuẩn, không có citation; nhánh trả lời yêu cầu ID hợp lệ khớp nội dung citation | Câu từ chối kèm khẳng định nghỉ 100 ngày bị chặn; từ chối thuần và đáp án có nguồn qua |
| Health báo ready dù thiếu vector; chat 500 | Kiểm tra đủ artifact, hash, số vector, chuẩn hóa, ID graph và cấu hình encoder; lỗi chỉ mục trả ready=false/chat 503 | Test xóa vector ở bản sao, chỉnh hash/encoder; HTTP smoke chỉ mục tốt trả 200 |
| 160/449 đoạn bị bỏ phần cuối khi embedding | Cửa sổ 256 token, overlap 64, embedding mọi cửa sổ rồi trung bình/chuẩn hóa; không đổi ID/gold | Đoạn dài có cùng đầu nhưng khác đuôi cho vector khác nhau; 449vector 384 chiều hữu hạn và chuẩn hóa |
| Nhận diện số hiệu khác nhau theo cách đặt document_id | Alias số/năm lấy từ metadata cho mọi văn bản; nhận cả `242/2022` và `242 năm 2022` | Test 242/2022,427/2022,721/2024 nhận cùng nút theo hai cách diễn đạt |
| Citation `[ID1, ID2]` bị chặn sai | Đọc nhóm citation, kiểm tra từng ID; không bỏ qua ID lạ cùng nhóm | Test nhóm hai ID hợp lệ qua; nhóm có FAKE bị chặn; R03 JSON API gốc được kiểm tra lại thành công |

Kiểm tra ID/cấu trúc không chứng minh toàn bộ phát biểu được chứng cứ hỗ trợ. Những lỗi nội dung mới quan sát được trong thực nghiệm được ghi vào báo cáo, không hard-code câu hỏi hoặc điều chỉnh gold theo đáp án.

## Cấu trúc chỉ mục sau sửa

`data/processed/versions/<version>/` chứa corpus, vector, graph, legal_relations và build_meta. `data/processed/current` trỏ tới phiên bản đang dùng; các đường dẫn cũ `articles.jsonl`, `vectors.npy`, `graph.json` là liên kết tương thích. Searcher pin một thư mục phiên bản khi đọc, không lấy lần lượt artifact qua các phiên bản khác nhau. API cache engine theo phiên bản/cấu hình encoder và kiểm tra chỉ mục trước request.

Các snapshot trước sửa giữ ở `evaluation/runs/pre_fix_20261001/` và `data/processed/versions/legacy_pre_atomic/`. Không dọn/xóa lịch sử tự động. Cơ chế symlink/atomic rename này phục vụ máy Linux hiện tại; chưa kiểm tra triển khai Windows hoặc xử lý sự cố mất điện ở cấp filesystem.

Corpus vẫn 9 PDF/449 đoạn, 480 nút/1.872 cạnh, 22 quan hệ pháp lý. Text và ID không đổi; bổ sung metadata ngày ban hành cho bản hợp nhất để tạo alias. Vector đổi vì đọc đủ đoạn dài. Lượt dựng mới khoảng 28,80 giây trên máy hiện tại; thời gian không bao gồm OCR thủ công/tải encoder lần đầu. Manifest ghi 160 đoạn cần nhiều cửa sổ và `silent_truncation=false`.

## Điều phối Gemini và tái lập

- Model hiện tại: `gemini-3.5-flash-lite`, đúng mã trong [tài liệu Google](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).
- Nhịp chung API/CLI tối thiểu 5 giây (~12 RPM), file pacing được khóa trên cùng máy. 40 request thực tế có khoảng cách nhỏ nhất **5,000067 giây**. Không khẳng định quota15 RPM cho mọi tài khoản; [quota phụ thuộc project/model/tier](https://ai.google.dev/gemini-api/docs/rate-limits).
- SDK một request/lượt, timeout 30 giây, giới hạn output 2048 token, cùng prompt/temperature cho hai phương pháp; lưu responseJSON thô, token, trace, thời điểm request, thời gian chờ và độ trễ pipeline riêng.
- Runner đổi luân phiên thứ tự hai phương pháp theo câu; không chạy cùng tập lệch nhau.
- Các lệnh đánh giá truy xuất tạo run mới, không ghi đè CSV/JSON cũ. Requirements pin phiên bản trực tiếp đã chạy; chưa là lock đầy đủ mọi dependency gián tiếp và chưa test cài mới trong môi trường sạch.

## Kiểm tra đã hoàn tất

1. **15 test hồi quy qua**, gồm các nhánh trên, API validation/missing key, ba mode truy xuất và bỏ lời gọi thứ hai sau lỗi 503/429/403/404 giả lập. Không gọi Gemini thật trong tests.
2. Compile `src`, `evaluation`, `tests`, `server.py` qua.
3. TypeScript/Vite build frontend qua. Frontend dùng `ready` để hiện dữ liệu chưa sẵn sàng và khóa gửi khi không có chỉ mục; số OCR lấy từ API.
4. HTTP thật health/chat compare retrieve-only trả 200; health đọc đúng model 3.5 Flash-Lite, 9 văn bản/449 đoạn/8 OCR. Chưa kiểm tra thao tác/layout bằng trình duyệt do công cụ trình duyệt không khả dụng trong phiên review.
5. **174 lượt truy xuất**: 30 câu cũ +8 quan hệ +20 câu có phạm vi rõ, mỗi bộ chạy RAG/hybrid không graph/GraphRAG; không có lỗi thực thi.
6. **40 request Gemini thật/20 cặp**, không lỗi dịch vụ/quota. Log gốc có một lỗi validation local của R03 GraphRAG; sau sửa parser và revalidate offline có 20/20 cặp hợp lệ. Không tạo request mới hoặc sửa response thô để khôi phục trường hợp này.
7. Sau bản sửa parser, thêm **một request HTTP sinh đáp án** cho R03/GraphRAG: API trả 200, model 3.5 Flash-Lite, `error=null`, citation hai ID hợp lệ. Lượt smoke này lưu riêng ở `http_generation_smoke.json`, không đưa vào bộ 20 cặp để so sánh. Tổng request Gemini trong phiên sửa/test là 41, trong đó40 thuộc thực nghiệm chính.

Log API gốc được giữ nguyên cùng metadata của code khi gọi. `generation_revalidated.json` là artifact dẫn xuất, ghi hash log gốc, SHA validator mới, lỗi trước sửa và0 request mới. Số liệu token/thời gian luôn lấy request gốc. Điều này khác chạy lại model sau sửa; không giả nhận cả 40 đáp án đã đi qua parser mới tại thời điểm request.

## Kết quả và những gì còn hạn chế

[Báo cáo thực nghiệm](../evaluation/runs/research_20261001/BAO_CAO_THUC_NGHIEM.md) chứa mỗi câu/gold, hai đáp án nguyên bản, citation, token, thời gian, điểm đối chiếu và phân tích thắng/thua. Điểm nội dung là sơ bộ do trợ lý AI đối chiếu; chưa có người phản biện độc lập.

| Thước đo | RAG | GraphRAG |
|---|---:|---:|
| Recall trên25 câu có gold của bộ 30 |0,74|0,78|
| Tìm đủ mọi gold trên bộ 30 |17/25|16/25|
| Recall8 câu quan hệ |0,25|1,00|
| Đúng ý chính/phạm vi trên16 câu có đáp án |8/16|11/16|
| Đủ ý theo gold |4/16|8/16|
| Nguồn hỗ trợ phát biểu |9/16|12/16|
| Từ chối đúng4 câu ngoài corpus |4/4|4/4|
| Độ trễ TB20 lượt sinh (không gồm chờ pacing) |1,636s|1,748s|

GraphRAG có lợi thế ở các câu quan hệ/phiên bản được thiết kế trong bộ nội bộ. RAG tốt hơn ở S07/M01, cả hai ngang nhau ở S06/V04 và bốn câu ngoài corpus. Chưa có bằng chứng đủ để kết luận ưu thế chung; bộ nhỏ/thiên lệch và chấmAI cần được kiểm tra độc lập.

Các vấn đề chất lượng còn lại là dữ liệu nghiên cứu cần phân tích, không phải tất cả đã được sửa bằng patch này: M02 thiếu phân biệt 33 tín chỉ trong đợt đăng ký và 27 khối lượng học kỳ; S07 GraphRAG chọn sai văn bản/trọng tâm; M05/M08 thiếu một phần gold; một số đáp án bỏ điều kiện/ngoại lệ dù đoạn nguồn đã được tìm. Không dùng membership citation để tuyên bố đáp án đã đúng.

## Lệnh chạy

```bash
python3 -m compileall -q src evaluation tests server.py
HF_HUB_OFFLINE=1 python3 -m unittest discover -s tests -v
npm run build --prefix frontend
python3 -m evaluation.research_study report
python3 -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Mở `http://127.0.0.1:8000`. Lượt kiểm tra HTTP được chạy trên server tạm, sau đó dừng; muốn demo cần chạy lệnh uvicorn. Khi đổi .env, khởi động lại backend. Khi đổi encoder/cách tạo vector, chạy prepare, tạo run đánh giá mới và giữ snapshot cũ.
