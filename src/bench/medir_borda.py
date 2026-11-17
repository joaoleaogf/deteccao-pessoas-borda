"""E5, borda: mede UMA combinação modelo x precisão x resolução da fonte no contêiner ARM64.

O que faz: carrega os 350 quadros do conjunto de teste já redimensionados para a resolução da
fonte (fora da medição: é o quadro que a câmera entregaria) e processa um quadro depois do outro,
sem ritmo de câmera. Para cada quadro mede, com time.perf_counter:
  t_pre_ms    quadro da fonte -> tensor de entrada (redimensionar se preciso, normalizar, quantizar)
  t_infer_ms  Interpreter.invoke() do LiteRT (--threads, padrão 4)
  t_post_ms   saída bruta -> detecções de pessoa (decodificação + NMS)
  t_e2e_ms    soma dos três
e também o uso de CPU do processo (tempo de CPU / tempo de parede, em %, pode passar de 100 com
várias threads; lido com resource.getrusage, porque o psutil devolve zero sob o QEMU) e a memória residente (RSS). Os 50 primeiros quadros são marcados como aquecimento.
Os cenários de 5, 15 e 30 FPS NÃO são medidos aqui: são derivados depois (src/analysis).
O ambiente (emulado pelo QEMU ou ARM64 nativo) fica no manifesto; nenhum dos dois é um Raspberry Pi.

O que gera, em results/e5/borda/<modelo>_<precisao>_<res>/:
  quadros.csv       uma linha por quadro
  deteccoes.json    detecções de pessoa por image_id (normalizadas 0..1)
  manifesto.json    data, versões, perfil, sha256 do modelo, parâmetros
  COMPLETO          marcador gravado por último (combinação com ele não roda de novo)

Roda no contêiner borda-arm64. Uso:
  python src/bench/medir_borda.py --modelo yolov8n --precisao int8 --res 320 [--perfil rpi4b]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import platform
import resource
import sys
import time
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import DATA, MODELS, RAIZ, RESULTS, ler_yaml, sha256  # noqa: E402
from deteccao import (LIMIAR_IOU_NMS, LIMIAR_PONTUACAO, MAX_DETECCOES, Detector,  # noqa: E402
                      quadro_da_fonte, resolucao_entrada)


def descrever_cpu() -> str:
    """Modelo de CPU como o sistema informa (lscpu; em ARM o 'Model name' vem do código da peça)."""
    import subprocess

    try:
        saida = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=10).stdout
        campos = [l.strip() for l in saida.splitlines() if l.split(":")[0].strip() in
                  ("Architecture", "Vendor ID", "Model name", "CPU(s)", "Thread(s) per core", "BogoMIPS")]
        return "; ".join(campos)
    except (OSError, subprocess.SubprocessError):
        return ""


def lista_teste() -> list[dict]:
    with open(RAIZ / "configs" / "conjunto_teste.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", required=True, choices=["yolov8n", "ssd_mobilenet_v1", "efficientdet_lite0"])
    ap.add_argument("--precisao", required=True, choices=["fp32", "int8"])
    ap.add_argument("--res", required=True, type=int, choices=[320, 480, 640])
    ap.add_argument("--perfil", default="rpi4b", help="perfil de configs/profiles.yaml (só registrado)")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--ambiente", default="emulado (QEMU)",
                    help="descrição registrada no manifesto, ex.: \"ARM64 nativo (Oracle A1, Neoverse-N1)\"")
    ap.add_argument("--quadros", type=int, default=None, help="limita o número de quadros (teste curto)")
    ap.add_argument("--saida", type=Path, default=RESULTS / "e5" / "borda")
    args = ap.parse_args()

    import numpy as np
    import psutil

    amostra = ler_yaml("scenarios.yaml")["amostragem"]
    aquec = amostra["aquecimento_descartado"]
    teste = lista_teste()[: args.quadros or amostra["quadros_por_combinacao"]]
    nome = f"{args.modelo}_{args.precisao}_{args.res}"
    pasta = args.saida / nome
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "COMPLETO").unlink(missing_ok=True)

    arq_modelo = MODELS / f"{args.modelo}_{args.precisao}_{resolucao_entrada(args.modelo, args.res)}.tflite"
    print(f"== {nome}: carregando {len(teste)} quadros", flush=True)
    quadros = [quadro_da_fonte(DATA / "teste_coco" / "imagens" / t["arquivo"], args.res) for t in teste]
    det = Detector(arq_modelo, args.modelo, num_threads=args.threads)
    proc = psutil.Process(os.getpid())

    inicio = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    linhas, deteccoes = [], {}
    for i, (t, q) in enumerate(zip(teste, quadros)):
        cpu0, w0 = resource.getrusage(resource.RUSAGE_SELF), time.perf_counter()
        a = time.perf_counter()
        x = det.preprocessar(q)
        b = time.perf_counter()
        y = det.inferir(x)
        c = time.perf_counter()
        d_ = det.posprocessar(y)
        e = time.perf_counter()
        cpu1 = resource.getrusage(resource.RUSAGE_SELF)
        cpu_pct = 100.0 * ((cpu1.ru_utime + cpu1.ru_stime) - (cpu0.ru_utime + cpu0.ru_stime)) / max(e - w0, 1e-9)
        deteccoes[t["image_id"]] = np.round(d_, 5).tolist()
        linhas.append({
            "frame_idx": i, "image_id": t["image_id"], "aquecimento": i < aquec,
            "t_pre_ms": round((b - a) * 1000, 3), "t_infer_ms": round((c - b) * 1000, 3),
            "t_post_ms": round((e - c) * 1000, 3), "t_e2e_ms": round((e - a) * 1000, 3),
            "cpu_pct": round(cpu_pct, 1), "rss_mb": round(proc.memory_info().rss / 2**20, 1),
            "deteccoes": len(d_),
        })
        if i % 25 == 0:
            print(f"  quadro {i}: e2e {linhas[-1]['t_e2e_ms']:.0f} ms ({args.ambiente})", flush=True)

    with open(pasta / "quadros.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    (pasta / "deteccoes.json").write_text(json.dumps(deteccoes), encoding="utf-8")
    manifesto = {
        "combinacao": nome, "modelo": args.modelo, "precisao": args.precisao, "resolucao_fonte": args.res,
        "arquivo_modelo": arq_modelo.name, "sha256_modelo": sha256(arq_modelo),
        "resolucao_entrada": det.res_entrada, "quadros": len(linhas), "aquecimento": aquec,
        "perfil": args.perfil, "threads": args.threads, "inicio_utc": inicio,
        "fim_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "arquitetura": platform.machine(), "python": platform.python_version(),
        "versoes": {p: version(p) for p in ("ai-edge-litert", "numpy", "pillow", "psutil")},
        "qemu_cpu": os.environ.get("QEMU_CPU", "(padrão do emulador)"),
        "cpus_visiveis": os.cpu_count(), "nms": {"iou": LIMIAR_IOU_NMS, "pontuacao_min": LIMIAR_PONTUACAO,
                                                "max_deteccoes": MAX_DETECCOES},
        "ambiente": args.ambiente, "kernel": platform.release(), "cpu": descrever_cpu(),
    }
    (pasta / "manifesto.json").write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")
    (pasta / "COMPLETO").write_text(manifesto["fim_utc"], encoding="utf-8")
    print(f"== {nome} concluída", flush=True)


if __name__ == "__main__":
    main()
