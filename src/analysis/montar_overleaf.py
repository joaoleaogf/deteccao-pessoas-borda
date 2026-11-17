"""Artigo: monta o projeto LaTeX da equipe (classe da disciplina) e gera o zip para o Overleaf.

O que faz: parte do projeto Overleaf da equipe guardado localmente em data/projeto_equipe/ (classe
PioliEdgeComp.cls, estilo apalike2_ptBR.bst, config/ e figuras), que não vai para o git, e sobrepõe o
conteúdo deste repositório: docs/artigo/equipe/ (main.tex, configuracao.tex, seções, resumo,
referencias.bib e figuras da equipe), as macros e tabelas geradas pela análise (docs/artigo/numeros.tex
e tabelas/) e as figuras da análise em pgfplots (docs/artigo/figuras/). A classe não é alterada.
O resultado tem a mesma estrutura do projeto da equipe, para substituir os arquivos no Overleaf.

O que gera: build/artigo_equipe/ (projeto completo) e build/artigo_equipe.zip
Roda em qualquer Python 3. Uso: python src/analysis/montar_overleaf.py [--base DIR]
"""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
DA_BASE = ["PioliEdgeComp.cls", "apalike2_ptBR.bst", "config", "figs"]
IGNORAR = {".aux", ".log", ".bbl", ".blg", ".out", ".fls", ".fdb_latexmk", ".synctex.gz"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, default=RAIZ / "data" / "projeto_equipe",
                    help="projeto Overleaf da equipe (descompactado)")
    ap.add_argument("--saida", type=Path, default=RAIZ / "build" / "artigo_equipe")
    args = ap.parse_args()

    if not (args.base / "PioliEdgeComp.cls").exists():
        raise SystemExit(f"Projeto da equipe não encontrado em {args.base} (falta PioliEdgeComp.cls).")
    if args.saida.exists():
        shutil.rmtree(args.saida)
    args.saida.mkdir(parents=True)

    for item in DA_BASE:
        orig = args.base / item
        if orig.exists():
            (shutil.copytree if orig.is_dir() else shutil.copy2)(orig, args.saida / item)
    shutil.copytree(RAIZ / "docs" / "artigo" / "equipe", args.saida, dirs_exist_ok=True)
    shutil.copy2(RAIZ / "docs" / "artigo" / "numeros.tex", args.saida / "numeros.tex")
    shutil.copytree(RAIZ / "docs" / "artigo" / "tabelas", args.saida / "tabelas")
    # Figuras de dados e diagrama: PDF pré-compilado em figs/e6-*.pdf, fonte em figs/src/e6-*.tex
    (args.saida / "figs" / "src").mkdir(parents=True, exist_ok=True)
    for f in sorted((RAIZ / "docs" / "artigo" / "figuras").glob("*")):
        if f.suffix == ".pdf":
            shutil.copy2(f, args.saida / "figs" / f"e6-{f.name}")
        elif f.suffix == ".tex":
            shutil.copy2(f, args.saida / "figs" / "src" / ("e6_pre.tex" if f.name == "_pre.tex" else f"e6-{f.name}"))

    arq_zip = args.saida.with_suffix(".zip")
    with zipfile.ZipFile(arq_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(args.saida.rglob("*")):
            if f.is_file() and f.suffix not in IGNORAR and f.name != "main.pdf":
                z.write(f, f.relative_to(args.saida))
    print(f"Projeto em {args.saida.relative_to(RAIZ)}; zip em {arq_zip.relative_to(RAIZ)}")


if __name__ == "__main__":
    sys.exit(main())
