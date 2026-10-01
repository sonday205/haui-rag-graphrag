# Quy Chế AI · HaUI

Ứng dụng hỏi đáp có dẫn nguồn từ quy chế đào tạo HaUI, kèm chế độ so sánh **RAG vector** và **GraphRAG cấu trúc**. Giao diện React, API FastAPI, tìm kiếm/embedding chạy cục bộ; Gemini chỉ dùng để viết câu trả lời từ các đoạn PDF đã truy xuất. Giao diện và tài liệu bằng tiếng Việt.

**Phạm vi hiện tại:** 11 nguồn khảo sát, 9 PDF trong corpus (1 có lớp chữ, 8 có bản OCR do người dùng cung cấp), 449 đoạn và 22 quan hệ văn bản có chứng cứ. Hiệu lực hiện hành của các văn bản chưa được xác minh; nội dung OCR chưa được hiệu đính toàn bộ.

## Cài đặt

Cần Python 3.11+, Node.js 20+ và npm. Máy cần Internet khi tải PDF, mô hình embedding và cài gói lần đầu.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm install --prefix frontend
```

`PyMuPDF` đọc PDF; `transformers`/`torch` tạo embedding đa ngôn ngữ; `scikit-learn` và `networkx` truy xuất đồ thị; `google-genai` gọi Gemini; `FastAPI` phục vụ API và bản web build; React/Vite xây giao diện. Không cần Neo4j hay hạ tầng riêng.

## Tạo lại dữ liệu

```bash
python -m src.sources
python -m src.project prepare
```

PDF gốc ở `data/raw/`; bản Markdown từ ZIP của người dùng đã giải nén ở `data/ocr/`. `data/source_manifest.csv` giữ URL, thời điểm truy cập, SHA-256 PDF/OCR, số trang, lỗi và lý do chọn. Chỉ mục ở `data/processed/`. Trình nạp từ chối bản OCR thiếu trang hoặc sai hash. Lần đầu tạo vector, mô hình `paraphrase-multilingual-MiniLM-L12-v2` được tải đúng revision ghi trong `config.json`.

Từ 01/10/2026, mỗi lần dựng tạo một phiên bản ở `data/processed/versions/`, kiểm tra xong mới đổi liên kết `current`. Các đường dẫn `articles.jsonl`, `vectors.npy`, `graph.json` vẫn dùng được. Khi lỗi OCR/model, phiên bản đang dùng giữ nguyên. Đoạn dài được embedding qua cửa sổ 256 token, overlap 64 rồi lấy trung bình và chuẩn hóa; không bỏ phần cuối hoặc đổi ID gold. Phiên bản encoder/cấu hình và hash từng artifact nằm trong `build_meta.json`.

## Cấu hình Gemini

Tạo `.env` từ `.env.example`, đặt `GEMINI_API_KEY` **chỉ trên máy chủ**. `.env` đã bị loại khỏi Git và không được gửi vào trình duyệt. Model hiện tại là `gemini-3.5-flash-lite` trong cả config và `.env`. Ngày 01/10/2026 đã chạy 40 request/20 cặp bằng model này, không lỗi dịch vụ/quota. Nếu không có key, bật **Chỉ truy xuất** trong giao diện; API vẫn hiển thị đoạn gốc và trace. Nếu dịch vụ lỗi, giao diện hiển thị lỗi thay vì tạo đáp án giả.

Nhãn “Đã cấu hình key” chỉ xác nhận backend đã đọc key. Nếu Gemini trả 503, giao diện báo “Gemini tạm quá tải”, vẫn hiển thị chứng cứ và bỏ lời gọi sinh thứ hai của chế độ so sánh trong lượt đó. API và CLI dùng chung nhịp tối thiểu 5 giây/request (~12/phút) trên cùng máy; không thử lại HTTP ngầm, timeout 30 giây. Mức 15 RPM người dùng cung cấp là giới hạn mục tiêu; [quota thực tế phụ thuộc project/model/tier](https://ai.google.dev/gemini-api/docs/rate-limits). Sau khi đổi `.env`, khởi động lại backend; sau build frontend, tải lại trang. Lịch sử hội thoại cũ vẫn lưu trên trình duyệt.

## Chạy ứng dụng

Phát triển bằng hai terminal:

```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

