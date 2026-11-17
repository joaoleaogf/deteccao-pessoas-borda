#!/usr/bin/env bash
# E6, passo 4: compila cada figura do artigo (pgfplots/TikZ) em um PDF vetorial independente.
#
# O que faz: para cada docs/artigo/figuras/<nome>.tex (as figuras de dados geradas por artigo_tex.py e o
# diagrama medicao.tex), monta um documento standalone com docs/artigo/figuras/_pre.tex (mesmas fontes e
# larguras da classe da disciplina) e compila com pdflatex. Assim o artigo inclui PDFs prontos e não
# redesenha as figuras a cada compilação (o que estourava o tempo do plano gratuito do Overleaf).
#
# O que gera: docs/artigo/figuras/<nome>.pdf
# Roda no contêiner texlive/texlive. Uso: bash src/analysis/compilar_figuras.sh
set -euo pipefail
[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && { sed -n '2,10p' "$0"; exit 0; }
cd "$(dirname "$0")/../../docs/artigo/figuras"
tmp="$(mktemp -d)"
for fonte in *.tex; do
  [[ "$fonte" == _pre.tex ]] && continue
  nome="${fonte%.tex}"
  # O standalone redefine \columnwidth no \begin{document}: as larguras da classe são fixadas depois dele.
  { cat _pre.tex
    printf '\\begin{document}\n\\setlength{\\columnwidth}{249.57481pt}\\setlength{\\textwidth}{512.14963pt}\\setlength{\\linewidth}{\\columnwidth}\n\\input{%s}\n\\end{document}\n' "$PWD/$fonte"
  } > "$tmp/$nome.tex"
  (cd "$tmp" && pdflatex -interaction=nonstopmode -halt-on-error "$nome.tex" > "$nome.saida" 2>&1) \
    || { echo "FALHOU: $nome"; grep -m5 '^!' "$tmp/$nome.log" || true; exit 1; }
  cp "$tmp/$nome.pdf" "$nome.pdf"
  echo "OK $nome.pdf"
done
rm -rf "$tmp"
