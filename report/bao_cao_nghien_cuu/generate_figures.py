"""Tạo hình và bảng từ artifact đã lưu; không gọi model hoặc thay đổi điểm."""
from pathlib import Path
import csv
import json
import hashlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / "evaluation/runs/research_20261001"
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 11,
                     "pdf.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})
METHODS = ["rag", "hybrid", "graph_rag"]
LABELS = ["RAG vector", "Hybrid", "GraphRAG"]
COLORS = ["#276a9e", "#8a8a8a", "#d07b32"]
rows = list(csv.DictReader((RUN / "retrieval_summary.csv").open()))
print("Methods:", sorted({r["method"] for r in rows}))
# Runner gọi đối chứng là hybrid; lấy đúng tên trong artifact.
hybrid = next(m for m in {r["method"] for r in rows} if m not in {"rag", "graph_rag"})
METHODS[1] = hybrid
def row(suite, method, category="all"):
    return next(r for r in rows if r["suite"] == suite and r["method"] == method and r["category"] == category)

fig, ax = plt.subplots(figsize=(7.1, 3.0))
x = np.arange(3)
for j, (m, label, color) in enumerate(zip(METHODS, LABELS, COLORS)):
    vals = [float(row(s, m)["mean_recall_at_5"]) for s in ["original_30", "relations_8", "scoped_20"]]
    bars = ax.bar(x + (j-1)*.24, vals, .23, label=label, color=color)
    ax.bar_label(bars, fmt="%.2f", fontsize=9, padding=2)
ax.set_xticks(x, ["Bộ 30 (25 có gold)", "Bộ quan hệ (8)", "Bộ 20 (16 có gold)"])
ax.set_ylim(0, 1.17); ax.set_ylabel("Recall@5 trung bình")
ax.legend(ncol=3, loc="lower left", bbox_to_anchor=(0, 1.01), frameon=False)
fig.tight_layout(); fig.savefig(HERE / "figures/recall_suites.pdf"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7.1, 3.0))
x = np.arange(4)
for j, (m, label, color) in enumerate(zip(METHODS, LABELS, COLORS)):
    vals = [float(row("scoped_20", m, c)["mean_recall_at_5"]) for c in ["mot_dieu", "nhieu_dieu", "phien_ban", "quan_he"]]
    bars = ax.bar(x + (j-1)*.24, vals, .23, label=label, color=color)
    ax.bar_label(bars, fmt="%.2f", fontsize=9, padding=2)
ax.set_xticks(x, ["Một điều", "Nhiều điều", "Phiên bản", "Quan hệ"])
ax.set_ylim(0, 1.17); ax.set_ylabel("Recall@5 trung bình")
ax.legend(ncol=3, loc="lower left", bbox_to_anchor=(0, 1.01), frameon=False)
fig.tight_layout(); fig.savefig(HERE / "figures/recall_groups.pdf"); plt.close(fig)

scores = json.loads((RUN / "answer_scores.json").read_text())["rows"]
fig, ax = plt.subplots(figsize=(7.1, 2.65))
x = np.arange(3)
for j, (m, label, color) in enumerate(zip(["rag", "graph_rag"], ["RAG vector", "GraphRAG"], [COLORS[0], COLORS[2]])):
    vals = [sum(r[k] for r in scores if r["method"] == m and r[k] is not None)/16 for k in ["correct", "complete", "citation_support"]]
    bars = ax.bar(x + (j-.5)*.3, vals, .29, label=label, color=color)
    ax.bar_label(bars, labels=[f"{int(v*16)}/16" for v in vals], padding=2)
ax.set_xticks(x, ["Đúng ý chính", "Đủ ý", "Nguồn hỗ trợ"])
ax.set_ylim(0, 1.05); ax.set_ylabel("Tỷ lệ đạt (chấm AI sơ bộ)")
ax.legend(ncol=2, loc="upper left", frameon=False)
fig.tight_layout(); fig.savefig(HERE / "figures/answer_quality.pdf"); plt.close(fig)

generation = json.loads((RUN / "generation_revalidated.json").read_text())["rows"]
fig, ax = plt.subplots(figsize=(7.1, 2.6))
times = [[r["response"]["latency_ms"]/1000 for r in generation if r["method"] == m] for m in ["rag", "graph_rag"]]
bp = ax.boxplot(times, tick_labels=["RAG vector", "GraphRAG"], widths=.35, patch_artist=True)
for p, c in zip(bp["boxes"], [COLORS[0], COLORS[2]]): p.set_facecolor(c); p.set_alpha(.35)
for j, vals in enumerate(times):
    ax.scatter(np.full(len(vals),j+1) + np.linspace(-.12,.12,len(vals)), vals, s=14, alpha=.75, color=[COLORS[0],COLORS[2]][j])
ax.set_ylabel("Độ trễ pipeline (giây)")
fig.tight_layout(); fig.savefig(HERE / "figures/latency.pdf"); plt.close(fig)

def esc(text):
    return str(text).replace("\\", "\\textbackslash{}").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("{", "\\{").replace("}", "\\}")
questions = [json.loads(line) for line in (ROOT / "evaluation/questions_research_20261001.jsonl").read_text().splitlines()]
table = [r"\begin{tabularx}{\textwidth}{l X cc}", r"\toprule ID & Nội dung rút gọn & RAG & Graph \\", r"\midrule"]
short = {"S02":"Tuần rút lớp học phần", "S04":"Tỷ lệ đào tạo trực tuyến", "S06":"Thi bổ sung do lý do chính đáng", "S07":"Khoảng điểm A và F", "M01":"Điều kiện tốt nghiệp và thời hạn cấp bằng", "M02":"Khối lượng tín chỉ và rút học phần", "M05":"Học chương trình thứ hai, công nhận tín chỉ", "M08":"Điểm thành phần và đánh giá trực tuyến", "V01":"Thời gian tối đa của chương trình 4 năm", "V02":"Văn bản bị quy chế hợp nhất thay thế", "V04":"Thời gian học tối đa trong TT08", "V05":"Tuần rút theo quy chế hợp nhất", "R01":"Hai quyết định bị QĐ721 thay thế", "R02":"Căn cứ TT08 và QĐ239 của quy định khóa luận", "R03":"Quan hệ QĐ663, QĐ787 và bản hợp nhất", "R06":"Hai quyết định bị TT08 thay thế", "U01":"Học phí năm 2026–2027", "U02":"Lịch thi cá nhân", "U03":"Tình trạng tốt nghiệp cá nhân", "U05":"Đào tạo sau đại học AI hiện tại"}
for q in questions:
    sid=q["question_id"]
    result=[]
    for m in ["rag","graph_rag"]:
        s=next(r for r in scores if r["question_id"]==sid and r["method"]==m)
        result.append(str(s["correct"]) if s["correct"] is not None else "TC")
    table.append(f"{sid} & {short[sid]} & {result[0]} & {result[1]} " + r"\\")
table += [r"\bottomrule", r"\end{tabularx}"]
(HERE / "question_table.tex").write_text("\n".join(table))
inputs=[RUN/"retrieval_summary.csv", RUN/"answer_scores.json", RUN/"generation_revalidated.json", ROOT/"evaluation/questions_research_20261001.jsonl"]
(HERE / "artifact_hashes.json").write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}, indent=2))
