#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
task_root="$(cd ../.. && pwd)"
task_tex="$task_root/.local-tools/tex/.TinyTeX/bin/x86_64-linux/xelatex"
if command -v xelatex >/dev/null 2>&1; then
  task_tex="$(command -v xelatex)"
fi
if [[ ! -x "$task_tex" ]]; then
  echo "Cần cài XeLaTeX (TeX Live/TinyTeX) trước khi biên dịch." >&2
  exit 1
fi
mkdir -p build
for task_pass in 1 2 3; do
  "$task_tex" -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build main.tex > "build/pass-$task_pass.log" 2>&1
done
cp build/main.pdf ../BAO_CAO_NGHIEN_CUU_RAG_GRAPHRAG.pdf
echo "PDF: $task_root/report/BAO_CAO_NGHIEN_CUU_RAG_GRAPHRAG.pdf"
