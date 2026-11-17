"""Artigo: monta o projeto LaTeX no template de artigo do IMC/UNIFEI e gera o zip para o Overleaf.

O que faz: copia os arquivos do template (classe imc.cls, estilo apalike2_ptBR.bst, config/ e main.tex)
de uma pasta local, sem alterá-los, exceto a sigla do curso na linha \\documentclass, como o próprio
template indica. Junta o conteúdo do trabalho (docs/artigo/overleaf/: configuracao.tex, resumo, seções,
referencias.bib), as macros e as tabelas geradas (docs/artigo/numeros.tex e tabelas/) e as figuras da
análise (figures/e6_*.pdf). O template não vai para o git (não tem licença de redistribuição):
baixe-o do link da disciplina e deixe em data/template_artigo_imc/.

O que gera: build/artigo_overleaf/ (projeto completo) e build/artigo_overleaf.zip
(no Overleaf: New Project > Upload Project).
Roda em qualquer Python 3. Uso: python src/analysis/montar_overleaf.py [--template DIR] [--curso sin|cco]
"""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
DO_TEMPLATE = ["imc.cls", "apalike2_ptBR.bst", "main.tex", "config"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", type=Path, default=RAIZ / "data" / "template_artigo_imc")
    ap.add_argument("--curso", choices=["sin", "cco"], default="sin")
    ap.add_argument("--saida", type=Path, default=RAIZ / "build" / "artigo_overleaf")
    args = ap.parse_args()

    if not (args.template / "imc.cls").exists():
        raise SystemExit(f"Template não encontrado em {args.template}. Baixe o template de artigo da disciplina.")
    if args.saida.exists():
        shutil.rmtree(args.saida)
    args.saida.mkdir(parents=True)

    for item in DO_TEMPLATE:
        orig = args.template / item
        (shutil.copytree if orig.is_dir() else shutil.copy2)(orig, args.saida / item)
    main_tex = args.saida / "main.tex"
    texto = main_tex.read_text(encoding="utf-8")
    if r"\documentclass[cco]{imc}" not in texto:
        raise SystemExit("main.tex do template mudou: confira a linha \\documentclass.")
    main_tex.write_text(texto.replace(r"\documentclass[cco]{imc}", rf"\documentclass[{args.curso}]{{imc}}"),
                        encoding="utf-8")

    conteudo = RAIZ / "docs" / "artigo" / "overleaf"
    shutil.copytree(conteudo, args.saida, dirs_exist_ok=True)
    shutil.copy2(RAIZ / "docs" / "artigo" / "numeros.tex", args.saida / "numeros.tex")
    shutil.copytree(RAIZ / "docs" / "artigo" / "tabelas", args.saida / "tabelas")
    (args.saida / "figs").mkdir(exist_ok=True)
    for fig in sorted((RAIZ / "figures").glob("e6_*.pdf")):
        shutil.copy2(fig, args.saida / "figs" / fig.name)

    arq_zip = args.saida.with_suffix(".zip")
    with zipfile.ZipFile(arq_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(args.saida.rglob("*")):
            if f.is_file() and f.suffix not in {".aux", ".log", ".bbl", ".blg", ".out", ".fls", ".fdb_latexmk"} \
                    and f.name != "main.pdf":
                z.write(f, f.relative_to(args.saida))
    print(f"Projeto em {args.saida.relative_to(RAIZ)}; zip em {arq_zip.relative_to(RAIZ)}")


if __name__ == "__main__":
    sys.exit(main())
