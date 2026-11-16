"""E4, critério de aceite: confere, por script, o tipo dos tensores de cada modelo.

O que faz: abre cada models/*.tflite com o LiteRT e registra formato e tipo da entrada e das
saídas, quantos tensores existem de cada tipo, o tamanho e o sha256 do arquivo. Um modelo
INT8 é "inteiro total" quando não tem nenhum tensor float32 (entrada, saída, pesos e
ativações em inteiros).

O que gera: results/modelos.csv, uma linha por modelo.
Com --estrito, termina com erro se algum INT8 não for inteiro total.
Roda no contêiner de preparação, ambiente /opt/venv-export.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import MODELS, RESULTS, partes_do_nome, sha256  # noqa: E402

INTEIROS = {"int8", "uint8", "int16", "int32", "int64"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--estrito", action="store_true", help="erro se algum INT8 não for inteiro total")
    args = ap.parse_args()

    from ai_edge_litert.interpreter import Interpreter

    linhas, problemas = [], []
    for arq in sorted(MODELS.glob("*.tflite")):
        modelo, precisao, res = partes_do_nome(arq)
        it = Interpreter(model_path=str(arq))
        it.allocate_tensors()
        ent = it.get_input_details()[0]
        saidas = it.get_output_details()
        tipos = Counter(t["dtype"].__name__ for t in it.get_tensor_details())
        ent_int = ent["dtype"].__name__ in INTEIROS
        sai_int = all(s["dtype"].__name__ in INTEIROS for s in saidas)
        total = tipos.get("float32", 0) == 0
        linhas.append(
            {
                "arquivo": arq.name,
                "modelo": modelo,
                "precisao": precisao,
                "resolucao": res,
                "tamanho_bytes": arq.stat().st_size,
                "sha256": sha256(arq),
                "entrada_formato": "x".join(map(str, ent["shape"])),
                "entrada_tipo": ent["dtype"].__name__,
                "saidas_formato": ";".join("x".join(map(str, s["shape"])) for s in saidas),
                "saidas_tipo": ";".join(s["dtype"].__name__ for s in saidas),
                "tensores_float32": tipos.get("float32", 0),
                "tensores_int8_uint8": tipos.get("int8", 0) + tipos.get("uint8", 0),
                "tensores_total": sum(tipos.values()),
                "entrada_inteira": ent_int,
                "saida_inteira": sai_int,
                "inteiro_total": total,
            }
        )
        if precisao == "int8" and not total:
            problemas.append(arq.name)
        if precisao == "fp32" and tipos.get("int8", 0) + tipos.get("uint8", 0) > 0:
            raise SystemExit(f"{arq.name} deveria ser FP32, mas tem tensores int8/uint8.")

    if not linhas:
        raise SystemExit("Nenhum modelo em models/. Rode os scripts de src/prepare/ antes.")
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "modelos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} modelos conferidos -> results/modelos.csv")
    if problemas:
        print("ATENÇÃO: modelos INT8 que NÃO são inteiro total (têm tensores float32):")
        for p in problemas:
            print(f"  - {p}")
        print("Veja a decisão D2 em docs/decisoes.md.")
        if args.estrito:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
