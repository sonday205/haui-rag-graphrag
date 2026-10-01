"""Tải các nguồn HaUI công khai, giữ file gốc và ghi manifest kể cả nguồn bị loại."""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import fitz
import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ("QC2023", "Quy chế đào tạo trình độ đại học, bản hợp nhất QĐ 744/2021 và 666/2023", "https://sict.haui.edu.vn/vn/html/quy-che", "https://sict.haui.edu.vn/media/29/uffile-upload-no-title29811.pdf", "quyche_hop_nhat_2023.pdf", "744/QĐ-ĐHCN; 666/QĐ-ĐHCN", "2021-08-19; 2023-06-01", "đại học", "Bản hợp nhất có nêu sửa đổi QĐ 744/2021 bởi QĐ 666/2023", "chọn: văn bản đọc được"),
    ("QD663_2019", "Sửa đổi quy chế đào tạo tín chỉ QĐ 787/2018", "https://dttc.haui.edu.vn/vn/quy-che-dao-tao/quyet-dinh-sua-doi-bo-sung-mot-so-noi-dung-cua-quy-che-dao-tao-dai-hoc-cao-dang-theo-hoc-che-tin-chi-ban-hanh-tai-quyet-dinh-so-787-qd-dhcn-ngay-09-08-2018-cua-hieu-truong-truong-dhcn-hn/49838", "https://dttc.haui.edu.vn/media/2/uftai-ve-tai-day2712.pdf", "sua_doi_2019.pdf", "663/QĐ-ĐHCN", "2019-07-12", "đại học và cao đẳng", "sửa QĐ 787/2018", "loại khỏi chỉ mục: PDF ảnh quét"),
    ("DA2019", "Quy định đồ án, khóa luận tốt nghiệp", "https://dttc.haui.edu.vn/vn/quy-che-dao-tao/quy-dinh-thuc-hien-do-an-khoa-luan-tot-nghiep-doi-voi-sinh-vien-trinh-do-dai-hoc/49826", "https://dttc.haui.edu.vn/media/2/uftai-ve-tai-day2656.pdf", "do_an_2019.pdf", "", "2019-02-14", "đại học", "", "loại khỏi chỉ mục: PDF ảnh quét"),
    ("TT08_2021", "Thông tư 08/2021/TT-BGDĐT đăng trên HaUI", "https://www.haui.edu.vn/vn/vbpl/detail/102", "https://www.haui.edu.vn/media/2/ufi2516.pdf", "thong_tu_08_2021.pdf", "08/2021/TT-BGDĐT", "2021-03-18", "đại học", "", "loại khỏi chỉ mục: PDF ảnh quét"),
    ("KL_SICT", "Quy định đồ án, khóa luận tốt nghiệp đăng trên SICT", "https://sict.haui.edu.vn/vn/html/quy-che", "https://sict.haui.edu.vn/media/29/uffile-upload-no-title29868.pdf", "khoa_luan.pdf", "1077/QĐ-ĐHCN", "2023-08-30", "đại học", "", "loại khỏi chỉ mục: PDF ảnh quét"),
    ("NN_SICT", "Quy định chuẩn đầu ra ngoại ngữ", "https://sict.haui.edu.vn/vn/html/quy-che", "https://sict.haui.edu.vn/media/29/uffile-upload-no-title29675.pdf", "ngoai_ngu.pdf", "242/QĐ-ĐHCN", "2022", "đại học", "", "loại khỏi chỉ mục: PDF ảnh quét"),
    ("HP_SICT", "Danh sách học phần thay thế 2022", "https://sict.haui.edu.vn/vn/html/quy-che", "https://sict.haui.edu.vn/media/29/uffile-upload-no-title29709.pdf", "hoc_phan_thay_the.pdf", "427/QĐ-ĐHCN", "2022-04-27", "đại học", "", "loại khỏi chỉ mục: PDF ảnh quét"),
    ("QD721_2024", "Quy định đánh giá kết quả học tập QĐ 721/2024", "https://tac.haui.edu.vn/vn/quy-dinh", "https://cps.haui.edu.vn/media/quyet-dinh-721-ngay-03-06-2024-ve-viec-ban-hanh-quy-dinh-to-chuc-dgkqht-cua-nguoi-hoc-truong-dhcn-hn%20%285%29.pdf", "danh_gia_2024.pdf", "721/QĐ-ĐHCN", "2024-06-03", "người học HaUI", "thay QĐ 254/2023 và QĐ 1432/2023 theo PDF", "loại khỏi chỉ mục: PDF ảnh quét"),
    ("QD847_2017", "Sửa đổi quy chế đào tạo QĐ 1015/2015", "https://dttc.haui.edu.vn/vn/quy-che-dao-tao", "https://dttc.haui.edu.vn/media/2/uftai-ve-tai-day2542.pdf", "sua_doi_2017.pdf", "847/QĐ-ĐHCN", "2017-08-04", "đại học và cao đẳng", "sửa QĐ 1015/2015", "loại khỏi chỉ mục: PDF ảnh quét"),
    ("QD254_2023", "Quy định đánh giá kết quả học tập QĐ 254/2023", "https://tac.haui.edu.vn/vn/quy-dinh/quy-dinh-to-chuc-hoat-dong-danh-gia-ket-qua-hoc-tap-cua-sinh-vien-truong-dai-hoc-cong-nghiep-ha-noi/63257", "https://fee.haui.edu.vn/media/30/uffile-upload-no-title30983.pdf", "danh_gia_2023.pdf", "254/QĐ-ĐHCN", "2023-03-06", "sinh viên HaUI", "bị QĐ 721/2024 thay theo PDF", "loại: URL trả 404"),
    ("QD1432_2023", "Sửa đổi quy định đánh giá kết quả học tập", "https://tac.haui.edu.vn/vn/quy-dinh/quyet-dinh-so-1432-ve-viec-sua-doi-bo-sung-mot-so-dieu-cua-quy-dinh-ve-to-chuc-hoat-dong-danh-gia-ket-qua-hoc-tap-cua-sinh-vien-truong-dai-hoc-cong-nghiep-ha-noi/63266", "https://fee.haui.edu.vn/media/31/uffile-upload-no-title31095.pdf", "danh_gia_sua_2023.pdf", "1432/QĐ-ĐHCN", "2023-11-06", "sinh viên HaUI", "bị QĐ 721/2024 thay theo PDF", "loại: URL trả 404"),
]


