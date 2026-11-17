"""E5, borda: roda as 18 combinações, uma por processo novo, INT8 primeiro, e é retomável.

O que faz: para cada combinação modelo x precisão x resolução de configs/scenarios.yaml, chama
src/bench/medir_borda.py em um processo Python novo. Combinação com o marcador COMPLETO não roda
de novo; se o contêiner cair, rodar outra vez continua de onde parou. Grava um log de andamento.

O que gera: results/e5/borda/<combinação>/ (veja medir_borda.py) e results/e5/borda/andamento.log
Roda no contêiner borda-arm64. Uso: python src/bench/coletar_borda.py [--perfil rpi4b] [--precisao int8] [--quadros N]
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum import RESULTS, ler_yaml  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--perfil", default="rpi4b")
    ap.add_argument("--quadros", type=int, default=None, help="teste curto: limita os quadros")
    ap.add_argument("--precisao", choices=["fp32", "int8"], default=None, help="roda só uma precisão")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--ambiente", default="emulado (QEMU)", help="descrição registrada no manifesto")
    ap.add_argument("--saida", type=Path, default=RESULTS / "e5" / "borda")
    args = ap.parse_args()

    f = ler_yaml("scenarios.yaml")["fatores"]
    combos = [(m, p, r) for p in sorted(f["precisao"], key=lambda p: p != "int8")  # INT8 primeiro
              for m in f["modelo"] for r in f["resolucao"]]
    if args.precisao:
        combos = [c for c in combos if c[1] == args.precisao]
    args.saida.mkdir(parents=True, exist_ok=True)
    log = args.saida / "andamento.log"
    for m, p, r in combos:
        pasta = args.saida / f"{m}_{p}_{r}"
        if (pasta / "COMPLETO").exists():
            print(f"já concluída: {pasta.name}", flush=True)
            continue
        agora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        with open(log, "a", encoding="utf-8") as lg:
            lg.write(f"{agora} início {pasta.name}\n")
        cmd = [sys.executable, str(Path(__file__).parent / "medir_borda.py"), "--modelo", m, "--precisao", p,
               "--res", str(r), "--perfil", args.perfil, "--saida", str(args.saida),
               "--threads", str(args.threads), "--ambiente", args.ambiente]
        if args.quadros:
            cmd += ["--quadros", str(args.quadros)]
        rc = subprocess.run(cmd).returncode
        agora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        with open(log, "a", encoding="utf-8") as lg:
            lg.write(f"{agora} fim {pasta.name} código {rc}\n")
        if rc != 0:
            raise SystemExit(f"Falhou: {pasta.name} (código {rc})")
    print("Borda: todas as combinações concluídas.", flush=True)


if __name__ == "__main__":
    main()