```bash
npm run dev --prefix frontend
```

Mở `http://127.0.0.1:5173`. Vite chuyển `/api` về FastAPI. Giao diện có lịch sử hội thoại trên trình duyệt, câu hỏi gợi ý từ bộ đánh giá, ba chế độ (so sánh/RAG/GraphRAG), dẫn nguồn mở thẳng trang PDF, đoạn gốc, trace, thời gian và token.

Để chạy một cổng sau khi build:

```bash
npm run build --prefix frontend
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Mở `http://127.0.0.1:8000`. API: `/api/health`, `/api/suggestions`, `POST /api/chat`. API key không có trong phản hồi. Mặc định chỉ lắng nghe `127.0.0.1`; khi triển khai công khai cần đặt kiểm soát truy cập và hạn mức gọi API ở lớp máy chủ.

## Truy xuất và đánh giá

Không gọi Gemini:

```bash
python -m src.project query 'Sinh viên được rút học phần vào tuần nào?' --method rag --retrieve-only
python -m src.project evaluate --retrieve-only
```

Lệnh `evaluate` tạo thư mục run mới trong `evaluation/runs/`, gồm `latest.json`, `results.csv`, `summary.csv`, không ghi đè run cũ; có thể đặt `--run-id`. `Recall@5` chỉ có mẫu số trên câu có gold ID. Bộ 8 câu kiểm tra quan hệ chạy bằng `python -m evaluation.evaluate_multidoc`, ghi JSON có timestamp mới. Bộ này viết sau đồ thị nên chỉ dùng kiểm tra chức năng cạnh. Các file `evaluation/runs/latest.json`, `evaluation/results.csv`, `evaluation/summary.csv` và `report/report.md` giữ số liệu lịch sử trước lần sửa 01/10.

Đánh giá Gemini với checkpoint sau **mỗi lời gọi**:

```bash
python -m evaluation.run_gemini --run-id post_ocr_relations_v2 --questions-file questions_multidoc_ocr.jsonl --ids R01 R02 R03 --max-new-calls 2
```

Run sau OCR dùng `--run-id` riêng và lưu câu trả lời, chứng cứ, trace, token, thời gian và lỗi vào `evaluation/runs/gemini_<run-id>.jsonl`. Script đổi luân phiên thứ tự RAG/GraphRAG giữa câu hỏi, lưu thời điểm bắt đầu request, thời gian chờ nhịp riêng; SDK tối đa một request HTTP mỗi lượt. Script dừng ngay với `429`/lỗi quyền và sau hai lỗi `503` liên tiếp. `--retry-errors` chỉ dùng khi dịch vụ ổn định. Chỉ so sánh cặp đủ hai kết quả. Metadata khóa SHA corpus/vector/graph/câu hỏi/code/script, model hiệu dụng (kể cả `.env`) và phiên bản runtime. Đổi model/corpus phải tạo run mới.

[Báo cáo đánh giá Gemini](evaluation/BAO_CAO_DANH_GIA_GEMINI.md) giữ 7 cặp trước OCR. [Lượt thử sau OCR cũ](evaluation/BAO_CAO_GEMINI_SAU_OCR.md) giữ lỗi 503 và lượt model 3.8 Flash, không gộp với số liệu mới.

## Thực nghiệm quy mô gọn ngày 01/10/2026