def main():
    now = datetime.now(timezone.utc).isoformat()
    target = ROOT / "data/raw"
    target.mkdir(parents=True, exist_ok=True)
    records = []
    for document_id, title, page_url, file_url, filename, number, issued, audience, relation, selection in SOURCES:
        file = target / filename
        error = ""
        if not file.exists() and "404" not in selection:
            try:
                response = requests.get(file_url, timeout=30)
                response.raise_for_status()
                if not response.content.startswith(b"%PDF"):
                    raise ValueError("Phản hồi không phải PDF")
                file.write_bytes(response.content)
            except Exception as exc:
                error = f"{type(exc).__name__}: {str(exc)[:120]}"
        sha = hashlib.sha256(file.read_bytes()).hexdigest() if file.exists() else ""
        pages = len(fitz.open(file)) if file.exists() else 0
        text_chars = sum(len(p.get_text()) for p in fitz.open(file)) if file.exists() else 0
        ocr_file = ROOT / "data/ocr" / (Path(filename).stem + ".md")
        ocr_chars = len(ocr_file.read_text(encoding="utf-8")) if ocr_file.exists() else 0
        ocr_sha = hashlib.sha256(ocr_file.read_bytes()).hexdigest() if ocr_file.exists() else ""
        if file.exists() and text_chars < 500:
            selection = ("chọn: OCR do người dùng cung cấp, đã khớp số trang; chưa hiệu đính toàn bộ"
                         if ocr_chars else "loại khỏi chỉ mục: PDF ảnh quét, chưa OCR/đối chiếu")
        accessed = datetime.fromtimestamp(file.stat().st_mtime, timezone.utc).isoformat() if file.exists() else now
        records.append({"id": document_id, "title": title, "page_url": page_url, "file_url": file_url,
            "domain": urlparse(file_url).hostname, "file_type": "PDF", "document_number": number,
            "issued_date": issued, "accessed_at_utc": accessed, "audience": audience,
            "amendment_relation": relation, "validity_status": "unknown", "validity_basis": "Chưa đối chiếu đầy đủ hiệu lực; QĐ 721 và bản hợp nhất chỉ có phát biểu trong chính PDF",
            "selection_reason": selection, "download_error": error or ("HTTP 404 đã kiểm tra 2026-09-28" if "404" in selection else ""),
            "sha256": sha, "local_path": str(file.relative_to(ROOT)) if file.exists() else "", "pages": pages,
            "extracted_chars": text_chars, "ocr_chars": ocr_chars, "ocr_sha256": ocr_sha})
    with (ROOT / "data/source_manifest.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    print(f"manifest: {len(records)} nguồn, {sum(bool(r['sha256']) for r in records)} PDF đã tải, "
          f"{sum(bool(r['sha256']) and (r['extracted_chars']>=500 or r['ocr_chars']>0) for r in records)} văn bản vào corpus")


if __name__ == "__main__":
    main()
