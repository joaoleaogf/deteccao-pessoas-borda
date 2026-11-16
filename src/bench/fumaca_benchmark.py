"""E4, passo 7: teste de fumaça com o benchmark_model, uma vez por modelo.

O que faz: roda o binário nativo benchmark_model (ferramenta oficial do TensorFlow Lite/LiteRT)
em cada models/*.tflite com poucas execuções, só para confirmar que a ferramenta funciona
com todos os modelos dentro do contêiner ARM64. Flags usadas:
  --graph        arquivo do modelo        --num_threads  threads de CPU
  --warmup_runs  execuções de aquecimento --num_runs     execuções contadas
Os tempos são de ambiente EMULADO, com amostra mínima: servem de teste, não de resultado.

O que gera:
  results/benchmark_fumaca/<modelo>.txt   saída completa do benchmark_model
  results/benchmark_fumaca.csv            uma linha por modelo, com os números lidos da saída

Termina com erro se o benchmark falhar em algum modelo. Roda no contêiner borda-arm64.
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import MODELS, RESULTS, partes_do_nome  # noqa: E402

# Linha-resumo: "Inference timings in us: Init: 1, First inference: 2, Warmup (avg): 3, Inference (avg): 4"
TEMPOS = re.compile(
    r"Init: ([\d.e+]+), First inference: ([\d.e+]+), Warmup \(avg\): ([\d.e+]+), Inference \(avg\): ([\d.e+]+)"
)
MEMORIA = re.compile(r"Memory footprint delta.*?init=([\d.]+)\s+overall=([\d.]+)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--num-threads", type=int, default=4)
    ap.add_argument("--warmup-runs", type=int, default=1)
    ap.add_argument("--num-runs", type=int, default=5)
    args = ap.parse_args()

    pasta = RESULTS / "benchmark_fumaca"
    pasta.mkdir(parents=True, exist_ok=True)
    linhas, falhas = [], []
    for arq in sorted(MODELS.glob("*.tflite")):
        modelo, precisao, res = partes_do_nome(arq)
        cmd = ["benchmark_model", f"--graph={arq}", f"--num_threads={args.num_threads}",
               f"--warmup_runs={args.warmup_runs}", f"--num_runs={args.num_runs}"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        saida = r.stdout + r.stderr
        (pasta / f"{arq.stem}.txt").write_text("$ " + " ".join(cmd) + "\n" + saida, encoding="utf-8")
        t, m = TEMPOS.search(saida), MEMORIA.search(saida)
        ok = r.returncode == 0 and t is not None
        linhas.append(
            {
                "arquivo": arq.name, "modelo": modelo, "precisao": precisao, "resolucao": res,
                "natureza": "teste_de_fumaca_emulado", "ok": ok,
                "num_threads": args.num_threads, "warmup_runs": args.warmup_runs, "num_runs": args.num_runs,
                "init_us": t.group(1) if t else "",
                "primeira_inferencia_us": t.group(2) if t else "",
                "aquecimento_media_us": t.group(3) if t else "",
                "inferencia_media_us": t.group(4) if t else "",
                "memoria_delta_init_mb": m.group(1) if m else "",
                "memoria_delta_total_mb": m.group(2) if m else "",
            }
        )
        print(("OK   " if ok else "FALHA"), arq.name)
        if not ok:
            falhas.append(arq.name)

    if not linhas:
        raise SystemExit("Nenhum modelo em models/.")
    with open(RESULTS / "benchmark_fumaca.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} modelos -> results/benchmark_fumaca.csv")
    if falhas:
        raise SystemExit(f"benchmark_model falhou em: {', '.join(falhas)} (veja results/benchmark_fumaca/)")


if __name__ == "__main__":
    main()
