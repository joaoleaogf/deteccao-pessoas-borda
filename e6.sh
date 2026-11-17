#!/usr/bin/env bash
# Etapa E6 (análise) com um comando (Linux, macOS ou WSL). No Windows sem WSL, use e6.ps1.
#
# O que faz, em ordem (contêiner borda-prep):
#   1. deriva os cenários de 5, 15 e 30 FPS, calcula mAP@50 e F1 e escreve results/summary.csv
#   2. faz os testes pareados, as figuras (figures/) e results/RESUMO.md
# Determinístico: rodar duas vezes dá os mesmos arquivos.
#
# Uso: ./e6.sh
set -euo pipefail
cd "$(dirname "$0")"
[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && { sed -n '2,9p' "$0"; exit 0; }
M=(-v "$PWD":/repo -w /repo)
PY=/opt/venv-export/bin/python
echo "== [1/2] Cenários derivados, qualidade e results/summary.csv"
docker run --rm --platform linux/amd64 "${M[@]}" borda-prep $PY src/analysis/derivar_cenarios.py
echo "== [2/2] Testes, figuras e results/RESUMO.md"
docker run --rm --platform linux/amd64 "${M[@]}" borda-prep $PY src/analysis/estatistica.py
echo "E6 concluída. Veja results/RESUMO.md, results/stats/ e figures/."
