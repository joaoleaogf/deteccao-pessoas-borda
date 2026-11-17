"""E4, passo 1: escreve docs/ambiente.md a partir do que foi anotado durante a execução.

O que faz: junta os arquivos de results/ambiente/ (host, contêiner de preparação, compilador
Edge TPU e contêiner ARM64), gravados pelos outros passos, em um único documento. Nada é
digitado à mão: se um arquivo não existe, o documento diz que aquela parte não foi executada.

O que gera: docs/ambiente.md. Roda em qualquer Python 3 (só biblioteca padrão).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import RAIZ, RESULTS  # noqa: E402

SECOES = [
    ("host.txt", "Host", "Máquina que roda o Docker. Anotado por e4.sh ou e4.ps1."),
    ("prep.txt", "Contêiner de preparação (linux/amd64)", "Imagem borda-prep: exportação e quantização."),
    ("edgetpu.txt", "Edge TPU Compiler (linux/amd64)", "Imagem borda-edgetpu."),
    ("arm64.txt", "Contêiner de medição (linux/arm64, emulado por QEMU)", "Imagem borda-arm64."),
    ("oracle_a1.txt", "Máquina ARM64 nativa da coleta da E5 (Oracle A1)",
     "VM criada só para a coleta da borda (decisão D10) e apagada depois. Anotado pela coleta."),
]


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    partes = [
        "# Ambiente do experimento",
        "",
        "Gerado por `src/prepare/registrar_ambiente.py` a partir de `results/ambiente/`. Não edite à mão:",
        "rode a etapa de novo para atualizar.",
        "",
    ]
    for arquivo, titulo, descricao in SECOES:
        partes += [f"## {titulo}", "", descricao, ""]
        caminho = RESULTS / "ambiente" / arquivo
        if caminho.exists():
            partes += ["```text", caminho.read_text(encoding="utf-8", errors="replace").strip(), "```", ""]
        else:
            partes += ["_Não executado nesta máquina (arquivo ausente: " f"`results/ambiente/{arquivo}`)._", ""]
    (RAIZ / "docs").mkdir(exist_ok=True)
    (RAIZ / "docs" / "ambiente.md").write_text("\n".join(partes), encoding="utf-8")
    print("docs/ambiente.md atualizado")


if __name__ == "__main__":
    main()