[Báo cáo sửa lỗi](docs/FIX_REPORT_2026-10-01.md) và [báo cáo thực nghiệm](evaluation/runs/research_20261001/BAO_CAO_THUC_NGHIEM.md) là tài liệu hiện tại. Đã chạy 15 test hồi quy, một lượt HTTP sinh đáp án sau sửa parser, 174 lượt truy xuất (30 câu cũ + 8 quan hệ + 20 câu có phạm vi rõ, qua RAG/hybrid/GraphRAG) và 40 request Gemini cho 20 cặp. Chấm nội dung là đối chiếu sơ bộ bởi trợ lý AI, chưa có người phản biện độc lập; bộ câu hỏi nội bộ có thiên lệch.

```bash
HF_HUB_OFFLINE=1 python3 -m unittest discover -s tests -v
python3 -m evaluation.research_study report
```

`HF_HUB_OFFLINE=1` chỉ dùng khi model embedding đã tải vào cache. Bộ 20 câu/gold ở `evaluation/questions_research_20261001.jsonl`; đầu ra nguyên bản ở `gemini_research_20261001_35lite.jsonl`; JSON/CSV/phiếu chấm và trace ở `evaluation/runs/research_20261001/`. Một đáp án R03 được kiểm tra lại offline sau sửa cách đọc citation nhóm; log API gốc giữ nguyên, không gọi thêm Gemini.

Để chạy lại thực nghiệm sinh, đặt **run ID mới**:

```bash
python3 -m evaluation.run_gemini --run-id research_repeat_01 --questions-file questions_research_20261001.jsonl --max-new-calls 40
```

## Cấu trúc chính

```text
frontend/                         React + Vite, giao diện hỏi đáp
server.py                          FastAPI, giữ key ở backend
src/sources.py                     tải nguồn, manifest
src/ocr_corpus.py                  kiểm tra/tách bản OCR
src/legal_graph.py                 đồ thị và quan hệ có chứng cứ
src/project.py                     corpus, RAG, GraphRAG, Gemini
data/raw/                          PDF gốc
data/ocr/                          Markdown OCR theo trang
data/relations_reviewed.json       22 cạnh pháp lý đã rà
data/processed/                    đoạn, vector, đồ thị
evaluation/questions.jsonl         câu hỏi/đáp án chuẩn
evaluation/questions_multidoc_ocr.jsonl  8 câu kiểm tra quan hệ
evaluation/runs/                   kết quả truy xuất và Gemini
evaluation/BAO_CAO_DANH_GIA_GEMINI.md
report/report.md                   bối cảnh và phép đo truy xuất
docs/OCR_AND_LEGAL_GRAPH.md         quy trình OCR và đồ thị
docs/data_audit.md                 kiểm tra nguồn, lỗi OCR
docs/demo_script.md                kịch bản trình bày
```

[Báo cáo tổng thể](report/report.md) nêu thiết kế và phép đo truy xuất. [Tài liệu OCR/đồ thị](docs/OCR_AND_LEGAL_GRAPH.md) giải thích từng loại cạnh, chứng cứ và giới hạn. Đồ thị chỉ bao phủ các quan hệ đã xác minh trong nguồn thu thập; muốn kết luận quy định đang áp dụng cần đối chiếu thêm văn bản chính thức mới và ngày hiệu lực.

## Báo cáo nghiên cứu hoàn chỉnh

- [Báo cáo PDF 22 trang](report/BAO_CAO_NGHIEN_CUU_RAG_GRAPHRAG.pdf).
- [Nguồn XeLaTeX đóng gói](report/NGUON_XELATEX_RAG_GRAPHRAG.zip).
- [Hướng dẫn chỉnh sửa và biên dịch](report/bao_cao_nghien_cuu/README.md).

Báo cáo sử dụng số liệu thực nghiệm ngày 01/10/2026, tập trung thiết kế so sánh, kết quả và phân tích nguyên nhân. Điểm đáp án là chấm AI sơ bộ, chưa có người chấm độc lập; không kết luận GraphRAG có ưu thế trên mọi loại câu hỏi.
