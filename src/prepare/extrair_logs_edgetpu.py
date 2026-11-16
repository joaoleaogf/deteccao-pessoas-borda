"""E4, passo 5: extrai dos relatórios do Edge TPU Compiler os números para o artigo.

O que faz: lê results/edgetpu_logs/<modelo>.log e <modelo>.saida.txt e procura, por expressão
regular, as linhas do relatório: operadores que iriam para a TPU, operadores que ficam na
CPU, memória no chip e fora do chip, subgrafos e a tabela de operadores. Campo que não
aparece no relatório fica vazio no CSV; nada é estimado ou preenchido à mão.

O que gera:
  results/edgetpu_compile.csv      uma linha por modelo INT8
  results/edgetpu_operadores.csv   uma linha por (modelo, operador, situação)

Roda em qualquer Python 3 (só biblioteca padrão).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import RESULTS, partes_do_nome  # noqa: E402

CAMPOS = {
    "versao_compilador": r"Edge TPU Compiler version (\S+)",
    "tempo_compilacao_ms": r"Model compiled successfully in (\d+) ms",
    "tamanho_entrada": r"Input size: (.+)",
    "tamanho_saida": r"Output size: (.+)",
    "memoria_no_chip_usada": r"On-chip memory used for caching model parameters: (.+)",
    "memoria_no_chip_restante": r"On-chip memory remaining for caching model parameters: (.+)",
    "memoria_fora_do_chip": r"Off-chip memory used for streaming uncached model parameters: (.+)",
    "subgrafos_edgetpu": r"Number of Edge TPU subgraphs: (\d+)",
    "operacoes_total": r"Total number of operations: (\d+)",
    "operacoes_na_tpu": r"Number of operations that will run on Edge TPU: (\d+)",
    "operacoes_na_cpu": r"Number of operations that will run on CPU: (\d+)",
}
UNIDADES = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}
# Linha da tabela "Operator  Count  Status", ex.: "CONV_2D   14   Mapped to Edge TPU"
LINHA_OPERADOR = re.compile(r"^([A-Z][A-Z0-9_]+)\s+(\d+)\s+(\S.*\S)\s*$", re.MULTILINE)


def em_bytes(texto: str) -> str:
    """'6.52MiB' -> '6836715'. Devolve vazio se o texto não estiver no formato esperado."""
    m = re.fullmatch(r"([\d.]+)\s*(B|KiB|MiB|GiB)", texto.strip())
    return str(round(float(m.group(1)) * UNIDADES[m.group(2)])) if m else ""


def extrair(texto: str) -> tuple[dict, list[tuple[str, int, str]]]:
    linha = {}
    for campo, padrao in CAMPOS.items():
        m = re.search(padrao, texto)
        linha[campo] = m.group(1).strip() if m else ""
    for campo in ("memoria_no_chip_usada", "memoria_no_chip_restante", "memoria_fora_do_chip"):
        linha[campo + "_bytes"] = em_bytes(linha[campo])
    operadores = [(o, int(n), s) for o, n, s in LINHA_OPERADOR.findall(texto)]
    return linha, operadores


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pasta", type=Path, default=RESULTS / "edgetpu_logs", help="pasta com os relatórios")
    args = ap.parse_args()

    saidas = sorted(args.pasta.glob("*.saida.txt"))
    if not saidas:
        raise SystemExit(f"Nenhum relatório em {args.pasta}. Rode src/prepare/compilar_edgetpu.sh antes.")
    linhas, ops = [], []
    for saida in saidas:
        nome = saida.name.removesuffix(".saida.txt")
        modelo, precisao, res = partes_do_nome(Path(nome + ".tflite"))
        texto = saida.read_text(encoding="utf-8", errors="replace")
        log = args.pasta / f"{nome}.log"
        if log.exists():
            texto += "\n" + log.read_text(encoding="utf-8", errors="replace")
        campos, operadores = extrair(texto)
        # Se o relatório não trouxer as linhas de total, soma a tabela de operadores (e anota a origem).
        campos["contagem_origem"] = "linhas_do_relatorio" if campos["operacoes_na_tpu"] else ""
        unicos = set(operadores)
        if not campos["operacoes_na_tpu"] and unicos:
            na_tpu = sum(n for _, n, s in unicos if s == "Mapped to Edge TPU")
            campos["operacoes_na_tpu"] = str(na_tpu)
            campos["operacoes_na_cpu"] = str(sum(n for _, n, _ in unicos) - na_tpu)
            campos["contagem_origem"] = "soma_da_tabela_de_operadores"
        linhas.append(
            {
                "arquivo": nome + ".tflite",
                "modelo": modelo,
                "precisao": precisao,
                "resolucao": res,
                "compilou": bool(campos["tempo_compilacao_ms"]),
                **campos,
            }
        )
        vistos = set()
        for operador, n, situacao in operadores:  # a tabela aparece na saída e no .log: sem duplicar
            if (operador, n, situacao) not in vistos:
                vistos.add((operador, n, situacao))
                ops.append({"arquivo": nome + ".tflite", "operador": operador, "quantidade": n, "situacao": situacao})

    for destino, dados in (("edgetpu_compile.csv", linhas), ("edgetpu_operadores.csv", ops)):
        if dados:
            with open(RESULTS / destino, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(dados[0]))
                w.writeheader()
                w.writerows(dados)
            print(f"{len(dados)} linhas -> results/{destino}")
    falhas = [linha["arquivo"] for linha in linhas if not linha["compilou"]]
    if falhas:
        print("ATENÇÃO: não compilaram (veja results/edgetpu_logs/):", ", ".join(falhas))


if __name__ == "__main__":
    main()
